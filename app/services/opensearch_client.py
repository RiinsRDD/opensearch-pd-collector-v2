import httpx
from typing import AsyncGenerator, Dict, Any, Optional, List
from app.core.config import settings
import logging
import re

class OpenSearchClient:
    def __init__(self):
        self.base_url = settings.OPENSEARCH_URL
        self.auth = (settings.OS_USERNAME, settings.OS_PASSWORD)
        self.verify = settings.OS_VERIFY_CERTS
        self.headers = {"Content-Type": "application/json"}

    async def get_indices(self, 
                          exclude_patterns: Optional[List[str]] = None, 
                          exclude_regexes: Optional[List[str]] = None, 
                          include_regexes: Optional[List[str]] = None) -> list[str]:
        exclude_patterns = exclude_patterns or []
        exclude_regexes = exclude_regexes or []
        include_regexes = include_regexes or []

        async with httpx.AsyncClient(verify=self.verify, auth=self.auth) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/_cat/indices/?format=json&h=index",
                    headers=self.headers,
                    timeout=10.0
                )
                resp.raise_for_status()
                data = resp.json()
                all_indices = [item["index"] for item in data if "index" in item]

                filtered_indices = []
                for idx in all_indices:
                    # 1. Точное/частичное исключение по паттерну
                    if any(pat in idx for pat in exclude_patterns):
                        continue

                    # 2. Исключение по регуляркам
                    if any(re.search(reg, idx) for reg in exclude_regexes):
                        continue
                    
                    # 3. Разрешающие регулярки
                    if include_regexes:
                        if not any(re.search(reg, idx) for reg in include_regexes):
                            continue

                    filtered_indices.append(idx)

                return filtered_indices
            except Exception as e:
                logging.error(f"Error fetching indices: {e}")
                return []

    async def search_after_generator(
        self, 
        index_pattern: str, 
        batch_size: int = 10000, 
        time_from: str = "now-1h", 
        time_to: str = "now",
        search_after: Optional[list] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        
        query = {
            "size": batch_size,
            "sort": [{"@timestamp": "asc"}, {"_id": "asc"}],
            "query": {
                "range": {
                    "@timestamp": {"gte": time_from, "lt": time_to}
                }
            }
        }

        current_search_after = search_after

        async with httpx.AsyncClient(verify=self.verify, auth=self.auth) as client:
            while True:
                if current_search_after:
                    query["search_after"] = current_search_after
                
                try:
                    resp = await client.post(
                        f"{self.base_url}/{index_pattern}/_search",
                        json=query,
                        headers=self.headers,
                        timeout=60.0
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    hits = data.get("hits", {}).get("hits", [])
                    if not hits:
                        break

                    for hit in hits:
                        yield hit

                    current_search_after = hits[-1].get("sort")
                    if not current_search_after:
                        break
                except httpx.HTTPError as e:
                    logging.error(f"HTTPError compiling search_after for {index_pattern}: {e}")
                    break
