import asyncio
import os
import sys

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.settings import SystemSetting, RegexRule
from app.models.indices import IndexOwner
from app.models.tags import Tag
from loguru import logger

async def seed_data():
    logger.info("Начинаем заполнение базы локальными тестовыми данными...")
    async with async_session_maker() as session:
        # Проверяем, пуста ли база (по базовым настройкам)
        from sqlalchemy import select
        result = await session.execute(select(SystemSetting))
        if result.scalars().first():
            logger.info("База уже заполнена данными. Пропускаем.")
            return

        # 1. Системные настройки
        settings = [
            SystemSetting(key="EXAMPLES_COUNT", value="5"),
            SystemSetting(key="SCAN_INTERVAL_HOURS", value="24"),
            SystemSetting(key="is_phone", value="true"),
            SystemSetting(key="is_email", value="true"),
            SystemSetting(key="is_card", value="true"),
            SystemSetting(key="is_fio", value="false"),
        ]
        session.add_all(settings)

        # 2. Базовые регулярные выражения
        regex_rules = [
            RegexRule(
                rule_type="regex",
                pdn_type="phone",
                value=r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
            ),
            RegexRule(
                rule_type="regex",
                pdn_type="email",
                value=r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            ),
            RegexRule(
                rule_type="regex",
                pdn_type="card",
                value=r"(?<![\d.])(?:\d{16}|(?:\d{4} ){3}\d{4}|(?:\d{4}-){3}\d{4})(?!\d)",
            ),
            RegexRule(
                rule_type="regex",
                pdn_type="fio",
                value=r"\s([A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,}\s+[A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,}(?:\s+[A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,})?)\b",
            ),
            RegexRule(
                rule_type="exclude_pattern",
                pdn_type="email",
                value=r".*@test\.com",
            ),
            RegexRule(
                rule_type="path_exclude_global",
                pdn_type="any",
                value="kubernetes.namespace.name",
            )
        ]
        session.add_all(regex_rules)

        # 3. Индексы и Ответственные
        index_owners = [
            IndexOwner(
                index_pattern="bcs-tech-logs*",
                team_name="Platform Team",
                contact_email="platform@example.com",
                notes="CMDB: IS-1234",
                jira_key="TECH"
            ),
            IndexOwner(
                index_pattern="client-activity*",
                team_name="CRM Team",
                contact_email="crm@example.com",
                notes="CMDB: IS-5678",
                jira_key="CRM"
            )
        ]
        session.add_all(index_owners)

        # 4. Базовые Теги
        tags = [
            Tag(name="Критично", color="#ff0000"),
            Tag(name="Не ПДн", color="#00ff00"),
            Tag(name="Фейк/Тест", color="#808080"),
        ]
        session.add_all(tags)

        # Сохранение (commit)
        await session.commit()
        logger.info("База успешно заполнена начальными данными!")

if __name__ == "__main__":
    asyncio.run(seed_data())
