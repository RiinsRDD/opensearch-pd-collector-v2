# 3. Движок сканера (Scanner Engine)

Движок сканирования `ScannerService` (`app/services/scanner.py`) — ядро системы, отвечающее за работу с OpenSearch и рекурсивный анализ JSON-документов.

## Ключевые методы

| Метод | Описание |
|-------|----------|
| `_traverse(obj, path)` | Рекурсивный обход JSON. Возвращает список `(path, value)` для всех финальных текстовых значений с полным JSON-путём в dot-нотации |
| `_generate_cache_key(index_pattern, field_path, pdn_type, context)` | SHA256-хэш от `"index_pattern|field_path|pdn_type|context|scan_fields"` |
| `process_document(doc, index_pattern)` | Обработка одного документа OS: flatten → detect → match |
| `_apply_tag(cache_key, tag_code)` | Присвоение тега (`G`, `S`, `U`) к `PatternTagLink` |
| `_clear_single_scan_tags(index_pattern)` | Удаление всех тегов `S` для паттернов указанного индекса |
| `_save_examples(cache_key, examples, status, scan_type)` | Сохранение `PDNFinding` с логикой замены/дополнения примеров |

## Логика работы

1. **Запрос к кластеру OpenSearch:**
   - `OpenSearchClient.search_after_generator()` — обход через `search_after` для получения результатов за пределами лимита 10 000 документов.

2. **Анализ документа (Flattening):**
   - `_traverse()` рекурсивно обходит JSON-документ. Поддерживает dict, list, примитивы. Собирает все финальные текстовые значения с полным путём (например, `hits.user.contacts.email`).

3. **Передача детектору:**
   - Каждое строковое значение, его JSON-путь и список правил передаются в `PDNDetectors.detect(text, field_path, rules)` для проверки по активным регулярным выражениям и исключениям.

4. **Агрегация и кэширование:**
   - Совпадения группируются по `(index_pattern, field_path, pdn_type, context_type)`, вычисляется `cache_key` через SHA256. В `context_type` могут быть `base`, `structured_key`, `free_text`, `ambiguous`. Дополнительно учитываются значения `Scan Fields`.
   - Если ключ уже есть в `pdn_patterns` — обновляется `last_seen`.
   - Если ключа нет — создаётся новый `PDNPattern` + сохраняются примеры `PDNFinding`.

## Режимы сканирования и тегирование

| Режим | Тег | Логика примеров |
|-------|-----|-----------------|
| **Global Scan** | `G` | Стандартное сканирование всех активных индексов |
| **Single Scan** | `S` | Перед запуском удаляются старые `S` теги индекса. Новые примеры добавлены к существующим |
| **Update Examples** | `U` | Если статус `new` → замена примеров. Иначе → добавление к старым |
