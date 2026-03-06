from sqlalchemy import Column, Integer, String, Boolean
from app.models.base import Base

class IndexOwner(Base):
    __tablename__ = "index_owners"

    id = Column(Integer, primary_key=True, index=True)
    index_pattern = Column(String, unique=True, index=True, nullable=False)
    team_name = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    jira_key = Column(String, nullable=True)
    is_active = Column(Boolean, default=True) # Сканировать ли этот индекс
    override_global_settings = Column(Boolean, default=False)
