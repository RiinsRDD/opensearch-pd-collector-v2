from app.models.pdn import PDNPattern, PDNFinding
from app.models.settings import SystemSetting, RegexRule, StatusSetting, IndexKeyExclusion
from app.models.tags import Tag, PatternTagLink
from app.models.tasks import JiraTask
from app.models.indices import IndexOwner
from app.models.logs import ScannerLog

# Удобно импортировать все модели из app.models для Alembic и инициализации БД
__all__ = [
    "Base",
    "PDNPattern",
    "PDNFinding",
    "SystemSetting",
    "RegexRule",
    "StatusSetting",
    "Tag",
    "PatternTagLink",
    "JiraTask",
    "IndexOwner",
    "IndexKeyExclusion",
    "ScannerLog"
]
