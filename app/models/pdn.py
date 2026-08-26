from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship, foreign
from datetime import datetime
from app.models.base import Base

class PDNPattern(Base):
    __tablename__ = "pdn_patterns"

    cache_key = Column(String, primary_key=True, index=True)
    index_pattern = Column(String, index=True, nullable=False)
    field_path = Column(String, nullable=False)
    pdn_type = Column(String, nullable=False)
    context_type = Column(String, nullable=False)
    key_hint = Column(String, nullable=True)
    extra_fields = Column(JSON, nullable=True)

    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    hit_count = Column(Integer, default=1)

    status = Column(String, default="new")
    false_positive_comment = Column(String, nullable=True)
    custom_message = Column(String, nullable=True)

    # Relationships
    findings = relationship(
        "PDNFinding",
        primaryjoin="PDNPattern.cache_key==PDNFinding.cache_key",
        viewonly=True
    )
    pattern_tags = relationship(
        "PatternTagLink",
        primaryjoin="PDNPattern.cache_key==PatternTagLink.pattern_cache_key",
        viewonly=True
    )
    jira_tasks = relationship(
        "JiraTask",
        primaryjoin="foreign(PDNPattern.index_pattern)==JiraTask.index_pattern",
        viewonly=True,
        uselist=True,
    )


class PDNFinding(Base):
    __tablename__ = "pdn_findings"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String, ForeignKey("pdn_patterns.cache_key"), index=True, nullable=False)
    
    doc_id = Column(String, nullable=False)
    index_pattern = Column(String, nullable=False)

    raw_value = Column(String, nullable=False)
    field_path = Column(String, nullable=False)
    
    prefix_raw = Column(String, nullable=True)
    suffix_raw = Column(String, nullable=True)

    full_document = Column(JSON, nullable=True)
    found_at = Column(DateTime, default=datetime.utcnow)