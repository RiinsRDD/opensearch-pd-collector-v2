# 13. Структура проекта (Project Structure)

Полная карта файлов проекта с назначением каждого элемента.

```
opensearch-pd-collector-v2/
│
├── .env                               # Переменные окружения (см. 14_env_and_config.md)
├── .gitignore                         # Единый gitignore (Python + Node.js)
├── Dockerfile                         # Multi-stage Dockerfile (builder + frontend-builder + runtime)
├── alembic.ini                        # Конфигурация Alembic (путь к миграциям, sqlalchemy.url)
├── requirements.txt                   # Python-зависимости; тесты: pytest, pytest-asyncio, pytest-cov, aiosqlite
├── pytest.ini                         # asyncio, --cov=app, xml+term, --cov-fail-under=40
├── docker-compose.yml                 # Единый compose с профилями: core, monitoring, full
├── docker-compose.override.yml        # Dev override: hot-reload, --reload
├── prometheus.yml                     # Ожидается compose-ом; на E.1 файла в корне нет
│
├── app/                               # ===== BACKEND (FastAPI) =====
│   ├── main.py                        # Создание FastAPI app, middleware, exception handlers, /metrics, /health
│   │
│   ├── core/                          # Ядро приложения
│   │   ├── config.py                  # Settings (pydantic-settings): DB, OpenSearch, Logs, JWT
│   │   ├── logger.py                  # setup_logging() — Loguru (stdout JSON + файлы)
│   │   └── metrics.py                 # Prometheus метрики: scanner, jira, db, http, scheduler
│   │
│   ├── db/                            # Слой данных
│   │   ├── session.py                 # AsyncSession, engine (asyncpg), get_db()
│   │   └── repository.py              # CRUDBase — generic CRUD (pk_field для композитных PK)
│   │
│   ├── models/                        # SQLAlchemy ORM модели
│   │   ├── __init__.py                # Реэкспорт: Base, PDN*, settings, Tag*, JiraTask, IndexOwner, ScannerLog, User, ScanFieldConfig
│   │   ├── base.py                    # declarative_base()
│   │   ├── pdn.py                     # PDNPattern, PDNFinding (FK relationship)
│   │   ├── settings.py                # SystemSetting, RegexRule, StatusSetting
│   │   ├── indices.py                 # IndexOwner
│   │   ├── tags.py                    # Tag, PatternTagLink (M2M)
│   │   ├── tasks.py                   # JiraTask
│   │   ├── logs.py                    # ScannerLog
│   │   └── scan_field_config.py       # ScanFieldConfig
│   │
│   ├── services/                      # Бизнес-логика
│   │   ├── scanner.py                 # ScannerService — ядро анализа (traverse, cache_key, tagging, sliding window)
│   │   ├── detectors.py               # PDNDetectors — поиск ФИО, телефонов, email, карт
│   │   ├── opensearch_client.py       # OpenSearchClient — connection pooling, search_after_generator
│   │   ├── jira_integration.py        # JiraService — retry logic (tenacity), rate limit handling
│   │   └── scheduler.py               # ScanScheduler — APScheduler (CronTrigger, metrics)
│   │
│   └── api/                           # REST API
│       ├── router.py                  # Подключение всех роутеров
│       ├── deps.py                    # DI: get_current_user, require_viewer/analyst/admin
│       └── endpoints/
│           ├── __init__.py
│           ├── auth.py                # POST /login, GET /me (JWT + bcrypt)
│           ├── settings.py            # 20+ эндпоинтов настроек
│           ├── index_owners.py        # CRUD /index-owners
│           ├── indices_tree.py        # GET / (+ full_document), PATCH/DELETE, POST /jira/tasks, GET /jira/history
│           ├── tasks.py               # GET / = alias history; POST / = 410
│           └── scanner.py             # POST /scan, GET /status, GET /logs
│
├── migrations/                        # ===== ALEMBIC МИГРАЦИИ =====
│   ├── env.py                         # Alembic env (async engine)
│   ├── script.py.mako                 # Шаблон миграции
│   └── versions/                      # 6 миграций
│       ├── 7ee6282b4ef6_initial_migration.py
│       ├── 914484850430_add_custom_message_to_pdn_pattern.py
│       ├── 9f2c1b3bf858_add_jira_task_history_fields.py
│       ├── cf1b3474db3e_add_users_table.py
│       ├── 13694664e7a5_add_missing_tables_scan_fields_index.py
│       └── 731ca325f61e_add_performance_indexes.py
│
├── frontend/                          # ===== FRONTEND (React + Vite + TypeScript) =====
│   ├── index.html                     # Точка входа HTML
│   ├── vite.config.ts                 # Vite config (react + tailwindcss плагины)
│   ├── package.json                   # Зависимости и npm-скрипты
│   ├── tsconfig.json / tsconfig.*.json
│   ├── eslint.config.js
│   └── src/
│       ├── main.tsx                   # Точка входа React (BrowserRouter обёртка)
│       ├── App.tsx                    # Корневой: AuthProvider → SelectionProvider → Header → Routes → StatusBar
│       ├── index.css                  # @import "tailwindcss"
│       ├── api/
│       │   └── client.ts              # Axios-клиент, authApi, indicesApi, scannerApi, settingsApi, types
│       ├── context/
│       │   ├── SelectionContext.tsx   # selectedPatterns + selectedIndexPattern
│       │   └── AuthContext.tsx        # user, loading, login(), logout(), автозагрузка /me
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Header.tsx         # Навигация, кнопка Jira (скрыта для viewer), поиск, профиль
│       │   │   ├── Sidebar.tsx        # Боковая навигация (не используется)
│       │   │   └── ScannerStatusBar.tsx # Статус сканера + polling + модалка логов
│       │   ├── modals/
│       │   │   ├── SingleScanModal.tsx # Реальный triggerScan через scannerApi (admin only)
│       │   │   └── ScannerLogsModal.tsx # Реальная загрузка логов
│       │   ├── settings/              # 8 вкладок настроек (read-only для non-admin)
│       │   │   ├── GlobalExceptions.tsx
│       │   │   ├── IndexExceptions.tsx
│       │   │   ├── IndexOwnersList.tsx
│       │   │   ├── PdnRegexList.tsx
│       │   │   └── ScanFieldsList.tsx
│       │   └── tree/
│       │       └── IndicesTree.tsx    # Дерево индексов (Explorer) — live API GET /indices, маппинг через utils/mapIndicesTree
│       ├── pages/
│       │   ├── Dashboard.tsx          # Master-Detail; raw tab = full_document или «нет документа»
│       │   ├── Settings.tsx           # Настройки (error/empty states, нет silent fallback)
│       │   ├── Tasks.tsx              # GET /indices/jira/history
│       │   └── Login.tsx              # Страница входа (username/password, 401/403 handling)
│       ├── mocks/
│       │   └── indicesTree.mock.ts    # Архив mockData дерева (UX-справочник, не импортируется в UI)
│       ├── types/
│       │   └── api.ts                 # Shared types: PDNPattern, JiraTask, ScannerStatus, etc.
│       └── utils/
│           ├── mapIndicesTree.ts      # Маппер API IndicesTreeResponse → UI IndexPatternNode[]
│           └── rbac.ts                # Хелперы RBAC: canCreateJira, canEditPattern, canDeletePattern, canScan, canWriteSettings                     
│
├── tests/                             # ===== ТЕСТЫ =====
│   ├── conftest.py                    # sqlite+aiosqlite, async_client, db_with_data, JWT override (admin)
│   ├── test_detectors.py              # Базовые тесты детекторов
│   ├── test_detectors_extended.py     # 23 теста: phone/email/card/fio, edge cases, multiple matches
│   ├── test_opensearch_client.py      # Unit тесты OS клиента
│   ├── test_scanner.py                # Базовые тесты сканера
│   ├── test_scanner_integration.py    # Интеграционные тесты сканера (6 тестов)
│   ├── test_settings.py               # Тесты настроек
│   ├── test_api_endpoints.py          # API тесты: indices, jira, settings, scanner, health, errors
│   └── seed_mock_data.py              # Идемпотентный seed демо-данных (python -m tests.seed_mock_data)
│
├── .github/workflows/                 # ===== CI/CD =====
│   └── ci.yml                         # GitHub Actions: pytest (coverage.xml), ruff, frontend, docker
│
├── docs/                              # ===== ДОКУМЕНТАЦИЯ =====
│   ├── 01_overview.md
│   ├── 02_database.md
│   ├── 03_scanner_engine.md
│   ├── 04_detectors.md
│   ├── 05_api_endpoints.md
│   ├── 06_settings_system.md
│   ├── 07_jira_integration.md
│   ├── 08_scheduler.md
│   ├── 09_auth_and_roles.md
│   ├── 10_frontend_spec.md
│   ├── 11_logging_and_monitoring.md
│   ├── 12_docker_and_infrastructure.md
│   ├── 13_project_structure.md
│   ├── 14_env_and_config.md
│   └── grafana-dashboards/
│       └── pdn-collector.json         # Grafana дашборд (12 панелей)
│
├── logs/                              # Логи (run.log, errors.log)
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
Frontend → GET /api/v1/indices → IndicesTree данные (selectinload)
Frontend → GET /api/v1/settings/global → Настройки для отображения
Frontend → POST /api/v1/scanner/scan/{pattern} → Запуск сканирования (scannerApi)
Frontend → POST /api/v1/indices/jira/tasks → Создание задач (indicesApi)
ScannerService → OpenSearchClient (pooling) → OpenSearch кластер
ScannerService → PDNDetectors → Анализ значений
ScannerService → Repository → PostgreSQL (PDNPattern, PDNFinding)
JiraService → httpx (retry) → Jira REST API
ScanScheduler → ScannerService (connection pooling)
Prometheus → /metrics → Grafana дашборд
```