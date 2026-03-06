from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

class ScanScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        # We start the scheduler. In a real app we'd load timing from DB.
        self.scheduler.add_job(
            self._scheduled_scan_job,
            CronTrigger(minute="0"), # Runs every hour at minute 0
            id="hourly_scan_job",
            replace_existing=True
        )
        self.scheduler.start()
        logging.info("Started Background Scheduler for scanning")

    def stop(self):
        self.scheduler.shutdown()
        logging.info("Stopped Background Scheduler")

    async def _scheduled_scan_job(self):
        logging.info("Running scheduled background global scan...")
        from app.db.session import async_session_maker
        from app.services.scanner import ScannerService
        from app.services.opensearch_client import OpenSearchClient
        from sqlalchemy.future import select
        from app.models.settings import SystemSetting
        
        async with async_session_maker() as db:
            try:
                # В будущем можно брать список актуальных индексов из Settings или какой-то таблицы, 
                # пока просто запускам по *
                indices_to_scan = ["*"]
                
                # Инициализация
                os_client = OpenSearchClient()
                scanner = ScannerService(os_client)
                
                # Запуск
                total_new = await scanner.run_global_scan(db, hours=1, indices=indices_to_scan)
                logging.info(f"Scheduled scan completed successfully. Found {total_new} new/updated keys.")
                
            except Exception as e:
                logging.error(f"Scheduled scan failed: {e}")

scheduler_service = ScanScheduler()
