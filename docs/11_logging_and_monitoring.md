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

Сервис разворачивается с Docker Compose. Мониторинг состоит из:

### Экспортеры (`docker-compose.exporters.yml`)

| Сервис | Образ | Порт | Назначение |
|--------|-------|------|------------|
| `postgres_exporter` | `prometheuscommunity/postgres-exporter` | 9187 | Метрики PostgreSQL |
| `node_exporter` | `prom/node-exporter:latest` | 9100 | Метрики хоста |

### Prometheus (`docker-compose.prometheus.yml`)

- Образ: `prom/prometheus:latest`
- Порт: 9090
- Конфиг: `./prometheus.yml` (маппится как volume)
- Volume: `prometheus_data`

### Grafana (`docker-compose.grafana.yml`)

- Образ: `grafana/grafana:latest`
- Порт: 3000
- Credentials: `GRAFANA_USER` / `GRAFANA_PASSWORD` (default: `admin/admin`)
- Volume: `grafana_data`
