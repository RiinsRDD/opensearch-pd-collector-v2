# 14. Переменные окружения и конфигурация (Environment & Config)

## Файл `.env`

Расположен в корне проекта. Читается через `pydantic-settings` (`app/core/config.py`).

Текущее содержимое:

```
POSTGRES_SERVER=localhost
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

    # Logs
    LOG_DIR: Path = Path("logs")
    RUN_LOG_NAME: str = "run.log"
    ERR_LOG_NAME: str = "errors.log"
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

### Docker Compose

| Переменная | По умолчанию | Файл | Описание |
|------------|-------------|------|----------|
| `POSTGRES_USER` | `pdn_user` | `docker-compose.postgres.yml` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | `pdn_password` | `docker-compose.postgres.yml` | Пароль PostgreSQL |
| `POSTGRES_DB` | `pdn_collector` | `docker-compose.postgres.yml` | Имя БД |
| `GRAFANA_USER` | `admin` | `docker-compose.grafana.yml` | Логин Grafana |
| `GRAFANA_PASSWORD` | `admin` | `docker-compose.grafana.yml` | Пароль Grafana |

### Frontend

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `VITE_API_BASE_URL` | `/api/v1` | Базовый URL для API-запросов (в `frontend/src/api/client.ts`) |

## Alembic (`alembic.ini`)

Ключевая настройка — `sqlalchemy.url`. Для production устанавливается через переменную окружения или переопределяется в `migrations/env.py` (использует `settings.DATABASE_URL`).
