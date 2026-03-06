from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from app.db.session import get_db
from app.services.scanner import ScannerService
from app.services.opensearch_client import OpenSearchClient
from app.models.logs import ScannerLog
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SingleScanRequest(BaseModel):
    hours: int = 24
    maxDocs: int = 10000

async def _bg_scan_task(index_pattern: str, max_docs: int):
    # We acquire a new DB session for the background task
    from app.db.session import async_session_maker
    async with async_session_maker() as db:
        log = ScannerLog(
            scan_type="single", 
            target_index=index_pattern, 
            status="running"
        )
        db.add(log)
        await db.commit()
        
        try:
            os_client = OpenSearchClient()
            scanner = ScannerService(os_client)
            
            # TODO: We might want to compute hours logic inside search_after_generator. 
            # Passing max_docs for now.
            findings = await scanner.scan_index(
                db=db, 
                index_pattern=index_pattern, 
                max_docs=max_docs, 
                is_global=False, 
                scan_type_tag='S'
            )
            
            log.status = "success"
            log.findings_count = findings
            log.duration_seconds = int((datetime.utcnow() - log.started_at).total_seconds())
            log.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Background scan error for {index_pattern}: {e}")
            log.status = "failed"
            log.error_message = str(e)
            log.duration_seconds = int((datetime.utcnow() - log.started_at).total_seconds())
            log.completed_at = datetime.utcnow()
            
        finally:
            db.add(log)
            await db.commit()

@router.post("/scan/{index_pattern}")
async def trigger_scan(index_pattern: str, params: SingleScanRequest, bg_tasks: BackgroundTasks):
    """Запуск одиночного сканирования с параметрами (Тегирование 'S')"""
    bg_tasks.add_task(_bg_scan_task, index_pattern, params.maxDocs)
    return {"message": f"Одиночное сканирование {index_pattern} запущено в фоне.", "params": params.dict()}

@router.get("/status")
async def get_scanner_status(db: AsyncSession = Depends(get_db)):
    """Текущий статус сканера (для ScannerStatusBar)"""
    res = await db.execute(select(ScannerLog).filter(ScannerLog.status == "running").order_by(desc(ScannerLog.started_at)).limit(1))
    running_log = res.scalars().first()
    
    if running_log:
        return {
            "status": "active",
            "current_index_pattern": running_log.target_index,
            "eta": "Running" # ETA calc would be complex without knowing total docs
        }
    else:
        return {
            "status": "idle",
            "current_index_pattern": None,
            "eta": None
        }

@router.get("/logs")
async def get_scanner_logs(db: AsyncSession = Depends(get_db), limit: int = 50):
    """История последних запусков сканера (для модального окна логов)"""
    res = await db.execute(select(ScannerLog).order_by(desc(ScannerLog.started_at)).limit(limit))
    logs = res.scalars().all()
    
    return [
        {
            "id": log.id,
            "scan_type": log.scan_type,
            "target_index": log.target_index,
            "status": log.status,
            "findings_count": log.findings_count,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "duration_seconds": log.duration_seconds,
            "details": log.error_message if log.status == "failed" else f"Успешно найдено {log.findings_count} шт."
        }
        for log in logs
    ]
