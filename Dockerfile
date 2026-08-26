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