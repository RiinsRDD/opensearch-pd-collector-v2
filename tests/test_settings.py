import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.db.session import get_db
from app.models.base import Base

# --- Mock DB Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
async def prepare_db():
    # Setup test DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# --- Tests ---
from app.models.settings import SystemSetting, RegexRule
from app.models.tags import Tag, PatternTagLink
from app.models.pdn import PDNPattern

@pytest.mark.asyncio
async def test_get_global_settings(async_client):
    response = await async_client.get("/api/v1/settings/global")
    assert response.status_code == 200
    data = response.json()
    assert "pdn_flags" in data
    assert "examples_count" in data
    assert "scan_interval_hours" in data
    assert "mail_service_names" in data

@pytest.mark.asyncio
async def test_update_global_settings(async_client):
    payload = {
        "pdn_flags": {"phone": True, "email": False, "card": True, "fio": True},
        "examples_count": 10,
        "scan_interval_hours": 12,
        "exclude_index_patterns": ["test-*"],
        "exclude_index_regexes": [],
        "include_index_regexes": [],
        "mail_service_names": ["gmail.com"],
        "unknown_mail_service_parts": [],
        "card_bank_bins_4": ["1234"],
        "invalid_def_codes": ["999"],
        "surn_ends_cis": ["ов"],
        "surn_ends_world": ["son"],
        "patron_ends": ["ович"],
        "fio_special_markers": ["оглы"]
    }
    response = await async_client.post("/api/v1/settings/global", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Global settings and system rules updated"
    
    # Verify the update
    get_res = await async_client.get("/api/v1/settings/global")
    data = get_res.json()
    assert data["examples_count"] == 10
    assert data["scan_interval_hours"] == 12
    assert data["pdn_flags"]["email"] is False
    assert data["pdn_flags"]["phone"] is True
    assert "gmail.com" in data["mail_service_names"]

@pytest.mark.asyncio
async def test_crud_pdn_types(async_client):
    # Get initial list
    get_res = await async_client.get("/api/v1/settings/pdn-types")
    assert get_res.status_code == 200

    # Add new type
    new_type_payload = {
        "pdn_type": "custom_id",
        "regex_value": r"^\d{6}$"
    }
    add_res = await async_client.post("/api/v1/settings/pdn-types", json=new_type_payload)
    assert add_res.status_code == 200
    rule_id = add_res.json()["data"]["id"]

    # Verify it exists
    list_res = await async_client.get("/api/v1/settings/pdn-types/list")
    assert "custom_id" in list_res.json()

    # Update the newly added type
    update_payload = {"regex_value": r"^\d{8}$"}
    upd_res = await async_client.put(f"/api/v1/settings/pdn-types/{rule_id}", json=update_payload)
    assert upd_res.status_code == 200

    # Delete the type
    del_res = await async_client.delete(f"/api/v1/settings/pdn-types/{rule_id}")
    assert del_res.status_code == 200

@pytest.mark.asyncio
async def test_get_global_exclusions(async_client):
    response = await async_client.get("/api/v1/settings/exclusions/global")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_delete_tag_globally(async_client):
    # Create a test tag first
    async with TestingSessionLocal() as session:
        tag = Tag(name="test_delete_tag", color="#123456")
        session.add(tag)
        await session.commit()

    # Call API to delete it
    response = await async_client.delete("/api/v1/settings/tags/test_delete_tag")
    assert response.status_code == 200
    assert "успешно удален" in response.json()["message"]
