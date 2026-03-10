# 10. Frontend Specification

Frontend — Single Page Application (SPA) с паттерном Master-Detail (Explorer View).

## Стек технологий

| Пакет | Версия | Назначение |
|-------|--------|------------|
| React | 19.2.0 | UI-фреймворк |
| TypeScript | 5.9.3 | Типизация |
| Vite | 7.3.1 | Сборщик (HMR) |
| Tailwind CSS | 4.2.1 | Utility-first стилизация (через `@tailwindcss/vite` плагин) |
| React Router DOM | 7.13.1 | SPA-роутинг |
| Axios | 1.13.6 | HTTP-клиент |
| Lucide React | 0.575.0 | Иконки |
| react-json-view-lite | 2.5.0 | Рендер JSON-документов |
| clsx | 2.1.1 | CSS-классы по условию |
| tailwind-merge | 3.5.0 | Мердж Tailwind-классов |

## Карта файлов

```
frontend/
├── index.html                         # Точка входа HTML
├── vite.config.ts                     # Конфигурация Vite (react + tailwindcss плагины)
├── tsconfig.json                      # Корневой TypeScript config
├── tsconfig.app.json                  # TypeScript config для app
├── tsconfig.node.json                 # TypeScript config для node
├── eslint.config.js                   # ESLint конфигурация
├── package.json                       # Зависимости и скрипты
└── src/
    ├── main.tsx                       # Точка входа React (BrowserRouter)
    ├── App.tsx                        # Корневой компонент (Layout + Routes)
    ├── index.css                      # Глобальные стили (@import "tailwindcss")
    ├── api/
    │   └── client.ts                  # Axios-клиент и API-функции
    ├── context/
    │   └── SelectionContext.tsx        # React Context для выделения паттернов
    ├── components/
    │   ├── layout/
    │   │   ├── Header.tsx             # Верхняя панель навигации
    │   │   ├── Sidebar.tsx            # Боковая навигация (НЕ ИСПОЛЬЗУЕТСЯ в текущем Layout)
    │   │   └── ScannerStatusBar.tsx   # Нижняя панель статуса сканера
    │   ├── modals/
    │   │   ├── SingleScanModal.tsx    # Модальное окно одиночного сканирования
    │   │   └── ScannerLogsModal.tsx   # Модальное окно логов сканера
    │   └── tree/
    │       └── IndicesTree.tsx        # Компонент дерева индексов (Explorer)
    ├── pages/
    │   ├── Dashboard.tsx              # Главная страница (Master-Detail layout)
    │   ├── Settings.tsx               # Страница настроек
    │   └── Tasks.tsx                  # Страница глобальных задач Jira
    ├── assets/                        # Статические ресурсы
    └── utils/                         # Утилиты (пока пусто)
```

## Роутинг (`App.tsx`)

| Путь | Компонент | Описание |
|------|-----------|----------|
| `/` | `Dashboard` | Главная: дерево + детали |
| `/settings` | `Settings` | Настройки системы |
| `/tasks` | `Tasks` | Глобальная история задач |
| `*` | `Navigate to "/"` | Редирект на главную |

Layout: `Header` (сверху) → `main` (контент) → `ScannerStatusBar` (внизу). Всё обёрнуто в `SelectionProvider`.

## Компоненты

### `Header.tsx` (`components/layout/`)

Тёмная навигационная панель (`bg-slate-900`, высота `h-14`):

- **Логотип** «PDN Collector» (ссылка на `/`)
- **Навигация**: «Сканер» (`/`), «Задачи» (`/tasks`)
- **Кнопка «Завести задачу в Jira»**: Активна при `selectedPatterns.length > 0` ИЛИ `selectedIndexPattern !== null`. Показывает счётчик `confirmed`
- **Поиск** по хэшам/индексам (input)
- **Уведомления** (Bell icon с красным dot)
- **Меню профиля** (dropdown): «Настройки системы» (`/settings`), «Мои Задачи Jira» (`/tasks`), «Выйти»

### `Sidebar.tsx` (`components/layout/`)

> **НЕ ИСПОЛЬЗУЕТСЯ** в текущем Layout. Содержит навигацию: Дерево индексов, Статистика сканера, Задачи Jira, Настройки. Может использоваться в будущем.

### `ScannerStatusBar.tsx` (`components/layout/`)

Нижняя панель. Показывает текущий статус сканера и сканируемый паттерн индекса. При клике открывает `ScannerLogsModal`.

### `IndicesTree.tsx` (`components/tree/`)

Основной компонент дерева (~18 KB). Иерархическая структура:

- **Уровень 1**: Паттерн индекса (`bcs-tech-logs-*`). Счётчик новых заданий (красный бейдж `+5`). Клик выделяет индекс, двойной клик сворачивает/разворачивает.
- **Уровень 2**: Тип ПДн (`PHONE`, `EMAIL`, `FIO`, `CARD`)
- **Уровень 3**: Контекст нахождения (`base` 📄, `structured_key` 🔑, `free_text` 📝, `ambiguous` ⚠️).
- **Уровень 4**: Cache-key (`PDNPattern`). Содержит статусные точки, `field_path`, inline-бейджи и значения `extra_fields` (Scan Fields), иконки тегов.

**Выделение**: Строго одиночное — один cache_key за раз. Выделение индекса также меняет `selectedIndexPattern`.

Кнопки над деревом: «Развернуть всё» / «Свернуть всё». Фильтрация по статусу и тегам.

**Props**:

```typescript
interface IndicesTreeProps {
    selectedCacheKeys: string[];
    selectedIndexPattern: string | null;
    onSelectPatterns: (patterns: PDNPattern[], idxPattern?: string | null) => void;
}
```

**Экспортируемый тип**:

```typescript
interface PDNPattern {
    cache_key: string;
    index_pattern: string;
    field_path: string;
    pdn_type: string;
    context_type: string;
    status: string;
    hit_count: number;
    tags: string[];
}
```

### `SingleScanModal.tsx` (`components/modals/`)

Модальное окно одиночного сканирования конкретного индекса. Параметры:

- Количество часов (за какой период)
- Лимит документов (`maxDocs`)

### `ScannerLogsModal.tsx` (`components/modals/`)

Модальное окно с логами сканера за последние запуски. Открывается по клику на `ScannerStatusBar`.

## Страницы

### `Dashboard.tsx` (`pages/`)

Главная страница с Master-Detail layout:

- **Левая панель** (по умолчанию 350px, с возможностью ресайза пользователем): `IndicesTree`
- **Правая панель** (flex-1): зависит от выделения:
  - **Если выбран cache_key** → 3 вкладки:
    1. **Паттерн**: статистика, статус (dropdown select), теги, кнопки действий, поле для custom_message
    2. **Примеры**: закэшированные контексты (doc_id, raw_value, field_path)
    3. **Сырой документ**: JSON-viewer через `react-json-view-lite`
  - **Если выбран индекс** → таблица задач Jira с поиском, кнопка «Одиночное сканирование»
  - **Если ничего не выбрано** → заглушка «Выберите элемент»

### `Settings.tsx` (`pages/`)

Страница настроек с секциями (переключение через боковое меню):

- **Общие**: управление глобальными параметрами (интервалы, лимиты), активными типами ПДн (динамические чекбоксы на основе базы) и правилами фильтрации индексов (regex/pattern exclude/include).
- **Словари парсеров ПДн**: управление массивами настроек по каждому типу ПДн. Массивы редактируются общим блоком (через запятую) в inline-редакторе (без модальных окон), и при сохранении автоматически переводятся в нижний регистр, дедублицируются и сортируются по алфавиту для оптимизации поиска. Поле «Неизвестные домены» (unknown_mail_service_parts) доступно только для чтения.
- **Регулярки ПДн** (`PdnRegexList.tsx`): таблица управления системными и пользовательскими типами ПДн и их базовыми регулярными выражениями (с поддержкой добавления и удаления).
- **Настройка Jira**: управление параметрами для интеграции (Base URL, ключи проекта, типы задачи, кастомные поля атрибутов для CMDB).
- **Глобальные исключения** (`GlobalExceptions.tsx`): управление таблицей `regex_rules` (exclude, prefix, suffix, full_path) с динамическими вкладками типов ПДн.
- **Исключения индексов** (`IndexExceptions.tsx`): управление `IndexKeyExclusion` по каждому отдельному индексу
- **Доп. поля (Scan Fields)** (`ScanFieldsList.tsx`): управление дополнительными полями (например `kubernetes.container.name`), которые добавляются в Cache Key для изоляции инцидентов по микросервисам.
- **Статусы и Цвета**: настройка цветов для `StatusSetting`
- **Управление тегами**: глобальное удаление тегов

> **Отказоустойчивость**: `Settings.tsx` и `ScanFieldsList.tsx` реализованы с fallback-механизмом. Если API-бэкенд недоступен или возвращает некорректные данные, интерфейс загружает тестовые "mock"-данные вместо вечной блокирующей загрузки или выброса React Error (белый экран).

### `Tasks.tsx` (`pages/`)

Глобальная страница задач Jira:

- Список всех задач с пагинацией
- Фильтрация и поиск

## State Management

### `SelectionContext.tsx` (`context/`)

React Context для синхронизации состояния выделения между `IndicesTree`, `Header` и `Dashboard`:

```typescript
interface SelectionContextType {
    selectedPatterns: PDNPattern[];
    setSelectedPatterns: (patterns: PDNPattern[]) => void;
    selectedIndexPattern: string | null;
    setSelectedIndexPattern: (idx: string | null) => void;
}
```

### API-клиент (`api/client.ts`)

Axios-инстанс с `baseURL = VITE_API_BASE_URL || '/api/v1'`:

```typescript
export const indicesApi = {
    getTree: () => apiClient.get('/indices')
};

export const settingsApi = {
    getSettings: () => apiClient.get('/settings')
};

export const exclusionsApi = {
    getGlobal: () => apiClient.get('/settings/exclusions/global'),
    addGlobal: (data) => apiClient.post('/settings/exclusions/global', data),
    deleteGlobal: (id) => apiClient.delete(`/settings/exclusions/global/${id}`),
    getIndex: (indexPattern) => apiClient.get('/settings/exclusions/index', { params: { index_pattern: indexPattern } }),
    addIndex: (data) => apiClient.post('/settings/exclusions/index', data),
    deleteIndex: (id) => apiClient.delete(`/settings/exclusions/index/${id}`),
    getIndicesList: () => apiClient.get('/settings/exclusions/indices-list')
};
```

## Команды разработки

```bash
cd frontend
npm install        # Установка зависимостей
npm run dev        # Dev-сервер (Vite HMR)
npm run build      # Production-сборка (tsc + vite build)
npm run lint       # ESLint проверка
npm run preview    # Preview production-сборки
```

## Переменная окружения

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `VITE_API_BASE_URL` | `/api/v1` | Базовый URL для API-запросов |
