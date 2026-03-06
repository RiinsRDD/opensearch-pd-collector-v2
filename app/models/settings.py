from sqlalchemy import Column, Integer, String, Boolean
from app.models.base import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(String, default="string") # string, int, bool, json

class RegexRule(Base):
    """
    Таблица для хранения регулярок, исключений, префиксов/суффиксов.
    """
    __tablename__ = "regex_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    pdn_type = Column(String, index=True, nullable=False) # 'phone', 'email', 'card', 'fio'
    rule_type = Column(String, nullable=False) # 'regex', 'exclude_pattern', 'prefix_exclude', 'suffix_exclude', 'exclude_key', 'invalid_def_code'
    value = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

class IndexKeyExclusion(Base):
    """Per-index полнопутевое исключение ключей документа."""
    __tablename__ = "index_key_exclusions"

    id = Column(Integer, primary_key=True, index=True)
    index_pattern = Column(String, index=True, nullable=False)  # "my-test-tech-index*"
    pdn_type = Column(String, nullable=False)                    # "phone", "email", "card", "fio"
    key_path = Column(String, nullable=False)                    # "kubernetes.namespace.container"
    is_active = Column(Boolean, default=True)

class StatusSetting(Base):
    """
    Таблица для хранения кастомных статусов и их цветов
    """
    __tablename__ = "status_settings"

    id = Column(String, primary_key=True, index=True) # 'new', 'confirmed', 'false_positive', 'unverified'
    label = Column(String, nullable=False)
    color = Column(String, nullable=False) # e.g., '#ef4444'
    is_active = Column(Boolean, default=True)
