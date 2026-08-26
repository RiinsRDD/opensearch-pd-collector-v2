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
| `POST` | `/login` | JSON `{username, password}` (не form). JWT с `sub`, `role`, **без `exp`** |
| `GET` | `/me` | Данные текущего пользователя (decode JWT) |

**Пример ответа `/login`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Пример ответа `/me`:**
```json
{
  "id": 1,
  "username": "admin",
  "role": "admin",
  "is_active": true
}
```

---

## `/api/v1/settings` (`app/api/endpoints/settings.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/global` | Получить глобальные настройки (`EXAMPLES_COUNT`, флаги ПДн, правила индексов, конфигурации парсеров ПДн: email-домены, бины карт, и т.д., а также параметры интеграции Jira `jira_*`). **Все запросы через `await db.execute(select(...))` — никаких синхронных `db.query()`** |
| `POST` | `/global` | Обновить настройки (на вход `GlobalSettingsResponse`). Примечание: `unknown_mail_service_parts` является read-only со стороны UI и игнорируется при обновлении. |
| `GET` | `/indices` | Получить индивидуальные настройки индексов |
| `POST` | `/indices` | Обновить/создать настройку индекса |
| `GET` | `/index-owners` | Получить список всех маппингов владельцев индексов (assignee Jira, тех. долг) |
| `POST` | `/index-owners` | Создать маппинг владельца индекса |
| `PUT` | `/index-owners/{owner_id}` | Изменить маппинг владельца индекса |
| `DELETE` | `/index-owners/{owner_id}` | Удалить маппинг владельца индекса |
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
| `GET` | `/scan-fields` | Получить конфигурации дополнительных полей сканирования |
| `POST` | `/scan-fields` | Создать конфигурацию дополнительного поля |
| `DELETE` | `/scan-fields/{id}` | Удалить конфигурацию поля сканирования |
| `GET` | `/pdn-types` | Получить список всех регулярных выражений ПДн (с полем `is_system`) |
| `GET` | `/pdn-types/list` | Получить простой список уникальных типов ПДн |
| `POST` | `/pdn-types` | Добавить новый тип ПДн (сразу активирует флагом `is_{type}`) |
| `PUT` | `/pdn-types/{rule_id}` | Обновить регулярное выражение ПДн |
| `DELETE` | `/pdn-types/{rule_id}` | Удалить пользовательский тип ПДн (нельзя удалить системные `phone`, `email`, `card`, `fio`) |

---

## `/api/v1/indices` (`app/api/endpoints/indices_tree.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Древовидная структура индексов с фильтрацией по `status` и `tags`. Возвращает `{tree: [], new_counts: {}}`. Предзагрузка `findings`, `tags`, `jira_tasks` через `selectinload`. У узла `cache_key` в `pattern`: `examples` (до 3 `raw_value`, по `found_at` DESC) и `full_document` (JSON самого свежего finding или `null`) |
| `PATCH` | `/{cache_key}` | Обновление паттерна. Body: `{status?: str, custom_message?: str}` — меняются только переданные поля. 404 если паттерна нет. Роль: analyst/admin. Ответ: `{cache_key, status, custom_message}` |
| `DELETE` | `/{cache_key}` | Удаление паттерна вместе с `PDNFinding` и `PatternTagLink`. 404 если нет. Роль: admin. Ответ: `{ok: true, cache_key}` |
| `POST` | `/examples/update/{cache_key}` | Принудительное обновление примеров (тег `U`). 404 если паттерна нет. Скан индекса уходит в `BackgroundTasks` (`ScannerService.update_examples_for_pattern` → `_save_examples` + `_apply_tag('U')` только на этот `cache_key`). Ответ сразу: `{accepted: true, cache_key, message}` — примеры ещё не переписаны |
| `POST` | `/jira/tasks` | Создание задач Jira для выбранных `cache_keys`. Body: `{cache_keys: str[], custom_message?: str}`. Bearer = `User.jira_token`; без токена — **400** |
| `GET` | `/jira/tasks/{index_pattern}` | Задачи Jira для конкретного индекса (сортировка по алфавиту) |
| `GET` | `/jira/history` | История задач с пагинацией (`limit`, `page`) |
| `POST` | `/jira/create_all_confirmed` | Создание задач по всем `Confirmed` паттернам глобально (с таймаутом между запросами). Токен — `User.jira_token` текущего admin; без токена — **400** |

---

## `/api/v1/tasks` (`app/api/endpoints/tasks.py`)

Страница UI `/tasks` ходит в `GET /api/v1/indices/jira/history` (`indicesApi.getJiraHistory`), не сюда. Роутер оставлен как совместимый alias.

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Тот же ответ, что `GET /api/v1/indices/jira/history`: `{items, total, limit, page}`. Роль: viewer+ |
| `POST` | `/` | **410 Gone**. Создание задач только через `POST /api/v1/indices/jira/tasks`. В ответе нет слова mock |

---

## `/api/v1/scanner` (`app/api/endpoints/scanner.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/scan/{index_pattern}` | Одиночное сканирование. Body: `{hours: int, maxDocs: int}`. Тег `S`. **Реальный вызов через `scannerApi.triggerScan()`** |
| `GET` | `/status` | Статус сканера: `{status, current_index_pattern, eta}`. **Polling каждые 10 сек через `scannerApi.getStatus()`** |
| `GET` | `/logs` | История последних запусков. Поля: `id, scan_type, target_index, status, findings_count, started_at, duration_seconds, details`. **Реальная загрузка через `scannerApi.getLogs()`** |

---

## Дополнительные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | Health check (определён в `app/main.py`). Возвращает `{status: "ok", project: "PDN Collector V2"}` |
| `GET` | `/metrics` | Prometheus метрики (определён в `app/main.py` через `app.core.metrics.metrics_endpoint`). Возвращает `text/plain` формат Prometheus |

---

## Формат ошибок (единый для всего API)

Все ошибки возвращают единую структуру:

```json
{
  "error": {
    "code": 404,
    "message": "Pattern not found",
    "details": [],
    "request_id": "a1b2c3d4"
  }
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `code` | int | HTTP статус код |
| `message` | string | Человекочитаемое сообщение об ошибке |
| `details` | array | Детали валидации (для 422) или пустой массив |
| `request_id` | string | Уникальный ID запроса (из заголовка `X-Request-ID` или генерируется) |

**Request ID:** При каждом запросе генерируется/пробрасывается `X-Request-ID` (middleware), возвращается в заголовке ответа, используется для трейсинга в логах.

**Обработчики исключений:**
| Исключение | Статус | Описание |
|------------|--------|----------|
| `HTTPException` | original | Пользовательские ошибки (404, 400, 403, 410, etc.) |
| `RequestValidationError` (FastAPI, тело/query) | 422 | Ошибки разбора запроса; `details` = `exc.errors()` |
| `ValidationError` (pydantic, не RequestValidationError) | 422 | Тот же JSON-формат; отдельный handler, не объединять в уме |
| `SQLAlchemyError` | 500 | Ошибки базы данных (логируются с traceback) |
| `Exception` (generic) | 500 | Все остальные неперехваченные ошибки |

---

## Middleware

- **Request ID** — генерирует/пробрасывает `X-Request-ID`, добавляет в `request.state` и заголовок ответа
- **Metrics** — считает `http_requests_total` и `http_request_duration_seconds` по `method`, `endpoint`, `status`