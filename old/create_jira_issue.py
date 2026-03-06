import json
import csv
import urllib3
import re
import logging
import logging.handlers
import copy
import argparse
import time

import jira_issue_settings as jst
from settings import IN_JSON_DIR, DONE_JSON_DIR, OWNERS_FILE, ERRORS_JSON_DIR
from settings import JIRA_CA_CACHE_FILE, JIRA_CA_RESULT_FILE, RAW_DATA_DIR_DONE
from settings import IN_JSON_DIR_RAW, UNVERIFIED_JSON_DIR, UNVERIFIED_JSON_DIR_RAW
from settings import ERRORS_JSON_DIR_RAW
from settings import OWNERS_FILE_DEV, JIRA_CA_CACHE_FILE_DEV, JIRA_CA_RESULT_FILE_DEV

from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

from utils import get_tb
from utils import exec_request
from utils import send_email_with_attachments

from jira_issue_payload import JIRA_ISSUE_PAYLOAD


def replace_file_name(name):
    return re.sub(r'[\\/*?:"<>| ]', "_", name)


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
                maxBytes=3 * 1024 * 1024,
                backupCount=3,
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


def read_owners_csv(file_path, err_list):  # (file_path: str) -> dict
    """
    Читает owners.csv и возвращает словарь с данными.
    index как основной ключ, остальные данные внутри вложенного словаря.
    """
    result = {}
    path = Path(file_path)
    
    try:
        with path.open('r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            # Чтение всех строк
            for row in reader:
                index_val = row.get('index', "")
                cmdb_key = row.get('cmdb-key', "")
                tech_debt_id = row.get('tech_debt_id', "")
                
                # Проверка наличия всех полей
                if all([index_val, cmdb_key, tech_debt_id]):
                    result[index_val] = {
                        'cmdb-key': str(cmdb_key),
                        'tech_debt_id': str(tech_debt_id)
                    }
                else:
                    msg = f"Имеются недостающие данные по ответственным: \
                        index_val: {index_val}, cmdb_key: {cmdb_key}, tech_debt_id: {tech_debt_id}"
                    err_list.append(msg)
                    run_log.error(msg)
                    continue
        
        run_log.info("Файл ответственных успешно прочитан")
        return result
        
    except Exception as e:
        tb = get_tb()
        err_msg = f"Не удалось получить ответственных за индекс, исключение: {e}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)
        return {}


def handle_file_movement(source, target, index, err_list, log):
    moved, failed = move_files_by_index(source, target, index, err_list)
    if moved:
        log.info(f"Успешно перенесено в {target} [{index}]: {moved}")
    if failed:
        msg = f"Ошибка переноса в {target} [{index}]: {failed}"
        err_list.append(msg)
        log.error(msg)
    return moved, failed


def init_jira_cache(path, err_list):
    fieldnames = ["index", "jira_ca_key", "status", "created", "updated"]

    if path.exists():
        return

    try:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
    except Exception as e:
        msg = f"Не удалось создать jira cache file {path}: {e}"
        err_list.append(msg)
        run_log.error(get_tb())
        run_log.error(msg)


def read_jira_cache(path, err_list):
    """
    Читает кэш, возвращает словарь index -> {jira_ca_key, status, created, updated}.
    Не трогает файл.
    """
    cache = {}
    if not path.exists():
        return cache

    try:
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache[row["index"]] = {
                    "jira_ca_key": row["jira_ca_key"],
                    "status": int(row.get("status", 0)),
                    "created": row.get("created"),
                    "updated": row.get("updated"),
                }
    except Exception as e:
        msg = f"Не удалось прочитать jira cache file: {path}. Исключение: {e}"
        err_list.append(msg)
        run_log.error(get_tb())
        run_log.error(msg)

    return cache


def write_jira_cache(path, cache, err_list):
    fieldnames = ["index", "jira_ca_key", "status", "created", "updated"]
    try:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for idx, entry in cache.items():
                writer.writerow({
                    "index": idx,
                    "jira_ca_key": entry["jira_ca_key"],
                    "status": entry["status"],
                    "created": entry.get("created", ""),
                    "updated": entry.get("updated", ""),
                })
    except Exception as e:
        msg = f"Ошибка записи Jira кеша {path}: {e}"
        err_list.append(msg)
        run_log.error(get_tb())
        run_log.error(msg)


def append_or_reset_jira_cache(cache, index, jira_ca_key):
    """
    Добавляет новый индекс в кэш или, если запись уже есть, сбрасывает status=0.
    """
    ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    if index in cache:
        # Сброс статуса существующей записи
        cache[index]["jira_ca_key"] = jira_ca_key
        cache[index]["status"] = 0
        cache[index]["updated"] = ts
    else:
        # Новая запись
        cache[index] = {
            "jira_ca_key": jira_ca_key,
            "status": 0,
            "created": ts,
            "updated": ts,
        }


def update_jira_cache(cache, index, jira_ca_key):
    """
    Обновляет существующую запись кэша.
    """
    ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    if index not in cache:
        msg = f"update_jira_cache: index {index} не найден"
        run_log.warning(msg)
        return

    entry = cache[index]
    entry["jira_ca_key"] = jira_ca_key
    entry["updated"] = ts


def get_jira_issue_done(jira_ca_key, err_list):
    """
    Проверяет, закрыта ли задача в Jira.

    Возвращает:
        True  — если статус "done"
        False — если в работе
        None  — если ошибка запроса или некорректный ответ
    """
    url = f"{jira_base_url}/rest/api/2/issue/{jira_ca_key}?fields=status"

    response, r_err = exec_request(
        url, "GET", headers=jst.HEADERS,
        logger=run_log, max_retries=3
    )

    if r_err:
        err_list.append(f"Ошибка при запросе к {url}: {r_err}")
        return None

    try:
        data = response.json()
        return data["fields"]["status"]["statusCategory"]["key"] == "done"
    except (ValueError, AttributeError) as e:
        err_msg = f"Ошибка обработки данных, исключение: {e}"
        err_list.append(err_msg)
        run_log.error(get_tb())
        run_log.error(err_msg)
        return None


def get_account_name(attributes, id, err_list):
    try:
        return next(
            (
                attr['objectAttributeValues'][0]['value'] 
                for attr in attributes 
                if attr.get('objectTypeAttributeId') == id
            ), 
            None
        )
    except Exception as e:
        tb = get_tb()
        err_msg = f"Не удалось получить объект AccountName: id={id}; исключение: {e}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)


# Для типизации не забыть импортировать from typing import Dict, List
# (results_file: Path, *, index_name: str, jira_ca_key: str, aggregated: Dict, action: str # "created" | "updated", headers: List[str], err_list: List[str]) -> None:
def append_results_csv(results_file, *, index_name, jira_ca_key, aggregated, action, err_list):
    """
    Append-only audit CSV writer.
    """

    headers = [
        "index",
        "ca_key",
        "type",
        "field_path",
        "action",
        "ts",
    ]

    try:
        file_exists = results_file.exists()
        # ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        with results_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)

            if not file_exists:
                writer.writeheader()

            for field_path, field_data in aggregated.get("fields", {}).items():
                field_type = field_data.get("type")
                if not field_type:
                    continue

                writer.writerow({
                    "index": index_name,
                    "ca_key": jira_ca_key,
                    "type": field_type,
                    "field_path": field_path,
                    "action": action,
                    "ts": ts,
                })

    except Exception as e:
        msg = f"[append_results_csv]: index={index_name} ca_key={jira_ca_key}: {e}"
        err_list.append(msg)
        run_log.error(get_tb())


def get_insight_object_key(attributes, id, err_list, entity_name="object"):
    try:
        return next(
            (
                attr['objectAttributeValues'][0]['referencedObject']['objectKey']
                for attr in attributes
                if attr.get('objectTypeAttributeId') == id
            ), 
            None
        )
    except Exception as e:
        tb = get_tb()
        err_msg = f"Не удалось получить cmdb ключ {entity_name}: id={id}; исключение: {e}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)

    return None


def get_key_number(key):
        return key.split('-')[1]


def get_description_by_url(url, err_list):
    """
    Выполняет запрос и извлекает description
    """
    response, r_err = exec_request(
        url, "GET", headers=jst.HEADERS,
        logger=run_log, max_retries=3
    )
    
    if r_err:
        err_list.append(f"Ошибка при запросе к {url}: {r_err}")
        return None

    try:
        data = response.json()
        fields = data.get('fields', {})
        if fields:
            return fields.get("description", "")
    except (ValueError, AttributeError) as e:
        tb = get_tb()
        err_msg = f"Ошибка обработки данных, исключение: {e}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)
    
    return None


def get_account_name_by_url(url, err_list):
    """
    Выполняет запрос и извлекает логин из атрибутов объекта.
    """
    response, r_err = exec_request(
        url, "GET", headers=jst.HEADERS,
        logger=run_log, max_retries=3
    )
    
    if r_err:
        err_list.append(f"Ошибка при запросе к {url}: {r_err}")
        return None

    try:
        data = response.json()
        attributes = data.get('attributes', [])
        if attributes:
            return get_account_name(attributes, jst.ACCOUNT_NAME_ID, err_list)
    except (ValueError, AttributeError) as e:
        tb = get_tb()
        err_msg = f"Ошибка обработки данных, исключение: {e}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)
    
    return None


def find_none_keys(data, parent_key=''):
    none_keys = []
    
    if isinstance(data, dict):
        for k, v in data.items():
            # Формируем полный путь к ключу для наглядности
            full_key = f"{parent_key}.{k}" if parent_key else k
            
            if v is None:
                none_keys.append(full_key)
            else:
                # Рекурсивно идем глубже
                none_keys.extend(find_none_keys(v, full_key))
                
    elif isinstance(data, list):
        for i, item in enumerate(data):
            # Для списков добавляем индекс в путь
            full_key = f"{parent_key}[{i}]"
            none_keys.extend(find_none_keys(item, full_key))
            
    return none_keys


# def mask_email(value, err_list):  # (value: str) -> str
#     """
#     Пример:
#     alexandro@example.ru -> a•••o@e•••••e.ru
#     """
#     try:
#         local, domain = value.split("@", 1)

#         # local-part
#         if len(local) >= 2:
#             masked_local = f"{local[0]}{mask_char * 3}{local[-1]}"
#         else:
#             masked_local = f"{mask_char * 5}" 

#         # domain + tld
#         domain_parts = domain.rsplit(".", 1)
#         domain_name = domain_parts[0]
#         tld = "." + domain_parts[1] if len(domain_parts) == 2 else ""

#         if len(domain_name) >= 2:
#             masked_domain = f"{domain_name[0]}{mask_char * 5}{domain_name[-1]}"
#         else:
#             masked_domain = f"{mask_char * 5}" 

#         return f"{masked_local}@{masked_domain}{tld}"

#     except Exception as e:
#         tb = get_tb()
#         err_msg = f"Не удалось замаскировать email: {e}, значение: {value}"
#         err_list.append(err_msg)

#         run_log.error(tb)
#         run_log.error(err_msg)

#         return f"{mask_char * 3}"


def mask_email(value, err_list):  # (value: str, err_list: list) -> str
    """
    Маскирует email:
    - домен не маскируется
    - если длина local <= 3 → маскируем полностью
    - если длина local == 4 → первый и последний оставляем
    - если длина local >= 5 → первый и последний оставляем, середину маскируем
    """

    try:
        if not value or "@" not in value:
            return mask_char * 3

        local, domain = value.split("@", 1)

        if not local:
            return mask_char * 3

        length = len(local)

        # ≤ 3 — полностью маскируем
        if length <= 3:
            masked_local = mask_char * length

        # == 4 — первый и последний
        elif length == 4:
            masked_local = f"{local[0]}{mask_char * 2}{local[-1]}"

        # >= 5 — первый и последний, середина маскируется полностью
        else:
            masked_local = f"{local[0]}{mask_char * (length - 2)}{local[-1]}"

        return f"{masked_local}@{domain}"

    except Exception as e:
        tb = get_tb()
        err_msg = f"Не удалось замаскировать email: {e}, значение: {value}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)

        return mask_char * 3


# def mask_phone(value, err_list):  # (value: str) -> str
#     """
#     Маскирует телефон, сохраняя формат:
#     - первая цифра видима
#     - последние 2 цифры видимы
#     - остальные цифры заменяются на '*'
#     """
#     try:
#         # Позиции всех цифр в строке
#         digit_positions = [i for i, c in enumerate(value) if c.isdigit()]

#         if len(digit_positions) < 3:
#             return f"{mask_char * 3}"

#         first_digit_pos = digit_positions[0]
#         last_visible_positions = set(digit_positions[-2:])

#         chars = list(value)

#         for pos in digit_positions:
#             # первую цифру и последние две — не маскируем
#             if pos == first_digit_pos or pos in last_visible_positions:
#                 continue
#             chars[pos] = f"{mask_char}"

#         return "".join(chars)

#     except Exception as e:
#         tb = get_tb()
#         err_msg = f"Не удалось замаскировать phone: {e}"
#         err_list.append(err_msg)

#         run_log.error(tb)
#         run_log.error(err_msg)

#         return f"{mask_char * 3}"


def mask_phone(value, err_list):  # (value: str, err_list: list) -> str
    """
    Маскирует телефон, сохраняя формат строки:
    - если начинается с 9 -> первые 3 цифры видимы
    - если начинается с 7 или 8 -> первые 4 цифры видимы
    - иначе -> только первая цифра видима
    - последние 2 цифры всегда видимы
    - остальные цифры заменяются на mask_char
    """
    try:
        if not value:
            return mask_char * 3

        # Все позиции цифр в строке
        digit_positions = [i for i, c in enumerate(value) if c.isdigit()]
        total_digits = len(digit_positions)

        if total_digits < 3:
            return mask_char * 3

        # Первая цифра номера (логическая, а не позиция 0 в строке)
        first_digit_char = value[digit_positions[0]]

        # Определяем сколько цифр оставлять в начале
        if first_digit_char == "9":
            visible_prefix_len = 3
        elif first_digit_char in ("7", "8"):
            visible_prefix_len = 4
        else:
            visible_prefix_len = 1

        # Если номер слишком короткий — не ломаем логику
        visible_prefix_len = min(visible_prefix_len, total_digits - 2)

        # Позиции, которые не маскируем
        visible_positions = set(digit_positions[:visible_prefix_len])
        visible_positions.update(digit_positions[-2:])

        chars = list(value)

        for pos in digit_positions:
            if pos not in visible_positions:
                chars[pos] = mask_char

        return "".join(chars)

    except Exception as e:
        tb = get_tb()
        err_msg = f"Не удалось замаскировать phone: {e}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)

        return mask_char * 3


def mask_card(value, err_list):  # (value: str) -> str
    """
    Маскирует номер карты, сохраняя формат:
    - первые 6 цифр видимы (BIN)
    - последние 4 цифры видимы
    - остальные цифры заменяются на '*'
    """
    try:
        digit_positions = [i for i, c in enumerate(value) if c.isdigit()]

        # минимально допустимо: 6 + 4
        if len(digit_positions) < 10:
            return f"{mask_char * len(value)}"

        first_visible = set(digit_positions[:6])
        last_visible = set(digit_positions[-4:])

        chars = list(value)

        for pos in digit_positions:
            if pos in first_visible or pos in last_visible:
                continue
            chars[pos] = f"{mask_char}"

        return "".join(chars)

    except Exception as e:
        tb = get_tb()
        err_msg = f"Не удалось замаскировать card: {e}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)

        return f"{mask_char * len(value)}"


def mask_value(value, value_type, err_list):  # (value: str, value_type: str) -> str
    try:
        masker = MASKERS.get(value_type)
        if not masker:
            return f"{mask_char * len(value)}"
        return masker(value, err_list)
    except Exception as e:
        tb = get_tb()
        err_msg = f"Ошибка при обработке маскера: {e}"
        err_list.append(err_msg)

        run_log.error(tb)
        run_log.error(err_msg)

        return f"{mask_char * len(value)}"


# (source_dir: Path, target_dir: Path, index_prefix: str) -> Tuple[List[Path], List[Path]]
def move_files_by_index(source_dir, target_dir, index_prefix, err_list):  
    """
    Переносит все *.json файлы из source_dir в target_dir,
    у которых имя начинается с index_prefix + '__'

    Возвращает True если хотя бы один файл перемещён,
    иначе False
    """
    moved = []
    failed = []

    for file in source_dir.glob("*.json"):
        try:
            if not file.name.startswith(index_prefix + "__"):
                continue

            target = target_dir / file.name
            file.replace(target)
            moved.append(target)

        except Exception as e:
            tb = get_tb()
            err_msg = f"Не удалось прочитать файл: {file}, исключение: {e}"
            err_list.append(err_msg)

            run_log.error(tb)
            run_log.error(err_msg)
            
            failed.append(file)

    return moved, failed


def group_files_by_index(input_dir):  # (input_dir: str) -> dict[str, list[Path]]
    """
    Группирует файлы по имени индекса (до первого '__')
    """
    groups = defaultdict(list)

    for file in Path(input_dir).glob("*.json"):
        index_name = file.name.split("__", 1)[0]
        groups[index_name].append(file)

    return dict(groups)


def read_finding_file(path):  # (path: Path) -> dict
    """
    Чтение одного файла
    """
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def normalize_index_name(name):  # (name: str) -> str
    return name.replace("_", "-").strip()


def aggregate_index_files(index_name, files, err_list, examples_limit=jst.AGGREGATE_EXAMPLE_LIMIT):
    """
    Объединяет данные всех файлов одного индекса
    Берёт первые examples_limit примеров БЕЗ дедупликации
    """
    result = {
        "index": None,
        "fields": {}
    }

    result["index"] = index_name

    for file in files:
        try:
            data = read_finding_file(file)
        except Exception as e:
            tb = get_tb()
            err_msg = f"Не удалось прочитать файл: {file}, исключение: {e}"
            err_list.append(err_msg)

            run_log.error(tb)
            run_log.error(err_msg)

            continue

        try:
            json_index_norm = normalize_index_name(data["index"].rstrip("*"))

            if json_index_norm != index_name:
                # логирование: несовпадение индекса
                # file, expected_index, json_index
                run_log.error(f"индекс из файла {file} не совпадает с нормализованным индексом в имени файла {index_name}")
                continue

            field = data["field"]
            field_type = data["type"]
            key = (field, field_type)
            examples = list(data.get("examples", {}).values())

            # if field not in result["fields"]:
            #     result["fields"][field] = {
            #         "type": field_type,
            #         "examples": []
            #     }

            if key not in result["fields"]:
                result["fields"][key] = {
                    "field": field,
                    "type": field_type,
                    "examples": []
                }
            

            # result["fields"][field]["examples"].extend(examples)
            result["fields"][key]["examples"].extend(examples)

        except KeyError as e:
            # битый / неполный файл
            tb = get_tb()
            err_msg = f"Битый / неполный файл: {file}, исключение: {e}"
            err_list.append(err_msg)

            run_log.error(tb)
            run_log.error(err_msg)
            continue

    # ⬇⬇⬇ ВАЖНО: только лимит, без дедупликации
    for field_data in result["fields"].values():
        field_data["examples"] = field_data["examples"][:examples_limit]

    return result


def render_header(index_name):  # (index_name: str) -> str
    return (
        f"Реализовать маскирование или полное исключение ПДн при их передаче в индекс *{index_name}**.\n"
        f"Также необходимо проверить индекс на наличие других персональных данных.\n"
    )
    # как было
    # return (
    #     f"Реализовать маскирование или исключение ПДн из индекса *{index_name}**.\n"
    #     f"Необходимо проверить индекс так же на наличие других персональных данных.\n"
    # )


def render_fields(index_data, err_list, mask_values):  # (index_data: dict, err_list: list, mask_values: bool = True) -> str
    lines = ["Найденные поля:\n"]

    # for field, meta in index_data["fields"].items():
    for meta in index_data["fields"].values():
        field = meta["field"]
        lines.append(f'Поле: "{field}"')
        lines.append(f"Тип: {meta['type']}")
        lines.append("Примеры:")

        for ex in meta["examples"]:
            try:
                # Заранее определяем значения
                # doc_id = f"`{ex.get('doc_id')}`"
                # timestamp = f"`{ex.get('@timestamp')}`"

                if mask_values:
                    masked_value = mask_value(ex.get("value", ""), meta["type"], err_list)
                    line = f"value: {masked_value}, doc_id: {ex.get('doc_id')}, @timestamp: {ex.get('@timestamp')}"
                    # val = ex.get("value", "")
                    # masked_raw = mask_value(val, meta["type"], err_list)
                    # masked_value = f"`{masked_raw}`"
                    # line = f"value: {masked_value}, doc_id: {doc_id}, @timestamp: {timestamp}"
                else:
                    line = f"doc_id: {ex.get('doc_id')}, @timestamp: {ex.get('@timestamp')}"
                    # line = f"doc_id: {doc_id}, @timestamp: {timestamp}"

                lines.append(line)
            except Exception as e:
                tb = get_tb()
                err_msg = f"Ошибка при формировании description, исключение: {e}"
                err_list.append(err_msg)
                run_log.error(tb)
                run_log.error(err_msg)
                continue

        lines.append("\n")  # пустая строка между полями

    return "\n".join(lines)


# def render_fields(index_data, err_list, mask_values=True):
#     lines = ["Найденные поля:\n"]

#     for meta in index_data["fields"].values():
#         field = meta["field"]
#         lines.append(f'Поле: "{field}"')
#         lines.append(f"Тип: {meta['type']}")
#         lines.append("Примеры:")

#         for ex in meta["examples"]:
#             try:
#                 # В Jira Wiki Markup моноширинный шрифт — это {{text}}
#                 doc_id = f"{{{{{ex.get('doc_id')}}}}}"
#                 timestamp = f"{{{{{ex.get('@timestamp')}}}}}"
                
#                 if mask_values:
#                     val = ex.get("value", "")
#                     masked_raw = mask_value(val, meta["type"], err_list)
#                     masked_value = f"{{{{{masked_raw}}}}}"
#                     line = f"value: {masked_value}, doc_id: {doc_id}, @timestamp: {timestamp}"
#                 else:
#                     line = f"doc_id: {doc_id}, @timestamp: {timestamp}"
                
#                 lines.append(line)
#             except Exception as e:
#                 tb = get_tb()
#                 err_msg = f"Ошибка при формировании description, исключение: {e}"
#                 err_list.append(err_msg)
#                 run_log.error(tb)
#                 run_log.error(err_msg)
#                 continue

#         lines.append("\n")

#     return "\n".join(lines)


# (index_name: str, index_data: dict, err_list: list, mask_values: bool = True, create: bool = True) -> str
def render_issue_description(index_name, index_data, err_list, mask_values=jst.MASK_VALUE, create=True):
    parts = []
    if create:
        parts.append(render_header(index_name))
    parts.append(render_fields(index_data, err_list, mask_values))
    return "\n".join(parts)


def build_issues(input_dir, err_list):  # (input_dir: str) -> dict[str, dict]
    """
    Возвращает:
    {
      index-name: aggregated_data  # без рендера текста
    }
    """
    grouped_files = group_files_by_index(input_dir)
    issues = {}

    for index_name, files in grouped_files.items():
        index_name_norm = normalize_index_name(index_name)
        aggregated = aggregate_index_files(index_name_norm, files, err_list)
        # issue_text = render_issue_description(index_name_norm, aggregated, err_list)
        issues[index_name] = aggregated  # сюда возвращаем не нормализованное имя индекса

    return issues


def build_jira_payload(
    owner_data,
    index,
    description,
    err_list,
    run_log,
):  # owner_data: dict, index: str, description: str, err_list: list, run_log
    payload = copy.deepcopy(JIRA_ISSUE_PAYLOAD)
    fields = payload["fields"]

    assignee_cmdb_key_number = owner_data.get("cmdb-key")
    tech_debt_id = owner_data.get("tech_debt_id")

    # Получаем текущую дату и прибавляем 90 дней
    # Форматируем в строку ГГГГ-ММ-ДД
    future_date = datetime.now() + timedelta(days=jst.DUEDATE_DAYS)
    duedate = future_date.strftime("%Y-%m-%d")

    

    # ---------------------------------------------
    # Получаем объект исполнителя
    # assignee_cmdb_insight_url = "https://sd-jira.bcs.ru/secure/insight/assets/CMDB-2793524"

    assignee_cmdb_insight_api_object_url  = insight_api_object_url + f"/{assignee_cmdb_key_number}"

    assignee_obj = None
    response, r_err = exec_request(
        assignee_cmdb_insight_api_object_url, "GET", headers=jst.HEADERS,
        logger=run_log, max_retries=3
    )
    if not r_err:
        assignee_obj = response.json()
    else:
        err_list.append(f"Ошибка при запросе к {assignee_cmdb_insight_api_object_url}: {r_err}")

    assignee_attributes = None
    if assignee_obj:
        assignee_attributes = assignee_obj.get('attributes', [])

    # ---------------------------------------------
    assignee = None  # assignee
    l1_manager_key_number = None  # customfield_42231, L1 manager
    l2_manager_key_number = None  # customfield_42232, L2 manager
    l1_manager = None
    l2_manager = None
    team_members = []  # customfield_10030, участники
    if jst.EXTRA_TEAM_MEMBERS:
        team_members.extend(jst.EXTRA_TEAM_MEMBERS)
    team_key = None

    if assignee_attributes:
        run_log.info("Получаем assignee account_name")
        assignee = get_account_name(assignee_attributes, jst.ACCOUNT_NAME_ID, err_list)
        run_log.info(f"assignee account_name: {assignee}")

        if assignee:
            team_members.append(assignee)

            # ---------------------------------------------
            # Получаем объекты и аккаунт нейм manager и teamlead
            run_log.info("Получаем объект assignee_teamlead_key")
            assignee_teamlead_key = get_insight_object_key(assignee_attributes, jst.ASSIGNEE_TEAMLEAD_ID, err_list, "Teamlead")
            run_log.info(f"assignee_teamlead_key: {assignee_teamlead_key}")

            run_log.info("Получаем объект assignee_manager_key")
            assignee_manager_key = get_insight_object_key(assignee_attributes, jst.ASSIGNEE_MANAGER_ID, err_list, "Manager")
            run_log.info(f"assignee_manager_key: {assignee_manager_key}")
            
            if assignee_teamlead_key:
                assignee_teamlead_key_number = get_key_number(assignee_teamlead_key)
                teamlead_cmdb_insight_api_object_url = insight_api_object_url + f"/{assignee_teamlead_key_number}"

                run_log.info("Получаем assignee_teamlead account_name")
                assignee_teamlead = get_account_name_by_url(teamlead_cmdb_insight_api_object_url, err_list)
                run_log.info(f"assignee_teamlead account_name: {assignee_teamlead}")

                assignee_teamlead and team_members.append(assignee_teamlead)

            if assignee_manager_key:
                assignee_manager_key_number = get_key_number(assignee_manager_key)
                manager_cmdb_insight_api_object_url = insight_api_object_url + f"/{assignee_manager_key_number}"

                run_log.info("Получаем assignee_manager account_name")
                assignee_manager = get_account_name_by_url(manager_cmdb_insight_api_object_url, err_list)
                run_log.info(f"assignee_manager account_name: {assignee_manager}")

                assignee_manager and team_members.append(assignee_manager)

        run_log.info("Получаем объект team_key")
        team_key = get_insight_object_key(assignee_attributes, jst.TEAM_NAME_ID, err_list, "Team")
        run_log.info(f"team_key: {team_key}")
        if not team_key:
            team_key = jst.DEFAULT_UNREGISTERED_TEAM

        run_log.info("Получаем объект l1_manager_key")
        l1_manager_key = get_insight_object_key(assignee_attributes, jst.L1_MANAGER_ID, err_list, "L1_Manager")
        run_log.info(f"l1_manager_key: {l1_manager_key}")

        run_log.info("Получаем объект l2_manager_key")
        l2_manager_key = get_insight_object_key(assignee_attributes, jst.L2_MANAGER_ID, err_list, "L2_Manager")
        run_log.info(f"l2_manager_key: {l2_manager_key}")

        fields["customfield_42231"][0]["key"] = l1_manager_key
        fields["customfield_42232"][0]["key"] = l2_manager_key

        # ---------------------------------------------
        # Получаем объекты и аккаунт нейм l1 и l2 менеджеров
        # Этот блок под вопросом, пока убрал
        # if l1_manager_key:
        #     l1_manager_key_number = get_key_number(l1_manager_key)
        #     l1_cmdb_insight_api_object_url = insight_api_object_url + f"/{l1_manager_key_number}"

        #     run_log.info("Получаем l1_manager account_name")
        #     l1_manager = get_account_name_by_url(l1_cmdb_insight_api_object_url, err_list)
        #     run_log.info(f"l1_manager account_name: {l1_manager}")

        #     l1_manager and team_members.append(l1_manager)  # ещё под вопросом

        # if l2_manager_key:
        #     l2_manager_key_number = get_key_number(l2_manager_key)
        #     l2_cmdb_insight_api_object_url = insight_api_object_url + f"/{l2_manager_key_number}"

        #     run_log.info("Получаем l2_manager account_name")
        #     l2_manager = get_account_name_by_url(l2_cmdb_insight_api_object_url, err_list)
        #     run_log.info(f"l2_manager account_name: {l2_manager}")

        #     l2_manager and team_members.append(l2_manager)  # ещё под вопросом
        
    # ---------------------------------------------
    # Получаем объект и account name контроллера
    supervisor_cmdb_insight_api_object_url = insight_api_object_url + f"/{jst.SUPERVISOR_CMDB_KEY_NUMBER}"

    run_log.info("Получаем supervisor account_name")
    supervisor = get_account_name_by_url(supervisor_cmdb_insight_api_object_url, err_list)  # customfield_22738, контролер
    run_log.info(f"supervisor account_name: {supervisor}")

    supervisor and team_members.append(supervisor)

    # ---------------------------------------------

    fields["summary"] = f"Исключение ПДн из индекса {index}"
    fields["duedate"] = duedate
    fields["description"] = description

    fields["customfield_29834"]["child"]["id"] = tech_debt_id  # ??? технический долг
    fields["customfield_22738"]["name"] = supervisor
    # fields["customfield_17230"][0]["id"] = None  # ??? колонна  # прописана в settings, статичная, берется из ИС
    fields["customfield_22932"][0]["key"] = team_key

    fields["assignee"]["name"] = assignee

    fields["customfield_10030"] = [{"name": x} for x in set(team_members)]

    run_log.info(f"duedate: {duedate}")

    return payload


def jira_request(
    *,
    url,
    method,
    payload,
    logger,
    err_list,
    statuses,
):  # *, url: str, method: str, payload: dict, logger, errors: list, statuses: list[int] | None = None
    """
    POST -> возвращает jira_key или None
    PUT  -> возвращает True / False
    """
    response, r_err = exec_request(
        url,
        method,
        headers=jst.HEADERS,
        json=payload,
        logger=logger,
        statuses=statuses,
        max_retries=3,
    )

    method = method.upper()

    if r_err:
        err_list.append(f"Ошибка при запросе к {url}: {r_err}")
        return None if method == "POST" else False

    if method == "POST":
        try:
            data = response.json()
            jira_key = data.get("key", "")
            if not jira_key:
                err_list.append(f"Jira не вернула key для {url}")
                return None
            return jira_key
        except (ValueError, AttributeError) as e:
            tb = get_tb()
            err_msg = f"Ошибка обработки ответа Jira: {e}"
            err_list.append(err_msg)
            logger.error(tb)
            logger.error(err_msg)
            return None

    if method == "PUT":
        # если мы здесь — статус уже валиден
        return True

    err_list.append(f"Неподдерживаемый метод: {method}")
    return None


if __name__ == "__main__":
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    main_errors = list()

    # 1. Парсим аргументы
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["dev", "prod"], default="dev")
    args = parser.parse_args()

    env_suffix = "_dev" if args.env == 'dev' else ""

    logs_dir = Path(__file__).parent / 'logs'

    # Получаем имя текущего файла (например, 'myscript.py')
    script_name = Path(__file__).name 

    # Выбор в зависимости от аргумента
    if args.env == "dev":
        insight_api_object_url = jst.SD_INSIGHT_API_OBJECT_URL

        create_issue_url = jst.SD_CREATE_ISSUE_URL
        jira_base_url = jst.SD_JIRA_BASE_URL
        
        jira_cache_file = JIRA_CA_CACHE_FILE_DEV
        jira_result_file = JIRA_CA_RESULT_FILE_DEV

        owners_f = OWNERS_FILE_DEV

        run_log = setup_logger('run_logger', logs_dir, f"{script_name}_{jst.RUN_LOG_NAME_DEV}")
        err_log = setup_logger('err_logger', logs_dir, f"{script_name}_{jst.ERR_LOG_NAME_DEV}")
    else:
        insight_api_object_url = jst.INSIGHT_API_OBJECT_URL

        create_issue_url = jst.CREATE_ISSUE_URL
        jira_base_url = jst.JIRA_BASE_URL

        jira_cache_file = JIRA_CA_CACHE_FILE
        jira_result_file = JIRA_CA_RESULT_FILE

        owners_f = OWNERS_FILE

        run_log = setup_logger('run_logger', logs_dir, f"{script_name}_{jst.RUN_LOG_NAME}")
        err_log = setup_logger('err_logger', logs_dir, f"{script_name}_{jst.ERR_LOG_NAME}")


    run_log.info('#' * 65)
    run_log.info('Начало скрипта')

    mask_char = jst.MASK_CHAR

    try:
        DONE_JSON_DIR.mkdir(parents=True, exist_ok=True)
        ERRORS_JSON_DIR.mkdir(parents=True, exist_ok=True)
        RAW_DATA_DIR_DONE.mkdir(parents=True, exist_ok=True)
        IN_JSON_DIR_RAW.mkdir(parents=True, exist_ok=True)
        UNVERIFIED_JSON_DIR.mkdir(parents=True, exist_ok=True)
        UNVERIFIED_JSON_DIR_RAW.mkdir(parents=True, exist_ok=True)
        ERRORS_JSON_DIR_RAW.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        err_msg = f"Ошибка обработки ответа Jira: {e}"
        main_errors.append(err_msg)
        run_log.error(get_tb())
        run_log.error(err_msg)

    # create_issue_url = jst.SD_CREATE_ISSUE_URL
    # jira_base_url = jst.SD_JIRA_BASE_URL
    # create_issue_url = jst.CREATE_ISSUE_URL
    # jira_base_url = jst.JIRA_BASE_URL

    MASKERS = {
        "email": mask_email,
        "phone": mask_phone,
        "card": mask_card,
    }

    # Инициализация и чтение кэша
    init_jira_cache(jira_cache_file, main_errors)
    ca_cache = read_jira_cache(jira_cache_file, main_errors)

    issues_aggregated = build_issues(IN_JSON_DIR, main_errors)
    # run_log.info(f"issues_aggregated: {issues_aggregated}")
    run_log.info(f"len(issues_aggregated): {len(issues_aggregated)}")

    for index_name, aggregated in issues_aggregated.items():
        errors = list()
        if main_errors: errors.append(1)  # не сдвигая весь блок на \t, если есть ошибки в main_errors, то добавляем 1 в errors

        index_name_norm = normalize_index_name(index_name)

        # Получаем данные владельца по нормализованному индексу
        owners = read_owners_csv(owners_f, errors)
        owner_data = owners.get(index_name_norm, {})

        # Проверка кэша
        cache_entry = ca_cache.get(index_name_norm)
        run_log.info(f"cache_entry in start: {cache_entry}")
        can_create = False

        if not cache_entry:
            can_create = True
        else:
            jira_ca_key = cache_entry["jira_ca_key"]
            is_done = get_jira_issue_done(jira_ca_key, errors)

            if is_done is True:
                cache_entry["status"] = 1  # только в памяти
                can_create = True
            elif is_done is False:
                can_create = False
            else:
                msg = f"Ошибка получения статуса {jira_ca_key}"
                errors.append(msg)
                run_log.error(msg)
        run_log.info(f"cache_entry after checking issue status: {cache_entry}")

        action = "created" if can_create else "updated"

        if can_create:
            # CREATE
            run_log.info("Создаем новую коррмеру")
            if not owner_data:
                msg = f"Не найден владелец по индексу {index_name_norm}"
                errors.append(msg)
                run_log.error(msg)
            else:
                description = render_issue_description(index_name_norm, aggregated, errors, create=True)
                payload = build_jira_payload(
                    owner_data=owner_data,
                    index=index_name_norm,
                    description=description,
                    err_list=errors,
                    run_log=run_log
                )

                payload_none_fields = find_none_keys(payload)
                run_log.info(f"payload: {payload}")

                if payload_none_fields:
                    msg = f"Имеются незаполненные поля в payload по индексу {index_name_norm}"
                    errors.append(msg)
                    run_log.warning(msg)
                    run_log.info(payload_none_fields)
                else:
                    jira_ca_key = None
                    if not errors:
                        jira_ca_key = jira_request(
                            url=create_issue_url,
                            method="POST",
                            payload=payload,
                            logger=run_log,
                            err_list=errors,
                            statuses=[200, 201],
                        )
                    if jira_ca_key:
                        jira_ca_url = f"{jira_base_url}/browse/{jira_ca_key}"
                        run_log.info(f"Создана коррмера {jira_ca_url}")
                        append_or_reset_jira_cache(ca_cache, index_name_norm, jira_ca_key)

                        print(jira_ca_url)

                        handle_file_movement(IN_JSON_DIR, DONE_JSON_DIR, index_name, errors, run_log)

                        append_results_csv(
                            jira_result_file,
                            index_name=index_name_norm,
                            jira_ca_key=jira_ca_key,
                            aggregated=aggregated,
                            action=action,
                            err_list=errors
                        )

                        if jst.USE_SMTP:
                            subject = f"Создана коррмера {jira_ca_key} по индексу {index_name_norm}"
                            body = f"Ссылка - {jira_ca_url}\n"
                            smtp_err = send_email_with_attachments(jst.TO_ADDR, subject, body, logger=run_log)
                            if smtp_err:
                                main_errors.append(smtp_err)
                                run_log.error(f"smtp_err: {smtp_err}")

        else:
            # UPDATE
            jira_ca_key = cache_entry["jira_ca_key"]
            run_log.info(f"Обновляем коррмеру {jira_ca_key}")
            update_issue_url = f"{create_issue_url}/{jira_ca_key}"
            description = get_description_by_url(update_issue_url, errors)  # вернет None, если задачи такой нет
            if description is None:
                msg = f"Ошибка получения description (is None) из {jira_ca_key}"
                errors.append(msg)
            else:
                dt_text = f"{datetime.now():%d.%m.%Y %H:%M:%S}"
                description += f"\n{'-' * 15} Обновлен {dt_text} {'-' * 15}\n"
                description += render_issue_description(index_name_norm, aggregated, errors, create=False)
                description += "\n"
                payload = {"fields": {"description": description}}

            if not errors:
                # создать новый payload
                ok = jira_request(
                    url=update_issue_url,
                    method="PUT",
                    payload=payload,
                    logger=run_log,
                    err_list=errors,
                    statuses=[200, 204],
                )

                if not ok:
                    msg = f"Не удалось выполнить UPDATE {jira_ca_key}"
                    errors.append(msg)
                else:
                    jira_ca_url = f"{jira_base_url}/browse/{jira_ca_key}"
                    run_log.info(f"Обновлена коррмера {jira_ca_url}")
                    update_jira_cache(ca_cache, index_name_norm, jira_ca_key)

                    print(jira_ca_url)

                    handle_file_movement(IN_JSON_DIR, DONE_JSON_DIR, index_name, errors, run_log)
                    
                    append_results_csv(
                        jira_result_file,
                        index_name=index_name_norm,
                        jira_ca_key=jira_ca_key,
                        aggregated=aggregated,
                        action=action,
                        err_list=errors
                    )

                    if jst.USE_SMTP:
                        subject = f"Обновлена коррмера {jira_ca_key} по индексу {index_name_norm}"
                        body = f"Ссылка - {jira_ca_url}\n"
                        smtp_err = send_email_with_attachments(jst.TO_ADDR, subject, body, logger=run_log)
                        if smtp_err:
                            main_errors.append(smtp_err)
                            run_log.error(f"smtp_err: {smtp_err}")

        if errors:
            handle_file_movement(IN_JSON_DIR, ERRORS_JSON_DIR, index_name, errors, run_log)

            if jst.USE_SMTP:
                # def send_email_with_attachments(to_addrs, subject, body, smtp_port=SMTP_PORT, attachments=None, logger=None):
                subject = f"Имеются ошибки при создании/обновлении коррмеры по индексу {index_name_norm}"
                body = f"errors:\n{errors}\n"
                smtp_err = send_email_with_attachments(jst.TO_ADDR, subject, body, logger=run_log)
                if smtp_err:
                    main_errors.append(smtp_err)
                    run_log.error(f"smtp_err: {smtp_err}")
        
        # Таймер нужен для обхода ограничений на стороне Jira (30 запросов в минуту)
        time.sleep(75)

    write_jira_cache(jira_cache_file, ca_cache, main_errors)

    if main_errors:
        if jst.USE_SMTP:
            # def send_email_with_attachments(to_addrs, subject, body, smtp_port=SMTP_PORT, attachments=None, logger=None):
            subject = f"Имеются основные ошибки (main_errors) в работе скрипта при создании/обновлении коррмеры"
            body = f"main_errors:\n{main_errors}\n"
            smtp_err = send_email_with_attachments(jst.TO_ADDR, subject, body, logger=run_log)
            if smtp_err:
                main_errors.append(smtp_err)
                run_log.error(f"smtp_err: {smtp_err}")

        run_log.error(f"main_errors: {main_errors}")
        err_log.error(f"main_errors: {main_errors}")

    input("\n\nClose manualy")
