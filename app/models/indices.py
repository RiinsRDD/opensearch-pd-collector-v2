from sqlalchemy import Column, Integer, String, Boolean
from app.models.base import Base

class IndexOwner(Base):
    __tablename__ = "index_owners"

    id = Column(Integer, primary_key=True, index=True)
    index_pattern = Column(String, unique=True, index=True, nullable=False)
    cmdb_url = Column(String, nullable=True)
    tech_debt_id = Column(String, nullable=True)
    fio = Column(String, nullable=True)
