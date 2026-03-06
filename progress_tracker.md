# PDN Collector V2 Progress Tracker

Используйте этот чек-лист для отслеживания процесса пошаговой реализации:

## Бэкенд (FastAPI)

- [x] ✅ **M001: Базовая структура БД и ORM модели**
  - [x] Создан CRUDBase и настройки `pydantic-settings`
  - [x] Модели SQLAlchemy (Settings, Indices, PDN, Logs)
  - [x] Инициализирован Alembic, создана первая миграция
- [x] ✅ **M002: Настройки системы (Settings API)**
  - [x] Эндпоинты `/settings/global`, `/settings/indices`
  - [x] Эндпоинты `/settings/pdn-types`,`/settings/exclusions`
  - [x] Покрыто валидацией Pydantic
  - [x] Добавлено каскадное удаление: `DELETE /tags/{tag_name}` и написаны unit-тесты
- [x] ✅ **M003: Детекторы ПДн и клиент OpenSearch**
  - [x] Логика `OpenSearchClient` (генератор `search_after`)
  - [x] Детекторы: Phone, Email, FIO, Card (с поддержкой regex из БД)
  - [x] Написаны unit-тесты
- [x] ✅ **M004: Движок Сканера и Scanner API**
  - [x] Алгоритм `_traverse` (flatten JSON)
  - [x] Расчёт хеша `cache_key` и формирование `PDNPattern`/`PDNFinding`
  - [x] Эндпоинты API: `/scanner/scan`, `/scanner/logs`
- [x] ✅ **M005: Интеграция с Jira и Indices Tree API**
  - [x] Макет `JiraService`
  - [x] `/indices` API для древовидного представления данных
  - [x] Интеграция с историей задач (Tasks)

## Фронтенд (React, Vite, Tailwind)

- [ ] **M006: Frontend: Каркас и Роутинг**
  - [ ] Конфигурация Vite, TypeScript+Tailwind, ESLint
  - [ ] `App.tsx` (React Router) + `Header`, базовые верстки страниц
- [ ] **M007: Frontend: API Axios и Contexts**
  - [ ] Настроенный инстанс Axios (`client.ts`)
  - [ ] `SelectionContext` (Master-Detail state)
- [ ] **M008: Frontend: Master-Detail Dashboard и Settings UI**
  - [ ] Компонент `IndicesTree`
  - [ ] Правая панель Dashboard (вкладки Паттерн, Примеры, Сырой JSON)
  - [ ] UI страницы Settings (Глобальные, Регулярки, Исключения, Настройка Jira)

## Опционально

- [ ] **Настройка Docker окружения** (api, db, exporters, grafana, prometheus)
- [ ] **Настройка CI/CD**
- [ ] **Продакшен деплой**
