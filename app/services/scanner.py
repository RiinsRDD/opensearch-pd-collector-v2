from typing import Dict, Any, List, Set, Tuple, Optional
import hashlib
from datetime import datetime
import json
import logging
import fnmatch
from app.services.detectors import PDNDetectors
from app.services.opensearch_client import OpenSearchClient
from app.models.pdn import PDNPattern, PDNFinding
from app.models.settings import RegexRule, IndexKeyExclusion
from app.models.scan_field_config import ScanFieldConfig
from app.models.tags import Tag, PatternTagLink
from app.models.logs import ScannerLog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

logger = logging.getLogger(__name__)


class ScannerService:
    def __init__(self, opensearch_client: OpenSearchClient):
        self.os_client = opensearch_client
        self.detectors = PDNDetectors()

    def _traverse(self, obj: Any, path: str = "") -> List[Tuple[str, str]]:
        """
        Рекурсивный обход JSON словаря. Возвращает список кортежей (path, value) только для строк и чисел.
        """
        results = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                results.extend(self._traverse(v, new_path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                results.extend(self._traverse(item, new_path))
        elif isinstance(obj, (str, int, float)):
            results.append((path, str(obj)))
        return results

    def _calculate_cache_key(
        self,
        index_pattern: str,
        field_path: str,
        pdn_type: str,
        context_type: str,
        key_hint: Optional[str],
        extra_fields_values: Dict[str, str],
    ) -> str:
        """
        Вычисление cache_key (SHA256).
        
        Формула:
        structured_key: SHA256(index_pattern + field_path + pdn_type + key_hint + extra_field_vals...)
        free_text:      SHA256(index_pattern + field_path + pdn_type + "free_text" + extra_field_vals...)
        ambiguous:      SHA256(index_pattern + field_path + pdn_type + "ambiguous" + extra_field_vals...)
        """
        if context_type == "structured_key":
            context_part = key_hint or ""
        else:
            context_part = context_type  # "free_text" or "ambiguous"

        # Sort extra fields by key for deterministic hashing
        extra_parts = "|".join(
            extra_fields_values.get(k, "")
            for k in sorted(extra_fields_values.keys())
        )
        
        raw = f"{index_pattern}|{field_path}|{pdn_type}|{context_part}|{extra_parts}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _extract_extra_fields(
        self, source: Dict[str, Any], scan_field_configs: List[ScanFieldConfig], index_pattern: str
    ) -> Dict[str, str]:
        """
        Extract values of additional fields from the document source.
        Returns dict like {"NameOfMicroService": "auth-svc", "kubernetes.container.name": "api-gw"}.
        """
        result = {}
        for config in scan_field_configs:
            # Check if this config applies to this index
            if config.index_pattern != "*" and not fnmatch.fnmatch(index_pattern, config.index_pattern):
                continue
            
            # Navigate dot-notation path in the source document
            value = source
            for part in config.field_path.split("."):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            
            result[config.field_path] = str(value) if value is not None else ""
        
        return result

    async def _get_active_rules(self, db: AsyncSession) -> tuple:
        # Получаем все активные правила (регулярки, глобальные исключения ключей, и т.д.)
        result_rules = await db.execute(select(RegexRule).filter(RegexRule.is_active == True))
        global_rules = result_rules.scalars().all()

        result_exclusions = await db.execute(select(IndexKeyExclusion).filter(IndexKeyExclusion.is_active == True))
        index_exclusions = result_exclusions.scalars().all()
        
        # Load scan field configs
        result_configs = await db.execute(select(ScanFieldConfig).filter(ScanFieldConfig.is_active == True))
        scan_field_configs = result_configs.scalars().all()
        
        return global_rules, index_exclusions, scan_field_configs

    async def _apply_tag(self, db: AsyncSession, cache_key: str, tag_code: str):
        # Находим Tag по имени
        tag_result = await db.execute(select(Tag).filter(Tag.name == tag_code))
        tag = tag_result.scalars().first()
        if not tag:
            # Если тега нет, создадим (mock behavior for safety)
            tag = Tag(name=tag_code, color="#000000", description=f"Auto-generated tag {tag_code}")
            db.add(tag)
            await db.flush()
            
        # Проверим, есть ли связь
        link_result = await db.execute(
            select(PatternTagLink)
            .filter(PatternTagLink.pattern_cache_key == cache_key, PatternTagLink.tag_id == tag.id)
        )
        existing_link = link_result.scalars().first()
        if not existing_link:
            new_link = PatternTagLink(pattern_cache_key=cache_key, tag_id=tag.id)
            db.add(new_link)

    async def _clear_single_scan_tags(self, db: AsyncSession, cache_keys: List[str]):
        """Очищаем тег 'S' для списка паттернов"""
        if not cache_keys:
            return
        tag_result = await db.execute(select(Tag).filter(Tag.name == 'S'))
        tag = tag_result.scalars().first()
        if tag:
            await db.execute(
                delete(PatternTagLink)
                .where(PatternTagLink.tag_id == tag.id)
                .where(PatternTagLink.pattern_cache_key.in_(cache_keys))
            )

    async def scan_index(self, db: AsyncSession, index_pattern: str, max_docs: int = 1000, is_global: bool = False, scan_type_tag: str = 'S') -> int:
        """
        Осуществляет сканирование OpenSearch индекса(ов) по маске.
        """
        global_rules, index_exclusions, scan_field_configs = await self._get_active_rules(db)
        
        # Индексные исключения для текущего индекса
        current_index_exclusions = [e for e in index_exclusions if e.index_pattern == index_pattern]

        doc_generator = self.os_client.search_after_generator(index_pattern=index_pattern, max_docs=max_docs)
        
        findings_count = 0
        patterns_to_update = set()

        async for doc in doc_generator:
            source = doc.get("_source", {})
            doc_id = doc.get("_id")
            _index = doc.get("_index")
            
            # Extract extra fields from the document
            extra_fields_values = self._extract_extra_fields(source, scan_field_configs, index_pattern)
            
            flat_items = self._traverse(source)
            for path, val in flat_items:
                # 1. Сначала фильтруем по index_exclusions
                skip_path = False
                for exc in current_index_exclusions:
                    if exc.key_path == path and exc.pdn_type in ('all', 'any'):
                        skip_path = True
                        break
                if skip_path:
                    continue

                # Determine if this field is a free-text field
                is_free_text = PDNDetectors.is_free_text_field(path)

                # 2. Вызываем детектор с is_free_text flag
                detector_matches = self.detectors.detect(val, path, global_rules, is_free_text=is_free_text)
                
                # Применяем фильтр по index_type 
                for match in detector_matches:
                    pdn_type = match['type']
                    match_val = match['value']
                    context_type = match['context_type']
                    key_hint = match.get('key_hint')
                    prefix_raw = match.get('prefix_raw')
                    suffix_raw = match.get('suffix_raw')

                    # Исключили ли мы этот ПДн тип для этого пути индекса?
                    if any(exc.key_path == path and exc.pdn_type == pdn_type for exc in current_index_exclusions):
                        continue

                    cache_key = self._calculate_cache_key(
                        index_pattern, path, pdn_type,
                        context_type, key_hint, extra_fields_values
                    )

                    # 3. Работа с БД (PDNPattern & PDNFinding)
                    pattern_result = await db.execute(select(PDNPattern).filter(PDNPattern.cache_key == cache_key))
                    pattern = pattern_result.scalars().first()

                    if not pattern:
                        pattern = PDNPattern(
                            cache_key=cache_key,
                            index_pattern=index_pattern,
                            field_path=path,
                            pdn_type=pdn_type,
                            context_type=context_type,
                            key_hint=key_hint,
                            extra_fields=extra_fields_values if extra_fields_values else None,
                            hit_count=1,
                            status="new"
                        )
                        db.add(pattern)
                        findings_count += 1
                    else:
                        pattern.hit_count += 1
                        pattern.last_seen = datetime.utcnow()
                    
                    # Привязываем тег к паттерну
                    patterns_to_update.add(cache_key)

                    # Добавляем finding с prefix/suffix context
                    if pattern.status == "new":
                        finding = PDNFinding(
                            cache_key=cache_key,
                            doc_id=doc_id,
                            index_pattern=_index,
                            raw_value=match_val,
                            field_path=path,
                            prefix_raw=prefix_raw,
                            suffix_raw=suffix_raw,
                            full_document=source
                        )
                        db.add(finding)

        # Теги и коммиты
        if not is_global and scan_type_tag == 'S':
             # Очистить теги 'S' для старых паттернов этого индекса
             result_all_idx_patterns = await db.execute(select(PDNPattern.cache_key).filter(PDNPattern.index_pattern == index_pattern))
             all_cache_keys_for_index = result_all_idx_patterns.scalars().all()
             await self._clear_single_scan_tags(db, all_cache_keys_for_index)

        for cache_key in patterns_to_update:
            await self._apply_tag(db, cache_key, scan_type_tag)
            
        await db.commit()
        return findings_count

    async def run_global_scan(self, db: AsyncSession, hours: int = 1, indices: List[str] = None):
        """
        Глобальное сканирование.
        """
        if not indices:
            indices = ["*"]

        total_findings = 0
        for index_pattern in indices:
            log = ScannerLog(scan_type="global", target_index=index_pattern, status="running")
            db.add(log)
            await db.commit()
            
            try:
                findings = await self.scan_index(db, index_pattern, max_docs=1000, is_global=True, scan_type_tag='G')
                total_findings += findings
                
                log.status = "success"
                log.findings_count = findings
                log.completed_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error scanning index {index_pattern}: {e}")
                log.status = "failed"
                log.error_message = str(e)
                log.completed_at = datetime.utcnow()
            
            finally:
                db.add(log)
                await db.commit()
                
        return total_findings
