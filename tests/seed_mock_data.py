"""Демо-данные для разработки и демонстрации UI.

Идемпотентный скрипт: при каждом запуске очищает seed-таблицы и заполняет заново
(пользователи admin/analyst/viewer апсертятся по username).

Запуск из корня репозитория (нужна доступная PostgreSQL из .env):

    python -m tests.seed_mock_data
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy import delete, select

from app.api.deps import get_password_hash
from app.db.session import async_session_maker
from app.models.indices import IndexOwner
from app.models.pdn import PDNFinding, PDNPattern
from app.models.scan_field_config import ScanFieldConfig
from app.models.settings import RegexRule, StatusSetting, SystemSetting
from app.models.tags import PatternTagLink, Tag
from app.models.tasks import JiraTask
from app.models.user import User

# Фиксированная «сегодня» для воспроизводимых timestamps (согласовано с last 7 days).
_NOW = datetime(2026, 8, 26, 18, 0, 0)

MAIL_SERVICE_NAMES = [
    "gmail", "google", "googlemail", "yandex", "ya", "mail", "bk", "list", "inbox",
    "outlook", "hotmail", "live", "msn", "yahoo", "aol", "icloud", "me", "mac",
    "proton", "protonmail", "zoho", "gmx", "rambler", "lenta", "autorambler",
    "myrambler", "fastmail", "tutanota", "seznam", "qq", "naver", "hanmail",
    "orange", "wanadoo", "web", "mailbox", "posteo", "laposte", "email", "e-mail",
    "hey", "duck", "tuta", "pm", "ukr", "iua", "meta", "bigmir", "interia",
    "libero", "virgilio", "rediff", "sina", "foxmail", "daum", "lycos",
    "comcast", "verizon", "att", "btinternet", "tonline", "freenet", "poczta",
]

CARD_BANK_BINS_4 = [
    "2203", "4054", "4180", "4195", "4556", "4732", "5115",
    "5130", "5452", "5519", "5545", "5594", "5597",
]

INVALID_DEF_CODES = [
    "941", "942", "943", "944", "945", "946", "947", "948", "949",
    "972", "973", "974", "975", "976", "940", "996",
    "950", "951", "952", "953",
]

SURN_ENDS_CIS = [
    "ович", "евич", "овна", "евна", "ична", "енко", "янко",
    "ский", "ская", "цкий", "цкая", "швили", "дзе", "ани",
    "янц", "янс", "уни", "ова", "ева", "ина", "ых", "их",
    "инич", "ovich", "evich", "ovna", "evna", "ichna",
    "enko", "skiy", "skaya", "tskiy", "shvili", "adze",
]

SURN_ENDS_WORLD = [
    "son", "sen", "sh", "stein", "berg", "man", "mann", "er", "ez", "es",
    "ic", "ich", "is", "as", "skas", "ska", "itis", "en", "eau", "ard",
]

PATRON_ENDS = [
    "ович", "евич", "ич", "овна", "евна", "ична", "оглы", "кызы",
    "ovich", "evich", "ovna", "evna", "ich", "ogly", "kyzy",
]

FIO_SPECIAL_MARKERS = [
    "оглы", "кызы", "ogly", "kyzy", "ибн", "ibn", "фон", "von", "ван", "van", "де", "de",
]

JIRA_SETTINGS = {
    "jira_base_url": "https://jira.bcs.ru",
    "jira_project_key": "EIB",
    "jira_issue_type": "15400",
    "jira_priority": "4",
    "jira_components": "47920",
    "jira_labels": "dtsz_auto_pd_discovery",
    "jira_dib_service": "CMDB-859449",
    "jira_epic_link": "EIB-15679",
    "jira_cfo": "CMDB-3968",
    "jira_kipd_type": "68857",
    "jira_task_source": "28834",
    "jira_action_group": "28819",
    "jira_action_type": "28830",
    "jira_process": "CMDB-2760490",
    "jira_criticality_level": "52414",
    "jira_location_type": "55677",
    "jira_it_system": "CMDB-1358427",
    "jira_exploit_poc": "68865",
    "jira_cvss_score": "0",
    "jira_column_id": "43720",
    "jira_risk_text": "Утечка критичных данных",
    "jira_work_description": (
        "Исключить попадание открытых персональных данных в индексы OpenSearch. "
        "Настроить фильтрацию или применение одностороннего хеширования/маскирования "
        "для полей, содержащих конфиденциальную информацию."
    ),
}

DEMO_USERS = [
    ("admin", "admin123", "admin"),
    ("analyst", "analyst123", "analyst"),
    ("viewer", "viewer123", "viewer"),
]


def _cache_key(
    index_pattern: str,
    field_path: str,
    pdn_type: str,
    context_type: str,
    key_hint: Optional[str],
    extra_fields: Dict[str, str],
) -> str:
    """Тот же алгоритм, что ScannerService._calculate_cache_key."""
    context_part = (key_hint or "") if context_type == "structured_key" else context_type
    extra_parts = "|".join(extra_fields.get(k, "") for k in sorted(extra_fields.keys()))
    raw = f"{index_pattern}|{field_path}|{pdn_type}|{context_part}|{extra_parts}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _hours_ago(hours: int) -> datetime:
    return _NOW - timedelta(hours=hours)


def _log_doc(
    *,
    index_name: str,
    message: str,
    extra: Dict[str, Any],
    timestamp: datetime,
) -> Dict[str, Any]:
    doc: Dict[str, Any] = {
        "@timestamp": timestamp.isoformat() + "Z",
        "index": index_name,
        "message": message,
        "NameOfMicroService": extra.get("NameOfMicroService", "unknown-svc"),
        "kubernetes": {
            "container": {"name": extra.get("kubernetes.container.name", "app")},
            "labels": {"app": extra.get("kubernetes.labels.app", "app")},
        },
        "system": {"env": extra.get("system.env", "prod")},
    }
    doc.update({k: v for k, v in extra.items() if k not in (
        "NameOfMicroService", "kubernetes.container.name",
        "kubernetes.labels.app", "system.env",
    )})
    return doc


async def _wipe_seed_tables(session) -> None:
    logger.info("Очистка предыдущих демо-данных...")
    await session.execute(delete(PatternTagLink))
    await session.execute(delete(PDNFinding))
    await session.execute(delete(JiraTask))
    await session.execute(delete(PDNPattern))
    await session.execute(delete(Tag))
    await session.execute(delete(ScanFieldConfig))
    await session.execute(delete(IndexOwner))
    await session.execute(delete(RegexRule))
    await session.execute(delete(SystemSetting))
    await session.execute(delete(StatusSetting))
    await session.flush()


async def _upsert_users(session) -> None:
    logger.info("Пользователи (admin / analyst / viewer)...")
    for username, password, role in DEMO_USERS:
        result = await session.execute(select(User).filter(User.username == username))
        user = result.scalars().first()
        password_hash = get_password_hash(password)
        if user:
            user.password_hash = password_hash
            user.role = role
            user.is_active = True
        else:
            session.add(User(
                username=username,
                password_hash=password_hash,
                role=role,
                is_active=True,
            ))
    await session.flush()


async def _seed_settings(session) -> None:
    logger.info("SystemSetting + StatusSetting...")
    settings: List[SystemSetting] = [
        SystemSetting(key="EXAMPLES_COUNT", value="3", type="int", description="Sliding window примеров (сканер)"),
        SystemSetting(key="examples_count", value="3", type="int", description="Sliding window примеров (API)"),
        SystemSetting(key="SCAN_INTERVAL_HOURS", value="1", type="int", description="Интервал глобального скана"),
        SystemSetting(key="scan_interval_hours", value="1", type="int", description="Интервал глобального скана (API)"),
        SystemSetting(key="BATCH_SIZE", value="10000", type="int", description="Размер пачки документов OpenSearch"),
        SystemSetting(key="batch_size", value="10000", type="int", description="Размер пачки документов (API)"),
        SystemSetting(key="is_phone", value="true", type="bool"),
        SystemSetting(key="is_email", value="true", type="bool"),
        SystemSetting(key="is_card", value="true", type="bool"),
        SystemSetting(key="is_fio", value="true", type="bool"),
    ]
    for key, value in JIRA_SETTINGS.items():
        settings.append(SystemSetting(
            key=key,
            value=value,
            type="int" if key == "jira_cvss_score" else "string",
        ))
    session.add_all(settings)
    session.add_all([
        StatusSetting(id="new", label="New", color="#ef4444", is_active=True),
        StatusSetting(id="confirmed", label="Confirmed", color="#3b82f6", is_active=True),
        StatusSetting(id="done", label="Done", color="#10b981", is_active=True),
        StatusSetting(id="false_positive", label="False Positive", color="#eab308", is_active=True),
        StatusSetting(id="unverified", label="Unverified", color="#94a3b8", is_active=True),
    ])
    await session.flush()


async def _seed_regex_rules(session) -> None:
    logger.info("RegexRule (системные regex + словари)...")
    rules: List[RegexRule] = [
        RegexRule(
            pdn_type="phone",
            rule_type="regex",
            value=r"(?<![\d\w.])(?:\+?[78])?[\s\-]?\(?(9\d{2})\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?![\d\w.])",
        ),
        RegexRule(
            pdn_type="email",
            rule_type="regex",
            value=r"[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z]{2,}",
        ),
        RegexRule(
            pdn_type="card",
            rule_type="regex",
            value=r"(?<![\d.])(?:\d{16}|(?:\d{4} ){3}\d{4}|(?:\d{4}-){3}\d{4})(?!\d)",
        ),
        RegexRule(
            pdn_type="fio",
            rule_type="regex",
            value=r"\s([A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,}\s+[A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,}(?:\s+[A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,})?)\b",
        ),
        RegexRule(pdn_type="email", rule_type="exclude_pattern", value=r".*@test\.com"),
        RegexRule(pdn_type="email", rule_type="exclude_pattern", value="@example.local"),
        RegexRule(pdn_type="phone", rule_type="prefix_exclude", value="cardId="),
        RegexRule(pdn_type="phone", rule_type="prefix_exclude", value='inn":"'),
        RegexRule(pdn_type="phone", rule_type="suffix_exclude", value="@"),
        RegexRule(pdn_type="phone", rule_type="exclude_key", value="userLogin"),
        RegexRule(pdn_type="phone", rule_type="exclude_key", value="ns"),
        RegexRule(pdn_type="card", rule_type="exclude_key", value="eventId"),
    ]
    rules.extend(RegexRule(pdn_type="email", rule_type="mail_service_name", value=v) for v in MAIL_SERVICE_NAMES)
    rules.extend(RegexRule(pdn_type="card", rule_type="card_bank_bin_4", value=v) for v in CARD_BANK_BINS_4)
    rules.extend(RegexRule(pdn_type="phone", rule_type="invalid_def_code", value=v) for v in INVALID_DEF_CODES)
    rules.extend(RegexRule(pdn_type="fio", rule_type="surn_end_cis", value=v) for v in SURN_ENDS_CIS)
    rules.extend(RegexRule(pdn_type="fio", rule_type="surn_end_world", value=v) for v in SURN_ENDS_WORLD)
    rules.extend(RegexRule(pdn_type="fio", rule_type="patron_end", value=v) for v in PATRON_ENDS)
    rules.extend(RegexRule(pdn_type="fio", rule_type="fio_special_marker", value=v) for v in FIO_SPECIAL_MARKERS)
    session.add_all(rules)
    await session.flush()
    logger.info(f"  RegexRule: {len(rules)} записей")


async def _seed_index_owners(session) -> None:
    logger.info("IndexOwner...")
    session.add_all([
        IndexOwner(
            index_pattern="bcs-tech-logs-*",
            fio="GasanovOI",
            cmdb_url="https://jira.bcs.ru/browse/CMDB-2803910",
            tech_debt_id="51495",
        ),
        IndexOwner(
            index_pattern="bcs-career-*",
            fio="KlimenkoKA",
            cmdb_url="https://jira.bcs.ru/browse/CMDB-2617286",
            tech_debt_id="51493",
        ),
        IndexOwner(
            index_pattern="client-activity-api-*",
            fio="PetrovPP",
            cmdb_url="https://jira.bcs.ru/browse/CMDB-123456",
            tech_debt_id="51490",
        ),
        IndexOwner(
            index_pattern="billing-events-*",
            fio="SidorovSS",
            cmdb_url="https://jira.bcs.ru/browse/CMDB-789012",
            tech_debt_id="51492",
        ),
        IndexOwner(
            index_pattern="frontend-logs-*",
            fio="SmirnovAA",
            cmdb_url="https://jira.bcs.ru/browse/CMDB-345678",
            tech_debt_id="51494",
        ),
        IndexOwner(
            index_pattern="payments-api-*",
            fio="KozlovKK",
            cmdb_url="https://jira.bcs.ru/browse/CMDB-222222",
            tech_debt_id="51496",
        ),
        IndexOwner(
            index_pattern="market-data-*",
            fio="IvanovaII",
            cmdb_url="https://jira.bcs.ru/browse/CMDB-111111",
            tech_debt_id="51491",
        ),
    ])
    await session.flush()


async def _seed_scan_fields(session) -> None:
    logger.info("ScanFieldConfig...")
    session.add_all([
        ScanFieldConfig(index_pattern="*", field_path="NameOfMicroService", is_required=True, is_active=True),
        ScanFieldConfig(index_pattern="*", field_path="kubernetes.container.name", is_required=True, is_active=True),
        ScanFieldConfig(index_pattern="bcs-tech-logs-*", field_path="system.env", is_required=False, is_active=True),
        ScanFieldConfig(index_pattern="client-activity-*", field_path="kubernetes.labels.app", is_required=False, is_active=True),
    ])
    await session.flush()


def _pattern_specs() -> List[Dict[str, Any]]:
    """18 паттернов с реалистичными extra_fields, статусами и примерами."""
    tech_extra = {
        "NameOfMicroService": "auth-gateway",
        "kubernetes.container.name": "auth-gw",
        "system.env": "prod",
    }
    career_extra = {
        "NameOfMicroService": "career-api",
        "kubernetes.container.name": "career",
    }
    activity_extra = {
        "NameOfMicroService": "client-activity-api",
        "kubernetes.container.name": "activity",
        "kubernetes.labels.app": "client-activity",
    }
    billing_extra = {
        "NameOfMicroService": "billing-core",
        "kubernetes.container.name": "billing",
    }
    frontend_extra = {
        "NameOfMicroService": "web-ui",
        "kubernetes.container.name": "nginx",
    }
    payments_extra = {
        "NameOfMicroService": "payments-api",
        "kubernetes.container.name": "payments",
    }
    market_extra = {
        "NameOfMicroService": "md-feed",
        "kubernetes.container.name": "md-feed",
    }

    return [
        {
            "index_pattern": "bcs-tech-logs-*",
            "field_path": "message",
            "pdn_type": "phone",
            "context_type": "free_text",
            "key_hint": None,
            "extra_fields": tech_extra,
            "status": "new",
            "hit_count": 12,
            "custom_message": None,
            "tags": ["S"],
            "values": [
                ("+7 900 123-45-67", "client phone=", " in request"),
                ("8 (912) 555-01-02", "notify ", " via sms"),
                ("+79161112233", "callback=", " timeout"),
            ],
        },
        {
            "index_pattern": "bcs-tech-logs-*",
            "field_path": "user.email",
            "pdn_type": "email",
            "context_type": "structured_key",
            "key_hint": "user.email",
            "extra_fields": tech_extra,
            "status": "confirmed",
            "hit_count": 28,
            "custom_message": "Email в plaintext логах auth-gateway, нужна маскировка.",
            "tags": ["G", "High"],
            "values": [
                ("ivan.petrov@gmail.com", "login=", ""),
                ("maria.s@yandex.ru", "user=", ""),
                ("demo.user@mail.ru", "account=", ""),
            ],
        },
        {
            "index_pattern": "bcs-tech-logs-*",
            "field_path": "user.full_name",
            "pdn_type": "fio",
            "context_type": "structured_key",
            "key_hint": "user.full_name",
            "extra_fields": tech_extra,
            "status": "confirmed",
            "hit_count": 9,
            "custom_message": None,
            "tags": ["G"],
            "values": [
                ("Иванов Иван Иванович", "fio=", ""),
                ("Петрова Анна Сергеевна", "client=", ""),
                ("Сидоров Пётр Алексеевич", "user=", ""),
            ],
        },
        {
            "index_pattern": "bcs-tech-logs-*",
            "field_path": "payment.card",
            "pdn_type": "card",
            "context_type": "structured_key",
            "key_hint": "payment.card",
            "extra_fields": tech_extra,
            "status": "new",
            "hit_count": 4,
            "custom_message": None,
            "tags": ["High"],
            "values": [
                ("2203 0012 3456 7890", "pan=", ""),
                ("4111111111111111", "card=", ""),
                ("5452-0000-0000-0004", "pan=", ""),
            ],
        },
        {
            "index_pattern": "bcs-career-*",
            "field_path": "applicant.phone",
            "pdn_type": "phone",
            "context_type": "structured_key",
            "key_hint": "applicant.phone",
            "extra_fields": career_extra,
            "status": "unverified",
            "hit_count": 7,
            "custom_message": None,
            "tags": ["U"],
            "values": [
                ("+7 903 111-22-33", "", ""),
                ("89165554433", "phone=", ""),
                ("+7(999)123-45-67", "mobile=", ""),
            ],
        },
        {
            "index_pattern": "bcs-career-*",
            "field_path": "applicant.email",
            "pdn_type": "email",
            "context_type": "structured_key",
            "key_hint": "applicant.email",
            "extra_fields": career_extra,
            "status": "confirmed",
            "hit_count": 33,
            "custom_message": "Резюме кандидатов пишутся в OpenSearch без хеширования email.",
            "tags": ["G", "High"],
            "values": [
                ("candidate.one@outlook.com", "email=", ""),
                ("hr.test@icloud.com", "contact=", ""),
                ("anna.k@protonmail.com", "mail=", ""),
            ],
        },
        {
            "index_pattern": "bcs-career-*",
            "field_path": "applicant.name",
            "pdn_type": "fio",
            "context_type": "free_text",
            "key_hint": None,
            "extra_fields": career_extra,
            "status": "new",
            "hit_count": 15,
            "custom_message": None,
            "tags": ["S"],
            "values": [
                ("Кузнецова Ольга Викторовна", "applicant ", " applied"),
                ("Смирнов Алексей Дмитриевич", "name=", " CV"),
                ("Новикова Елена Павловна", "fio ", " uploaded"),
            ],
        },
        {
            "index_pattern": "client-activity-api-*",
            "field_path": "payload.phone",
            "pdn_type": "phone",
            "context_type": "structured_key",
            "key_hint": "payload.phone",
            "extra_fields": activity_extra,
            "status": "confirmed",
            "hit_count": 41,
            "custom_message": "Телефон клиента в activity-событиях.",
            "tags": ["G", "Internal"],
            "values": [
                ("+79031112233", "phone=", ""),
                ("8 926 000-11-22", "msisdn=", ""),
                ("+7 495 123-45-67", "contact=", ""),
            ],
        },
        {
            "index_pattern": "client-activity-api-*",
            "field_path": "payload.email",
            "pdn_type": "email",
            "context_type": "structured_key",
            "key_hint": "payload.email",
            "extra_fields": activity_extra,
            "status": "false_positive",
            "hit_count": 3,
            "false_positive_comment": "Технический адрес noreply сервиса, не ПДн клиента.",
            "custom_message": None,
            "tags": ["Fake", "Low"],
            "values": [
                ("noreply@service.local", "from=", ""),
                ("alerts@internal.svc", "sender=", ""),
                ("healthcheck@k8s.local", "probe=", ""),
            ],
        },
        {
            "index_pattern": "client-activity-api-*",
            "field_path": "payload.card_number",
            "pdn_type": "card",
            "context_type": "structured_key",
            "key_hint": "payload.card_number",
            "extra_fields": activity_extra,
            "status": "new",
            "hit_count": 6,
            "custom_message": None,
            "tags": ["High"],
            "values": [
                ("2203001122334455", "card=", ""),
                ("5115 1111 1111 1118", "pan=", ""),
                ("5555555555554444", "number=", ""),
            ],
        },
        {
            "index_pattern": "billing-events-*",
            "field_path": "customer.fio",
            "pdn_type": "fio",
            "context_type": "structured_key",
            "key_hint": "customer.fio",
            "extra_fields": billing_extra,
            "status": "confirmed",
            "hit_count": 22,
            "custom_message": "ФИО плательщика в billing-событиях.",
            "tags": ["G"],
            "values": [
                ("Васильев Игорь Николаевич", "payer=", ""),
                ("Морозова Татьяна Юрьевна", "customer=", ""),
                ("Фёдоров Кирилл Олегович", "client=", ""),
            ],
        },
        {
            "index_pattern": "billing-events-*",
            "field_path": "customer.phone",
            "pdn_type": "phone",
            "context_type": "structured_key",
            "key_hint": "customer.phone",
            "extra_fields": billing_extra,
            "status": "new",
            "hit_count": 18,
            "custom_message": None,
            "tags": ["S"],
            "values": [
                ("+7 981 222-33-44", "phone=", ""),
                ("89217778899", "msisdn=", ""),
                ("+7(911)000-12-34", "contact=", ""),
            ],
        },
        {
            "index_pattern": "billing-events-*",
            "field_path": "payment.pan",
            "pdn_type": "card",
            "context_type": "structured_key",
            "key_hint": "payment.pan",
            "extra_fields": billing_extra,
            "status": "unverified",
            "hit_count": 5,
            "custom_message": None,
            "tags": ["U", "High"],
            "values": [
                ("4012888888881881", "pan=", ""),
                ("2203-4411-2233-0001", "card=", ""),
                ("5105105105105100", "number=", ""),
            ],
        },
        {
            "index_pattern": "frontend-logs-*",
            "field_path": "event.userEmail",
            "pdn_type": "email",
            "context_type": "structured_key",
            "key_hint": "event.userEmail",
            "extra_fields": frontend_extra,
            "status": "new",
            "hit_count": 50,
            "custom_message": None,
            "tags": ["S", "Internal"],
            "values": [
                ("web.user@yahoo.com", "email=", ""),
                ("front.qa@hotmail.com", "user=", ""),
                ("guest@fastmail.com", "login=", ""),
            ],
        },
        {
            "index_pattern": "frontend-logs-*",
            "field_path": "event.message",
            "pdn_type": "phone",
            "context_type": "free_text",
            "key_hint": None,
            "extra_fields": frontend_extra,
            "status": "false_positive",
            "hit_count": 2,
            "false_positive_comment": "Совпадение с trace id, не телефон.",
            "custom_message": None,
            "tags": ["Fake", "Low"],
            "values": [
                ("9001112233", "trace=", " span"),
                ("9120001122", "id=", " req"),
                ("9991234567", "nonce=", ""),
            ],
        },
        {
            "index_pattern": "frontend-logs-*",
            "field_path": "event.userName",
            "pdn_type": "fio",
            "context_type": "free_text",
            "key_hint": None,
            "extra_fields": frontend_extra,
            "status": "confirmed",
            "hit_count": 11,
            "custom_message": None,
            "tags": ["G"],
            "values": [
                ("Орлов Максим Андреевич", "user ", " clicked"),
                ("Белова Дарья Игоревна", "profile ", " updated"),
                ("Егоров Никита Романович", "session ", " started"),
            ],
        },
        {
            "index_pattern": "payments-api-*",
            "field_path": "body.card",
            "pdn_type": "card",
            "context_type": "structured_key",
            "key_hint": "body.card",
            "extra_fields": payments_extra,
            "status": "confirmed",
            "hit_count": 8,
            "custom_message": "PAN в теле payments-api, критично.",
            "tags": ["G", "High"],
            "values": [
                ("4111111111111111", "card=", ""),
                ("2200123456789010", "pan=", ""),
                ("5500000000000004", "number=", ""),
            ],
        },
        {
            "index_pattern": "market-data-*",
            "field_path": "comment",
            "pdn_type": "email",
            "context_type": "free_text",
            "key_hint": None,
            "extra_fields": market_extra,
            "status": "unverified",
            "hit_count": 1,
            "custom_message": None,
            "tags": ["U", "Low"],
            "values": [
                ("trader.a@gmx.com", "cc=", " in comment"),
                ("desk@zoho.com", "reply=", ""),
                ("ops@seznam.cz", "notify=", ""),
            ],
        },
    ]


async def _seed_patterns_and_findings(session, specs: List[Dict[str, Any]]) -> None:
    logger.info("PDNPattern + PDNFinding...")
    findings_count = 0

    for spec_i, spec in enumerate(specs):
        extra = spec["extra_fields"]
        cache_key = _cache_key(
            spec["index_pattern"],
            spec["field_path"],
            spec["pdn_type"],
            spec["context_type"],
            spec["key_hint"],
            extra,
        )
        first_seen = _hours_ago(160 - spec_i * 4)
        last_seen = _hours_ago(2 + spec_i)
        session.add(PDNPattern(
            cache_key=cache_key,
            index_pattern=spec["index_pattern"],
            field_path=spec["field_path"],
            pdn_type=spec["pdn_type"],
            context_type=spec["context_type"],
            key_hint=spec["key_hint"],
            extra_fields=extra,
            first_seen=first_seen,
            last_seen=last_seen,
            hit_count=spec["hit_count"],
            status=spec["status"],
            false_positive_comment=spec.get("false_positive_comment"),
            custom_message=spec.get("custom_message"),
        ))
        concrete_index = spec["index_pattern"].replace("*", "prod-2026.08")
        for j, (raw_value, prefix, suffix) in enumerate(spec["values"]):
            found_at = _hours_ago(spec_i * 3 + j * 5 + 1)
            doc_id = f"{spec['index_pattern']}|{spec['field_path']}|{spec['pdn_type']}|{j}"
            full_document = _log_doc(
                index_name=concrete_index,
                message=f"{prefix}{raw_value}{suffix}",
                extra={**extra, spec["field_path"]: raw_value},
                timestamp=found_at,
            )
            session.add(PDNFinding(
                cache_key=cache_key,
                doc_id=doc_id,
                index_pattern=concrete_index,
                raw_value=raw_value,
                field_path=spec["field_path"],
                prefix_raw=prefix or None,
                suffix_raw=suffix or None,
                full_document=full_document,
                found_at=found_at,
            ))
            findings_count += 1

        spec["_cache_key"] = cache_key
        spec["_tag_names"] = spec["tags"]

    await session.flush()
    logger.info(f"  PDNPattern: {len(specs)}, PDNFinding: {findings_count}")


async def _seed_tags(session, specs: List[Dict[str, Any]]) -> None:
    logger.info("Tag + PatternTagLink...")
    tags = [
        Tag(name="G", color="#22c55e", description="Global scan"),
        Tag(name="S", color="#3b82f6", description="Single index scan"),
        Tag(name="U", color="#a855f7", description="Examples updated"),
        Tag(name="High", color="#ef4444", description="Высокий приоритет"),
        Tag(name="Low", color="#94a3b8", description="Низкий приоритет"),
        Tag(name="Fake", color="#78716c", description="Фейк / тест / не ПДн"),
        Tag(name="Internal", color="#f97316", description="Внутренний сервис"),
    ]
    session.add_all(tags)
    await session.flush()
    by_name = {t.name: t for t in tags}

    links = 0
    for spec in specs:
        cache_key = spec["_cache_key"]
        for tag_name in spec["_tag_names"]:
            session.add(PatternTagLink(
                pattern_cache_key=cache_key,
                tag_id=by_name[tag_name].id,
                assigned_at=_hours_ago(10),
            ))
            links += 1
    await session.flush()
    logger.info(f"  Tags: {len(tags)}, links: {links}")


async def _seed_jira_tasks(session) -> None:
    logger.info("JiraTask...")
    session.add_all([
        JiraTask(
            jira_issue_key="EIB-12003",
            index_pattern="bcs-tech-logs-*",
            status="open",
            assignee="GasanovOI",
            author_name="admin",
            jira_url="https://jira.bcs.ru/browse/EIB-12003",
            created_at=_hours_ago(30),
        ),
        JiraTask(
            jira_issue_key="SEC-1004",
            index_pattern="client-activity-api-*",
            status="in_progress",
            assignee="PetrovPP",
            author_name="analyst",
            jira_url="https://jira.bcs.ru/browse/SEC-1004",
            created_at=_hours_ago(72),
        ),
        JiraTask(
            jira_issue_key="EIB-12015",
            index_pattern="billing-events-*",
            status="resolved",
            assignee="SidorovSS",
            author_name="admin",
            jira_url="https://jira.bcs.ru/browse/EIB-12015",
            created_at=_hours_ago(120),
            resolved_at=_hours_ago(12),
        ),
        JiraTask(
            jira_issue_key="TECH-8821",
            index_pattern="frontend-logs-*",
            status="open",
            assignee="SmirnovAA",
            author_name="analyst",
            jira_url="https://jira.bcs.ru/browse/TECH-8821",
            created_at=_hours_ago(8),
        ),
        JiraTask(
            jira_issue_key="EIB-11990",
            index_pattern="bcs-career-*",
            status="rejected",
            assignee="KlimenkoKA",
            author_name="admin",
            jira_url="https://jira.bcs.ru/browse/EIB-11990",
            created_at=_hours_ago(150),
            resolved_at=_hours_ago(140),
        ),
    ])
    await session.flush()


async def seed_data() -> None:
    logger.info("Начинаем заполнение базы демо-данными...")
    async with async_session_maker() as session:
        await _wipe_seed_tables(session)
        await _upsert_users(session)
        await _seed_settings(session)
        await _seed_regex_rules(session)
        await _seed_index_owners(session)
        await _seed_scan_fields(session)
        specs = _pattern_specs()
        await _seed_patterns_and_findings(session, specs)
        await _seed_tags(session, specs)
        await _seed_jira_tasks(session)
        await session.commit()
    logger.info("Демо-данные успешно записаны.")
    logger.info("Логины: admin/admin123, analyst/analyst123, viewer/viewer123")


def main() -> None:
    import asyncio
    asyncio.run(seed_data())


if __name__ == "__main__":
    main()
