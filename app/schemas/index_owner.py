from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class IndexOwnerBase(BaseModel):
    index_pattern: str = Field(..., description="Паттерн индекса")
    cmdb_url: Optional[str] = Field(None, description="Полный путь url в CMDB базе")
    tech_debt_id: Optional[str] = Field(None, description="Тех долг")
    fio: Optional[str] = Field(None, description="ФИО ответственного")


class IndexOwnerCreate(IndexOwnerBase):
    pass


class IndexOwnerUpdate(IndexOwnerBase):
    pass


class IndexOwnerInDBBase(IndexOwnerBase):
    id: int

    model_config = {"from_attributes": True}


class IndexOwner(IndexOwnerInDBBase):
    pass
