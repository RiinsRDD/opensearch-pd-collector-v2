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
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    
    with patch("httpx.AsyncClient", return_value=mock_client) as mock_async_client:
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
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
    
    mock_client = AsyncMock()
    mock_client.post.side_effect = [mock_resp_1, mock_resp_2, mock_resp_3]
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        gen = client.search_after_generator("test-index")
        
        results = []
        async for item in gen:
            results.append(item)
            
        assert len(results) == 3
        assert results[0]["_id"] == "1"
        assert results[1]["_id"] == "2"
        assert results[2]["_id"] == "3"
