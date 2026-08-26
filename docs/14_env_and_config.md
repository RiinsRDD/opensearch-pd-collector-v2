# 14. Переменные окружения и конфигурация (Environment & Config)

## Файл `.env`

Расположен в корне проекта. Читается через `pydantic-settings` (`app/core/config.py`).

Пример содержимого для Docker:
```
POSTGRES_SERVER=db
POSTGRES_USER=pdn_user
POSTGRES_PASSWORD=pdn_password
POSTGRES_DB=pdn_collector
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```

Для локальной разработки:
```
POSTGRES_SERVER=localhost
POSTGRES_USER=pdn_user
POSTGRES_PASSWORD=pdn_password
POSTGRES_DB=pdn_collector
```

## Класс `Settings` (`app/core/config.py`)

```python
class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "PDN Collector V2"
    VERSION: str = "2.0.0"

    # OpenSearch
    OPENSEARCH_URL: str = "https://es-od.usvc.global.bcs"
    OS_USERNAME: str = ""
    OS_PASSWORD: str = ""
    OS_VERIFY_CERTS: bool = False

    # PostgreSQL
    POSTGRES_USER: str = "pdn_user"
    POSTGRES_PASSWORD: str = "pdn_password"
    POSTGRES_DB: str = "pdn_collector"
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"  # Изменить в production!
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней

    # Logs
    LOG_DIR: Path = Path("logs")
    RUN_LOG_NAME: str = "run.log"
    ERR_LOG_NAME: str = "errors.log"

    # Prometheus (опционально)
    PROMETHEUS_MULTIPROC_DIR: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
```

### Computed Properties

| Property | Формула |
|----------|---------|
| `DATABASE_URL` | `postgresql://{user}:{password}@{server}:{port}/{db}` |
| `DATABASE_URL_ASYNC` | `postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}` |

### Источники значений

`model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`

Приоритет: переменная окружения ОС → `.env` файл → значение по умолчанию в классе.

## Полный список переменных окружения

### Backend (.env)

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `PROJECT_NAME` | `PDN Collector V2` | Название проекта (для FastAPI docs) |
| `VERSION` | `2.0.0` | Версия API |
| `OPENSEARCH_URL` | `https://es-od.usvc.global.bcs` | URL кластера OpenSearch |
| `OS_USERNAME` | `""` | Логин OpenSearch |
| `OS_PASSWORD` | `""` | Пароль OpenSearch |
| `OS_VERIFY_CERTS` | `False` | Проверка SSL-сертификатов |
| `POSTGRES_USER` | `pdn_user` | Пользователь БД |
| `POSTGRES_PASSWORD` | `pdn_password` | Пароль БД |
| `POSTGRES_DB` | `pdn_collector` | Имя базы данных |
| `POSTGRES_SERVER` | `db` | Хост БД (в docker: `db`, локально: `localhost`) |
| `POSTGRES_PORT` | `5432` | Порт БД |
| `LOG_DIR` | `logs` | Директория для логов |
| `RUN_LOG_NAME` | `run.log` | Имя файла общих логов |
| `ERR_LOG_NAME` | `errors.log` | Имя файла ошибок |
| `JWT_SECRET_KEY` | `change-me-in-production` | **Обязательно сменить в production!** |
| `JWT_ALGORITHM` | `HS256` | Алгоритм подписи JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Время жизни access token (7 дней) |
| `PROMETHEUS_MULTIPROC_DIR` | `""` | Для multiprocess Prometheus (gunicorn) |

### Docker Compose (в `docker-compose.yml`)

| Переменная | По умолчанию | Сервис | Описание |
|------------|-------------|--------|----------|
| `POSTGRES_USER` | `pdn_user` | `db` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | `pdn_password` | `db` | Пароль PostgreSQL |
| `POSTGRES_DB` | `pdn_collector` | `db` | Имя БД |
| `GRAFANA_USER` | `admin` | `grafana` | Логин Grafana |
| `GRAFANA_PASSWORD` | `admin` | `grafana` | Пароль Grafana |

### Frontend

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `VITE_API_BASE_URL` | `/api/v1` | Базовый URL для API-запросов (в `frontend/src/api/client.ts`) |

## Alembic (`alembic.ini`)

Ключевая настройка — `sqlalchemy.url`. Для production устанавливается через переменную окружения или переопределяется в `migrations/env.py` (использует `settings.DATABASE_URL_ASYNC`).

## Профили Docker Compose

В едином `docker-compose.yml` используются профили:

| Профиль | Сервисы | Команда запуска |
|---------|---------|-----------------|
| `core` | `api`, `db` | `docker compose --profile core up -d` |
| `monitoring` | `postgres_exporter`, `node_exporter`, `prometheus`, `grafana` | `docker compose --profile monitoring up -d` |
| `full` | все сервисы | `docker compose --profile full up -d` |

Dev режим (с hot-reload, использует `docker-compose.override.yml`):
```bash
docker compose --profile core up
```

## Seed демо-данных

После `alembic upgrade head` и при доступной PostgreSQL (`POSTGRES_SERVER=localhost` на хосте или `db` в Docker):

```bash
python -m tests.seed_mock_data
```

Скрипт читает `DATABASE_URL_ASYNC` из `app.core.config.Settings` (те же переменные, что и API). Подробности содержимого — в `docs/02_database.md`.