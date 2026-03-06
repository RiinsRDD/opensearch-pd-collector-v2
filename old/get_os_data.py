# get_os_data.py

import requests
import json
import re
import time
import urllib3
import csv
import logging
import logging.handlers

from pathlib import Path
from datetime import datetime
from requests.auth import HTTPBasicAuth
from collections import defaultdict
from functools import lru_cache

import settings as st


def setup_logger(logger_name, log_path, log_name):
    logs_dir = Path(log_path)
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / log_name

    log_format = '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'
    formatter = logging.Formatter(log_format)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if not logger.hasHandlers():
        if 'err' in log_name:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
        else:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def normalize_name(value: str) -> str:
    value = value.replace('[', '_').replace(']', '')
    return re.sub(r'[^a-zA-Z0-9]+', '_', value).strip('_').lower()


def initialize_pattern_validators():
    """Инициализация валидаторов для каждого типа данных"""
    st.PATTERNS['email']['validator'] = get_valid_emails
    st.PATTERNS['phone']['validator'] = get_valid_phones
    st.PATTERNS['card']['validator'] = get_valid_cards
    st.PATTERNS['fio']['validator'] = get_valid_fio


def fetch_opensearch_request_with_retry(url, method='GET', body=None, max_attempts=5):
    data = json.dumps(body) if body else None
    
    for attempt in range(max_attempts):
        try:
            print(f"Выполнение запроса: {method} {url} (Попытка {attempt + 1}/{max_attempts}).")
            
            resp = requests.request(
                method,
                url,
                auth=HTTPBasicAuth(st.decode(st.USERNAME), st.decode(st.PASSWORD)),
                headers=st.HEADERS,
                data=data,
                timeout=60,
                verify=False
            )
            
            resp.raise_for_status()
            print(f"Запрос успешно выполнен.")
            return resp.json()

        except requests.exceptions.HTTPError as e:
            if resp.status_code in [429, 500, 502, 503, 504]:
                if attempt < max_attempts - 1:
                    sleep_time = 2 ** attempt
                    print(f"Ошибка {resp.status_code}, ожидание {sleep_time}с перед повтором...")
                    time.sleep(sleep_time)
                    continue
                else:
                    print(f"Попытки исчерпаны. Ошибка {e.response.status_code}.")
                    return {}
            else:
                print(f"Неповторяемая ошибка HTTP {e.response.status_code}.")
                return {}

        except requests.exceptions.RequestException as e:
            if attempt < max_attempts - 1:
                print(f"Сетевая ошибка, ожидание 5с перед повтором... (Попытка {attempt + 1}/{max_attempts}).")
                time.sleep(5)
                continue
            else:
                print(f"Повторная сетевая ошибка. Прекращение работы.")
                return {}
    
    return {}


def parse_indices(indices, exclude_indices_keyword=st.EXCLUDE_INDICES_KEYWORDS):
    try:
        patterns = {}
        digit_pattern = re.compile(r'[.-]\d+.*$')

        for item in indices:
            if 'index' in item:
                index_name = item['index']

                should_exclude = any(index_name.startswith(keyword) for keyword in exclude_indices_keyword)
                if should_exclude:
                    continue
                
                match = digit_pattern.search(index_name)
                if match:
                    base_name = index_name[:match.start()]
                    pattern = base_name + '*'
                else:
                    pattern = index_name
                
                if pattern not in patterns:
                    patterns[pattern]= 0
                patterns[pattern] += 1
        
        return patterns
    
    except Exception as e:
        print(f"ERROR in parse_indices: An error occurred during processing: {e}")
        return {}


def is_valid_mobile_body(clean_digits, invalid_def_codes):
    """
    Техническая проверка "очищенного" номера (пункты 2, 3, 4).
    Принимает строку только из цифр.
    """
    # 2. Нормализация длины и получение DEF-кода
    if len(clean_digits) == 10:
        def_code = clean_digits[0:3]
        body = clean_digits
    elif len(clean_digits) == 11 and clean_digits[0] in ('7', '8'):
        def_code = clean_digits[1:4]
        body = clean_digits[1:]
    else:
        return False # Неверная длина для мобильного РФ

    # 3. Проверка по черному списку кодов (94x, 97x и т.д.)
    if def_code in invalid_def_codes:
        return False

    # 4. Проверка на фейк (все цифры одинаковые, например 9999999999)
    if len(set(body)) == 1:
        return False

    return True


def get_valid_phones(value):
    """
    Находит все телефоны и возвращает только те, что:
    - не содержат паттерны из exclude_patterns
    - перед ними нет exclude_prefixes
    - после них нет suffix_exclude
    """
    valid_phones = []
    
    phone_cfg = st.PATTERNS['phone']
    exclude_patterns = phone_cfg['exclude_patterns']
    prefix_exclude = phone_cfg.get('prefix_exclude', [])
    suffix_exclude = phone_cfg.get('suffix_exclude', [])
    invalid_def_codes = phone_cfg['invalid_def_codes']

    for match in phone_cfg['regex'].finditer(value):
        phone = match.group()
        start, end = match.start(), match.end()

        # 1. Проверяем исключения внутри самого номера
        if any(pattern in phone for pattern in exclude_patterns):
            continue

        # 2. Проверяем исключения по ПРЕФИКСАМ (перед номером)
        if any(
            start >= len(px) and value[start - len(px):start] == px
            for px in prefix_exclude
        ):
            continue

        # 3. Проверяем исключения по ПОСТФИКСАМ (после номера)
        # Проверяем, не начинается ли строка сразу за номером с запрещенного текста
        if any(
            value[end:end + len(sx)] == sx
            for sx in suffix_exclude
        ):
            continue

        # 4. Техническая валидация
        clean_digits = ''.join(filter(str.isdigit, phone))
        if not is_valid_mobile_body(clean_digits, invalid_def_codes): 
            continue

        valid_phones.append(phone)

    return valid_phones


@lru_cache(maxsize=8192)
def is_known_mail_service(email: str) -> bool:
    try:
        domain = email.split('@', 1)[1].lower()
    except (IndexError, AttributeError):
        return False

    domain_parts = set(domain.split('.'))

    mail_services = st.PATTERNS['email']['mail_service_names']

    return not domain_parts.isdisjoint(mail_services)


def get_valid_emails(value):  # (value: str) -> list[str]
    result = []

    email_cfg = st.PATTERNS['email']
    exclude = email_cfg['exclude_patterns']

    for email in email_cfg['regex'].finditer(value):
        email_str = email.group() # сохраняем как строку
        email_lc = email.group().lower()

        # exclude
        if exclude and any(pat in email_lc for pat in exclude):
            continue

        # проверка сервиса
        if not is_known_mail_service(email_lc):
            # сохраняем неизвестные части домена
            try:
                domain = email_lc.split('@', 1)[1]
                st.UNKNOWN_MAIL_SERVICE_PARTS.add(domain)
            except IndexError:
                pass

            continue

        result.append(email_str)

    return result


def luhn_check(number):  # (number: str) -> bool
    try:
        digits = [int(d) for d in number]
        checksum = 0
        parity = len(digits) % 2

        for i, d in enumerate(digits):
            if i % 2 == parity:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d

        return checksum % 10 == 0
    except Exception as e:
        return False


def get_valid_cards(value):  # (value: str)
    results = []

    card_cfg = st.PATTERNS['card']
    # card_bins = card_cfg['card_bins']

    allowed_bins = card_cfg['card_bank_bins_4']

    for match in st.CARD_REGEX.finditer(value):
        original = match.group()

        # нормализация ТОЛЬКО для проверки
        normalized = re.sub(r"[ -]", "", original)

        # строго 16 цифр
        if len(normalized) != 16:
            continue

        # BIN
        # if not normalized.startswith(card_bins):
        #     continue

        # ПРОВЕРКА BIN: если первых 4 цифр нет в списке разрешенных — пропускаем
        if normalized[:4] not in allowed_bins:
            continue

        # Luhn
        if not luhn_check(normalized):
            continue

        # сохраняем ИСХОДНОЕ значение
        results.append(original)

    return results


def get_valid_fio(value):
    results = []
    
    fio_cfg = st.PATTERNS['fio']

    surn_ends_cis = fio_cfg['surn_ends_cis']
    surn_ends_wolrd = fio_cfg['surn_ends_world']
    patron_ends = fio_cfg['patron_ends']
    fio_special_markers = fio_cfg['fio_special_markers']
    
    # Объединяем для проверки
    # all_surn_ends = surn_ends_cis + surn_ends_wolrd

    for match in st.FIO_REGEX.finditer(value):
        # group(1) берет текст без начального пробела
        original = match.group(1).strip()
        
        # Разбиваем и по пробелам, и по дефисам для точной проверки маркеров
        # "Мамед-оглы" станет ["мамед", "оглы"]
        words_lower = re.split(r'[\s\-]+', original.lower())

        # 1. Отчества
        has_patronymic = any(w.endswith(patron_ends) for w in words_lower)
        
        # 2. Фамилии
        has_surname = any(w.endswith(surn_ends_cis) for w in words_lower)
        
        # 3. Спец-маркеры (теперь поймает "оглы" даже внутри "Мамед-оглы")
        is_extra = any(w in fio_special_markers for w in words_lower)

        if has_patronymic or has_surname or is_extra:
            results.append(original)

    return results


def load_cache():
    """Загружает кэш из файла как set"""
    cache = set()
    if st.CACHE_FILE.exists():
        try:
            with open(st.CACHE_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Изменяем порядок: index, type, field (как в result.csv)
                    key = (row['index'], row['type'], row['field'])
                    cache.add(key)
            print(f"Загружен кэш из {st.CACHE_FILE}: {len(cache)} записей")
            run_log.info(f"Загружен кэш из {st.CACHE_FILE}: {len(cache)} записей")
        except Exception as e:
            print(f"Ошибка при загрузке кэша: {e}")
            run_log.error(f"Ошибка при загрузке кэша: {e}")
    return cache


def save_to_cache(cache_set):
    """Сохраняет весь кэш в файл (set)"""
    try:
        with open(st.CACHE_FILE, 'w', newline='', encoding='utf-8') as f:
            # Порядок полей: index, type, field
            writer = csv.DictWriter(f, fieldnames=['index', 'type', 'field'])
            writer.writeheader()
            for key in sorted(cache_set):
                writer.writerow({'index': key[0], 'type': key[1], 'field': key[2]})
        print(f"Кэш сохранён: {len(cache_set)} записей")
        run_log.info(f"Кэш сохранён: {len(cache_set)} записей")
    except Exception as e:
        print(f"Ошибка при сохранении в кэш: {e}")
        run_log.info(f"Ошибка при сохранении в кэш: {e}")


def load_results():
    """Загружает существующие результаты"""
    results = {}
    if st.RESULT_FILE.exists():
        try:
            with open(st.RESULT_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = (row['index'], row['type'], row['field'])
                    results[key] = row
            print(f"Загружены результаты из {st.RESULT_FILE}: {len(results)} записей")
        except Exception as e:
            print(f"Ошибка при загрузке результатов: {e}")
    return results


def traverse(obj, path="", result_list=None, current_key=None):
    """Рекурсивный обход структуры данных"""
    if result_list is None:
        result_list = []

    if isinstance(obj, (str, int, float)):
        value_str = str(obj)

        # Проверяем все типы данных из PATTERNS
        for data_type, pattern_config in st.PATTERNS.items():
            # --- ШАГ 1: ПРОВЕРКА ИСКЛЮЧЕНИЙ ПО КЛЮЧУ ---
            # Извлекаем список исключений для конкретного типа (например, для 'phone')
            exclude_keys = pattern_config.get('exclude_keys', [])

            # Если текущий ключ (например, 'id') есть в списке исключений для этого типа
            if exclude_keys and current_key in exclude_keys:
                continue # Пропускаем этот валидатор и переходим к следующему (например, к 'email')

            # Проверяем глобальные флаги для обратной совместимости
            if data_type == "email" and not st.IS_EMAIL:
                continue
            if data_type == "phone" and not st.IS_PHONE:
                continue
            if data_type == "card" and not st.IS_CARD:
                continue
            if data_type == "fio" and not st.IS_FIO:
                continue

            # Используем валидатор из конфигурации
            validator = pattern_config.get('validator')
            if validator:
                found_values = validator(value_str)
                if found_values:
                    # Создаем стандартизованный объект результата
                    result_obj = {
                        "field": path,
                        "type": data_type,
                        "values": found_values,
                        "found_count": len(found_values)
                    }
                    
                    # Добавляем сырое значение если нужно
                    if st.SAVE_FIELD_OBJ_VALUE:
                        result_obj[path] = obj
                    
                    result_list.append(result_obj)

    elif isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            # Передаем k как current_key
            traverse(v, new_path, result_list, current_key=k)
            
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]" if path else f"[{i}]"
            # Пробрасываем текущий ключ родителя дальше
            traverse(item, new_path, result_list, current_key=current_key)

    return result_list


def aggregate_matches(matches):
    """
    Агрегирует найденные совпадения по полю и типу.
    Ограничение по EXAMPLES_COUNT применяется для values, doc_ids, timestamps и examples.
    Полные field_count и total_count сохраняются.

    Пример входящих matches:
    matches = [
        {
            'field': 'user.email',
            'type': 'email',
            'values': ['a@a.ru', 'b@b.ru'],
            'found_count': 2,
            'doc_id': 'abc123',
            '@timestamp': '2026-02-05T10:00:00Z',
            '_source': { ... весь документ ... }
        },
        {
            'field': 'client.phone',
            'type': 'phone',
            'values': ['+7999...'],
            'found_count': 1,
            'doc_id': 'abc123',
            '_source': { ... тот же документ ... }
        }
    ]
    """
    aggregated = defaultdict(lambda: {
        'field_count': 0,
        'total_count': 0,
        'values': [],
        'doc_ids': [],
        'timestamps': [],
        'examples': {},
        '_seen_values': set()
    })

    for match in matches:
        key = (match['field'], match['type'])
        info = aggregated[key]

        # Полная статистика
        info['field_count'] += 1
        info['total_count'] += match['found_count']

        for value in match['values']:
            
            # пропускаем повторы
            if value in info['_seen_values']:
                continue

            info['_seen_values'].add(value)

             # лимит примеров
            if len(info['values']) >= st.EXAMPLES_COUNT:
                continue

            # Добавляем в values/doc_ids/timestamps с ограничением EXAMPLES_COUNT
            info['values'].append(value)
            info['doc_ids'].append(match.get('doc_id'))
            info['timestamps'].append(match.get('@timestamp'))

            # Формируем examples с ограничением EXAMPLES_COUNT
            example_key = f"example_{len(info['examples']) + 1}"
            info['examples'][example_key] = {
                'value': value,
                'doc_id': match.get('doc_id'),
                '@timestamp': match.get('@timestamp'),
                'raw_document': match.get('_source') if st.SAVE_FIELD_OBJ_VALUE else None
            }
            
    # удаляем служебное поле
    for info in aggregated.values():
        info.pop('_seen_values', None)

    return aggregated


def parse_index(pattern):
    """
    Вход:
        index pattern (logs-*)
        документы OpenSearch (батч, например 10000)

    Выход:
        matches: list[dict], hits: int|0

    Каждый элемент matches = одно поле одного документа,
    в котором найдены значения заданного типа.
    """

    all_matches = []
    
    try:
        url = f"{st.OPENSEARCH_URL}/{pattern}/_search"
        data = fetch_opensearch_request_with_retry(url, body=st.BODY)
        
        hits = data.get("hits", {}).get("hits", [])
        total_hits_obj = data.get("hits", {}).get("total", {})
        if isinstance(total_hits_obj, dict):
            total_matching = total_hits_obj.get('value', 0)
        else:
            total_matching = total_hits_obj
        print(f"  Найдено документов: {len(hits)} (за период: {total_matching}, ограничение batch: {st.BATCH_SIZE})")
        
        for h in hits:
            source = h.get("_source", {})
            doc_id = h.get("_id")
            timestamp = source.get("@timestamp", None)

            matches = traverse(source)

            for m in matches:
                m['index'] = pattern
                m['doc_id'] = doc_id
                m['@timestamp'] = timestamp
                m['_source'] = source

            all_matches.extend(matches)
        
        return all_matches, len(hits)
    
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Запрос не удался: {e}")
        return [], 0


def get_unique_path(path):  # (path: Path) -> Path
    """
    Если path существует, возвращает path с суффиксом _1, _2, ...
    """
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def save_index_data(pattern, aggregated, directory, include_raw=False):
    """
    Сохраняет агрегированные данные в JSON.
    include_raw=True → raw_data, include_raw=False → out_json
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    clean_pattern = normalize_name(pattern.rstrip('*'))
    date_suffix = datetime.now().strftime("%d%b%y").upper()  # Например: "_30DEC25"

    for (field, data_type), info in aggregated.items():
        field_clean = normalize_name(field)

        base_filename = f"{clean_pattern}__{data_type}__{field_clean}_{date_suffix}.json"
        base_path = directory / base_filename
        path = get_unique_path(base_path)

        # функция вызывается дважды, нам не нужно одно и то же логгировать
        if not include_raw:
            run_log.info(f"filename: {path.name}")

        examples = {}
        for key, ex in info['examples'].items():
            ex_copy = ex.copy()
            if not include_raw:
                ex_copy.pop('raw_document', None)
            examples[key] = ex_copy

        data = {
            'index': pattern,
            'field': field,
            'type': data_type,
            'field_count': info['field_count'],
            'total_count': info['total_count'],
            'values': info['values'],
            'doc_ids': info['doc_ids'],
            'timestamps': info['timestamps'],
            'examples': examples
        }

        with path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def save_to_results(results_data):
    """
    Сохраняет результаты в CSV.
    Предполагается, что все counts, timestamps и create_ts/update_ts уже рассчитаны в main().
    """
    try:
        fieldnames = [
            'index', 'type', 'field',
            'examples', 'doc_ids', 'timestamps',
            'create_ts', 'update_ts',
            'total_count', 'previous_count', 'current_count',
            'processed_docs'
        ]

        with open(st.RESULT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted(results_data.values(), key=lambda x: (x['index'], x['type'], x['field'])):
                writer.writerow(row)

        print(f"Результаты сохранены в {st.RESULT_FILE}: {len(results_data)} записей")
    except Exception as e:
        print(f"Ошибка при сохранении результатов: {e}")


def main():
    st.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    st.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    st.OUT_JSON_DIR.mkdir(parents=True, exist_ok=True)
    st.IN_JSON_DIR.mkdir(parents=True, exist_ok=True)

    initialize_pattern_validators()

    indices_url = f"{st.OPENSEARCH_URL}{st.INDICES_LIST_METHOD}"
    indices = fetch_opensearch_request_with_retry(indices_url)
    time.sleep(0.5)

    if not indices:
        print("Не удалось получить список индексов")
        return

    parsed_indices = parse_indices(indices)
    run_log.info(f"Индексы (all): {parsed_indices}")
    if not parsed_indices:
        print("Не найдено индексов для обработки")
        return

    tech_indices = [idx for idx in parsed_indices.keys() if 'tech' in idx]
    print(f"Найдено tech индексов: {len(tech_indices)}")
    run_log.info(f"Найдено tech индексов: {len(tech_indices)}")
    # print(json.dumps(tech_indices, indent=4, ensure_ascii=False))

    new_results = {}

    for pattern in tech_indices:
        print(f"\nОбработка индекса: {pattern}")
        run_log.info("*" * 35)
        run_log.info(f"Обработка индекса: {pattern}")

        # === читаем состояние ПЕРЕД индексом ===
        cache = load_cache()
        results_data = load_results()

        matches, hits_count = parse_index(pattern)
        if not matches:
            print(f"  Совпадений не найдено")
            continue

        aggregated = aggregate_matches(matches)
        filtered_aggregated = {}
        example_aggregate = """
        aggregated = {
            ('user.email', 'email'): {
                'field': 'user.email',
                'type': 'email',
                'field_count': 2,
                'total_count': 3,
                'values': ['a@a.ru', 'b@b.ru'],
                'examples': {
                'example_1': {
                    'value': 'a@a.ru',
                    'doc_id': 'abc123',
                    '_source': {...}
                }
                }
            }
            }
        """

        for (field, data_type), info in aggregated.items():
            cache_key = (pattern, data_type, field)
            run_log.info(f"cache_key: {cache_key}")
            result_key = cache_key

            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # === cache ===
            if cache_key not in cache:
                cache.add(cache_key)
                filtered_aggregated[(field, data_type)] = info
                print(f"  Новое: {pattern}.{field} ({data_type})")
                run_log.info(f"not in cache (new): {pattern}.{field} ({data_type})")
            else:
                print(f"  Обновлено: {pattern}.{field} ({data_type})")
                run_log.info(f"already in cache: {pattern}.{field} ({data_type})")
            
            # === results (ВСЕГДА) ===
            existing_row = results_data.get(result_key)

            if existing_row:
                create_ts = existing_row.get('create_ts', now_ts)
                previous_count = int(existing_row.get('current_count', 0))
                previous_processed_docs = int(existing_row.get('processed_docs', 0))
            else:
                create_ts = now_ts
                previous_count = 0
                previous_processed_docs = 0

            # Логика подсчетов
            current_count = info['total_count']
            total_count = previous_count + current_count
            current_processed_docs = hits_count
            total_processed_docs = previous_processed_docs + current_processed_docs

            # Сборка итогового словаря
            results_data[result_key] = {
                'index': pattern,
                'type': data_type,
                'field': field,
                'examples': st.EXAMPLES_SEPARATOR.join(info['values']),
                'doc_ids': st.EXAMPLES_SEPARATOR.join(info['doc_ids']),
                'timestamps': st.EXAMPLES_SEPARATOR.join(info['timestamps']),
                'create_ts': create_ts,
                'update_ts': now_ts,
                'total_count': total_count,
                'previous_count': previous_count,
                'current_count': current_count,
                'processed_docs': total_processed_docs
            }

        # Сохраняем все форматы
        # === JSON только если новое ===
        if filtered_aggregated:
            save_index_data(pattern, filtered_aggregated, st.RAW_DATA_DIR, include_raw=True)
            save_index_data(pattern, filtered_aggregated, st.OUT_JSON_DIR, include_raw=False)

        # === сохраняем состояние ПОСЛЕ индекса ===
        save_to_cache(cache)
        save_to_results(results_data)
    
        print(f"  Индекс {pattern} сохранён")
        run_log.info(f"Обработка индекса {pattern} завершена")

        time.sleep(0.5)


# if __name__ == '__main__':
#     urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # # Получаем имя текущего файла (например, 'myscript.py')
    # script_name = Path(__file__).name 

    # # для тестирования и отладки - пишет логи в директорию, откуда запускается скрипт
    # run_log = setup_logger('run_logger', st.LOG_DIR, f"{script_name}_{st.RUN_LOG_NAME}")
    # err_log = setup_logger('err_logger', st.LOG_DIR, f"{script_name}_{st.ERR_LOG_NAME}")

    # run_log.info("#" * 45)
    # run_log.info("Начало скрипта")
    
#     start_time = time.time()
    
#     try:
#         main()
#     except KeyboardInterrupt:
#         print("\nПрервано пользователем")
#     except Exception as e:
#         print(f"\nКритическая ошибка: {e}")
#         import traceback
#         traceback.print_exc()
    
#     end_time = time.time()
#     execution_time_seconds = end_time - start_time
#     print(f"\nСкрипт выполнен за: {execution_time_seconds:.2f} секунд")

############################

if __name__ == '__main__':
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    logs_dir = Path(__file__).parent / st.LOG_DIR
    # Получаем имя текущего файла (например, 'myscript.py')
    script_name = Path(__file__).name 

    # для тестирования и отладки - пишет логи в директорию, откуда запускается скрипт
    run_log = setup_logger('run_logger', logs_dir, f"{script_name}_{st.RUN_LOG_NAME}")
    err_log = setup_logger('err_logger', logs_dir, f"{script_name}_{st.ERR_LOG_NAME}")

    run_log.info("#" * 45)
    run_log.info("Начало скрипта")

    INTERVAL = 3600  # 1 час в секундах
    DURATION_DAYS = 7
    total_iterations = DURATION_DAYS * 24  # 24 итерации в день

    print(f"Скрипт запущен в циклическом режиме на {DURATION_DAYS} дней. Интервал: {INTERVAL/60:.0f} мин.")

    try:
        for iteration in range(1, total_iterations + 1):
            start_time = time.time()
            
            try:
                main()
            except Exception as e:
                print(f"\nОшибка во время выполнения main(): {e}")
                import traceback
                traceback.print_exc()
            
            execution_time = time.time() - start_time
            print(f"\nИтерация {iteration}/{total_iterations} завершена за: {execution_time:.2f} сек.")
            
            if iteration < total_iterations:
                print(f"Ожидание следующего запуска... (через {INTERVAL/60:.0f} мин)")
                time.sleep(INTERVAL)
            else:
                print("\nВсе запланированные итерации выполнены. Скрипт завершён.")

    except KeyboardInterrupt:
        print("\nЦикл остановлен пользователем вручную.")
