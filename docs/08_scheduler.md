# 8. Планировщик (Scheduler)

Для автоматизации регулярных проверок используется `APScheduler` — модуль `ScanScheduler` (`app/services/scheduler.py`). Планировщик работает в том же event-loop, что и FastAPI (`AsyncIOScheduler`), без необходимости в отдельных воркерах типа Celery.

## Класс `ScanScheduler`

| Метод | Описание |
|-------|----------|
| `__init__()` | Создаёт экземпляр `AsyncIOScheduler` |
| `start()` | Добавляет задачу `_scheduled_scan_job` с `CronTrigger(minute="0")` (каждый час в :00). ID задачи: `hourly_scan_job` |
| `stop()` | Останавливает планировщик |
| `_scheduled_scan_job()` | Async-функция фонового сканирования (заглушка, логика подключения к `ScannerService` не реализована) |

Глобальный экземпляр: `scheduler_service = ScanScheduler()` (создаётся при импорте модуля).

## Логика фоновой работы

1. **Cron-запуск** — расписание по `CronTrigger(minute="0")`.
2. При старте FastAPI (в `main.py`) должен инициализироваться планировщик.
3. `_scheduled_scan_job` должен вызывать `ScannerService.run_global_scan()` (не реализовано).

> **Статус:** Логика фоновой работы реализована (M004). Планировщик подключён и вызывает `ScannerService.run_global_scan()`.

## Ручное управление (Web UI)

Настройка и просмотр статуса доступны через:

- `GET /api/v1/scanner/status` — текущий статус сканера
- `POST /api/v1/scanner/scan/{index_pattern}` — ручной запуск одиночного сканирования
