# 3. Движок сканера (Scanner Engine)

Движок сканирования `ScannerService` (`app/services/scanner.py`) — ядро системы, отвечающее за работу с OpenSearch и рекурсивный анализ JSON-документов.

## Ключевые методы

| Метод | Описание |
|-------|----------|
| `_traverse(obj, path)` | Рекурсивный обход JSON. Возвращает список `(path, value)` для всех финальных текстовых значений с полным JSON-путём в dot-нотации |
| `_calculate_cache_key(index_pattern, field_path, pdn_type, context, extra_fields)` | SHA256-хэш от `"index_pattern|field_path|pdn_type|context|scan_fields"` |
| `_get_active_rules(db)` | Загрузка активных правил: regex, исключения, scan fields |
| `_apply_tag(cache_key, tag_code)` | Присвоение тега (`G`, `S`, `U`) к `PatternTagLink` |
| `_clear_single_scan_tags(index_pattern)` | Удаление всех тегов `S` для паттернов указанного индекса |
| `_save_examples(cache_key, examples, max_examples)` | Sliding window: оставляет последние N уникальных doc_id по found_at DESC |
| `update_examples_for_pattern(cache_key)` | Перескан индекса паттерна без массового тегирования; `_save_examples` + тег `U` только на этот `cache_key` |

## Логика работы

1. **Запрос к кластеру OpenSearch:**
   - `OpenSearchClient.search_after_generator()` — обход через `search_after` для получения результатов за пределами лимита 10 000 документов.
   - **Connection pooling:** `OpenSearchClient` использует один общий `httpx.AsyncClient` с пулом соединений (`max_connections=10`, `max_keepalive_connections=5`). Клиент работает как async context manager (`async with OpenSearchClient() as client:`) или можно вызвать `await client.close()`.

2. **Анализ документа (Flattening):**
   - `_traverse()` рекурсивно обходит JSON-документ. Поддерживает dict, list, примитивы. Собирает все финальные текстовые значения с полным путём (например, `hits.user.contacts.email`).

3. **Передача детектору:**
   - Каждое строковое значение, его JSON-путь и список правил передаются в `PDNDetectors.detect(text, field_path, rules)` для проверки по активным регулярным выражениям и исключениям.

4. **Агрегация и кэширование:**
   - Совпадения группируются по `(index_pattern, field_path, pdn_type, context_type)`, вычисляется `cache_key` через SHA256. В `context_type` могут быть `base`, `structured_key`, `free_text`, `ambiguous`. Дополнительно учитываются значения `Scan Fields`.
   - Если ключ уже есть в `pdn_patterns` — обновляется `last_seen` и `hit_count++`.
   - Если ключа нет — создаётся новый `PDNPattern` + сохраняются примеры `PDNFinding`.

5. **Sliding Window примеров (новая логика):**
   - При КАЖДОМ скане собираются ВСЕ найденные примеры для каждого `cache_key`.
   - После обработки всех документов вызывается `_save_examples()`:
     1. Загружаются существующие примеры из БД (ORDER BY found_at DESC)
     2. Дедуп по `doc_id` — новые примеры перезаписывают старые
     3. Сортировка по `found_at` DESC
     4. Оставляются топ-N (N = `EXAMPLES_COUNT` из настроек, дефолт 3)
     5. Старые удаляются, новые вставляются

## Режимы сканирования и тегирование

| Режим | Тег | Логика примеров |
|-------|-----|-----------------|
| **Global Scan** | `G` | Сканирование всех активных индексов. Примеры обновляются через sliding window (топ-N последних) |
| **Single Scan** | `S` | Сканирование конкретного индекса. Перед запуском удаляются старые `S` теги. Примеры обновляются через sliding window |
| **Update Examples** | `U` | `POST /api/v1/indices/examples/update/{cache_key}`: фон, скан индекса паттерна, sliding window, тег `U` только на запрошенный ключ |

## Метрики (Prometheus)

Автоматически собираются в процессе сканирования:

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `pdn_scan_duration_seconds` | Histogram | `scan_type`, `index_pattern` | Длительность сканирования |
| `pdn_findings_total` | Counter | `pdn_type`, `status` | Общее количество найденных ПДн |
| `pdn_scan_errors_total` | Counter | `scan_type`, `error_type` | Ошибки сканирования |
| `pdn_active_scans` | Gauge | `scan_type` | Количество активных сканирований |

Инструментирование:
```python
active_scans.labels(scan_type=scan_type).inc()
try:
    with scan_duration.labels(scan_type=scan_type, index_pattern=index_pattern).time():
        findings = await self.scan_index(...)
    scan_findings.labels(pdn_type='total', status='scanned').inc(findings_count)
finally:
    active_scans.labels(scan_type=scan_type).dec()
```

## Настройка количества примеров

Параметр `EXAMPLES_COUNT` в таблице `system_settings` (тип `int`, дефолт 3) задаёт максимальное количество примеров, хранящихся для одного `cache_key`. Изменяется через API `/api/v1/settings/global` или UI на вкладке "Общие".