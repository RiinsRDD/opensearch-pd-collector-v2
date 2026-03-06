from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.base import Base

class ScannerLog(Base):
    """
    История запусков сканера (как глобального, так и одиночного).
    """
    __tablename__ = "scanner_logs"

    id = Column(Integer, primary_key=True, index=True)
    scan_type = Column(String, nullable=False) # 'global', 'single'
    target_index = Column(String, nullable=True) # Для одиночного: паттерн индекса. Для глобального может быть null/all.
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    status = Column(String, nullable=False, default="running") # 'running', 'success', 'failed'
    findings_count = Column(Integer, default=0) # Кол-во новых найденных cache_key
    details = Column(String, nullable=True) # Логи в текстовом виде
    error_message = Column(String, nullable=True)
