# 11. Логирование и Мониторинг (Logging & Monitoring)

## Логирование (Loguru)

Настроено в `app/core/logger.py` — функция `setup_logging()`, вызывается при создании FastAPI-приложения.

### Конфигурация логгеров

| Sink | Уровень | Формат | Ротация | Хранение |
|------|---------|--------|---------|----------|
| `stdout` | INFO | JSON (serialize=True) | — | — |
| `logs/run.log` | INFO | Human-readable (`YYYY-MM-DD HH:mm:ss \| LEVEL \| name:func:line - message`) | 5 MB | 5 дней |
| `logs/errors.log` | ERROR | Human-readable (тот же формат) | 5 MB | 5 дней |

### Перехват стандартного logging

Реализован `InterceptHandler` — все сообщения через стандартный Python `logging` перенаправляются в Loguru.

### Логируемые события

- Новые совпадения ПДн
- Ошибки подключения к БД / OpenSearch
- Статистика завершившегося сканера
- Создание задач Jira

## Пути логов

Настраиваются через `app/core/config.py`:

| Параметр | Значение по умолчанию | Описание |
|----------|----------------------|----------|
| `LOG_DIR` | `logs/` | Директория логов |
| `RUN_LOG_NAME` | `run.log` | Файл общих логов |
| `ERR_LOG_NAME` | `errors.log` | Файл ошибок |

## Метрики (Prometheus / Grafana)

### Приложенные метрики (`app/core/metrics.py`)

Эндпоинт `/metrics` доступен в FastAPI приложении. Метрики собираются через `prometheus-client`.

#### Scanner метрики
| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `pdn_scan_duration_seconds` | Histogram | `scan_type`, `index_pattern` | Длительность сканирования |
| `pdn_findings_total` | Counter | `pdn_type`, `status` | Общее количество найденных ПДн |
| `pdn_scan_errors_total` | Counter | `scan_type`, `error_type` | Ошибки сканирования |

#### Jira метрики
| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `pdn_jira_tasks_created_total` | Counter | `index_pattern`, `result` | Созданные Jira задачи (success/failed) |
| `pdn_jira_errors_total` | Counter | `error_type` | Ошибки Jira (auth, rate_limit, http, timeout, connection, unexpected) |

#### DB метрики
| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `pdn_db_query_duration_seconds` | Histogram | `operation` | Длительность запросов к БД |

#### Scheduler метрики
| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `pdn_scheduler_job_status` | Gauge | `job_id` | Статус джобы (1=running, 0=stopped) |
| `pdn_scheduler_last_run_timestamp` | Gauge | `job_id` | Timestamp следующего запуска |

#### HTTP метрики
| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `pdn_http_requests_total` | Counter | `method`, `endpoint`, `status` | Общее количество HTTP запросов |
| `pdn_http_request_duration_seconds` | Histogram | `method`, `endpoint` | Длительность HTTP запросов |

#### Active scans
| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `pdn_active_scans` | Gauge | `scan_type` | Количество активных сканирований |

### Инструментирование кода

Метрики автоматически собираются в сервисах:

**Scanner (`app/services/scanner.py`):**
```python
with scan_duration.labels(scan_type=scan_type, index_pattern=index_pattern).time():
    findings = await self.scan_index(...)
scan_findings.labels(pdn_type='total', status='scanned').inc(findings_count)
active_scans.labels(scan_type=scan_type).inc()  # в начале
active_scans.labels(scan_type=scan_type).dec()  # в finally
```

**Jira (`app/services/jira_integration.py`):**
```python
jira_tasks_created.labels(index_pattern=index_pattern, result="success").inc()
jira_errors.labels(error_type="auth|rate_limit|http|timeout|connection|unexpected").inc()
jira_tasks_created.labels(index_pattern=index_pattern, result="failed").inc()
```

### Эндпоинт метрик

Доступен по адресу: `GET /metrics`

### Экспортеры инфраструктуры (`docker-compose.yml`)

| Сервис | Образ | Порт | Назначение |
|--------|-------|------|------------|
| `postgres_exporter` | `prometheuscommunity/postgres-exporter` | 9187 | Метрики PostgreSQL |
| `node_exporter` | `prom/node-exporter:latest` | 9100 | Метрики хоста |

### Prometheus

- Образ: `prom/prometheus:latest`
- Порт: 9090
- Ожидаемый конфиг: `./prometheus.yml` (volume в `docker-compose.yml`)
- Jobs по спецификации C.1: `pdn-collector` → `api:8000/metrics`, `postgres` → `postgres_exporter:9187`, `node` → `node_exporter:9100`
- **Факт на E.1:** файла `prometheus.yml` в корне репозитория нет — контейнер `prometheus` без него не стартует
- Volume: `prometheus_data`

### Grafana

- Образ: `grafana/grafana:latest`
- Порт: 3000
- Credentials: `GRAFANA_USER` / `GRAFANA_PASSWORD` (default: `admin/admin`)
- Volume: `grafana_data`
- Дашборд: `docs/grafana-dashboards/pdn-collector.json`

#### Панели дашборда:
1. **Scan Duration (p50, p95, p99)** — временные ряды длительности сканирования
2. **Findings by Type (last 1h)** — pie chart типов ПДн
3. **Findings by Status (last 1h)** — pie chart статусов
4. **Scan Errors (last 1h)** — pie chart ошибок сканирования
5. **Jira Tasks Created Rate** — временной ряд создания задач
6. **Jira Errors by Type (last 1h)** — pie chart ошибок Jira
7. **DB Query Duration (p50, p95, p99)** — временные ряды БД запросов
8. **Scheduler Job Status** — stat panel (running/stopped)
9. **Scheduler Next Run** — stat panel (unix timestamp)
10. **Active Scans** — stat panel (gauge)
11. **HTTP Requests Rate** — временной ряд HTTP запросов
12. **HTTP Request Duration (p50, p95, p99)** — временные ряды HTTP

### Команды

```bash
# Проверить метрики приложения
curl http://localhost:8000/metrics

# Запустить полный стек с мониторингом
docker compose --profile full up -d

# Открыть Grafana
open http://localhost:3000
# Login: admin / admin
# Import dashboard: docs/grafana-dashboards/pdn-collector.json
```

## Error Handling (Глобальный exception handler)

В `app/main.py` реализован единый формат ошибок и глобальные обработчики исключений.

### Единый формат ошибки

Все ошибки API возвращают единую структуру:

```json
{
  "error": {
    "code": 404,
    "message": "Pattern not found",
    "details": [],
    "request_id": "a1b2c3d4"
  }
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `code` | int | HTTP статус код |
| `message` | string | Человекочитаемое сообщение об ошибке |
| `details` | array | Детали валидации (для 422) или пустой массив |
| `request_id` | string | Уникальный ID запроса (из заголовка `X-Request-ID` или генерируется) |

### Request ID

- При каждом запросе генерируется/пробрасывается `X-Request-ID` (middleware)
- Возвращается в заголовке ответа `X-Request-ID`
- Используется для трейсинга в логах

### Обработчики исключений

| Исключение | Статус | Описание |
|------------|--------|----------|
| `HTTPException` | original | Пользовательские ошибки (404, 400, 403, 410, etc.) |
| `RequestValidationError` | 422 | Разбор query/body FastAPI; тот же JSON `{error.code,message,details,request_id}` |
| `ValidationError` (pydantic) | 422 | Тот же формат, отдельный handler |
| `SQLAlchemyError` | 500 | Ошибки базы данных (логируются с traceback) |
| `Exception` (generic) | 500 | Все остальные неперехваченные ошибки |

### Примеры ответов

**404 Not Found:**
```json
{
  "error": {
    "code": 404,
    "message": "Pattern not found",
    "details": [],
    "request_id": "a1b2c3d4"
  }
}
```

**422 Validation Error:**
```json
{
  "error": {
    "code": 422,
    "message": "Validation error",
    "details": [
      {"loc": ["body", "cache_keys"], "msg": "field required", "type": "value_error.missing"}
    ],
    "request_id": "a1b2c3d4"
  }
}
```

**500 Internal Server Error:**
```json
{
  "error": {
    "code": 500,
    "message": "Internal server error",
    "details": [],
    "request_id": "a1b2c3d4"
  }
}
```

### Логирование ошибок

- Все 500 ошибки логируются через `logger.exception()` с полным traceback
- В лог добавляется `request_id` для корреляции с запросом
- Логи попадают в `logs/errors.log` и stdout (JSON)