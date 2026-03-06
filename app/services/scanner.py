from typing import Dict, Any, List, Set, Tuple, Optional
import hashlib
from datetime import datetime
import json
import logging
from app.services.detectors import PDNDetectors
from app.services.opensearch_client import OpenSearchClient
from app.models.pdn import PDNPattern, PDNFinding
from app.models.settings import RegexRule, IndexKeyExclusion
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

    def _calculate_cache_key(self, index_pattern: str, field_path: str, pdn_type: str, match_value: str) -> str:
        """
        Вычисление cache_key (SHA256).
        Для группировки используем ключ = SHA256(index_pattern + field_path + pdn_type)
        (Чтобы все телефоны в одном поле индекса падали в 1 cache_key)
        """
        raw = f"{index_pattern}|{field_path}|{pdn_type}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def _get_active_rules(self, db: AsyncSession) -> tuple[List[RegexRule], List[IndexKeyExclusion]]:
        # Получаем все активные правила (регулярки, глобальные исключения ключей, и т.д.)
        result_rules = await db.execute(select(RegexRule).filter(RegexRule.is_active == True))
        global_rules = result_rules.scalars().all()

        result_exclusions = await db.execute(select(IndexKeyExclusion).filter(IndexKeyExclusion.is_active == True))
        index_exclusions = result_exclusions.scalars().all()
        
        return global_rules, index_exclusions

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
        global_rules, index_exclusions = await self._get_active_rules(db)
        
        # Индексные исключения для текущего индекса
        current_index_exclusions = [e for e in index_exclusions if e.index_pattern == index_pattern]

        doc_generator = self.os_client.search_after_generator(index_pattern=index_pattern, max_docs=max_docs)
        
        findings_count = 0
        patterns_to_update = set()

        async for doc in doc_generator:
            source = doc.get("_source", {})
            doc_id = doc.get("_id")
            _index = doc.get("_index")
            
            flat_items = self._traverse(source)
            for path, val in flat_items:
                # 1. Сначала фильтруем по index_exclusions
                # Если путь есть в полных исключениях индекса для конкретного типа (или всех), пропустим
                skip_path = False
                for exc in current_index_exclusions:
                    if exc.key_path == path and exc.pdn_type in ('all', 'any'):
                        skip_path = True
                        break
                if skip_path:
                    continue

                # 2. Вызываем детектор. Для каждого найденного ПДн он уже проверит глобальные исключения путей и префиксов/суффиксов.
                detector_matches = self.detectors.detect(val, path, global_rules)
                
                # Применяем фильтр по index_type 
                for match in detector_matches:
                    pdn_type = match['type']
                    match_val = match['value']

                    # Второе: исключили ли мы этот ПДн тип для этого пути индекса?
                    if any(exc.key_path == path and exc.pdn_type == pdn_type for exc in current_index_exclusions):
                        continue

                    cache_key = self._calculate_cache_key(index_pattern, path, pdn_type, match_val)

                    # 3. Работа с БД (PDNPattern & PDNFinding)
                    pattern_result = await db.execute(select(PDNPattern).filter(PDNPattern.cache_key == cache_key))
                    pattern = pattern_result.scalars().first()

                    if not pattern:
                        pattern = PDNPattern(
                            cache_key=cache_key,
                            index_pattern=index_pattern,
                            field_path=path,
                            pdn_type=pdn_type,
                            context_type="structured_key", # TODO: enhance heuristic if needed
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

                    # Добавляем finding, если паттерн "new" (ограничиваем, скажем, чтоб не лопнула база)
                    # Либо если мы обновляем (update examples)
                    if pattern.status == "new":
                        finding = PDNFinding(
                            cache_key=cache_key,
                            doc_id=doc_id,
                            index_pattern=_index,
                            raw_value=match_val,
                            field_path=path,
                            full_document=source
                        )
                        db.add(finding)

        # Теги и коммиты
        if not is_global and scan_type_tag == 'S':
             # Очистить теги 'S' для старых паттернов этого индекса
             # Сначала получаем все паттерны индекса
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
        # Пока примем, что indices - список всех актуальных паттернов, которые нужно сканировать.
        if not indices:
            indices = ["*"]

        total_findings = 0
        for index_pattern in indices:
            log = ScannerLog(scan_type="global", target_index=index_pattern, status="running")
            db.add(log)
            await db.commit()
            
            try:
                # В глобальном режиме сканируем, вешаем тег 'G'
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
