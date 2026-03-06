# Архитектура системы поиска ПДн в OpenSearch

> Техническое описание: структура БД, логика работы, фронтенд

---

## 1. Общая цель системы

Система предназначена для автоматического поиска персональных данных (ПДн) в индексах OpenSearch: номера телефонов, email-адреса, номера банковских карт, ФИО. В кластере может быть 300+ паттернов индексов, структура документов внутри индексов неоднородна — документы могут сильно отличаться друг от друга.

Доступ к маппингу индексов отсутствует. Схема строится динамически в процессе сканирования.

---

## 2. Сканер OpenSearch

### 2.1 Общий подход

- Батчевое чтение по 10 000 документов через `search_after` (scroll устарел).
- Рекурсивный обход каждого документа: flatten JSON в список пар `(dot.notation.path, value)`.
- Накопительная «живая схема» индекса: union всех ключей из обработанных батчей — вместо маппинга.
- Асинхронный обход индексов с семафором (не более 10 одновременно) — ускорение в 5–20 раз на 300+ индексах.
- Внутри батча обработка CPU-bound: `multiprocessing` или `ProcessPoolExecutor`.

### 2.2 Расписание запусков

- Cron раз в час — предсказуемо, пользователь знает актуальность данных.
- Защита от двойного запуска: при старте проверяем `scan_runs` на статус `running`. Если предыдущий ещё идёт — новый не стартует.
- Дополнительная проверка: если `last finished_at` < 55 минут назад — не запускать.

### 2.3 Детекторы ПДн

Два режима в зависимости от типа значения поля:

**Режим A — «чистое» значение** (поле `id: 79265524242`):

Регулярка матчит всё значение целиком. Имя поля само является контекстом.

**Режим B — свободный текст** (поле `raw_message`, `log`, `body`):

Регулярка с capture groups захватывает совпадение и окружение. Затем двухэтапный анализ контекста:

- **Этап 1** — ищем структурный ключ: паттерн `[ключ][разделитель : = => =''][совпадение]`. Если найден — берём только ключ как prefix.
- **Этап 2** — если структурного ключа нет — фиксируем `context_type: free_text`, короткий фрагмент только для логов, в кэш-ключ не идёт.
- **Этап 3** — prefix и suffix прогоняются через те же детекторы ПДн. Если срабатывает — обрезаем или сохраняем `null`. Это защита от кейса «ФИО → пробел → телефон».

### 2.4 Классификация контекста

Каждое найденное ПДн получает один из трёх типов:

- `structured_key` — найден `"some_id": 79265...`. Надёжный prefix, самый ценный случай.
- `free_text` — свободный текст, структурного ключа нет. Prefix не извлекается.
- `ambiguous` — что-то похожее на ключ, но уверенности нет (длинная фраза перед `:`).

Один и тот же телефон в `raw_message` как `structured_key` и как `free_text` — две разные записи в БД.

---

## 3. Структура базы данных

### 3.1 Таблица `scan_runs` — журнал прогонов

Каждый запуск получает UUID. Связана с `pdn_patterns` (`first_run_id`, `last_run_id`) и `pdn_findings` (`run_id`).

```sql
CREATE TABLE scan_runs (
    run_id              UUID PRIMARY KEY,
    started_at          TIMESTAMP,
    finished_at         TIMESTAMP,
    status              VARCHAR,  -- running / done / failed
    indices_scanned     INTEGER,
    total_new_patterns  INTEGER,
    total_hits          INTEGER
);
```

### 3.2 Таблица `pdn_patterns` — уникальные паттерны утечек

Один `cache_key` = один уникальный способ утечки (индекс + поле + тип ПДн + контекст). Обновляется при каждом прогоне.

```sql
CREATE TABLE pdn_patterns (
    cache_key                VARCHAR PRIMARY KEY,
    -- SHA256(index_pattern + field_path + pdn_type + key_hint)

    index_pattern            VARCHAR,       -- logstash-* (паттерн, не конкретный индекс)
    field_path               VARCHAR,       -- dot.notation путь в документе
    pdn_type                 VARCHAR,       -- PHONE / EMAIL / CARD / FIO
    context_type             VARCHAR,       -- structured_key / free_text / ambiguous
    key_hint                 VARCHAR,       -- "some_id" если structured_key

    container_name           VARCHAR,       -- kubernetes.container.name если есть
    microservice             VARCHAR,       -- NameOfMicroService если есть

    first_seen               TIMESTAMP,
    first_run_id             UUID REFERENCES scan_runs(run_id),
    last_seen                TIMESTAMP,
    last_run_id              UUID REFERENCES scan_runs(run_id),
    hit_count                INTEGER,       -- накапливается каждый прогон

    sample_doc_ids           VARCHAR[],     -- массив до 3 doc_id для быстрой проверки
    sample_doc_timestamps    TIMESTAMP[],

    status                   VARCHAR DEFAULT 'new',
    -- new / confirmed / false_positive / archived

    false_positive_comment   VARCHAR,
    false_positive_marked_at TIMESTAMP,
    false_positive_marked_by VARCHAR
);
```

### 3.3 Таблица `pdn_findings` — сырые доказательства

Пишется **один раз** при первом обнаружении паттерна. Максимум 3 строки на один `cache_key`. Не перезаписывается автоматически — только по запросу через кнопку «Обновить примеры». Хранит полный документ целиком (`full_document JSONB`).

```sql
CREATE TABLE pdn_findings (
    id              SERIAL PRIMARY KEY,
    cache_key       VARCHAR REFERENCES pdn_patterns(cache_key),
    run_id          UUID REFERENCES scan_runs(run_id),

    doc_id          VARCHAR,       -- _id документа в OpenSearch
    index_pattern   VARCHAR,       -- паттерн индекса

    raw_value       VARCHAR,       -- само найденное значение
    field_path      VARCHAR,
    prefix_raw      VARCHAR,       -- контекст до совпадения
    suffix_raw      VARCHAR,       -- контекст после совпадения
    key_hint        VARCHAR,

    container_name  VARCHAR,
    microservice    VARCHAR,

    full_document   JSONB,         -- весь документ целиком
    found_at        TIMESTAMP
);
```

### 3.4 Таблица `targeted_scans` — точечные прогоны

Для ручного запуска сканирования по конкретному индексу с выбором глубины и периода. Поддерживает продолжение с места остановки через курсор `search_after`.

```sql
CREATE TABLE targeted_scans (
    id                    SERIAL PRIMARY KEY,
    run_id                UUID REFERENCES scan_runs(run_id),
    index_pattern         VARCHAR,
    requested_by          VARCHAR,
    requested_at          TIMESTAMP,

    max_documents         INTEGER,   -- лимит документов (напр. 100 000)
    time_from             TIMESTAMP,
    time_to               TIMESTAMP,

    documents_scanned     INTEGER DEFAULT 0,
    current_search_after  VARCHAR,   -- курсор для продолжения после сбоя
    batches_done          INTEGER DEFAULT 0,
    status                VARCHAR,   -- pending / running / done / failed

    new_patterns_found    INTEGER,
    existing_confirmed    INTEGER,
    finished_at           TIMESTAMP
);
```

### 3.5 Таблица `findings_refresh` — запросы на обновление примеров

```sql
CREATE TABLE findings_refresh (
    id            SERIAL PRIMARY KEY,
    cache_key     VARCHAR REFERENCES pdn_patterns(cache_key),
    requested_by  VARCHAR,
    requested_at  TIMESTAMP,
    completed_at  TIMESTAMP,
    status        VARCHAR,  -- pending / done / failed
    new_findings  INTEGER
);
```

### 3.6 Таблица `index_owners` — ответственные по индексам

```sql
CREATE TABLE index_owners (
    id              SERIAL PRIMARY KEY,
    index_pattern   VARCHAR UNIQUE,
    team_name       VARCHAR,
    contact_person  VARCHAR,
    contact_email   VARCHAR,
    notes           VARCHAR
);
```

### 3.7 Таблица `correction_tasks` — задачи на исправление

```sql
CREATE TABLE correction_tasks (
    id              SERIAL PRIMARY KEY,
    index_pattern   VARCHAR REFERENCES index_owners(index_pattern),
    cache_keys      VARCHAR[],   -- какие паттерны вошли в задачу

    created_at      TIMESTAMP,
    created_by      VARCHAR,

    status          VARCHAR DEFAULT 'open',
    -- open / in_progress / resolved / rejected

    assignee        VARCHAR,     -- prefill из index_owners, можно переопределить
    comment         VARCHAR,
    resolved_at     TIMESTAMP,
    resolved_by     VARCHAR
);
```

### 3.8 Таблицы `correction_task_comments` и `correction_task_history`

```sql
CREATE TABLE correction_task_comments (
    id          SERIAL PRIMARY KEY,
    task_id     INTEGER REFERENCES correction_tasks(id),
    author      VARCHAR,
    text        VARCHAR,
    created_at  TIMESTAMP
);

CREATE TABLE correction_task_history (
    id          SERIAL PRIMARY KEY,
    task_id     INTEGER REFERENCES correction_tasks(id),
    changed_by  VARCHAR,
    changed_at  TIMESTAMP,
    field_name  VARCHAR,
    old_value   VARCHAR,
    new_value   VARCHAR
);
```

### 3.9 Таблица `tags` и `pdn_pattern_tags`

```sql
CREATE TABLE tags (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR UNIQUE,
    color       VARCHAR,       -- hex для фронта
    description VARCHAR,
    created_by  VARCHAR,
    created_at  TIMESTAMP
);

CREATE TABLE pdn_pattern_tags (
    pattern_cache_key  VARCHAR REFERENCES pdn_patterns(cache_key),
    tag_id             INTEGER REFERENCES tags(id),
    assigned_by        VARCHAR,
    assigned_at        TIMESTAMP,
    PRIMARY KEY (pattern_cache_key, tag_id)
);
```

### 3.10 Таблица `users`

```sql
CREATE TABLE users (
    id        SERIAL PRIMARY KEY,
    username  VARCHAR UNIQUE,
    email     VARCHAR,
    role      VARCHAR   -- admin / analyst / viewer
);
```

### 3.11 Таблица `regex_whitelist`

Паттерны значений, которые точно не ПДн, несмотря на срабатывание детектора. Проверяется до записи в `findings`.

```sql
CREATE TABLE regex_whitelist (
    id          SERIAL PRIMARY KEY,
    pattern     VARCHAR,       -- регулярка
    pdn_type    VARCHAR,       -- к какому типу относится
    description VARCHAR,       -- почему не ПДн (напр. "тестовые номера 790000xxxxx")
    created_by  VARCHAR,
    created_at  TIMESTAMP
);
```

### 3.12 Таблица `audit_log`

```sql
CREATE TABLE audit_log (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES users(id),
    action       VARCHAR,
    entity_type  VARCHAR,   -- pattern / finding / task / owner / tag
    entity_id    VARCHAR,
    old_value    JSONB,
    new_value    JSONB,
    created_at   TIMESTAMP
);
```

---

## 4. Логика записи при сканировании

### 4.1 Основной прогон

1. Нашли совпадение → вычислили `cache_key`.
2. Проверяем `pdn_patterns`: если `status = false_positive` → пропускаем полностью.
3. Если паттерн **новый** → `INSERT` в `pdn_patterns` + `INSERT` в `pdn_findings` (если findings по этому `cache_key` < 3).
4. Если паттерн **уже есть** → `UPDATE hit_count`, `last_seen`, `last_run_id`, `sample_doc_ids`. В `pdn_findings` **не пишем**.
5. `sample_doc_ids`: добавляем новый `doc_id` если его нет и длина массива < 3.

### 4.2 Формирование cache_key

```
structured_key:  SHA256(index_pattern + field_path + pdn_type + key_hint)
free_text:       SHA256(index_pattern + field_path + pdn_type + "free_text")
ambiguous:       SHA256(index_pattern + field_path + pdn_type + "ambiguous")
```

### 4.3 Обновление примеров по запросу (кнопка «Перезаписать примеры»)

1. `INSERT` в `findings_refresh` со статусом `pending`.
2. Сканер берёт `pending` задачи → `DELETE FROM pdn_findings WHERE cache_key = ?`.
3. Запускает мини-прогон по `index_pattern` паттерна.
4. Пишет новые findings как обычно (до 3 штук).
5. `UPDATE findings_refresh SET status = done`.
6. `pdn_patterns` не трогаем — кэш и статистика остаются.

### 4.4 Кнопка «Пересканировать с нуля»

```sql
DELETE FROM pdn_findings
WHERE cache_key IN (
    SELECT cache_key FROM pdn_patterns WHERE index_pattern = ?
);
DELETE FROM pdn_patterns WHERE index_pattern = ?;
```

После этого → запускается `targeted_scan` по этому `index_pattern`. Если данных в индексе уже нет — таблицы останутся пустыми. Это ответ на «мы всё почистили».

---

## 5. Точечный прогон (targeted scan)

### 5.1 Пагинация 100k документов

OpenSearch отдаёт максимум 10 000 за запрос. Для 100 000 документов за период:

1. Запускаем `targeted_scan`: `max_documents=100000`, `time_from=now-1h`, sort по `@timestamp`.
2. Батч 1: `search_after=null`, `size=10000` → обрабатываем → сохраняем последний timestamp как курсор.
3. `UPDATE targeted_scans SET current_search_after=cursor, documents_scanned+=10000`.
4. Батч 2: `search_after=cursor`, те же фильтры. И так далее.
5. Курсор сохраняется в БД — если процесс упал, продолжаем с места остановки.
6. Стоп: `documents_scanned >= max_documents` или документы кончились.

### 5.2 Когда использовать

- Точечная проверка после того как команда сообщила об исправлении.
- Быстрая проверка конкретного индекса без полного прогона всего кластера.
- Анализ за конкретный временной период.

---

## 6. Фронтенд

### 6.1 Общий layout

Классический master-detail: слева дерево индексов, справа содержимое выбранного.

```
┌─────────────────────┬──────────────────────────────────────────┐
│  Индексы            │  Детали                                  │
│                     │                                          │
│  ▶ logstash-*   12  │  [Паттерн] [Примеры] [Сырой документ]   │
│  ▼ nginx-*       3  │                                          │
│    ├ PHONE       2  │                                          │
│    └ EMAIL       1  │                                          │
│  ▶ kafka-*       7  │                                          │
└─────────────────────┴──────────────────────────────────────────┘
```

- Левая панель: список `index_pattern` с количеством паттернов. Новые подсвечиваются.
- Раскрытие по уровням: `index_pattern` → тип ПДн (PHONE/EMAIL/CARD/FIO) → конкретные паттерны (`field_path` + `key_hint`).
- Иконки статуса прямо в строке: new / confirmed / false_positive / archived.
- Правая панель: три вкладки — Паттерн, Примеры, Сырой документ.

### 6.2 Вкладка «Паттерн»

- Все поля из `pdn_patterns`: первый/последний раз найден, `hit_count`, `microservice`, `container`.
- Кнопки: «Пересканировать индекс», «Обновить примеры», «Отметить как false positive», «В архив».
- Форма редактирования тегов.

### 6.3 Вкладка «Примеры»

- Три строки из `pdn_findings`: `doc_id`, `raw_value`, `prefix`, `suffix`, `found_at`.
- По клику на строку — открывается сырой документ в третьей вкладке.

### 6.4 Вкладка «Сырой документ»

- `full_document` рендерится как JSON-дерево с подсветкой синтаксиса (`react-json-view`).
- Найденное значение подсвечивается в дереве.
- Документ отображается полностью, даже если весит 20 МБ — с lazy-рендером узлов.

### 6.5 Секции навигации

- `Все | Новые | Подтверждённые | False Positive | Архив` — фильтрация по `status`.
- Фильтры: по типу ПДн, микросервису, контейнеру, тегу, дате обнаружения.
- Мультиселект паттернов → создать задачу на исправление / обновить существующую / удалить выбранные.

### 6.6 Логика кнопки «Завести задачу на исправление»

1. Проверяем `index_owners`: если нет записи → предупреждение «Не заполнены ответственные».
2. Проверяем `correction_tasks`: если есть `open/in_progress` по этому `index_pattern` → показываем ссылку на существующую задачу.
3. Если всё чисто → форма: `assignee` (prefill из `index_owners`), `comment`, список `cache_keys`.
4. После подтверждения → `INSERT` в `correction_tasks`.

Задачи заводятся **только вручную**. Это защита от спама ложными срабатываниями.

### 6.7 Раздел «Ответственные» (index_owners)

- Таблица всех индексов с командами и контактами.
- CRUD: добавить, редактировать, удалить запись.
- Используется при создании задач и для email-уведомлений.

### 6.8 Раздел «Задачи» (correction_tasks)

- Список задач с фильтрацией по статусу и индексу.
- Детали задачи: список паттернов, история изменений, комментарии.
- Смена статуса: `open → in_progress → resolved / rejected`.
- Визуальная подсветка индексов с открытой задачей в левом дереве.

---

## 7. Дополнительный функционал

### 7.1 Whitelist регулярок

Таблица `regex_whitelist`: паттерны значений которые точно не ПДн несмотря на срабатывание детектора. Например тестовые номера `79000000000` или внутренние ID похожие на телефон. Проверяется до записи в `findings`.

### 7.2 Дашборд и аналитика

- Динамика: сколько новых паттернов появлялось по неделям.
- Топ индексов по количеству ПДн.
- Тренд по типам: PHONE растёт, EMAIL стабилен.
- Топ полей где чаще всего находят ПДн — помогает находить системные проблемы.

### 7.3 Сравнение прогонов

Diff между двумя `scan_run`: что появилось, что исчезло, что осталось. Особенно полезно после того как команда говорит «мы всё починили».

### 7.4 Экспорт

Выгрузка выбранных паттернов и findings в CSV или PDF. Нужно для передачи команде которая будет исправлять.

### 7.5 Уведомления

При появлении новых паттернов в индексе где уже есть открытая задача — автоматически добавлять комментарий к задаче. Или слать в Slack/email ответственному из `index_owners`.

### 7.6 Роли и права

- `viewer` — только просмотр.
- `analyst` — менять статусы, теги, создавать задачи.
- `admin` — удалять, управлять ответственными, запускать сканер.

### 7.7 Audit log

Таблица `audit_log`: любое действие пользователя — кто, когда, что изменил. На случай если кто-то случайно удалит важное или поставит `false_positive` на реальную утечку.

---

## 8. Технологический стек

- **Сканер**: Python, `asyncio` + `asyncio.Semaphore(10)`, `ProcessPoolExecutor` для CPU-bound обработки.
- **OpenSearch клиент**: `opensearch-py` с поддержкой `search_after`.
- **База данных**: PostgreSQL.
- **Бэкенд API**: FastAPI, REST эндпоинты для всех операций.
- **Фронтенд**: React, `react-json-view` для отображения сырых документов.
- **Расписание**: cron или APScheduler, запуск раз в час с защитой от двойного запуска.

---

*— конец документа —*
