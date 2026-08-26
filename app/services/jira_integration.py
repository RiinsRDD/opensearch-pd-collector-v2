import asyncio
import httpx
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.metrics import jira_tasks_created, jira_errors

logger = logging.getLogger(__name__)

RETRY_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)

class JiraService:
    def __init__(self, base_url: str = "https://jira.bcs.ru"):
        self.base_url = base_url

    def _validate_settings(self, settings: dict) -> Optional[str]:
        """Validate required Jira settings. Returns error message if invalid, None if valid."""
        required = ["jira_base_url", "jira_project_key", "jira_issue_type"]
        missing = [key for key in required if not settings.get(key)]
        if missing:
            return f"Missing required Jira settings: {', '.join(missing)}"
        return None

    def _build_headers(self, auth_token: str) -> dict:
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_payload(self, index_pattern: str, cache_keys: list, comment: str, settings: dict, assignee: Optional[str] = None, index_owner = None) -> dict:
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

        return payload

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(RETRY_EXCEPTIONS),
        reraise=True
    )
    async def _post_with_retry(self, client: httpx.AsyncClient, url: str, headers: dict, payload: dict) -> httpx.Response:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 5
            logger.warning(f"Jira rate limit hit, waiting {wait_time}s")
            raise httpx.HTTPStatusError(
                "Rate limited",
                request=resp.request,
                response=resp
            )
        if 500 <= resp.status_code < 600:
            logger.warning(f"Jira server error {resp.status_code}, will retry")
            resp.raise_for_status()
        if resp.status_code in (401, 403):
            logger.error(f"Jira auth error {resp.status_code}: token may be invalid")
            resp.raise_for_status()
        return resp

    async def create_issue(self, auth_token: str, index_pattern: str, cache_keys: list, comment: str, settings: dict, assignee: Optional[str] = None, index_owner = None) -> Optional[str]:
        """
        Create a correction task in Jira on behalf of the user using their auth_token
        """
        validation_error = self._validate_settings(settings)
        if validation_error:
            logger.error(validation_error)
            return None

        base_url = settings.get("jira_base_url", self.base_url)
        headers = self._build_headers(auth_token)
        payload = self._build_payload(index_pattern, cache_keys, comment, settings, assignee, index_owner)
        url = f"{base_url.rstrip('/')}/rest/api/2/issue"

        safe_payload = {k: v for k, v in payload.items() if "auth" not in str(k).lower() and "token" not in str(k).lower()}
        logger.info(f"Creating Jira issue for {index_pattern} with {len(cache_keys)} patterns to {base_url}")
        logger.debug(f"Jira payload: {safe_payload}")

        try:
            timeout = httpx.Timeout(connect=10.0, read=30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await self._post_with_retry(client, url, headers, payload)
                resp.raise_for_status()
                issue_key = resp.json().get("key")
                logger.info(f"Successfully created Jira issue: {issue_key}")
                jira_tasks_created.labels(index_pattern=index_pattern, result="success").inc()
                return issue_key
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                logger.error(f"Jira authentication failed: {e.response.status_code}")
                jira_errors.labels(error_type="auth").inc()
            elif e.response.status_code == 429:
                logger.error("Jira rate limit exceeded after retries")
                jira_errors.labels(error_type="rate_limit").inc()
            else:
                logger.error(f"Jira HTTP error: {e.response.status_code} - {e.response.text}")
                jira_errors.labels(error_type="http").inc()
            jira_tasks_created.labels(index_pattern=index_pattern, result="failed").inc()
            return None
        except httpx.TimeoutException:
            logger.error("Jira request timeout after retries")
            jira_errors.labels(error_type="timeout").inc()
            jira_tasks_created.labels(index_pattern=index_pattern, result="failed").inc()
            return None
        except httpx.ConnectError:
            logger.error("Failed to connect to Jira")
            jira_errors.labels(error_type="connection").inc()
            jira_tasks_created.labels(index_pattern=index_pattern, result="failed").inc()
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating Jira issue: {e}")
            jira_errors.labels(error_type="unexpected").inc()
            jira_tasks_created.labels(index_pattern=index_pattern, result="failed").inc()
            return None