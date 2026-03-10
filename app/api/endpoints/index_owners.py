from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.session import get_db
from app.models.indices import IndexOwner as IndexOwnerModel
from app.schemas.index_owner import IndexOwner, IndexOwnerCreate, IndexOwnerUpdate

router = APIRouter()

@router.get("/", response_model=List[IndexOwner])
async def get_index_owners(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IndexOwnerModel).order_by(IndexOwnerModel.index_pattern))
    return result.scalars().all()

@router.post("/", response_model=IndexOwner)
async def create_index_owner(owner: IndexOwnerCreate, db: AsyncSession = Depends(get_db)):
    # Check if exists
    result = await db.execute(select(IndexOwnerModel).where(IndexOwnerModel.index_pattern == owner.index_pattern))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Index owner for this pattern already exists")
    
    new_owner = IndexOwnerModel(
        index_pattern=owner.index_pattern,
        cmdb_url=owner.cmdb_url,
        tech_debt_id=owner.tech_debt_id,
        fio=owner.fio
    )
    db.add(new_owner)
    await db.commit()
    await db.refresh(new_owner)
    return new_owner

@router.put("/{owner_id}", response_model=IndexOwner)
async def update_index_owner(owner_id: int, owner: IndexOwnerUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IndexOwnerModel).where(IndexOwnerModel.id == owner_id))
    db_owner = result.scalars().first()
    if not db_owner:
        raise HTTPException(status_code=404, detail="Index owner not found")
        
    db_owner.index_pattern = owner.index_pattern
    db_owner.cmdb_url = owner.cmdb_url
    db_owner.tech_debt_id = owner.tech_debt_id
    db_owner.fio = owner.fio
    
    await db.commit()
    await db.refresh(db_owner)
    return db_owner

@router.delete("/{owner_id}")
async def delete_index_owner(owner_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IndexOwnerModel).where(IndexOwnerModel.id == owner_id))
    db_owner = result.scalars().first()
    if not db_owner:
        raise HTTPException(status_code=404, detail="Index owner not found")
        
    await db.delete(db_owner)
    await db.commit()
    return {"message": "Index owner deleted successfully"}
