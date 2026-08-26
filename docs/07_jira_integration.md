# 7. Интеграция с Jira (Jira Integration)

Модуль `JiraService` (`app/services/jira_integration.py`) обеспечивает создание задач (корректирующих мер) в Jira из Web-интерфейса.

## Класс `JiraService`

Инициализация: `JiraService()`

### Метод `create_issue`

```python
async def create_issue(
    self,
    auth_token: str,         # Bearer-токен пользователя для Jira
    index_pattern: str,      # Паттерн индекса
    cache_keys: list,        # Список cache_key для включения в задачу
    comment: str,            # Дополнительный комментарий
    settings: dict           # Словарь с настройками Jira (из БД)
) -> Optional[str]           # Возвращает Issue Key или None при ошибке
```

Формирует и отправляет `POST` запрос в `{jira_base_url}/rest/api/2/issue` с payload, который берет все параметры из передаваемого словаря `settings` (формируется из `SystemSetting` с префиксом `jira_`).
В структуру payload включаются:

- **Project key:** Берется из настройки `jira_project_key` (по умолчанию `EIB`)
- **Issue type:** Берется из `jira_issue_type`
- **Priority:** Парсится из `jira_priority`
- Множество кастомных полей (customfield_XXX) для CMDB: `jira_dib_service`, `jira_cfo`, `jira_process`, `jira_it_system` и т.д.
- **Владелец Индекса:** Если в БД `index_owners` есть запись для паттерна индекса, ФИО передается в `assignee`, а также заполняются поля CMDB Insight Object (`cmdb_url`) и Тех. долга (`tech_debt_id`).
- **Summary:** `[{index_pattern}]` + шаблон
- **Description:** Собирается из `jira_work_description` + список cache_keys

### Реализация HTTP-запросов

Используется `httpx.AsyncClient` с асинхронными запросами:
- **Timeout:** connect=10s, read=30s
- **Retry logic:** Exponential backoff (3 попытки, min 2s, max 10s) через `tenacity`
- **Retry условия:** Timeout, ConnectionError, 5xx ошибки, 429 rate limit

### Обработка ошибок

| Код | Действие |
|-----|----------|
| 401/403 | Токен невалиден/нет прав — логировать, вернуть `None` |
| 429 | Rate limit — ждать `Retry-After` header, ретрай |
| 5xx | Серверная ошибка — ретрай с exponential backoff |
| Timeout/ConnectError | Сеть — ретрай |
| Прочие | Логировать, вернуть `None` |

Логирование: payload (без auth_token) и ответ логируются на уровне `INFO`/`DEBUG`.

### Валидация настроек

Перед запросом проверяются обязательные поля:
- `jira_base_url`
- `jira_project_key`
- `jira_issue_type`

При отсутствии — ошибка логируется, возвращается `None`.

## Флоу создания задачи

1. **Пользователь** находит утечки ПДн в дереве индексов.
2. **Выделяет** `cache_key` → нажимает кнопку «Завести задачу».
3. **API** вызывает `POST /api/v1/indices/jira/tasks` с `{cache_keys, custom_message}`.
4. **JiraService** отправляет запрос в Jira API с `Authorization: Bearer {User.jira_token}`. Без токена шаг 3 не доходит до HTTP (400).
5. **При успехе** — `Issue Key` сохраняется в таблицу `jira_tasks` (`JiraTask`), `author_name` = `username`.
6. **В UI** — возле индекса появляется иконка задачи, если у паттерна есть задачи по `index_pattern`. Список: `GET /api/v1/indices/jira/tasks/{index_pattern}`. Глобальная страница Tasks: `GET /api/v1/indices/jira/history`.

## API-эндпоинты (в `indices_tree.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/indices/jira/tasks` | Создать задачи для `cache_keys`; токен = `User.jira_token`, иначе 400 |
| `GET` | `/api/v1/indices/jira/tasks/{index_pattern}` | Задачи для индекса |
| `GET` | `/api/v1/indices/jira/history` | История задач (`limit`, `page`) — путь UI Tasks |
| `POST` | `/api/v1/indices/jira/create_all_confirmed` | Создать задачи по всем `Confirmed` (admin, тот же `jira_token`) |
| `GET` | `/api/v1/tasks` | Alias `GET /indices/jira/history` |
| `POST` | `/api/v1/tasks` | 410 Gone |