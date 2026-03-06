# 5. API Эндпоинты (API Endpoints)

FastAPI приложение предоставляет набор REST API эндпоинтов. Все роутеры подключаются в `app/api/router.py` под общим префиксом `/api/v1`.

## Роутер (`app/api/router.py`)

```python
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(indices_tree.router, prefix="/indices", tags=["indices"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(scanner.router, prefix="/scanner", tags=["scanner"])
```

---

## `/api/v1/auth` (`app/api/endpoints/auth.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/login` | Авторизация (mock: возвращает `mock_token`) |
| `GET` | `/me` | Данные текущего пользователя (mock: `username=admin`, `role=admin`) |

> **Статус:** Mock-реализация без реальной JWT-верификации.

---

## `/api/v1/settings` (`app/api/endpoints/settings.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/global` | Получить глобальные настройки (`EXAMPLES_COUNT`, флаги ПДн, правила индексов, конфигурации парсеров ПДн: email-домены, бины карт, и т.д., а также параметры интеграции Jira `jira_*`) |
| `POST` | `/global` | Обновить настройки (на вход `GlobalSettingsResponse`). Примечание: `unknown_mail_service_parts` является read-only со стороны UI и игнорируется при обновлении. |
| `GET` | `/indices` | Получить индивидуальные настройки индексов |
| `POST` | `/indices` | Обновить/создать настройку индекса |
| `GET` | `/statuses` | Получить список статусов и их цветов |
| `POST` | `/statuses` | Обновить цвета статусов |
| `DELETE` | `/tags/{tag_name}` | Глобальное удаление тега (cascade) |
| `GET` | `/exclusions/global` | Получить список глобальных исключений |
| `POST` | `/exclusions/global` | Добавить глобальное исключение (exclude, prefix, suffix, full_path) |
| `DELETE` | `/exclusions/global/{id}` | Удалить глобальное исключение по ID |
| `GET` | `/exclusions/index` | Получить исключения ключей для индексов |
| `POST` | `/exclusions/index` | Добавить исключение конкретного пути ключа для индекса |
| `DELETE` | `/exclusions/index/{id}` | Удалить исключение ключа для индекса по ID |
| `GET` | `/exclusions/indices-list` | Получить уникальный список паттернов индексов для автодополнения |
| `GET` | `/pdn-types` | Получить список всех регулярных выражений ПДн (с полем `is_system`) |
| `GET` | `/pdn-types/list` | Получить простой список уникальных типов ПДн |
| `POST` | `/pdn-types` | Добавить новый тип ПДн (сразу активирует флагом `is_{type}`) |
| `PUT` | `/pdn-types/{rule_id}` | Обновить регулярное выражение ПДн |
| `DELETE` | `/pdn-types/{rule_id}` | Удалить пользовательский тип ПДн (нельзя удалить системные `phone`, `email`, `card`, `fio`) |

---

## `/api/v1/indices` (`app/api/endpoints/indices_tree.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Древовидная структура индексов с фильтрацией по `status` и `tags`. Возвращает `{tree: [], new_counts: {}}` |
| `POST` | `/examples/update/{cache_key}` | Принудительное обновление примеров (тег `U`). Логика: если `New` → перезапись, иначе → добавление |
| `POST` | `/jira/tasks` | Создание задач Jira для выбранных `cache_keys`. Body: `{cache_keys: str[], custom_message?: str}` |
| `GET` | `/jira/tasks/{index_pattern}` | Задачи Jira для конкретного индекса (сортировка по алфавиту) |
| `GET` | `/jira/history` | История задач с пагинацией (`limit`, `page`) |
| `POST` | `/jira/create_all_confirmed` | Создание задач по всем `Confirmed` паттернам глобально (с таймаутом) |

---

## `/api/v1/tasks` (`app/api/endpoints/tasks.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Список всех задач |
| `POST` | `/` | Создать задачу (mock) |

> **Статус:** Минимальная заглушка. Основная логика задач реализована в `indices_tree.py`.

---

## `/api/v1/scanner` (`app/api/endpoints/scanner.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/scan/{index_pattern}` | Одиночное сканирование. Body: `{hours: int, maxDocs: int}`. Тег `S` |
| `GET` | `/status` | Статус сканера: `{status, current_index_pattern, eta}` |
| `GET` | `/logs` | История последних запусков. Поля: `id, scan_type, target_index, status, findings_count, started_at, duration_seconds, details` |

---

## Дополнительный эндпоинт

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | Health check (определён в `app/main.py`). Возвращает `{status: "ok", project: "PDN Collector V2"}` |
