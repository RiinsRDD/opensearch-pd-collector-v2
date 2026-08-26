# 1. Обзор архитектуры (Overview)

## Описание

PDN Collector V2 — микросервис для автоматического поиска и сбора персональных данных (ПДн) в кластере OpenSearch. Система сканирует индексы на наличие ФИО, телефонов, email-адресов и номеров банковских карт согласно настроенным правилам.

Сервис разработан по принципам Clean Architecture и предоставляет REST API, умный поиск ФИО и фоновую обработку.

## Технологический стек

### Backend (Python 3.12+)

| Пакет | Версия | Назначение |
|-------|--------|------------|
| FastAPI | 0.135.1 | Асинхронный веб-фреймворк REST API |
| SQLAlchemy | 2.0.47 | ORM (asyncpg драйвер) |
| Alembic | 1.18.4 | Миграции БД |
| Pydantic | 2.12.5 | Валидация данных |
| pydantic-settings | 2.13.1 | Управление конфигурацией из `.env` |
| APScheduler | 3.11.2 | Планировщик фоновых задач |
| Loguru | 0.7.3 | Логирование (консоль + файл + JSON) |
| httpx | 0.28.1 | Асинхронный HTTP-клиент (OpenSearch, Jira) |
| opensearch-py | 3.1.0 | Клиент OpenSearch |
| asyncpg | 0.31.0 | Асинхронный драйвер PostgreSQL |
| psycopg2-binary | 2.9.11 | Синхронный драйвер PostgreSQL (для Alembic) |
| uvicorn | 0.41.0 | ASGI-сервер |
| python-jose | 3.5.0 | JWT токены |
| passlib | 1.7.4 | Хеширование паролей |
| tenacity | 8.5.0 | Retry logic с exponential backoff |
| prometheus-client | 0.20.0 | Метрики Prometheus /metrics |

### Frontend

| Пакет | Версия | Назначение |
|-------|--------|------------|
| React | 19.2.0 | UI-фреймворк |
| Vite | 7.3.1 | Сборщик с HMR |
| TypeScript | 5.9.3 | Типизация |
| Tailwind CSS | 4.2.1 | Utility-first стилизация |
| Axios | 1.13.6 | HTTP-клиент |
| React Router DOM | 7.13.1 | Роутинг SPA |
| Lucide React | 0.575.0 | Иконки |
| react-json-view-lite | 2.5.0 | Рендер JSON-документов |
| clsx | 2.1.1 | CSS-классы по условию |
| tailwind-merge | 3.5.0 | Мердж Tailwind-классов |

### Инфраструктура

- **PostgreSQL 15+** — СУБД для хранения настроек, паттернов, находок, задач.
- **Docker & Docker Compose** — контейнеризация (единый `docker-compose.yml` с профилями: `core`, `monitoring`, `full`).
- **Prometheus & Grafana** — метрики и дашборды (эндпоинт `/metrics`).
- **GitHub Actions CI** — автоматический запуск тестов, линта, сборки Docker.

### Управление зависимостями

- Backend: `pip install -r requirements.txt` (с зафиксированными версиями).
- Frontend: `npm install` из `frontend/package.json`.
- Деплой через Git + Docker (multi-stage build).

## Компоненты системы

1. **API Layer (`app/api/`):** REST-эндпоинты (auth, settings, indices, tasks, scanner) — все async.
2. **Service Layer (`app/services/`):** Бизнес-логика (scanner, detectors, jira_integration, opensearch_client, scheduler).
3. **Repository Layer (`app/db/repository.py`):** Универсальный CRUD-репозиторий (`CRUDBase` с PK field).
4. **Domain Layer (`app/models/`):** SQLAlchemy ORM модели (9 моделей, relationships).
5. **Core (`app/core/`):** Конфигурация (`config.py`), логирование (`logger.py`), метрики (`metrics.py`).
6. **Frontend (`frontend/`):** React SPA с Explorer-паттерном (Master-Detail).
7. **Background Scheduler:** APScheduler с `CronTrigger` — глобальное сканирование каждый час.
8. **Infrastructure:** Единый Docker Compose с профилями (core, monitoring, full), Prometheus exporters.

## Ключевые реализованные фичи

- ✅ JWT Auth + RBAC (Viewer/Analyst/Admin) с персональными Jira токенами
- ✅ Реальная Jira интеграция с retry logic (tenacity) и rate limit handling
- ✅ Sliding Window примеров (топ-3 последних по found_at)
- ✅ Connection pooling для OpenSearch (httpx.AsyncClient, max_connections=10)
- ✅ Асинхронные эндпоинты (N+1 fix в indices_tree через selectinload)
- ✅ Prometheus метрики: scanner, jira, db, http, scheduler
- ✅ Global exception handler с единым форматом ошибок + Request ID
- ✅ Multi-stage Dockerfile + единый compose с профилями
- ✅ GitHub Actions CI (pytest, ruff, mypy, frontend build, docker)
- ✅ Тесты: unit, integration, API (coverage ≥ 40%)
- ✅ Seed демо-данных: `python -m tests.seed_mock_data` (пользователи, настройки, паттерны, Jira)