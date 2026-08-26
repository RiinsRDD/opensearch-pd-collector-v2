# 8. Планировщик (Scheduler)

Для автоматизации регулярных проверок используется `APScheduler` — модуль `ScanScheduler` (`app/services/scheduler.py`). Планировщик работает в том же event-loop, что и FastAPI (`AsyncIOScheduler`), без необходимости в отдельных воркерах типа Celery.

## Класс `ScanScheduler`

| Метод | Описание |
|-------|----------|
| `__init__()` | Создаёт экземпляр `AsyncIOScheduler` |
| `start()` | Добавляет задачу `_scheduled_scan_job` с `CronTrigger(minute="0")` (каждый час в :00). ID задачи: `hourly_scan_job` |
| `stop()` | Останавливает планировщик |
| `_scheduled_scan_job()` | Async-функция фонового сканирования, вызывает `ScannerService.run_global_scan()` с `async with OpenSearchClient() as os_client:` |

Глобальный экземпляр: `scheduler_service = ScanScheduler()` (создаётся при импорте модуля).

## Интеграция с FastAPI

Планировщик запускается и останавливается вместе с приложением в `app/main.py`:

```python
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting API: {settings.PROJECT_NAME} v{settings.VERSION}")
    scheduler_service.start()
    job = scheduler_service.scheduler.get_job("hourly_scan_job")
    if job:
        logger.info(f"Next scheduled scan: {job.next_run_time}")
        from app.core.metrics import scheduler_job_status, scheduler_last_run
        scheduler_job_status.labels(job_id="hourly_scan_job").set(1)
        scheduler_last_run.labels(job_id="hourly_scan_job").set(job.next_run_time.timestamp())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API")
    scheduler_service.stop()
    from app.core.metrics import scheduler_job_status
    scheduler_job_status.labels(job_id="hourly_scan_job").set(0)
```

## Логика фоновой работы

1. **Cron-запуск** — расписание по `CronTrigger(minute="0")` (каждый час в :00).
2. При старте FastAPI планировщик инициализируется и начинает отсчёт.
3. `_scheduled_scan_job` вызывает `ScannerService.run_global_scan()` с параметрами `hours=1, indices=["*"]`.
4. Использует connection pooling через `async with OpenSearchClient() as os_client:`.

## Метрики (Prometheus)

Автоматически обновляются при старте/стопе и в `run_global_scan`:

| Метрика | Тип | Лейблы | Описание |
|---------|-----|--------|----------|
| `pdn_scheduler_job_status` | Gauge | `job_id` | Статус джобы (1=running, 0=stopped) |
| `pdn_scheduler_last_run_timestamp` | Gauge | `job_id` | Timestamp следующего запуска |

## Ручное управление (Web UI)

Настройка и просмотр статуса доступны через:
- `GET /api/v1/scanner/status` — текущий статус сканера (polling каждые 10 сек)
- `POST /api/v1/scanner/scan/{index_pattern}` — ручной запуск одиночного сканирования (тег `S`)
- `GET /api/v1/scanner/logs` — история запусков (модалка `ScannerLogsModal`)