import traceback
import sys
import requests
import time
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import COMMASPACE

from types import SimpleNamespace

from jira_issue_settings import SMTP_SERVER, SMTP_PORT, FROM_ADDR


def get_tb():
    exc_type, exc_value, exc_tb = sys.exc_info()
    tb = traceback.format_exception(exc_type, exc_value, exc_tb)
    tb = [''.join(line.split('\n')) for line in tb[1:]]
    return ', '.join(tb)


def get_logger(logger=None):
    """Возвращает переданный логгер или объект-заглушку с принтами."""
    if logger:
        return logger
    
    return SimpleNamespace(
        info=lambda *args, **kwargs: print("[INFO]", *args, **kwargs),
        warning=lambda *args, **kwargs: print("[WARNING]", *args, **kwargs),
        error=lambda *args, **kwargs: print("[ERROR]", *args, **kwargs)
    )


def exec_request(
    url,
    method="GET",
    json=None,
    data=None,
    logger=None,
    auth=None,
    headers=None,
    statuses=None,
    timeout=10,
    max_retries=5
):
    log = get_logger(logger)
    errors = []

    # Проверка должна быть такой:
    if json and data:
        msg = "Логическая ошибка: переданы json и data одновременно"
        log.error(msg)
        return None, [msg]  # Выходим из функции ТОЛЬКО если есть ошибка
    
    # Подготовка заголовков
    request_headers = {'User-Agent': 'http_utils/1.0'}
    if headers:
        request_headers.update(headers)

    # Авторизация
    if auth:
        if isinstance(auth, str):
            request_headers['Authorization'] = f'Bearer {auth}'
        elif isinstance(auth, tuple) and len(auth) == 2:
            import base64

            credentials = base64.b64encode(f'{auth[0]}:{auth[1]}'.encode()).decode()
            request_headers['Authorization'] = f'Basic {credentials}'

    expected_statuses = statuses if statuses else [200, 201]
    if isinstance(expected_statuses, int):
        expected_statuses = [expected_statuses]

    response = None

    for attempt in range(max_retries):
        try:
            log.info(f"Attempt {attempt + 1}/{max_retries}: {method} {url}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json,
                data=data,
                timeout=timeout
            )

            # 1. УСПЕХ
            if response.status_code in expected_statuses:
                log.info(f"Success: {response.status_code}")
                log.info(f"Response: {response}")
                return response, []

            # 2. ФАТАЛЬНЫЕ СТАТУСЫ (Клиентские ошибки 4xx)
            # 408 (Timeout) и 429 (Too Many Requests) — исключения, их стоит ретраить
            if 400 <= response.status_code < 500 and response.status_code not in [408, 429]:
                err_msg = f"Fatal status {response.status_code} (Client Error). Stopping."
                log.error(err_msg)
                errors.append(err_msg)
                break 

            # 3. ВРЕМЕННЫЕ ОШИБКИ СЕРВЕРА (5xx) или 408/429
            log.warning(f"Retryable status code: {response.status_code}")

        # СЕТЕВЫЕ ИСКЛЮЧЕНИЯ
        except (requests.exceptions.ConnectTimeout, 
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError) as e:
            tb = get_tb()
            log.warning(tb)
            log.warning(f"Network temporary error (attempt {attempt + 1}): {str(e)}")
            response = None # Чтобы в конце понять, что ответа не было

        except requests.exceptions.RequestException as e:
            # Слишком много редиректов, плохой URL, проблемы с SSL
            tb = get_tb()
            log.error(tb)

            err_msg = f"Fatal request error: {str(e)}"
            log.error(err_msg)
            errors.append(err_msg)
            break

        except Exception as e:
            tb = get_tb()
            log.error(tb)

            err_msg = f"Unexpected code error: {str(e)}"
            log.error(err_msg)
            errors.append(err_msg)
            break

        # Пауза перед следующей попыткой
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            log.info(f"Waiting {wait_time}s before next attempt...")
            time.sleep(wait_time)

    # Итог после всех попыток
    if not errors:
        final_msg = f"All {max_retries} attempts exhausted. Last status: {getattr(response, 'status_code', 'No Response')}"
        errors.append(final_msg)
        log.error(final_msg)

    return response, errors


def send_email_with_attachments(to_addrs, subject, body, smtp_port=SMTP_PORT, attachments=None, logger=None):
    log = get_logger(logger)

    errors = []
    
    smtp_server = SMTP_SERVER
    from_addr = FROM_ADDR

    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = COMMASPACE.join(to_addrs)
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    if attachments:
        for file_path in attachments:
            file_data = file_path.read_bytes()

            part = MIMEApplication(file_data)
            part.add_header('Content-Disposition', 'attachment', filename=file_path.name)
            msg.attach(part)
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.ehlo()
            log.info(f'email has been sent to the: {to_addrs}')
            return []
    except Exception as e:
        tb = get_tb()
        log.error(tb)

        err_msg = f"could not send email, err: {e}"
        log.error(err_msg)
        errors.append(err_msg)
        return errors
