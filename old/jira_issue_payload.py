# jira_issue_payload.py

import jira_issue_settings as jst


JIRA_ISSUE_PAYLOAD = {
    "fields": {
        "project": {"key": jst.PROJECT},
        "issuetype": {"id": jst.ISSUE_TYPE},
        "summary": None,
        "priority": {"id": jst.PRIORITY},
        "assignee": {"name": None},
        "components": [{"id": jst.COMPONENTS}],
        "duedate": None,
        "labels": jst.LABELS,

        "description": None,

        "customfield_31735": [{"key": jst.DIB_SERVICE}],
        "customfield_13031": jst.EPIC_LINK,
        "customfield_22439": [{"key": jst.CFO}],
        "customfield_34835": {"id": jst.KIPD_TYPE},

        "customfield_29834": {
            "id": "51490",
            "child": {"id": None}
        },

        "customfield_22738": {"name": None},
        "customfield_17230": [{"id": jst.COLUMN_ID}],
        "customfield_22932": [{"key": None}],

        "customfield_13552": {"id": jst.TASK_SOURCE},
        "customfield_22732": {"id": jst.ACTION_GROUP},
        "customfield_22733": {"id": jst.ACTION_TYPE},

        "customfield_29130": jst.RISK_TEXT,
        "customfield_17336": jst.WORK_DESCRIPTION,

        "customfield_27431": [{"key": jst.PROCESS}],
        "customfield_42231": [{"key": None}],
        "customfield_42232": [{"key": None}],

        "customfield_10030": None,  # (list of dicts)

        "customfield_30134": {"id": jst.CRITICALITY_LEVEL},
        "customfield_31240": {"id": jst.LOCATION_TYPE},
        "customfield_23230": [{"key": jst.IT_SYSTEM}],

        "customfield_34837": {"id": jst.EXPLOIT_POC},
        "customfield_34836": jst.CVSS_SCORE
    }
}

fields_description = """
payload = {
    "fields": {
        # Проект
        "project": {"key": "EIB"},  # Cybersec

        # Тип задачи
        "issuetype": {"id": "15400"},  # Корректирующее мероприятие

        # Тема
        "summary": "Тестовое корректирующее мероприятие №2 (создано через API)",

        # Приоритет
        # PRIORITY_BY_RISK = {"Блокер": "1", "Критическая": "2", "Серьезная": "3", "Незначительная": "4"}
        "priority": {"id": "4"},

        # Сервис ДИБ
        # https://sd-jira.bcs.ru/secure/insight/assets/CMDB-859449
        # https://sd-jira.bcs.ru/rest/insight/latest/object/859449
        "customfield_31735": [{"key": "CMDB-859449"},],  # 01. Предотвращение утечек информации

        # Epic Link
        # https://jira.bcs.ru/browse/EIB-15679
        "customfield_13031": "EIB-15679",

        # ЦФО №
        # https://sd-jira.bcs.ru/secure/insight/assets/CMDB-3968
        # https://sd-jira.bcs.ru/rest/insight/latest/object/3968
        "customfield_22439": [{"key": "CMDB-3968"}],
        # "customfield_22439": [{"key": None}],

        # Тип КИПД
        "customfield_34835": {"id": "68857"},  # Нарушение требований ИБ

        # Технический долг
        "customfield_29834": {
            "id": "51490",  # Да
            "child": {"id": "51493"},  # БКС Мир Инвестиций
        },
        
        # Контролер
        "customfield_22738": {"name": "GasanovOI"},
        
        # Колонна
        "customfield_17230": [{"id": "43720"},],  # Брокер

        # Количество переносов
        # "customfield_29131": 0,  # default - 0

        # Команды инсайт
        # https://sd-jira.bcs.ru/secure/insight/assets/CMDB-317048
        # https://sd-jira.bcs.ru/rest/insight/latest/object/317048
        "customfield_22932": [{"key": "CMDB-317048"}],

        # Срок исполнения
        "duedate": "2026-02-22",

        # Источник задачи
        "customfield_13552": {"id": "28834"},  # Внутренний аудит

        # Группа действий
        "customfield_22732": {"id": "28819"},  # Внутренний аудит

        # Тип действий
        "customfield_22733": {"id": "28830"},  # Корректирующее действие

        # Риск
        "customfield_29130": "Утечка критичных данных",  # string

        # Описание работ
        "customfield_17336": work_description,  # string

        # Процесс
        # 01. Предотвращение утечек информации
        # https://sd-jira.bcs.ru/secure/insight/assets/CMDB-2760490
        "customfield_27431": [{"key": "CMDB-2760490"}],  # list, dict, key - cmdb

        # Руководитель L1 (Инсайт)
        "customfield_42231": [],  # if empty - removes field
        # "customfield_42231": [{"key": "CMDB-313571"}],

        # Руководитель L2 (Инсайт)
        "customfield_42232": [],  # if empty - removes field
        # "customfield_42232": [{"key": "CMDB-313935"}],

        # Исполнитель
        "assignee": {"name": "GasanovOI"},  # it-owner
        # "assignee": {"name": None},  # it-owner

        # Участники
        # "GasanovOI", "KlimenkoKA", "NevskiyAG", "PirogovAV", "KolesovRV"
        "customfield_10030": [
            {"name": "GasanovOI"},
            {"name": "KlimenkoKA"},
            {"name": "NevskiyAG"},
            {"name": "PirogovAV"},
            {"name": "KolesovRV"},
        ],

        # Уровень критичности
        "customfield_30134": {"id": "52414"},  # Важные для бизнеса (Secondary)

        # Тип расположения
        "customfield_31240": {"id": "55677"}, # Внутренняя

        # ИТ система - Сервисы наблюдаемости и мониторинга МС (S37)
        # https://sd-jira.bcs.ru/secure/insight/assets/CMDB-1358427
        "customfield_23230": [{"key": "CMDB-1358427"}],

        # Описание
        "description": issue_description,

        # Компоненты
        "components": [{"id": "47920"}],  # Сопровождение

        # Метки
        "labels": ["dtsz_auto_pd_discovery"],  # label - dtsz_auto_pd_discovery

        # POC или следы эксплуатации
        "customfield_34837": {"id": "68865"},  # 68865 - no, 68864 - yes

        # CVSS оценка
        "customfield_34836": 0,

        # status
        # https://sd-jira.bcs.ru/rest/api/2/issue/EIB-38273/transitions

    }
}
"""
