import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import create_app
from app.db.session import get_db
from app.models.base import Base
from app.models.pdn import PDNPattern, PDNFinding
from app.models.settings import SystemSetting, RegexRule
from app.models.tags import Tag, PatternTagLink
from app.models.tasks import JiraTask
from app.models.logs import ScannerLog
from app.models.user import User
from app.api.deps import get_current_user, require_admin, require_analyst, require_viewer
from app.services.scheduler import scheduler_service
from datetime import datetime
from unittest.mock import patch

import app.models  # noqa: F401 — register all models on Base.metadata

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _fake_admin() -> User:
    return User(
        id=1,
        username="testadmin",
        password_hash="x",
        role="admin",
        is_active=True,
    )


def _apply_auth_overrides(app):
    admin = _fake_admin()
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[require_analyst] = lambda: admin
    app.dependency_overrides[require_viewer] = lambda: admin


@pytest_asyncio.fixture(scope="function")
async def db():
    """Create a fresh database for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_client(db):
    """Create an async test client with database and auth overrides."""
    app = create_app()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    _apply_auth_overrides(app)

    with patch.object(scheduler_service, "start"), patch.object(scheduler_service, "stop"):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
            yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def db_with_data(db):
    """Create database with realistic test data."""
    rules = [
        RegexRule(pdn_type="phone", rule_type="regex", value=r"7\d{10}", is_active=True),
        RegexRule(pdn_type="email", rule_type="regex", value=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", is_active=True),
        RegexRule(pdn_type="card", rule_type="regex", value=r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}", is_active=True),
        RegexRule(pdn_type="fio", rule_type="regex", value=r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+", is_active=True),
    ]
    for rule in rules:
        db.add(rule)

    settings = [
        SystemSetting(key="EXAMPLES_COUNT", value="3"),
        SystemSetting(key="SCAN_INTERVAL_HOURS", value="1"),
    ]
    for setting in settings:
        db.add(setting)

    patterns = [
        PDNPattern(
            cache_key="test_phone_001",
            index_pattern="bcs-tech-logs-*",
            field_path="user.phone",
            pdn_type="PHONE",
            context_type="base",
            hit_count=5,
            status="new",
            extra_fields={"service": "auth-svc"}
        ),
        PDNPattern(
            cache_key="test_email_001",
            index_pattern="bcs-tech-logs-*",
            field_path="user.email",
            pdn_type="EMAIL",
            context_type="base",
            hit_count=3,
            status="confirmed",
            extra_fields={"service": "user-svc"}
        ),
        PDNPattern(
            cache_key="test_card_001",
            index_pattern="payment-logs-*",
            field_path="card.number",
            pdn_type="CARD",
            context_type="base",
            hit_count=10,
            status="new",
            extra_fields={"service": "payment-svc"}
        ),
    ]
    for pattern in patterns:
        db.add(pattern)

    findings = [
        PDNFinding(
            cache_key="test_phone_001",
            doc_id="doc_1",
            index_pattern="bcs-tech-logs-2024.01.15",
            raw_value="79991234567",
            field_path="user.phone",
            prefix_raw="user: ",
            suffix_raw=", action: login",
            full_document={"user": {"phone": "79991234567"}},
            found_at=datetime(2024, 1, 15, 10, 30)
        ),
        PDNFinding(
            cache_key="test_email_001",
            doc_id="doc_2",
            index_pattern="bcs-tech-logs-2024.01.15",
            raw_value="test@example.com",
            field_path="user.email",
            prefix_raw="email: ",
            suffix_raw="",
            full_document={"user": {"email": "test@example.com"}},
            found_at=datetime(2024, 1, 15, 11, 30)
        ),
    ]
    for finding in findings:
        db.add(finding)

    tags = [
        Tag(name="G", color="#FFC107"),
        Tag(name="S", color="#9C27B0"),
        Tag(name="U", color="#4CAF50"),
    ]
    for tag in tags:
        db.add(tag)

    await db.commit()

    links = [
        PatternTagLink(pattern_cache_key="test_phone_001", tag_id=1),  # G
        PatternTagLink(pattern_cache_key="test_email_001", tag_id=2),  # S
    ]
    for link in links:
        db.add(link)

    jira_tasks = [
        JiraTask(
            jira_issue_key="SEC-1001",
            index_pattern="bcs-tech-logs-*",
            status="open",
            author_name="Ivanov Ivan",
            jira_url="https://jira.example.com/browse/SEC-1001"
        ),
        JiraTask(
            jira_issue_key="SEC-1002",
            index_pattern="payment-logs-*",
            status="resolved",
            author_name="Petrov Petr",
            jira_url="https://jira.example.com/browse/SEC-1002"
        ),
    ]
    for task in jira_tasks:
        db.add(task)

    scanner_logs = [
        ScannerLog(
            scan_type="global",
            target_index="bcs-tech-logs-*",
            status="success",
            started_at=datetime(2024, 1, 15, 9, 0),
            completed_at=datetime(2024, 1, 15, 9, 45),
            duration_seconds=2700,
            findings_count=8,
            details="Scan completed successfully"
        ),
        ScannerLog(
            scan_type="single",
            target_index="payment-logs-*",
            status="failed",
            started_at=datetime(2024, 1, 14, 10, 0),
            completed_at=datetime(2024, 1, 14, 10, 5),
            duration_seconds=300,
            findings_count=0,
            details="Connection timeout",
            error_message="OpenSearch connection failed"
        ),
    ]
    for log in scanner_logs:
        db.add(log)

    await db.commit()
    return db
