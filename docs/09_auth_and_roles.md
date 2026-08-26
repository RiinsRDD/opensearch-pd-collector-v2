# 9. Авторизация и Роли (Auth & Roles)

## Реализация

Авторизация реализована через **JWT токены** с ролевой моделью RBAC (Role-Based Access Control).

### Модель пользователя (`app/models/user.py`)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer, PK | Уникальный идентификатор |
| `username` | String, unique | Логин пользователя |
| `password_hash` | String | Bcrypt-хеш пароля |
| `role` | String, default="viewer" | Роль: `viewer`, `analyst`, `admin` |
| `jira_token` | String, nullable | Персональный Jira API Token |
| `is_active` | Boolean, default=True | Активен ли пользователь |
| `created_at` | DateTime | Дата создания |
| `last_login` | DateTime, nullable | Дата последнего входа |

### Эндпоинты (`app/api/endpoints/auth.py`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/auth/login` | JSON `{username, password}` (не OAuth2 form). JWT: `sub`, `role`, без `exp` |
| `GET` | `/api/v1/auth/me` | Данные текущего пользователя (decode JWT) |

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

### Ролевая модель (RBAC)

| Роль | Описание | Права |
|------|----------|-------|
| **Viewer** | Только чтение | GET /indices, GET /scanner/status, GET /scanner/logs, GET /jira/tasks, GET /jira/history, GET /settings/* (чтение) |
| **Analyst** | Аналитик | Всё от Viewer + POST /indices/jira/tasks, POST /indices/examples/update/{cache_key}, PATCH /indices/{cache_key} (status, custom_message) |
| **Admin** | Администратор | Полный доступ: POST /scanner/scan, POST /settings/global, POST /settings/*, DELETE /indices/{cache_key} (каскад findings + tag links), DELETE /tags, управление пользователями |

### Dependency Injection (`app/api/deps.py`)

```python
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User
def require_admin(user: User = Depends(get_current_user)) -> User
def require_analyst(user: User = Depends(get_current_user)) -> User
def require_viewer(user: User = Depends(get_current_user)) -> User
```

### Настройка JWT (`app/core/config.py`)

```python
JWT_SECRET_KEY: str = "change-me-in-production"
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # есть в Settings
```

`create_access_token` кодирует `sub` и `role` **без** claim `exp`. Срок из `ACCESS_TOKEN_EXPIRE_MINUTES` в JWT не пишется.

### Frontend (факт)

Нет `Login.tsx`, нет роута `/login`, Axios не ставит `Authorization`. Header: захардкоженные «A» / «Admin User»; кнопка «Выйти» токен не трогает. Живой API без Bearer → 401. В pytest `get_current_user` подменён на admin.

### Персональные ключи Jira

Каждый пользователь хранит свой **Jira API Token** в поле `User.jira_token`. `POST /api/v1/indices/jira/tasks` и `POST /api/v1/indices/jira/create_all_confirmed` берут его из текущего JWT-пользователя (`_require_jira_token`). Пустая строка или `null` → **400**, HTTP в Jira не уходит. В `jira_tasks.author_name` пишется `user.username` (для create_all_confirmed — `"system"`).

`GET /api/v1/tasks` — alias истории. `POST /api/v1/tasks` — 410, задач через этот путь нет.

### Миграция

```bash
alembic revision --autogenerate -m "add users table"
alembic upgrade head
```

Создаёт таблицу `users` с полями: `id`, `username`, `password_hash`, `role`, `jira_token`, `is_active`, `created_at`, `last_login`.

### Демо-пользователи

Создаются скриптом `python -m tests.seed_mock_data` (см. `docs/02_database.md`):

| username | password | role |
|----------|----------|------|
| `admin` | `admin123` | admin |
| `analyst` | `analyst123` | analyst |
| `viewer` | `viewer123` | viewer |

Пароли хешируются bcrypt через `get_password_hash`. Повторный запуск seed обновляет hash и роль, не создавая дубликатов.

### Зависимости

В `requirements.txt`:
- `python-jose[cryptography]` — генерация/верификация JWT
- `passlib[bcrypt]` — хеширование паролей