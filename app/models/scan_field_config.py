from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.models.base import Base


class ScanFieldConfig(Base):
    """
    Configuration for additional document fields used for PD separation/grouping.
    Each row defines an additional field_path to extract from documents of matching indices.
    Values of these fields are included in cache_key and stored in PDNPattern.extra_fields.
    
    Default required entries (index_pattern="*"):
      - NameOfMicroService
      - kubernetes.container.name
    """
    __tablename__ = "scan_field_configs"

    id = Column(Integer, primary_key=True, index=True)
    index_pattern = Column(String, nullable=False, default="*")  # "*" = all indices
    field_path = Column(String, nullable=False)  # e.g. "NameOfMicroService"
    is_active = Column(Boolean, default=True)
    is_required = Column(Boolean, default=False)  # True for mandatory fields (can't be deleted)
    created_at = Column(DateTime, default=datetime.utcnow)
