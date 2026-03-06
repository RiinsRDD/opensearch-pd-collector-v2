# settings.py

import base64
import re
import app_secrets
from pathlib import Path


def encode(s):
    return base64.b64encode(s.encode("utf-8")).decode("utf-8")


def decode(s):
    return base64.b64decode(s.encode("utf-8")).decode("utf-8")


# ========= OpenSearch =========
OPENSEARCH_URL = "https://es-od.usvc.global.bcs"
USERNAME = app_secrets.OS_USERNAME
PASSWORD = app_secrets.OS_PASSWORD

INDICES_LIST_METHOD = '/_cat/indices/?format=json&h=index'

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

BATCH_SIZE = 10000
TIME_RANGE_GTE = "now-60m/m"
TIME_RANGE_LT = "now/m"

BODY = {
    "size": BATCH_SIZE,
    "_source": True,
    "query": {
        "range": {
            "@timestamp": {"gte": TIME_RANGE_GTE, "lt": TIME_RANGE_LT}
        }
    }
}

# ========= Flags =========
IS_EMAIL = True
IS_PHONE = True
IS_CARD = True
IS_FIO = False
SAVE_FIELD_OBJ_VALUE = True
EXAMPLES_COUNT = 3
EXAMPLES_SEPARATOR = " | "

# ========= Paths =========
OUTPUT_DIR = Path("C:/Users/GasanovOI/Documents/bcsdocs/main_opensearch_data/")
SCRIPTS_DIR = Path("C:/Users/GasanovOI/Documents/bcsdocs/main_opensearch_data/opensearch-pd-collector")

RAW_DATA_DIR = OUTPUT_DIR / "raw_indices_data"
RAW_DATA_DIR_DONE = OUTPUT_DIR / "done_raw"
OUT_JSON_DIR = OUTPUT_DIR / "out"
IN_JSON_DIR = OUTPUT_DIR / "in"
IN_JSON_DIR_RAW = OUTPUT_DIR / "in_raw"
DONE_JSON_DIR = OUTPUT_DIR / "done"
ERRORS_JSON_DIR = OUTPUT_DIR / "errors"
ERRORS_JSON_DIR_RAW = OUTPUT_DIR / "errors_raw"
UNVERIFIED_JSON_DIR = OUTPUT_DIR / "unverified"
UNVERIFIED_JSON_DIR_RAW = OUTPUT_DIR / "unverified_raw"

CACHE_FILE = SCRIPTS_DIR / "cache_get_os_data.csv"
RESULT_FILE = SCRIPTS_DIR / "results_get_os_data.csv"

JIRA_CA_CACHE_FILE = SCRIPTS_DIR / "jira_ca_cache.csv"
JIRA_CA_RESULT_FILE = SCRIPTS_DIR / "jira_ca_result.csv"
JIRA_CA_CACHE_FILE_DEV = SCRIPTS_DIR / "jira_ca_cache_dev.csv"
JIRA_CA_RESULT_FILE_DEV = SCRIPTS_DIR / "jira_ca_result_dev.csv"

OWNERS_FILE = SCRIPTS_DIR / "owners.csv"
OWNERS_FILE_DEV = SCRIPTS_DIR / "owners_dev.csv"

LOG_DIR = "logs"
RUN_LOG_NAME = 'run.log'
ERR_LOG_NAME = 'errors.log'

# ========= Index exclude =========
EXCLUDE_INDICES_KEYWORDS = [
    '.kibana',
    '.ds-logs-infra-consul-default',
    '.opendistro-reports-definitions',
    '.opendistro-job-scheduler-lock',
    '.opensearch-observability',
    '.ds-logs-infra-consul-tech',
    '.opendistro-reports-instances',
    '.opensearch-notifications-config',
    'security-auditlog',
    '.opendistro_security',
    '.tasks',
    '.ds-logs-bcs-vault-tech',
    'elk-logstash-legacy',
    'bbcs-security-check-x-compliance-sanction-company-mass-business',
    '.ds-logs-kafka-innovations-prod-tech',
    '.ds-logs-',
    'bcs-virtual-assistant-vm-tech'
]

# ========= Regex =========
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z]{2,}")

# PHONE_REGEX = re.compile(
#     r'(?<![\.\w])'                # Граница перед: НЕ точка, буква, цифра, _
#     r'[+]?'                       # Опциональный плюс  
#     r'(?:7|8)?'                   # Опциональный код страны
#     r'(?:\s?|\-|\(\d{3}\)\s?)'    # Разделитель
#     r'\(?'                        # Скобка
#     r'9\d{2}'                     # Код оператора
#     r'\)?'                        # Скобка
#     r'(?:\s?|\-)'                 # Разделитель
#     r'\d{3}'                      # 3 цифры
#     r'(?:\s?|\-)'                 # Разделитель  
#     r'\d{2}'                      # 2 цифры
#     r'(?:\s?|\-)'                 # Разделитель
#     r'\d{2}'                      # 2 цифры
#     r'(?![.\w])'                  # Граница после: НЕ точка и НЕ буква/цифра
# )

# Новая регулярка от 24.02.2026
# 1. (?<![\d\w.]) - защита от дробей 0.916... и слитного написания с буквами
# 2. (?:\+?[78])? - поддержка +7, 7, 8 (опционально)
# 3. (9\d{2})     - код оператора
# 4. (?![\d\w.])  - защита от хвостов в ID и дробных частях
PHONE_REGEX = re.compile(
    r'(?<![\d\w.])'
    r'(?:\+?[78])?'
    r'[\s\-]?\(?'
    r'(9\d{2})'
    r'\)?[\s\-]?'
    r'\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    r'(?![\d\w.])'
)

# исключаем ещё точку в начале
CARD_REGEX = re.compile(
    r'(?<![\d.])(?:\d{16}|(?:\d{4} ){3}\d{4}|(?:\d{4}-){3}\d{4})(?!\d)'
)

# Регулярка теперь требует пробел в начале (\s).
# Ищет 2 или 3 слова, разделенных пробелами, каждое с большой буквы.
# Включает латиницу и кириллицу.
FIO_REGEX = re.compile(
    r'\s([A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,}\s+[A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,}(?:\s+[A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]{1,})?)\b'
)


# ========= Excludes =========
EMAIL_EXCLUDE = [
    '@bcscapitaldifc.com',
    'rabbit@rabbit',
    '@bcs.ru',
    '.bcs.ru',
    '@bcs-bank.',
    '@org.bcs',
    '@bnk-cpg-data-processing.usvc-mf.global.bcs',
    '@fintarget.',
    '@broker.bcs.',
    '@bcslife.',
    '@noemail.com',
    '@GLOBAL.BCS',
    '@bcsgm.',
    '@morningstar',
    '@bcsprime',
    '@bcswm.',
    '@theultimagm.',
    '@bcs-forex.',
    '@ultimabank.',
    '@bcstech.',
    '@theultima.',
    '@placeholder.',
    '@global.bcs',
    '@oast.me',
    'test@gmail.com',
    'mail.gmail.com',
    'test@mail.ru',
    '39dKvXZkMWqmTwijOe2fCEdH5Ow@gmail.com'
]

MAIL_SERVICE_NAMES = {
    # Google
    "gmail", "google", "googlemail",
    # Yandex
    "yandex", "ya",
    # Mail.ru group
    "mail", "bk", "list", "inbox",
    # Microsoft
    "outlook", "hotmail", "live", "msn",
    # Yahoo / AOL
    "yahoo", "aol",
    # Apple
    "icloud", "me", "mac",
    # Proton
    "proton", "protonmail",
    # Zoho
    "zoho",
    # GMX
    "gmx",
    # Rambler
    "rambler", "lenta", "autorambler", "myrambler",
    # Fastmail
    "fastmail",
    # Tutanota
    "tutanota",
    # Seznam (CZ)
    "seznam",
    # QQ / Tencent
    "qq",
    # Naver / Korea
    "naver", "hanmail",
    # Orange / Wanadoo
    "orange", "wanadoo",
    # Web.de
    "web",
    # UK / EU
    "mailbox", "posteo", "laposte",
    # Misc
    "email", "e-mail"
}

# Только для анализа
UNKNOWN_MAIL_SERVICE_PARTS = set()

PHONE_EXCLUDE = [
    '  '
]

PHONE_EXCLUDE_KEYS = [
    'statfsgettotalbytes',
    'k-login',
    'preferredUsername',
    'userLogin',
    'ns',
    'ms'
]

PHONE_PREFIX_EXCLUDE = [
    'cardId=',
    'dkbo_id":"',
    'dkboId": "',
    'absClientId": "',
    'absClientId":"',
    'inn":"',
    'rate=',
    'externalId=',
    'accountId=',
    'depositId=',
    'depositIdDepositInfoMap={',
    '"depId":',
    'clientId": "',
    'clientid\": \"'
    'accountId": "',
    'externalId": "',
    '"depId": "',
    'mainAccountId=',
    'dkboId":"',
    'absClientId":',
    'absClientId=',
    'dkboId=',
    'depTypeId": "',
    'iddog": "',
    'idacc": "',
    'ABSCLIENTID\":',
    'ABSCLIENTID":',
    'CLIENTID\":',
    'CLIENTID:',
    'Total.Current=',
    'sender_doc_id=',
    'ibsoId\":\"',
    'ibsoId":"',
    'inn=',
    'cardId\": \"',
    'cardId": "',
    'TYPE\": \"long\", \"value\": \"',
    'TYPE": "long", "value": "',
    '"Заведены активы\",\"note\":\"',
    '"Заведены активы","note":"',
    'k-login\":\"',
    'k-login":"',
    'apajax.php?rand=',
    'username=',
    'configPath=/nuclei_test/',
    'ИНН ',
    'beneficiaryAccountNumber=',
    'ID_DOG Value=\"',
    'ID_DOG Value="',
    'iddkbo\": \"',
    'iddkbo": "',
    'clientId=',
    'cards=[',
    'uid":"'
]

PHONE_SUFFIX_EXCLUDE = [
    '=DepositInfo',
    '@',
    ') : GET /v1/inn'
]

CARD_EXCLUDE_KEYS = [
    'eventId',
    'clientIds',
    'trace_id',
    'x-request-id'
]

CARD_BINS = (
    "4",     # Visa
    "5",     # Mastercard
    "220",   # MIR
)

CARD_BANK_BINS_4 = {
    "2203",
    "4054",
    "4180",
    "4195",
    "4556",
    "4732",
    "5115",
    "5130",
    "5452",
    "5519",
    "5545",
    "5594",
    "5597",
}

# Коды, начинающиеся на 9, но НЕ используемые реальными абонентами РФ
INVALID_DEF_CODES = {
    # Резервные диапазоны
    '941', '942', '943', '944', '945', '946', '947', '948', '949', 
    '972', '973', '974', '975', '976', # Добавлена запятая здесь
    '940', # Абхазия
    '996', # Киргизия (или технический мусор в ваших логах)
}

# СНГ Окончания
# SURN_ENDS_CIS = (
#     'ов', 'ова', 'ев', 'ева', 'ин', 'ина', 'ий', 'ая', 'ко', 'ян', 'ых', 'их', 'дзе', 'швили', 'ук', 'юк', 'як',
#     'ov', 'ova', 'ev', 'eva', 'in', 'ina', 'iy', 'y', 'ko', 'yan', 'uk', 'yuk', 'yak'
# )

SURN_ENDS_CIS = (
    'ович', 'евич', 'овна', 'евна', 'ична', # Отчества (самый сильный маркер)
    'енко', 'янко', 'енко',                 # Украинские (вместо просто 'ко')
    'ский', 'ская', 'цкий', 'цкая',         # Польские/Русские
    'швили', 'дзе', 'ани',                  # Грузинские
    'янц', 'янс', 'уни',                    # Армянские
    'ова', 'ева', 'ина', 'ых', 'их',        # Женские и зауральские
    'евич', 'ович', 'инич',                 # Специфические мужские
    
    # Транслит (для логов/билетов)
    'ovich', 'evich', 'ovna', 'evna', 'ichna',
    'enko', 'skiy', 'skaya', 'tskiy', 'shvili', 'adze'
)

# Мировые окончания фамилий (Западная Европа, США, Балтика)
SURN_ENDS_WORLD = (
    'son', 'sen', 'sh', 'stein', 'berg', 'man', 'mann', 'er', 'ez', 'es', 
    'ic', 'ich', 'is', 'as', 'skas', 'ska', 'itis', 'en', 'eau', 'ard'
)

# Отчества
PATRON_ENDS = (
    'ович', 'евич', 'ич', 'овна', 'евна', 'ична', 'оглы', 'кызы',
    'ovich', 'evich', 'ovna', 'evna', 'ich', 'ogly', 'kyzy'
)

# Спец-маркеры (могут быть отдельными словами или идти через дефис)
FIO_SPECIAL_MARKERS = ['оглы', 'кызы', 'ogly', 'kyzy', 'ибн', 'ibn', 'фон', 'von', 'ван', 'van', 'де', 'de']


# ========= Patterns =========
PATTERNS = {
    'email': {
        'regex': EMAIL_REGEX,
        'exclude_patterns': EMAIL_EXCLUDE,
        'mail_service_names': MAIL_SERVICE_NAMES,
        'validator': None  # Заполнится в get_os_data.py
    },
    'phone': {
        'regex': PHONE_REGEX,
        'exclude_patterns': PHONE_EXCLUDE,
        'prefix_exclude': PHONE_PREFIX_EXCLUDE,
        'suffix_exclude': PHONE_SUFFIX_EXCLUDE,
        'invalid_def_codes': INVALID_DEF_CODES,
        'exclude_keys': PHONE_EXCLUDE_KEYS,
        'validator': None  # Заполнится в get_os_data.py
    },
    'card': {
        'regex': CARD_REGEX,
        'card_bins': CARD_BINS,
        'card_bank_bins_4': CARD_BANK_BINS_4,
        'exclude_keys': CARD_EXCLUDE_KEYS,
        'validator': None # Заполнится в get_os_data.py
    },
    'fio': {
        'regex': FIO_REGEX,
        'surn_ends_cis': SURN_ENDS_CIS,
        'surn_ends_world': SURN_ENDS_WORLD,
        'patron_ends': PATRON_ENDS,
        'fio_special_markers': FIO_SPECIAL_MARKERS,
        'validator': None
    }
}
