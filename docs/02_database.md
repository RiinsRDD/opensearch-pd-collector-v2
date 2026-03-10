# 2. База данных (Database)

Микросервис хранит состояние и конфигурацию в PostgreSQL. Управление схемой — через миграции Alembic. Доступ к данным инкапсулирован через паттерн репозитория (`CRUDBase` в `app/db/repository.py`).

## Схема базы данных

### 1. Настройки системы (`app/models/settings.py`)

**SystemSetting** (`system_settings`):

| Поле | Тип | Описание |
|------|-----|----------|
| `key` | String, PK | Ключ настройки (`EXAMPLES_COUNT`, `SCAN_INTERVAL_HOURS`, динам. флаги `is_phone`, `is_inn`...) |
| `value` | String | Значение |
| `description` | String, nullable | Описание параметра |
| `type` | String, default `"string"` | Тип: `string`, `int`, `bool`, `json` |

**RegexRule** (`regex_rules`):

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | - |
| `pdn_type` | String, index | `phone`, `email`, `card`, `fio`, и любые пользовательские (динамические) |
| `rule_type` | String | `regex`, `exclude_pattern`, `prefix_exclude`, `suffix_exclude`, `exclude_key`, `invalid_def_code` |
| `value` | String | Значение правила |
| `is_active` | Boolean, default `True` | Активно ли |

**StatusSetting** (`status_settings`):

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | String, PK | `new`, `confirmed`, `done`, `false_positive`, `unverified` |
| `label` | String | Отображаемое имя |
| `color` | String | HEX-цвет (`#ef4444`) |
| `is_active` | Boolean, default `True` | Активен ли |

### 2. Владельцы индексов (`app/models/indices.py`)

**IndexOwner** (`index_owners`):

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | - |
| `index_pattern` | String, unique, index | Паттерн индекса (`bcs-career-*`) |
| `cmdb_url` | String, nullable | Полный URL IT-системы в CMDB Jira |
| `tech_debt_id` | String, nullable | Идентификатор тех. долга |
| `fio` | String, nullable | ФИО ответственного за индекс (assignee) |

### 3. Данные сканирования ПДн (`app/models/pdn.py`)

**PDNPattern** (`pdn_patterns`) — уникальное сочетание `(index_pattern, field, pdn_type)`:

| Поле | Тип | Описание |
|------|-----|----------|
| `cache_key` | String, PK | SHA256 хэш контекста |
| `index_pattern` | String, index | Паттерн индекса |
| `field_path` | String | JSON-путь поля |
| `pdn_type` | String | Тип ПДн |
| `context_type` | String | `base` / `structured_key` / `free_text` / `ambiguous` |
| `key_hint` | String, nullable | Подсказка по ключу |
| `first_seen` | DateTime | Дата первого обнаружения |
| `last_seen` | DateTime | Дата последнего обнаружения |
| `hit_count` | Integer, default `1` | Счётчик встреч |
| `status` | String, default `"new"` | Статус: `new`, `confirmed`, `false_positive`, `archived` |
| `false_positive_comment` | String, nullable | Комментарий при FP |
| `custom_message` | String, nullable | Пользовательский комментарий для Jira |

**PDNFinding** (`pdn_findings`) — конкретные примеры найденных данных:

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | - |
| `cache_key` | String, index | Ссылка на PDNPattern |
| `doc_id` | String | ID документа в OpenSearch |
| `index_pattern` | String | Имя индекса |
| `raw_value` | String | Найденное значение |
| `field_path` | String | JSON-путь |
| `prefix_raw` | String, nullable | Контекст до |
| `suffix_raw` | String, nullable | Контекст после |
| `full_document` | JSON, nullable | Полный документ |
| `found_at` | DateTime | Дата находки |

### 4. Задачи Jira (`app/models/tasks.py`)

**JiraTask** (`jira_tasks`):

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | - |
| `jira_issue_key` | String, unique, index | Ключ задачи (`SEC-101`) |
| `index_pattern` | String, index | Паттерн индекса |
| `status` | String, default `"open"` | `open`, `in_progress`, `resolved`, `rejected` |
| `assignee` | String, nullable | Исполнитель |
| `author_name` | String, nullable | ФИО автора создания |
| `jira_url` | String, nullable | Ссылка на задачу |
| `created_at` | DateTime | Дата создания |
| `resolved_at` | DateTime, nullable | Дата решения |

### 5. Тегирование (`app/models/tags.py`)

**Tag** (`tags`):

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | - |
| `name` | String, unique | Код тега (`G`, `S`, `U`, `fake`, `unverified`) |
| `color` | String, nullable | HEX-цвет для UI |
| `description` | String, nullable | Описание |
| `created_at` | DateTime | Дата создания |

**PatternTagLink** (`pattern_tags`) — M2M связь:

| Поле | Тип | Описание |
|------|-----|----------|
| `pattern_cache_key` | String, FK → `pdn_patterns.cache_key`, PK | - |
| `tag_id` | Integer, FK → `tags.id`, PK | - |
| `assigned_at` | DateTime | Дата присвоения |

### 6. Логи сканера (`app/models/logs.py`)

**ScannerLog** (`scanner_logs`):

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | - |
| `scan_type` | String | `global` / `single` |
| `target_index` | String, nullable | Целевой индекс (для single) |
| `started_at` | DateTime | Начало |
| `completed_at` | DateTime, nullable | Завершение |
| `duration_seconds` | Integer, nullable | Длительность |
| `status` | String, default `"running"` | `running`, `success`, `failed` |
| `findings_count` | Integer, default `0` | Кол-во новых cache_key |
| `details` | String, nullable | Текстовые логи |
| `error_message` | String, nullable | Сообщение об ошибке |

## Миграции

Миграции расположены в `migrations/versions/`. Текущие миграции:

1. `7ee6282b4ef6_initial_migration.py` — начальная миграция всех таблиц
2. `914484850430_add_custom_message_to_pdn_pattern.py` — добавлено поле `custom_message`
3. `9f2c1b3bf858_add_jira_task_history_fields.py` — добавлены поля истории задач

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Имя миграции"

# Применить все миграции
alembic upgrade head
```
