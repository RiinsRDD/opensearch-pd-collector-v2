from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.base import Base

class JiraTask(Base):
    __tablename__ = "jira_tasks"

    id = Column(Integer, primary_key=True, index=True)
    jira_issue_key = Column(String, unique=True, index=True, nullable=False)
    index_pattern = Column(String, index=True, nullable=False)
    
    status = Column(String, default="open") # open / in_progress / resolved / rejected
    assignee = Column(String, nullable=True)
    author_name = Column(String, nullable=True) # ФИО автора
    jira_url = Column(String, nullable=True) # Ссылка на задачу
    
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
