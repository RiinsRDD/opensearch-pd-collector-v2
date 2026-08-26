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

**Индексы:**
- `ix_pdn_pattern_idx_type_status` — составной (`index_pattern`, `pdn_type`, `status`) для фильтрации дерева

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

**Индексы:**
- `ix_pdn_finding_cache_key_found_at` — составной (`cache_key`, `found_at` DESC) для топ-3 примеров

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

**Индексы:**
- `ix_jira_task_index_created` — составной (`index_pattern`, `created_at` DESC) для задач по индексу

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

### 7. Логи сканера (`app/models/logs.py`)

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

**Индексы:**
- `ix_scanner_log_status_started` — составной (`status`, `started_at` DESC) для статуса сканера

### 7. Дополнительные поля сканирования (`app/models/scan_field_config.py`)

**ScanFieldConfig** (`scan_field_configs`):

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | - |
| `index_pattern` | String, default `"*"` | Паттерн индекса |
| `field_path` | String | JSON-путь поля (например, `kubernetes.container.name`) |
| `is_active` | Boolean, default `True` | Активно ли |
| `is_required` | Boolean, default `False` | Обязательное поле (нельзя удалить) |
| `created_at` | DateTime | Дата создания |

### 8. Исключения ключей по индексам (`app/models/settings.py`)

**IndexKeyExclusion** (`index_key_exclusions`):

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | - |
| `index_pattern` | String, index | Паттерн индекса |
| `pdn_type` | String | Тип ПДн (`phone`, `email`, `card`, `fio`) |
| `key_path` | String | Полный путь ключа (`kubernetes.namespace.container`) |
| `is_active` | Boolean, default `True` | Активно ли |

## Миграции

Миграции расположены в `migrations/versions/`. Текущие миграции:

1. `7ee6282b4ef6_initial_migration.py` — начальная миграция всех таблиц
2. `914484850430_add_custom_message_to_pdn_pattern.py` — добавлено поле `custom_message`, таблицы `jira_tasks`, `scanner_logs`, `status_settings`
3. `9f2c1b3bf858_add_jira_task_history_fields.py` — добавлены поля истории задач
4. `cf1b3474db3e_add_users_table.py` — таблица `users` для JWT авторизации
5. `13694664e7a5_add_missing_tables_scan_fields_index.py` — таблицы `scan_field_configs`, `index_key_exclusions`
6. `731ca325f61e_add_performance_indexes.py` — составные индексы для производительности

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Имя миграции"

# Применить все миграции
alembic upgrade head
```

## Демо-данные (`tests/seed_mock_data.py`)

Идемпотентный seed для локальной разработки и демонстрации UI. Перед записью очищает таблицы паттернов, находок, тегов, правил, настроек, владельцев и scan-fields; пользователей `admin` / `analyst` / `viewer` апсертит по `username`.

```bash
# из корня репозитория, PostgreSQL из .env должна быть доступна
python -m tests.seed_mock_data
```

Скрипт заполняет:

| Сущность | Объём |
|----------|--------|
| `User` | admin / analyst / viewer (пароли `admin123`, `analyst123`, `viewer123`) |
| `SystemSetting` | `EXAMPLES_COUNT=3`, `SCAN_INTERVAL_HOURS=1`, `BATCH_SIZE=10000`, флаги `is_*`, Jira custom fields |
| `RegexRule` | системные regex phone/email/card/fio, exclude_*, словари (50+ mail services, 13 BIN, 20 DEF-кодов, фамилии/отчества) |
| `IndexOwner` | 7 паттернов индексов с CMDB / tech_debt / ФИО |
| `ScanFieldConfig` | `*` → NameOfMicroService, kubernetes.container.name (required); плюс per-index поля |
| `PDNPattern` | 18 записей, статусы `new` / `confirmed` / `false_positive` / `unverified`, SHA256 `cache_key` как у сканера |
| `PDNFinding` | 3 примера на паттерн (54), `found_at` за последние 7 дней, реалистичный `full_document` |
| `Tag` + `PatternTagLink` | G, S, U, High, Low, Fake, Internal |
| `JiraTask` | 5 задач (EIB-12003, SEC-1004, EIB-12015, TECH-8821, EIB-11990) |

Ключи `EXAMPLES_COUNT` и `examples_count` пишутся оба: сканер читает uppercase, Settings API — lowercase.
