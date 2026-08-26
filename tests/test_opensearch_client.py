import pytest
from unittest.mock import AsyncMock, patch, Mock
from app.services.opensearch_client import OpenSearchClient
import httpx

@pytest.mark.asyncio
async def test_get_indices():
    client = OpenSearchClient()
    
    mock_resp = Mock()
    mock_resp.json.return_value = [
        {"index": "my-test-index"},
        {"index": "another-index"},
        {"index": "exclude-me"}
    ]
    mock_resp.raise_for_status = Mock()
    
    mock_internal_client = AsyncMock()
    mock_internal_client.get.return_value = mock_resp
    
    # Replace the internal client
    client._client = mock_internal_client
    
    indices = await client.get_indices(exclude_patterns=["exclude"])
    assert len(indices) == 2
    assert "my-test-index" in indices
    assert "another-index" in indices
    assert "exclude-me" not in indices

@pytest.mark.asyncio
async def test_search_after_generator():
    client = OpenSearchClient()
    
    mock_resp_1 = Mock()
    mock_resp_1.json.return_value = {
        "hits": {
            "hits": [
                {"_id": "1", "sort": [1]},
                {"_id": "2", "sort": [2]}
            ]
        }
    }
    
    mock_resp_2 = Mock()
    mock_resp_2.json.return_value = {
        "hits": {
            "hits": [
                {"_id": "3", "sort": [3]}
            ]
        }
    }
    
    mock_resp_3 = Mock()
    mock_resp_3.json.return_value = {
        "hits": {"hits": []}
    }
    
    mock_internal_client = AsyncMock()
    mock_internal_client.post.side_effect = [mock_resp_1, mock_resp_2, mock_resp_3]
    
    # Replace the internal client
    client._client = mock_internal_client
    
    gen = client.search_after_generator("test-index")
    
    results = []
    async for item in gen:
        results.append(item)
        
    assert len(results) == 3
    assert results[0]["_id"] == "1"
    assert results[1]["_id"] == "2"
    assert results[2]["_id"] == "3"

@pytest.mark.asyncio
async def test_context_manager():
    """Test that OpenSearchClient works as async context manager"""
    client = OpenSearchClient()
    
    mock_internal_client = AsyncMock()
    client._client = mock_internal_client
    
    async with client as c:
        assert c is client
    
    mock_internal_client.aclose.assert_called_once()

@pytest.mark.asyncio
async def test_close():
    """Test explicit close method"""
    client = OpenSearchClient()
    
    mock_internal_client = AsyncMock()
    client._client = mock_internal_client
    
    await client.close()
    
    mock_internal_client.aclose.assert_called_once()