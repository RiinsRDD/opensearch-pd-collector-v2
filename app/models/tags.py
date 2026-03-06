from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.models.base import Base

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    color = Column(String, nullable=True) # hex for frontend
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PatternTagLink(Base):
    __tablename__ = "pattern_tags"

    pattern_cache_key = Column(String, ForeignKey("pdn_patterns.cache_key"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
