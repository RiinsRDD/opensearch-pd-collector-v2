from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from pydantic import BaseModel
from app.db.session import get_db
from app.models.settings import SystemSetting, StatusSetting, IndexKeyExclusion, RegexRule
from app.models.indices import IndexOwner
from app.models.pdn import PDNPattern
from app.models.tags import Tag, PatternTagLink

router = APIRouter()

# ==================== Константы ====================

SYSTEM_PDN_TYPES = {'phone', 'email', 'card', 'fio'}

# ==================== Pydantic Схемы ====================

class GlobalExclusionCreate(BaseModel):
    pdn_type: str
    rule_type: str
    value: str

class IndexExclusionCreate(BaseModel):
    index_pattern: str
    pdn_type: str
    key_path: str

class PdnTypeCreate(BaseModel):
    pdn_type: str
    regex_value: str

class PdnTypeUpdate(BaseModel):
    regex_value: str

class GlobalSettingsResponse(BaseModel):
    pdn_flags: Dict[str, bool] = {"phone": True, "email": True, "card": True, "fio": False}
    examples_count: int = 5
    scan_interval_hours: int = 24
    exclude_index_patterns: List[str] = []
    exclude_index_regexes: List[str] = []
    include_index_regexes: List[str] = []
    mail_service_names: List[str] = [
        "gmail", "google", "googlemail", "yandex", "ya", "mail", "bk", "list", "inbox",
        "outlook", "hotmail", "live", "msn", "yahoo", "aol", "icloud", "me", "mac",
        "proton", "protonmail", "zoho", "gmx", "rambler", "lenta", "autorambler", 
        "myrambler", "fastmail", "tutanota", "seznam", "qq", "naver", "hanmail",
        "orange", "wanadoo", "web", "mailbox", "posteo", "laposte", "email", "e-mail"
    ]
    unknown_mail_service_parts: List[str] = []
    card_bank_bins_4: List[str] = [
        "2203", "4054", "4180", "4195", "4556", "4732", "5115", 
        "5130", "5452", "5519", "5545", "5594", "5597"
    ]
    invalid_def_codes: List[str] = [
        "941", "942", "943", "944", "945", "946", "947", "948", "949", 
        "972", "973", "974", "975", "976", "940", "996"
    ]
    surn_ends_cis: List[str] = [
        'ович', 'евич', 'овна', 'евна', 'ична', 'енко', 'янко', 
        'ский', 'ская', 'цкий', 'цкая', 'швили', 'дзе', 'ани',
        'янц', 'янс', 'уни', 'ова', 'ева', 'ина', 'ых', 'их', 
        'инич', 'ovich', 'evich', 'ovna', 'evna', 'ichna',
        'enko', 'skiy', 'skaya', 'tskiy', 'shvili', 'adze'
    ]
    surn_ends_world: List[str] = [
        'son', 'sen', 'sh', 'stein', 'berg', 'man', 'mann', 'er', 'ez', 'es', 
        'ic', 'ich', 'is', 'as', 'skas', 'ska', 'itis', 'en', 'eau', 'ard'
    ]
    patron_ends: List[str] = [
        'ович', 'евич', 'ич', 'овна', 'евна', 'ична', 'оглы', 'кызы',
        'ovich', 'evich', 'ovna', 'evna', 'ich', 'ogly', 'kyzy'
    ]
    fio_special_markers: List[str] = [
        'оглы', 'кызы', 'ogly', 'kyzy', 'ибн', 'ibn', 'фон', 'von', 'ван', 'van', 'де', 'de'
    ]

    # Jira Settings
    jira_base_url: str = "https://jira.bcs.ru"
    jira_project_key: str = "EIB"
    jira_issue_type: str = "15400"
    jira_priority: str = "4"
    jira_components: str = "47920"
    jira_labels: str = "dtsz_auto_pd_discovery"
    jira_dib_service: str = "CMDB-859449"
    jira_epic_link: str = "EIB-15679"
    jira_cfo: str = "CMDB-3968"
    jira_kipd_type: str = "68857"
    jira_task_source: str = "28834"
    jira_action_group: str = "28819"
    jira_action_type: str = "28830"
    jira_process: str = "CMDB-2760490"
    jira_criticality_level: str = "52414"
    jira_location_type: str = "55677"
    jira_it_system: str = "CMDB-1358427"
    jira_exploit_poc: str = "68865"
    jira_cvss_score: int = 0
    jira_column_id: str = "43720"
    jira_risk_text: str = "Утечка критичных данных"
    jira_work_description: str = "Исключить попадание открытых персональных данных в индексы OpenSearch. Настроить фильтрацию или применение одностороннего хеширования/маскирования для полей, содержащих конфиденциальную информацию."

# ==================== Глобальные параметры ====================

@router.get("/global", response_model=GlobalSettingsResponse)
async def get_global_settings(db: AsyncSession = Depends(get_db)):
    """Получение глобальных настроек (флаги, интервал, лимиты, системные правила)"""
    # 1. Запрашиваем SystemSettings
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    
    pdn_flags = {}
    settings_dict = {}
    for s in settings:
        if s.value.lower() == 'true':
            val = True
        elif s.value.lower() == 'false':
            val = False
        elif s.value.isdigit():
            val = int(s.value)
        else:
            val = s.value
            
        if s.key.startswith('is_'):
            pdn_type = s.key[3:]
            pdn_flags[pdn_type] = val
        else:
            settings_dict[s.key] = val

    # 2. Запрашиваем правила
    rules_res = await db.execute(select(RegexRule).filter(
        RegexRule.rule_type.in_([
            'regex', 'exclude_index_pattern', 'exclude_index_regex', 'include_index_regex',
            'mail_service_name', 'unknown_mail_service_part', 'card_bank_bin_4',
            'invalid_def_code', 'surn_end_cis', 'surn_end_world', 'patron_end', 'fio_special_marker'
        ])
    ))
    rules = rules_res.scalars().all()
    
    # Сбор всех типов ПДн (из regex правил)
    regex_types = {r.pdn_type for r in rules if r.rule_type == 'regex'}
    # Добавляем системные типы, даже если их почему-то нет
    all_types = regex_types.union(SYSTEM_PDN_TYPES)
    
    # Применяем значения по умолчанию для флагов, если они не заданы в БД
    for pt in all_types:
        if pt not in pdn_flags:
            pdn_flags[pt] = True if pt in SYSTEM_PDN_TYPES else False

    exclude_patterns = [r.value for r in rules if r.rule_type == 'exclude_index_pattern']
    exclude_regexes = [r.value for r in rules if r.rule_type == 'exclude_index_regex']
    include_regexes = [r.value for r in rules if r.rule_type == 'include_index_regex']

    # New fields
    mail_service_names = [r.value for r in rules if r.rule_type == 'mail_service_name']
    unknown_mail_service_parts = [r.value for r in rules if r.rule_type == 'unknown_mail_service_part']
    card_bank_bins_4 = [r.value for r in rules if r.rule_type == 'card_bank_bin_4']
    invalid_def_codes = [r.value for r in rules if r.rule_type == 'invalid_def_code']
    surn_ends_cis = [r.value for r in rules if r.rule_type == 'surn_end_cis']
    surn_ends_world = [r.value for r in rules if r.rule_type == 'surn_end_world']
    patron_ends = [r.value for r in rules if r.rule_type == 'patron_end']
    fio_special_markers = [r.value for r in rules if r.rule_type == 'fio_special_marker']

    default_resp = GlobalSettingsResponse()

    return GlobalSettingsResponse(
        pdn_flags=pdn_flags,
        examples_count=settings_dict.get('examples_count', 5),
        scan_interval_hours=settings_dict.get('scan_interval_hours', 24),
        exclude_index_patterns=exclude_patterns if exclude_patterns else default_resp.exclude_index_patterns,
        exclude_index_regexes=exclude_regexes if exclude_regexes else default_resp.exclude_index_regexes,
        include_index_regexes=include_regexes if include_regexes else default_resp.include_index_regexes,
        mail_service_names=mail_service_names if mail_service_names else default_resp.mail_service_names,
        unknown_mail_service_parts=unknown_mail_service_parts if unknown_mail_service_parts else default_resp.unknown_mail_service_parts,
        card_bank_bins_4=card_bank_bins_4 if card_bank_bins_4 else default_resp.card_bank_bins_4,
        invalid_def_codes=invalid_def_codes if invalid_def_codes else default_resp.invalid_def_codes,
        surn_ends_cis=surn_ends_cis if surn_ends_cis else default_resp.surn_ends_cis,
        surn_ends_world=surn_ends_world if surn_ends_world else default_resp.surn_ends_world,
        patron_ends=patron_ends if patron_ends else default_resp.patron_ends,
        fio_special_markers=fio_special_markers if fio_special_markers else default_resp.fio_special_markers,
        
        # Jira
        jira_base_url=settings_dict.get('jira_base_url', default_resp.jira_base_url),
        jira_project_key=settings_dict.get('jira_project_key', default_resp.jira_project_key),
        jira_issue_type=settings_dict.get('jira_issue_type', default_resp.jira_issue_type),
        jira_priority=settings_dict.get('jira_priority', default_resp.jira_priority),
        jira_components=settings_dict.get('jira_components', default_resp.jira_components),
        jira_labels=settings_dict.get('jira_labels', default_resp.jira_labels),
        jira_dib_service=settings_dict.get('jira_dib_service', default_resp.jira_dib_service),
        jira_epic_link=settings_dict.get('jira_epic_link', default_resp.jira_epic_link),
        jira_cfo=settings_dict.get('jira_cfo', default_resp.jira_cfo),
        jira_kipd_type=settings_dict.get('jira_kipd_type', default_resp.jira_kipd_type),
        jira_task_source=settings_dict.get('jira_task_source', default_resp.jira_task_source),
        jira_action_group=settings_dict.get('jira_action_group', default_resp.jira_action_group),
        jira_action_type=settings_dict.get('jira_action_type', default_resp.jira_action_type),
        jira_process=settings_dict.get('jira_process', default_resp.jira_process),
        jira_criticality_level=settings_dict.get('jira_criticality_level', default_resp.jira_criticality_level),
        jira_location_type=settings_dict.get('jira_location_type', default_resp.jira_location_type),
        jira_it_system=settings_dict.get('jira_it_system', default_resp.jira_it_system),
        jira_exploit_poc=settings_dict.get('jira_exploit_poc', default_resp.jira_exploit_poc),
        jira_cvss_score=int(settings_dict.get('jira_cvss_score', default_resp.jira_cvss_score)),
        jira_column_id=settings_dict.get('jira_column_id', default_resp.jira_column_id),
        jira_risk_text=settings_dict.get('jira_risk_text', default_resp.jira_risk_text),
        jira_work_description=settings_dict.get('jira_work_description', default_resp.jira_work_description)
    )

@router.post("/global")
async def update_global_settings(payload: GlobalSettingsResponse, db: AsyncSession = Depends(get_db)):
    """Обновление глобальных настроек и системных правил для индексов"""
    # 1. Обновление SystemSettings
    settings_map = {
        'examples_count': str(payload.examples_count),
        'scan_interval_hours': str(payload.scan_interval_hours),
        'jira_base_url': payload.jira_base_url,
        'jira_project_key': payload.jira_project_key,
        'jira_issue_type': payload.jira_issue_type,
        'jira_priority': payload.jira_priority,
        'jira_components': payload.jira_components,
        'jira_labels': payload.jira_labels,
        'jira_dib_service': payload.jira_dib_service,
        'jira_epic_link': payload.jira_epic_link,
        'jira_cfo': payload.jira_cfo,
        'jira_kipd_type': payload.jira_kipd_type,
        'jira_task_source': payload.jira_task_source,
        'jira_action_group': payload.jira_action_group,
        'jira_action_type': payload.jira_action_type,
        'jira_process': payload.jira_process,
        'jira_criticality_level': payload.jira_criticality_level,
        'jira_location_type': payload.jira_location_type,
        'jira_it_system': payload.jira_it_system,
        'jira_exploit_poc': payload.jira_exploit_poc,
        'jira_cvss_score': str(payload.jira_cvss_score),
        'jira_column_id': payload.jira_column_id,
        'jira_risk_text': payload.jira_risk_text,
        'jira_work_description': payload.jira_work_description
    }
    for pdn_type, is_active in payload.pdn_flags.items():
        settings_map[f'is_{pdn_type}'] = str(is_active).lower()

    res_settings = await db.execute(select(SystemSetting))
    existing_settings = {s.key: s for s in res_settings.scalars().all()}

    for key, val in settings_map.items():
        if key in existing_settings:
            existing_settings[key].value = val
        else:
            db.add(SystemSetting(key=key, value=val))

    # 2. Обновление списочных правил (системные и другие)
    await db.execute(delete(RegexRule).filter(
        RegexRule.rule_type.in_([
            'exclude_index_pattern', 'exclude_index_regex', 'include_index_regex',
            'mail_service_name', 'card_bank_bin_4',
            'invalid_def_code', 'surn_end_cis', 'surn_end_world', 'patron_end', 'fio_special_marker'
        ])
    ))
    
    rules_to_add = []
    # Индексы (system)
    for pat in payload.exclude_index_patterns:
        rules_to_add.append(RegexRule(pdn_type='system', rule_type='exclude_index_pattern', value=pat))
    for reg in payload.exclude_index_regexes:
        rules_to_add.append(RegexRule(pdn_type='system', rule_type='exclude_index_regex', value=reg))
    for reg in payload.include_index_regexes:
        rules_to_add.append(RegexRule(pdn_type='system', rule_type='include_index_regex', value=reg))

    # Email
    for item in payload.mail_service_names:
        rules_to_add.append(RegexRule(pdn_type='email', rule_type='mail_service_name', value=item))
    # (unknown_mail_service_parts is read-only for settings updates, managed by scanner)
        
    # Card
    for item in payload.card_bank_bins_4:
        rules_to_add.append(RegexRule(pdn_type='card', rule_type='card_bank_bin_4', value=item))
        
    # Phone
    for item in payload.invalid_def_codes:
        rules_to_add.append(RegexRule(pdn_type='phone', rule_type='invalid_def_code', value=item))
        
    # FIO
    for item in payload.surn_ends_cis:
        rules_to_add.append(RegexRule(pdn_type='fio', rule_type='surn_end_cis', value=item))
    for item in payload.surn_ends_world:
        rules_to_add.append(RegexRule(pdn_type='fio', rule_type='surn_end_world', value=item))
    for item in payload.patron_ends:
        rules_to_add.append(RegexRule(pdn_type='fio', rule_type='patron_end', value=item))
    for item in payload.fio_special_markers:
        rules_to_add.append(RegexRule(pdn_type='fio', rule_type='fio_special_marker', value=item))
    
    if rules_to_add:
        db.add_all(rules_to_add)

    await db.commit()
    return {"message": "Global settings and system rules updated"}

# ==================== Управление Регулярками ПДн (PDN Types) ====================

@router.get("/pdn-types")
async def get_pdn_types(db: AsyncSession = Depends(get_db)):
    """Получение всех типов регулярок ПДн"""
    result = await db.execute(select(RegexRule).filter(RegexRule.rule_type == 'regex'))
    rules = result.scalars().all()
    
    # Добавляем поле is_system
    response = []
    for r in rules:
        response.append({
            "id": r.id,
            "pdn_type": r.pdn_type,
            "value": r.value,
            "is_active": r.is_active,
            "is_system": r.pdn_type in SYSTEM_PDN_TYPES
        })
    return response

@router.get("/pdn-types/list")
async def get_pdn_types_list(db: AsyncSession = Depends(get_db)):
    """Получение только списка уникальных pdn_type"""
    result = await db.execute(select(RegexRule.pdn_type).filter(RegexRule.rule_type == 'regex').distinct())
    types = result.scalars().all()
    return sorted(list(set(types).union(SYSTEM_PDN_TYPES)))

@router.post("/pdn-types")
async def add_pdn_type(payload: PdnTypeCreate, db: AsyncSession = Depends(get_db)):
    """Добавить новый тип ПДн с регулярным выражением"""
    pdn_type = payload.pdn_type.strip().lower()
    if not pdn_type:
        raise HTTPException(status_code=400, detail="pdn_type cannot be empty")
        
    # Проверка существования
    result = await db.execute(select(RegexRule).filter(
        RegexRule.rule_type == 'regex',
        RegexRule.pdn_type == pdn_type
    ))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail=f"Pattern for type '{pdn_type}' already exists")
        
    new_rule = RegexRule(
        pdn_type=pdn_type,
        rule_type='regex',
        value=payload.regex_value,
        is_active=True
    )
    db.add(new_rule)
    
    # Добавляем флаг в настройки, если его нет
    setting_key = f"is_{pdn_type}"
    res_set = await db.execute(select(SystemSetting).filter(SystemSetting.key == setting_key))
    if not res_set.scalars().first():
        db.add(SystemSetting(key=setting_key, value="true"))
        
    await db.commit()
    await db.refresh(new_rule)
    
    return {
        "message": "PDN regex pattern added",
        "data": {
            "id": new_rule.id,
            "pdn_type": new_rule.pdn_type,
            "value": new_rule.value,
            "is_active": new_rule.is_active,
            "is_system": new_rule.pdn_type in SYSTEM_PDN_TYPES
        }
    }

@router.put("/pdn-types/{rule_id}")
async def update_pdn_type(rule_id: int, payload: PdnTypeUpdate, db: AsyncSession = Depends(get_db)):
    """Обновление регулярного выражения для существующего типа"""
    result = await db.execute(select(RegexRule).filter(RegexRule.id == rule_id, RegexRule.rule_type == 'regex'))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Regex pattern not found")
        
    rule.value = payload.regex_value
    await db.commit()
    
    return {"message": "PDN regex pattern updated"}

@router.delete("/pdn-types/{rule_id}")
async def delete_pdn_type(rule_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удаление пользовательского типа ПДн. 
    Системные типы защищены от удаления. 
    Удаляется только regex-правило и глобальный флаг сканирования.
    Глобальные исключения сохраняются.
    """
    result = await db.execute(select(RegexRule).filter(RegexRule.id == rule_id, RegexRule.rule_type == 'regex'))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Regex pattern not found")
        
    if rule.pdn_type in SYSTEM_PDN_TYPES:
        raise HTTPException(status_code=403, detail=f"Cannot delete system PDN type: {rule.pdn_type}")
        
    pdn_type = rule.pdn_type
    
    # Удаляем только конкретное правило (regex_rule)
    await db.delete(rule)
    
    # И удаляем сам чекбокс из настроек
    await db.execute(delete(SystemSetting).filter(SystemSetting.key == f"is_{pdn_type}"))
    
    await db.commit()
    return {"message": f"PDN type '{pdn_type}' deleted successfully. Exclusions are preserved."}

# ==================== Индивидуальные настройки индексов ====================

@router.get("/indices")
async def get_index_settings():
    """Получение индивидуальных настроек индексов (исключения, владельцы)"""
    return [{"index_pattern": "bcs-frontend-logs-*", "override_global_settings": True, "is_active": False}]

@router.post("/indices")
async def update_index_settings(payload: dict):
    """Обновление или создание индивидуальной настройки индекса"""
    return {"message": "Index settings updated", "data": payload}

# ==================== Статусы ====================

@router.get("/statuses")
async def get_statuses():
    """Получение списка статусов и их цветов для UI"""
    return [
        {"id": "new", "label": "New", "color": "#ef4444"},
        {"id": "confirmed", "label": "Confirmed", "color": "#3b82f6"},
        {"id": "done", "label": "Done", "color": "#10b981"},
        {"id": "false_positive", "label": "False Positive", "color": "#eab308"},
        {"id": "unverified", "label": "Unverified", "color": "#94a3b8"}
    ]

@router.post("/statuses")
async def update_statuses(payload: List[Dict[str, str]]):
    """Обновление цветов статусов"""
    return {"message": "Statuses updated", "data": payload}

# ==================== Теги ====================

@router.delete("/tags/{tag_name}")
async def delete_tag_globally(tag_name: str, db: AsyncSession = Depends(get_db)):
    """Глобальное удаление тега из всех cache_key"""
    result = await db.execute(select(Tag).filter(Tag.name == tag_name))
    tag = result.scalars().first()
    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_name}' not found")

    # Явное удаление связей для избежания проблем с cascade на уровне БД
    await db.execute(delete(PatternTagLink).filter(PatternTagLink.tag_id == tag.id))
    
    # Удаление самого тега
    await db.delete(tag)
    await db.commit()
    
    return {"message": f"Тег {tag_name} успешно удален глобально."}

# ==================== Глобальные исключения ====================

@router.get("/exclusions/global")
async def get_global_exclusions(db: AsyncSession = Depends(get_db)):
    """
    Получение всех глобальных исключений из regex_rules.
    Возвращает записи с rule_type in (exclude_pattern, prefix_exclude, suffix_exclude, exclude_key, full_path_key.exclude).
    """
    allowed_rule_types = ['exclude_pattern', 'prefix_exclude', 'suffix_exclude', 'exclude_key', 'full_path_key.exclude']
    result = await db.execute(select(RegexRule).filter(RegexRule.rule_type.in_(allowed_rule_types)))
    rules = result.scalars().all()
    return rules

@router.post("/exclusions/global")
async def add_global_exclusion(payload: GlobalExclusionCreate, db: AsyncSession = Depends(get_db)):
    """
    Добавить глобальное исключение.
    """
    new_rule = RegexRule(
        pdn_type=payload.pdn_type,
        rule_type=payload.rule_type,
        value=payload.value,
        is_active=True
    )
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return {
        "message": "Exclusion added",
        "data": new_rule
    }

@router.delete("/exclusions/global/{exclusion_id}")
async def delete_global_exclusion(exclusion_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить глобальное исключение по ID из regex_rules"""
    result = await db.execute(select(RegexRule).filter(RegexRule.id == exclusion_id))
    rule = result.scalars().first()
    if rule:
        await db.delete(rule)
        await db.commit()
    return {"message": f"Global exclusion {exclusion_id} deleted"}

# ==================== Исключения ключей индексов ====================

@router.get("/exclusions/index")
async def get_index_exclusions(index_pattern: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    """
    Получение per-index key exclusions.
    Опциональный фильтр по index_pattern.
    """
    query = select(IndexKeyExclusion)
    if index_pattern:
        query = query.filter(IndexKeyExclusion.index_pattern == index_pattern)
    result = await db.execute(query)
    exclusions = result.scalars().all()
    return exclusions

@router.post("/exclusions/index")
async def add_index_exclusion(payload: IndexExclusionCreate, db: AsyncSession = Depends(get_db)):
    """
    Добавить per-index key exclusion.
    """
    new_exclusion = IndexKeyExclusion(
        index_pattern=payload.index_pattern,
        pdn_type=payload.pdn_type,
        key_path=payload.key_path,
        is_active=True
    )
    db.add(new_exclusion)
    await db.commit()
    await db.refresh(new_exclusion)
    return {
        "message": "Index exclusion added",
        "data": new_exclusion
    }

@router.delete("/exclusions/index/{exclusion_id}")
async def delete_index_exclusion(exclusion_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить per-index key exclusion по ID"""
    result = await db.execute(select(IndexKeyExclusion).filter(IndexKeyExclusion.id == exclusion_id))
    exclusion = result.scalars().first()
    if exclusion:
        await db.delete(exclusion)
        await db.commit()
    return {"message": f"Index exclusion {exclusion_id} deleted"}

# ==================== Список индексов для autocomplete ====================

@router.get("/exclusions/indices-list")
async def get_indices_list(db: AsyncSession = Depends(get_db)):
    """
    Получение списка всех index_pattern из БД (обновляется после каждого сканирования).
    Используется для autocomplete при создании per-index exclusion.
    """
    # Fetch distinct index patterns from PDNPattern
    result = await db.execute(select(PDNPattern.index_pattern).distinct())
    patterns = result.scalars().all()
    
    # Also fetch from IndexOwner just in case
    result_owners = await db.execute(select(IndexOwner.index_pattern).distinct())
    owner_patterns = result_owners.scalars().all()
    
    all_patterns = sorted(list(set(patterns) | set(owner_patterns)))
    
    return all_patterns
