# 12. Docker и Инфраструктура (Docker & Infrastructure)

Проект использует Docker Compose для развёртывания. Все compose-файлы находятся в корне проекта и используют общую сеть `pdn_network`.

## Compose-файлы

| Файл | Сервис | Порт | Назначение |
|------|--------|------|------------|
| `docker-compose.yml` | `api` (pdn_collector_api) | 8000 | FastAPI приложение |
| `docker-compose.postgres.yml` | `db` (pdn_postgres) | 5432 | PostgreSQL 15 |
| `docker-compose.exporters.yml` | `postgres_exporter`, `node_exporter` | 9187, 9100 | Экспортеры метрик |
| `docker-compose.prometheus.yml` | `prometheus` | 9090 | Сбор метрик |
| `docker-compose.grafana.yml` | `grafana` | 3000 | Визуализация метрик |

## Сеть

Все сервисы используют общую **external** сеть `pdn_network`. Перед запуском необходимо создать:

```bash
docker network create pdn_network
```

## Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /code

RUN apt-get update && apt-get install -y gcc g++ libffi-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /code/

ENV PYTHONPATH=/code
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## `docker-compose.yml` (API)

```yaml
services:
  api:
    build: .
    container_name: pdn_collector_api
    restart: always
    ports: ["8000:8000"]
    volumes:
      - ./app:/code/app
      - ./logs:/code/logs
    env_file: [.env]
    networks: [pdn_network]
```

- Volume `./app:/code/app` — hot-reload кода при разработке.
- Volume `./logs:/code/logs` — логи доступны с хоста.

## `docker-compose.postgres.yml`

```yaml
services:
  db:
    image: postgres:15
    container_name: pdn_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-pdn_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-pdn_password}
      POSTGRES_DB: ${POSTGRES_DB:-pdn_collector}
    ports: ["5432:5432"]
    volumes: [pdn_pgdata:/var/lib/postgresql/data]
```

## `docker-compose.exporters.yml`

```yaml
services:
  postgres_exporter:
    image: prometheuscommunity/postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://${POSTGRES_USER:-pdn_user}:${POSTGRES_PASSWORD:-pdn_password}@db:5432/${POSTGRES_DB:-pdn_collector}?sslmode=disable"
    ports: ["9187:9187"]

  node_exporter:
    image: prom/node-exporter:latest
    ports: ["9100:9100"]
```

## `docker-compose.prometheus.yml`

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports: ["9090:9090"]
```

> Требуется файл `prometheus.yml` в корне проекта с конфигурацией scrape targets.

## `docker-compose.grafana.yml`

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    ports: ["3000:3000"]
    volumes: [grafana_data:/var/lib/grafana]
```

## Команды запуска

```bash
# Создать сеть (один раз)
docker network create pdn_network

# Запуск всех сервисов
docker compose -f docker-compose.yml -f docker-compose.postgres.yml -f docker-compose.exporters.yml -f docker-compose.prometheus.yml -f docker-compose.grafana.yml up -d

# Только API + БД
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d

# Логи API
docker logs -f pdn_collector_api

# Применение миграций (внутри контейнера)
docker exec pdn_collector_api alembic upgrade head
```
