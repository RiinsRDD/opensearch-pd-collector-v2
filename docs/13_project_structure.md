# 13. Структура проекта (Project Structure)

Полная карта файлов проекта с назначением каждого элемента.

```
opensearch-pd-collector-v2/
│
├── .env                               # Переменные окружения (см. 14_env_and_config.md)
├── .gitignore                         # Единый gitignore (Python + Node.js)
├── Dockerfile                         # Docker-образ для API
├── alembic.ini                        # Конфигурация Alembic (путь к миграциям, sqlalchemy.url)
├── requirements.txt                   # Python-зависимости с зафиксированными версиями
│
├── docker-compose.yml                 # API сервис
├── docker-compose.postgres.yml        # PostgreSQL 15
├── docker-compose.exporters.yml       # postgres_exporter + node_exporter
├── docker-compose.prometheus.yml      # Prometheus
├── docker-compose.grafana.yml         # Grafana
│
├── app/                               # ===== BACKEND (FastAPI) =====
│   ├── main.py                        # Создание FastAPI app, подключение роутера, health check
│   │
│   ├── core/                          # Ядро приложения
│   │   ├── config.py                  # Settings (pydantic-settings): DB, OpenSearch, Logs
│   │   └── logger.py                  # setup_logging() — Loguru (stdout JSON + файлы)
│   │
│   ├── db/                            # Слой данных
│   │   ├── session.py                 # AsyncSession, engine (asyncpg), get_db()
│   │   └── repository.py             # CRUDBase — generic CRUD (get, get_multi, create, update, remove)
│   │
│   ├── models/                        # SQLAlchemy ORM модели
│   │   ├── __init__.py                # Реэкспорт всех моделей (для Alembic)
│   │   ├── base.py                    # declarative_base()
│   │   ├── pdn.py                     # PDNPattern, PDNFinding
│   │   ├── settings.py                # SystemSetting, RegexRule, StatusSetting
│   │   ├── indices.py                 # IndexOwner
│   │   ├── tags.py                    # Tag, PatternTagLink (M2M)
│   │   ├── tasks.py                   # JiraTask
│   │   └── logs.py                    # ScannerLog
│   │
│   ├── services/                      # Бизнес-логика
│   │   ├── scanner.py                 # ScannerService — ядро анализа (traverse, cache_key, tagging)
│   │   ├── detectors.py               # PDNDetectors — поиск ФИО, телефонов, email, карт
│   │   ├── opensearch_client.py       # OpenSearchClient — get_indices(), search_after_generator()
│   │   ├── jira_integration.py        # JiraService — создание задач в Jira (mock)
│   │   └── scheduler.py              # ScanScheduler — APScheduler (CronTrigger, каркас)
│   │
│   └── api/                           # REST API
│       ├── router.py                  # Подключение всех роутеров (auth, settings, indices, tasks, scanner)
│       └── endpoints/
│           ├── __init__.py
│           ├── auth.py                # POST /login, GET /me (mock)
│           ├── settings.py            # GET/POST /global, GET/POST /indices, GET/POST /statuses, DELETE /tags
│           ├── index_owners.py        # CRUD /index-owners (настройки Jira assignee для индексов)
│           ├── indices_tree.py        # GET /, POST /examples/update, POST/GET /jira/tasks, GET /jira/history
│           ├── tasks.py               # GET /, POST / (заглушка)
│           └── scanner.py             # POST /scan/{pattern}, GET /status, GET /logs
│
├── migrations/                        # ===== ALEMBIC МИГРАЦИИ =====
│   ├── env.py                         # Alembic env (async engine)
│   ├── script.py.mako                 # Шаблон миграции
│   └── versions/
│       ├── 7ee6282b4ef6_initial_migration.py
│       ├── 914484850430_add_custom_message_to_pdn_pattern.py
│       └── 9f2c1b3bf858_add_jira_task_history_fields.py
│
├── frontend/                          # ===== FRONTEND (React + Vite + TypeScript) =====
│   ├── index.html                     # Точка входа HTML
│   ├── vite.config.ts                 # Vite config (react + tailwindcss плагины)
│   ├── package.json                   # Зависимости и npm-скрипты
│   ├── tsconfig.json / tsconfig.*.json
│   ├── eslint.config.js
│   └── src/
│       ├── main.tsx                   # Точка входа React (BrowserRouter обёртка)
│       ├── App.tsx                    # Корневой: SelectionProvider → Header → Routes → StatusBar
│       ├── index.css                  # @import "tailwindcss"
│       ├── api/
│       │   └── client.ts             # Axios-клиент, indicesApi, settingsApi
│       ├── context/
│       │   └── SelectionContext.tsx   # selectedPatterns + selectedIndexPattern
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Header.tsx         # Навигация, кнопка Jira, поиск, профиль
│       │   │   ├── Sidebar.tsx        # Боковая навигация (не используется)
│       │   │   └── ScannerStatusBar.tsx # Статус сканера (внизу экрана)
│       │   ├── modals/
│       │   │   ├── SingleScanModal.tsx # Параметры одиночного сканирования
│       │   │   └── ScannerLogsModal.tsx # Логи сканера
│       │   ├── settings/
│       │   │   ├── GlobalExceptions.tsx # Вкладка "Глобальные исключения"
│       │   │   ├── IndexExceptions.tsx  # Вкладка "Исключения индексов"
│       │   │   ├── IndexOwnersList.tsx  # Вкладка "Владельцы (Jira)"
│       │   │   ├── PdnRegexList.tsx     # Вкладка "Регулярки ПДн"
│       │   │   └── ScanFieldsList.tsx   # Вкладка "Дополнительные поля"
│       │   └── tree/
│       │       └── IndicesTree.tsx    # Дерево индексов (Explorer, ~18KB)
│       └── pages/
│           ├── Dashboard.tsx          # Главная: Master-Detail (350px tree + details)
│           ├── Settings.tsx           # Настройки системы
│           └── Tasks.tsx              # Глобальная история задач
│
├── tests/                             # ===== ТЕСТЫ =====
│   ├── test_detectors.py              # Тесты детекторов ПДн
│   └── seed_mock_data.py             # Скрипт для заполнения БД тестовыми данными
│
├── logs/                              # Логи (run.log, errors.log)
├── docs/                              # Документация (этот файл)
├── docs_archived/                     # Архив старой документации
├── old/                               # Устаревший код
└── notes_*.txt                        # Рабочие заметки
```

## Связи между компонентами

```
Frontend (React)
    ↓ Axios (VITE_API_BASE_URL)
FastAPI API Layer (app/api/)
    ↓ DI / direct import
Service Layer (app/services/)
    ↓ SQLAlchemy ORM
Repository Layer (app/db/)
    ↓ asyncpg
PostgreSQL
```

```
Frontend → GET /api/v1/indices → IndicesTree данные
Frontend → GET /api/v1/settings/global → Настройки для отображения
Frontend → POST /api/v1/scanner/scan/{pattern} → Запуск сканирования
Frontend → POST /api/v1/indices/jira/tasks → Создание задач
ScannerService → OpenSearchClient → OpenSearch кластер
ScannerService → PDNDetectors → Анализ значений
ScannerService → Repository → PostgreSQL (PDNPattern, PDNFinding)
JiraService → httpx → Jira REST API
ScanScheduler → ScannerService (каркас, не подключён)
```
