FROM python:3.12-slim

WORKDIR /code

# Установка системных зависимостей для сборки (компиляции)
RUN apt-get update && apt-get install -y gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем само приложение
COPY . /code/

ENV PYTHONPATH=/code

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
