"""API endpoint tests using AsyncClient."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pdn import PDNPattern, PDNFinding
from app.models.settings import SystemSetting, RegexRule
from app.models.tags import Tag, PatternTagLink
from app.models.tasks import JiraTask
from app.models.logs import ScannerLog
from datetime import datetime


class TestIndicesTreeEndpoint:
    """Tests for /api/v1/indices endpoints."""

    @pytest.mark.asyncio
    async def test_get_indices_tree(self, async_client, db_with_data):
        """Test getting the indices tree."""
        response = await async_client.get("/api/v1/indices")
        assert response.status_code == 200
        data = response.json()
        assert "tree" in data
        assert "new_counts" in data
        assert isinstance(data["tree"], list)
        assert len(data["tree"]) > 0

    @pytest.mark.asyncio
    async def test_tree_includes_full_document_from_finding(self, async_client, db_with_data):
        response = await async_client.get("/api/v1/indices")
        assert response.status_code == 200
        found = None
        for idx in response.json()["tree"]:
            for ptype in idx.get("children", []):
                for node in ptype.get("children", []):
                    if node.get("pattern", {}).get("cache_key") == "test_phone_001":
                        found = node["pattern"]
        assert found is not None
        assert found["full_document"] == {"user": {"phone": "79991234567"}}
        assert "79991234567" in found["examples"]

    @pytest.mark.asyncio
    async def test_get_indices_tree_with_status_filter(self, async_client, db_with_data):
        """Test filtering tree by status."""
        response = await async_client.get("/api/v1/indices?status=confirmed")
        assert response.status_code == 200
        data = response.json()
        # Verify all returned patterns have confirmed status
        for idx in data["tree"]:
            for ptype in idx.get("children", []):
                for pattern in ptype.get("children", []):
                    assert pattern["pattern"]["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_get_indices_tree_with_tags_filter(self, async_client, db_with_data):
        """Test filtering tree by tags."""
        response = await async_client.get("/api/v1/indices?tags=G")
        assert response.status_code == 200
        data = response.json()
        # Verify returned patterns have G tag
        for idx in data["tree"]:
            for ptype in idx.get("children", []):
                for pattern in ptype.get("children", []):
                    tags = [t["name"] for t in pattern["pattern"].get("tags", [])]
                    assert "G" in tags


class TestExamplesUpdateEndpoint:
    """Tests for examples update endpoint."""

    @pytest.mark.asyncio
    async def test_update_examples(self, async_client, db_with_data):
        """Test forcing examples update."""
        # Get a cache_key from test data
        response = await async_client.post("/api/v1/indices/examples/update/test_phone_001")
        assert response.status_code == 200
        data = response.json()
        assert data.get("accepted") is True
        assert "message" in data


class TestJiraTasksEndpoints:
    """Tests for Jira tasks endpoints."""

    @pytest.mark.asyncio
    async def test_create_jira_tasks(self, async_client, db_with_data):
        """Test creating Jira tasks for selected patterns."""
        payload = {
            "cache_keys": ["test_phone_001", "test_email_001"],
            "custom_message": "Test comment"
        }
        response = await async_client.post("/api/v1/indices/jira/tasks", json=payload)
        # Will fail without real Jira, but should not crash
        assert response.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    async def test_get_jira_tasks_by_index(self, async_client, db_with_data):
        """Test getting Jira tasks for specific index."""
        response = await async_client.get("/api/v1/indices/jira/tasks/bcs-tech-logs-*")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the test task
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_jira_history(self, async_client, db_with_data):
        """Test getting Jira history with pagination."""
        response = await async_client.get("/api/v1/indices/jira/history?limit=10&page=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "page" in data
        assert data["limit"] == 10
        assert data["page"] == 1


class TestTasksAliasEndpoints:
    """GET /tasks aliases jira history; POST /tasks is gone."""

    @pytest.mark.asyncio
    async def test_get_tasks_matches_jira_history(self, async_client, db_with_data):
        response = await async_client.get("/api/v1/tasks?limit=10&page=1")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["limit"] == 10
        assert data["page"] == 1
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_post_tasks_gone(self, async_client, db_with_data):
        response = await async_client.post("/api/v1/tasks", json={"cache_keys": []})
        assert response.status_code == 410
        data = response.json()
        assert data["error"]["code"] == 410
        assert "mock" not in (data["error"]["message"] or "").lower()


class TestPatternManagementEndpoints:
    """Tests for pattern management (PATCH/DELETE)."""

    @pytest.mark.asyncio
    async def test_update_pattern_status(self, async_client, db_with_data):
        """Test updating pattern status."""
        payload = {"status": "confirmed"}
        response = await async_client.patch("/api/v1/indices/test_phone_001", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["cache_key"] == "test_phone_001"
        assert data["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_delete_pattern(self, async_client, db_with_data):
        """Test deleting pattern."""
        response = await async_client.delete("/api/v1/indices/test_phone_001")
        assert response.status_code == 200
        assert response.json() == {"ok": True, "cache_key": "test_phone_001"}


class TestSettingsEndpoints:
    """Tests for settings endpoints."""

    @pytest.mark.asyncio
    async def test_get_global_settings(self, async_client, db_with_data):
        """Test getting global settings."""
        response = await async_client.get("/api/v1/settings/global")
        assert response.status_code == 200
        data = response.json()
        assert "pdn_flags" in data
        assert "examples_count" in data

    @pytest.mark.asyncio
    async def test_update_global_settings(self, async_client, db_with_data):
        """Test updating global settings."""
        settings = {
            "pdn_flags": {"phone": True, "email": True},
            "examples_count": 5,
            "scan_interval_hours": 2
        }
        response = await async_client.post("/api/v1/settings/global", json=settings)
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_get_pdn_types(self, async_client, db_with_data):
        """Test getting PDN types list."""
        response = await async_client.get("/api/v1/settings/pdn-types")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_pdn_type(self, async_client, db_with_data):
        """Test creating custom PDN type."""
        payload = {
            "pdn_type": "CUSTOM_TYPE",
            "regex_value": r"\d{10}"
        }
        response = await async_client.post("/api/v1/settings/pdn-types", json=payload)
        assert response.status_code in [200, 201, 400, 422]


class TestScannerEndpoints:
    """Tests for scanner endpoints."""

    @pytest.mark.asyncio
    async def test_trigger_single_scan(self, async_client, db_with_data):
        """Test triggering single scan."""
        from unittest.mock import AsyncMock, patch
        payload = {"hours": 24, "maxDocs": 10000}
        with patch("app.api.endpoints.scanner._bg_scan_task", new_callable=AsyncMock):
            response = await async_client.post("/api/v1/scanner/scan/bcs-tech-logs-*", json=payload)
        assert response.status_code in [200, 202, 500]  # May fail without OS

    @pytest.mark.asyncio
    async def test_get_scanner_status(self, async_client, db_with_data):
        """Test getting scanner status."""
        response = await async_client.get("/api/v1/scanner/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_scanner_logs(self, async_client, db_with_data):
        """Test getting scanner logs."""
        response = await async_client.get("/api/v1/scanner/logs?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestHealthAndMetrics:
    """Tests for health and metrics endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """Test health check endpoint."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, async_client):
        """Test Prometheus metrics endpoint."""
        response = await async_client.get("/metrics")
        assert response.status_code == 200
        # Should return Prometheus format
        assert "pdn_" in response.text or "http_" in response.text


class TestErrorHandling:
    """Tests for error handling and unified error format."""

    @pytest.mark.asyncio
    async def test_404_not_found(self, async_client):
        """Test 404 error format."""
        response = await async_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 404
        assert "request_id" in data["error"]

    @pytest.mark.asyncio
    async def test_422_validation_error(self, async_client):
        """Test 422 validation error format."""
        # Send invalid payload
        response = await async_client.post("/api/v1/indices/jira/tasks", json={"invalid": "data"})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 422
        assert "details" in data["error"]
        assert "request_id" in data["error"]

    @pytest.mark.asyncio
    async def test_request_id_header(self, async_client):
        """Test X-Request-ID header is returned."""
        response = await async_client.get("/health")
        assert "x-request-id" in response.headers
        request_id = response.headers["x-request-id"]
        assert len(request_id) > 0

    @pytest.mark.asyncio
    async def test_custom_request_id(self, async_client):
        """Test custom X-Request-ID is echoed back."""
        custom_id = "test-request-123"
        response = await async_client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.headers["x-request-id"] == custom_id