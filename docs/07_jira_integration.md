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

> **Статус:** Мок-реализация HTTP-запроса в данный момент отключена (возвращается сгенерированный ключ), однако структура полезной нагрузки (payload) выводится в лог/print для отладки.

## Флоу создания задачи

1. **Пользователь** находит утечки ПДн в дереве индексов.
2. **Выделяет** `cache_key` → нажимает кнопку «Завести задачу».
3. **API** вызывает `POST /api/v1/indices/jira/tasks` с `{cache_keys, custom_message}`.
4. **JiraService** отправляет запрос в Jira API с `Bearer {auth_token}` пользователя.
5. **При успехе** — `Issue Key` сохраняется в таблицу `jira_tasks` (`JiraTask`).
6. **В UI** — возле индекса появляется иконка задачи. Задачи видны в `GET /api/v1/indices/jira/tasks/{index_pattern}`.

## API-эндпоинты (в `indices_tree.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/indices/jira/tasks` | Создать задачи для `cache_keys` |
| `GET` | `/api/v1/indices/jira/tasks/{index_pattern}` | Задачи для индекса |
| `GET` | `/api/v1/indices/jira/history` | История задач (`limit`, `page`) |
| `POST` | `/api/v1/indices/jira/create_all_confirmed` | Создать задачи по всем `Confirmed` |
