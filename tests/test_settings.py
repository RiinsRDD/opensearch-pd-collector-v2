import pytest
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
    
    get_res = await async_client.get("/api/v1/settings/global")
    assert get_res.status_code == 200, get_res.text
    data = get_res.json()
    assert data["examples_count"] == 10
    assert data["scan_interval_hours"] == 12
    assert data["pdn_flags"]["email"] is False
    assert data["pdn_flags"]["phone"] is True
    assert "gmail.com" in data["mail_service_names"]


@pytest.mark.asyncio
async def test_crud_pdn_types(async_client):
    get_res = await async_client.get("/api/v1/settings/pdn-types")
    assert get_res.status_code == 200

    new_type_payload = {
        "pdn_type": "custom_id",
        "regex_value": r"^\d{6}$"
    }
    add_res = await async_client.post("/api/v1/settings/pdn-types", json=new_type_payload)
    assert add_res.status_code == 200
    rule_id = add_res.json()["data"]["id"]

    list_res = await async_client.get("/api/v1/settings/pdn-types/list")
    assert "custom_id" in list_res.json()

    update_payload = {"regex_value": r"^\d{8}$"}
    upd_res = await async_client.put(f"/api/v1/settings/pdn-types/{rule_id}", json=update_payload)
    assert upd_res.status_code == 200

    del_res = await async_client.delete(f"/api/v1/settings/pdn-types/{rule_id}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_get_global_exclusions(async_client):
    response = await async_client.get("/api/v1/settings/exclusions/global")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_delete_tag_globally(async_client, db):
    tag = Tag(name="test_delete_tag", color="#123456")
    db.add(tag)
    await db.commit()

    response = await async_client.delete("/api/v1/settings/tags/test_delete_tag")
    assert response.status_code == 200
    assert "успешно удален" in response.json()["message"]
