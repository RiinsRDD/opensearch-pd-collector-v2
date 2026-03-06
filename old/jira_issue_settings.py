# jira_issue_settings.py

import app_secrets


SD_JIRA_BASE_URL = "https://sd-jira.bcs.ru"
JIRA_BASE_URL = "https://jira.bcs.ru"
BEARER_TOKEN = app_secrets.JIRA_BEARER_TOKEN

SD_CREATE_ISSUE_URL = f"{SD_JIRA_BASE_URL}/rest/api/2/issue"
CREATE_ISSUE_URL = f"{JIRA_BASE_URL}/rest/api/2/issue"

# https://sd-jira.bcs.ru/rest/insight/latest/object/2793524
SD_INSIGHT_API_OBJECT_URL = f"{SD_JIRA_BASE_URL}/rest/insight/latest/object"
INSIGHT_API_OBJECT_URL = f"{JIRA_BASE_URL}/rest/insight/latest/object"

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

RUN_LOG_NAME = 'run.log'
ERR_LOG_NAME = 'errors.log'
RUN_LOG_NAME_DEV = 'run_dev.log'
ERR_LOG_NAME_DEV = 'errors_dev.log'

PROJECT = "EIB"
ISSUE_TYPE = "15400"  # Корректирующее мероприятие
PRIORITY = "3"  # {"Блокер": "1", "Критическая": "2", "Серьезная": "3", "Незначительная": "4"}
COMPONENTS = "47920"  # Сопровождение
LABELS = ["dtsz_auto_pd_discovery"]  # Метки
DIB_SERVICE = "CMDB-859449"  # 01. Предотвращение утечек информации
EPIC_LINK = "EIB-15679"  # https://jira.bcs.ru/browse/EIB-15679
CFO = "CMDB-3968"  # https://jira.bcs.ru/secure/insight/assets/CMDB-3968
KIPD_TYPE = "68857"  # Нарушение требований ИБ
TASK_SOURCE = "28834"  # Внутренний аудит
ACTION_GROUP = "28819"  # Внутренний аудит
ACTION_TYPE = "28830"  # Корректирующее действие
PROCESS = "CMDB-2760490"  # 01. Предотвращение утечек информации, https://sd-jira.bcs.ru/secure/insight/assets/CMDB-2760490
CRITICALITY_LEVEL = "52414"  # Важные для бизнеса (Secondary)
LOCATION_TYPE = "55677"  # Внутренняя
IT_SYSTEM = "CMDB-1358427"  # ИТ система - Сервисы наблюдаемости и мониторинга МС (S37), https://sd-jira.bcs.ru/secure/insight/assets/CMDB-1358427
EXPLOIT_POC = "68865"  # 68865 - no, 68864 - yes
CVSS_SCORE = 0  # CVSS оценка
COLUMN_ID = "43891"  # Вспомогательная деятельность

WORK_DESCRIPTION = "Исключить попадание открытых персональных данных в индексы OpenSearch. Настроить фильтрацию или применение одностороннего хеширования/маскирования для полей, содержащих конфиденциальную информацию."

# как пример, объект не используется
ISSUE_DESCRIPTION = """
Реализовать маскирование или исключение ПДн из индекса *{}*.

Примеры:
Индекс: {}
Поле: {}
Тип: {}
doc_id: {}
Timestamps: {}
"""

MASK_CHAR = "•"

MASK_VALUE = True
AGGREGATE_EXAMPLE_LIMIT = 3

RISK_TEXT = "Утечка критичных данных"

ACCOUNT_NAME_ID = 2268
L1_MANAGER_ID = 5224
L2_MANAGER_ID = 5225
TEAM_NAME_ID = 1494
ASSIGNEE_MANAGER_ID = 2275
ASSIGNEE_TEAMLEAD_ID = 1512

# Доп участники
EXTRA_TEAM_MEMBERS = {"KolesovRV", "KlimenkoKA", "MininaAA"}


# Для получения логина контролера
# https://sd-jira.bcs.ru/secure/insight/assets/CMDB-2793524
# GasanovOI
SUPERVISOR_CMDB_KEY_NUMBER = "2793524"

# Исполнитель
# https://sd-jira.bcs.ru/secure/insight/assets/CMDB-2793524
# https://sd-jira.bcs.ru/secure/insight/assets/CMDB-2874312
ASSIGNEE_CMDB_KEY_NUMBER = "2874312"

# Срок исполнения
DUEDATE_DAYS = 90

DEFAULT_UNREGISTERED_TEAM = "CMDB-2574344"  # https://jira.bcs.ru/secure/insight/assets/CMDB-2574344

# ---------------
# SMTP settings
SMTP_SERVER = 'nsk-smtp.global.bcs' # Сервер SMTP для отправки письма
SMTP_PORT = 25
FROM_ADDR = 'antifraud@bcs.ru'
TO_ADDR = 'gasanovoi@bcs.ru'
USE_SMTP = False
