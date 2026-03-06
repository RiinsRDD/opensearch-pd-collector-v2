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

### Инфраструктура

- **PostgreSQL 15+** — СУБД для хранения настроек, паттернов, находок, задач.
- **Docker & Docker Compose** — контейнеризация (5 compose-файлов).
- **Prometheus & Grafana** — метрики и дашборды.

### Управление зависимостями

- Backend: `pip install -r requirements.txt` (с зафиксированными версиями).
- Frontend: `npm install` из `frontend/package.json`.
- Деплой через Git + Docker (без uv).

## Компоненты системы

1. **API Layer (`app/api/`):** REST-эндпоинты (auth, settings, indices, tasks, scanner).
2. **Service Layer (`app/services/`):** Бизнес-логика (scanner, detectors, jira_integration, opensearch_client, scheduler).
3. **Repository Layer (`app/db/repository.py`):** Универсальный CRUD-репозиторий.
4. **Domain Layer (`app/models/`):** SQLAlchemy ORM модели (7 моделей).
5. **Core (`app/core/`):** Конфигурация (`config.py`) и логирование (`logger.py`).
6. **Frontend (`frontend/`):** React SPA с Explorer-паттерном (Master-Detail).
7. **Background Scheduler:** Планировщик регулярных сканирований (`APScheduler`).
8. **Infrastructure:** Docker Compose стек (API, PostgreSQL, Prometheus, Grafana, Exporters).
