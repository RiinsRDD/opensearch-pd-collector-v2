import httpx
import logging
from typing import Optional

class JiraService:
    def __init__(self, base_url: str = "https://jira.bcs.ru"):
        self.base_url = base_url

    async def create_issue(self, auth_token: str, index_pattern: str, cache_keys: list, comment: str, settings: dict, assignee: Optional[str] = None, index_owner = None) -> Optional[str]:
        """
        Create a correction task in Jira on behalf of the user using their auth_token
        """
        base_url = settings.get("jira_base_url", self.base_url)
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        description = f"Обнаружены совпадения ПДн в индексе {index_pattern}.\nДополнительный комментарий: {comment}\n\nПаттерны:\n"
        for key in cache_keys:
            description += f"- {key}\n"
            
        labels = [lbl.strip() for lbl in settings.get("jira_labels", "dtsz_auto_pd_discovery").split(",")] if settings.get("jira_labels") else []
            
        payload = {
            "fields": {
                "project": {"key": settings.get("jira_project_key", "EIB")},
                "issuetype": {"id": settings.get("jira_issue_type", "15400")},
                "summary": f"Утечка ПДн в индексе {index_pattern}",
                "priority": {"id": settings.get("jira_priority", "4")},
                "components": [{"id": settings.get("jira_components", "47920")}],
                "labels": labels,
                "description": description,
                "customfield_31735": [{"key": settings.get("jira_dib_service", "CMDB-859449")}],
                "customfield_13031": settings.get("jira_epic_link", "EIB-15679"),
                "customfield_22439": [{"key": settings.get("jira_cfo", "CMDB-3968")}],
                "customfield_34835": {"id": settings.get("jira_kipd_type", "68857")},
                "customfield_29834": {
                    "id": "51490",
                    "child": {"id": "51493"}
                },
                "customfield_17230": [{"id": settings.get("jira_column_id", "43720")}],
                "customfield_13552": {"id": settings.get("jira_task_source", "28834")},
                "customfield_22732": {"id": settings.get("jira_action_group", "28819")},
                "customfield_22733": {"id": settings.get("jira_action_type", "28830")},
                "customfield_29130": settings.get("jira_risk_text", "Утечка критичных данных"),
                "customfield_17336": settings.get("jira_work_description", ""),
                "customfield_27431": [{"key": settings.get("jira_process", "CMDB-2760490")}],
                "customfield_30134": {"id": settings.get("jira_criticality_level", "52414")},
                "customfield_31240": {"id": settings.get("jira_location_type", "55677")},
                "customfield_23230": [{"key": settings.get("jira_it_system", "CMDB-1358427")}],
                "customfield_34837": {"id": settings.get("jira_exploit_poc", "68865")},
                "customfield_34836": int(settings.get("jira_cvss_score", 0))
            }
        }
        
        if index_owner:
            if index_owner.fio:
                payload["fields"]["assignee"] = {"name": index_owner.fio}
            if index_owner.tech_debt_id:
                payload["fields"]["customfield_29834"]["child"]["id"] = index_owner.tech_debt_id
        elif assignee:
            payload["fields"]["assignee"] = {"name": assignee}

        async with httpx.AsyncClient() as client:
            try:
                # Mocking the actual request for now
                logging.info(f"Creating Jira issue for {index_pattern} with {len(cache_keys)} patterns to {base_url}")
                # resp = await client.post(f"{base_url}/rest/api/2/issue", json=payload, headers=headers)
                # resp.raise_for_status()
                # return resp.json().get("key")
                return f"CORRMERA-{abs(hash(index_pattern)) % 10000}"
            except Exception as e:
                logging.error(f"Failed to create Jira issue: {e}")
                return None
