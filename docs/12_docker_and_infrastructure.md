# 12. Docker и Инфраструктура (Docker & Infrastructure)

Проект использует Docker Compose для развёртывания. Все compose-файлы находятся в корне проекта и используют общую сеть `pdn_network`.

## Единый `docker-compose.yml` с профилями

Теперь все сервисы объединены в один файл с поддержкой профилей:

| Профиль | Сервисы | Описание |
|---------|---------|----------|
| `core` | `api`, `db` | Только API и PostgreSQL (минимальный стек) |
| `monitoring` | `postgres_exporter`, `node_exporter`, `prometheus`, `grafana` | Только мониторинг (если API уже работает) |
| `full` | все сервисы | Полный стек |

## Dockerfile (multi-stage build)

```dockerfile
# ---- Builder stage ----
FROM python:3.12-slim AS builder
WORKDIR /code
RUN apt-get update && apt-get install -y gcc g++ libffi-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Frontend builder ----
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Runtime stage ----
FROM python:3.12-slim
WORKDIR /code
COPY --from=builder /root/.local /root/.local
COPY --from=frontend-builder /frontend/dist /code/frontend/dist
COPY app/ ./app/
COPY alembic.ini .
COPY migrations/ ./migrations/
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/code
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Этапы сборки:**
1. **builder** — компиляция Python-зависимостей с `--user` флагом (не засоряет системный Python)
2. **frontend-builder** — сборка Vite/React фронтенда (`npm run build`)
3. **runtime** — финальный легкий образ, копирует только артефакты из builder stages

## `docker-compose.yml` (все сервисы в одном файле)

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
    profiles: ["core", "full"]

  db:
    image: postgres:15
    container_name: pdn_postgres
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-pdn_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-pdn_password}
      POSTGRES_DB: ${POSTGRES_DB:-pdn_collector}
    ports: ["5432:5432"]
    volumes: [pdn_pgdata:/var/lib/postgresql/data]
    networks: [pdn_network]
    profiles: ["core", "full"]

  postgres_exporter:
    image: prometheuscommunity/postgres-exporter
    container_name: pdn_postgres_exporter
    restart: always
    environment:
      DATA_SOURCE_NAME: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}?sslmode=disable"
    ports: ["9187:9187"]
    networks: [pdn_network]
    profiles: ["monitoring", "full"]

  node_exporter:
    image: prom/node-exporter:latest
    container_name: pdn_node_exporter
    restart: always
    ports: ["9100:9100"]
    networks: [pdn_network]
    profiles: ["monitoring", "full"]

  prometheus:
    image: prom/prometheus:latest
    container_name: pdn_prometheus
    restart: always
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports: ["9090:9090"]
    networks: [pdn_network]
    profiles: ["monitoring", "full"]

  grafana:
    image: grafana/grafana:latest
    container_name: pdn_grafana
    restart: always
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    ports: ["3000:3000"]
    volumes: [grafana_data:/var/lib/grafana]
    networks: [pdn_network]
    profiles: ["monitoring", "full"]

networks:
  pdn_network:
    external: true

volumes:
  pdn_pgdata:
  prometheus_data:
  grafana_data:
```

## `prometheus.yml` (корень репозитория)

Compose монтирует `./prometheus.yml:/etc/prometheus/prometheus.yml`. Без файла сервис `prometheus` не стартует.

**Факт на E.1:** файла в корне нет (C.1 в плане отмечен, содержимое в git отсутствует). Ожидаемые jobs:

| Job | Target | Назначение |
|-----|--------|------------|
| `prometheus` | `localhost:9090` | Self-scrape |
| `pdn-collector` | `api:8000`, path `/metrics` | Метрики FastAPI (`app/core/metrics.py`) |
| `postgres` | `postgres_exporter:9187` | PostgreSQL (профиль `monitoring` / `full`) |
| `node` | `node_exporter:9100` | Хост (профиль `monitoring` / `full`) |

`scrape_interval`: 15s. DNS-имена — сервисы из `docker-compose.yml` (не `db:9187`: Postgres сам метрик не отдаёт).

## `docker-compose.override.yml` (dev hot reload)

Автоматически подключается при `docker compose up` для разработки:

```yaml
services:
  api:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./app:/code/app
      - ./frontend/dist:/code/frontend/dist
    environment:
      - PYTHONPATH=/code
```

## Команды запуска

```bash
# Создать сеть (один раз)
docker network create pdn_network

# Только API + БД (минимальный стек)
docker compose --profile core up -d

# Полный стек (API + БД + мониторинг)
docker compose --profile full up -d

# Только мониторинг (если API уже есть)
docker compose --profile monitoring up -d

# Dev режим с hot-reload (использует override.yml)
docker compose --profile core up

# Логи API
docker logs -f pdn_collector_api

# Применение миграций (внутри контейнера)
docker exec pdn_collector_api alembic upgrade head

# Демо-данные (скрипт на хосте, БД на localhost:5432).
# В runtime-образ tests/ не копируется — запускать из корня репозитория:
POSTGRES_SERVER=localhost python -m tests.seed_mock_data
```

## Переменные окружения (`.env`)

```env
POSTGRES_SERVER=db
POSTGRES_USER=pdn_user
POSTGRES_PASSWORD=pdn_password
POSTGRES_DB=pdn_collector
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```

> **Важно:** В Docker `POSTGRES_SERVER=db` (имя сервиса в compose), на хосте — `localhost`.

## Устаревшие файлы

Следующие файлы больше не нужны и могут быть удалены:
- `docker-compose.postgres.yml`
- `docker-compose.exporters.yml`
- `docker-compose.prometheus.yml`
- `docker-compose.grafana.yml`