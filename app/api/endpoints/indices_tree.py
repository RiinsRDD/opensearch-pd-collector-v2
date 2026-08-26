from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import logging

from app.db.session import get_db
from app.models.pdn import PDNPattern, PDNFinding
from app.models.settings import SystemSetting
from app.models.tags import Tag, PatternTagLink
from app.models.tasks import JiraTask
from app.models.indices import IndexOwner
from app.services.jira_integration import JiraService
from app.services.opensearch_client import OpenSearchClient
from app.services.scanner import ScannerService
from app.api.deps import require_viewer, require_analyst, require_admin
from app.models.user import User
import asyncio

router = APIRouter()
jira_service = JiraService()
logger = logging.getLogger(__name__)

@router.get("/")
async def get_indices_tree(
    status: Optional[str] = None, 
    tags: Optional[str] = None, 
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_viewer)
):
    """
    Возвращает древовидную структуру индексов, типов ПДн и cache_key.
    Использует selectinload для предзагрузки findings, tags и jira_tasks (избегает N+1).
    """
    query = select(PDNPattern).options(
        selectinload(PDNPattern.findings),
        selectinload(PDNPattern.pattern_tags).selectinload(PatternTagLink.tag),
        selectinload(PDNPattern.jira_tasks)
    )
    if status:
        query = query.filter(PDNPattern.status == status)
    if tags:
        tag_names = tags.split(",")
        query = query.join(PatternTagLink).join(Tag).filter(Tag.name.in_(tag_names))
        
    result = await db.execute(query)
    patterns = result.scalars().unique().all()
    
    tree_map = {}
    new_counts = {}
    
    for p in patterns:
        idx = p.index_pattern
        ptype = p.pdn_type
        
        if idx not in tree_map:
            tree_map[idx] = {"id": idx, "name": idx, "type": "index", "children": {}}
            new_counts[idx] = 0
            
        if p.status == "new":
            new_counts[idx] += 1
            
        if ptype not in tree_map[idx]["children"]:
            tree_map[idx]["children"][ptype] = {"id": f"{idx}_{ptype}", "name": ptype, "type": "pdn_type", "children": []}
            
        # Get examples from preloaded findings (limit to 3, ordered by found_at DESC)
        findings = sorted(
            p.findings,
            key=lambda f: f.found_at.timestamp() if f.found_at else 0,
            reverse=True,
        )[:3]
        example_values = [f.raw_value for f in findings]
        first_full_document = findings[0].full_document if findings else None
        
        # Check if any jira task exists for this index
        has_jira = len(p.jira_tasks) > 0
        
        # Get tags from preloaded pattern_tags
        tag_list = [{"id": pt.tag.id, "name": pt.tag.name, "color": pt.tag.color} for pt in p.pattern_tags if pt.tag]
        
        child = {
            "id": p.cache_key,
            "name": p.field_path,
            "type": "cache_key",
            "pattern": {
                "cache_key": p.cache_key,
                "index_pattern": p.index_pattern,
                "field_path": p.field_path,
                "pdn_type": p.pdn_type,
                "context_type": p.context_type,
                "key_hint": p.key_hint,
                "extra_fields": p.extra_fields,
                "hit_count": p.hit_count,
                "status": p.status,
                "custom_message": p.custom_message,
                "tags": tag_list,
                "examples": example_values,
                "full_document": first_full_document,
                "has_jira_task": has_jira
            }
        }
        tree_map[idx]["children"][ptype]["children"].append(child)
        
    tree = []
    for idx, idx_data in tree_map.items():
        children_list = []
        for ptype, ptype_data in idx_data["children"].items():
            children_list.append(ptype_data)
        idx_data["children"] = children_list
        tree.append(idx_data)
        
    return {"tree": tree, "new_counts": new_counts}

class PatchPatternRequest(BaseModel):
    status: Optional[str] = None
    custom_message: Optional[str] = None


@router.patch("/{cache_key}")
async def patch_pattern(
    cache_key: str,
    payload: PatchPatternRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_analyst),
):
    result = await db.execute(select(PDNPattern).filter(PDNPattern.cache_key == cache_key))
    pattern = result.scalars().first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates:
        pattern.status = updates["status"]
    if "custom_message" in updates:
        pattern.custom_message = updates["custom_message"]

    await db.commit()
    await db.refresh(pattern)
    return {
        "cache_key": pattern.cache_key,
        "status": pattern.status,
        "custom_message": pattern.custom_message,
    }


@router.delete("/{cache_key}")
async def delete_pattern(
    cache_key: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    result = await db.execute(select(PDNPattern).filter(PDNPattern.cache_key == cache_key))
    pattern = result.scalars().first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    await db.execute(delete(PDNFinding).filter(PDNFinding.cache_key == cache_key))
    await db.execute(delete(PatternTagLink).filter(PatternTagLink.pattern_cache_key == cache_key))
    await db.delete(pattern)
    await db.commit()
    return {"ok": True, "cache_key": cache_key}


async def _bg_update_examples(cache_key: str):
    from app.db.session import async_session_maker
    async with async_session_maker() as db:
        try:
            async with OpenSearchClient() as os_client:
                scanner = ScannerService(os_client)
                await scanner.update_examples_for_pattern(db, cache_key)
        except Exception as e:
            logger.error(f"Background examples update error for {cache_key}: {e}")


@router.post("/examples/update/{cache_key}")
async def update_examples(
    cache_key: str,
    bg_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_analyst),
):
    """Принудительное обновление примеров для конкретного cache_key (тег 'U')."""
    result = await db.execute(select(PDNPattern).filter(PDNPattern.cache_key == cache_key))
    pattern = result.scalars().first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    bg_tasks.add_task(_bg_update_examples, cache_key)
    return {
        "accepted": True,
        "cache_key": cache_key,
        "message": f"Обновление примеров для {cache_key} запущено в фоне (тег 'U').",
    }

class CreateJiraTasksRequest(BaseModel):
    cache_keys: List[str]
    custom_message: Optional[str] = None

async def _get_jira_settings(db: AsyncSession) -> dict:
    result = await db.execute(select(SystemSetting).filter(SystemSetting.key.startswith("jira_")))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}

def _require_jira_token(user: User) -> str:
    token = (user.jira_token or "").strip()
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Jira token is not set for this user. Set jira_token before creating tasks.",
        )
    return token

@router.post("/jira/tasks")
async def create_jira_tasks(
    payload: CreateJiraTasksRequest, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_analyst)
):
    if not payload.cache_keys:
        raise HTTPException(status_code=400, detail="No cache keys provided")

    auth_token = _require_jira_token(user)
        
    # Get index pattern from the first confirmed pattern
    patterns_result = await db.execute(
        select(PDNPattern).filter(
            PDNPattern.cache_key.in_(payload.cache_keys),
            PDNPattern.status == "confirmed"
        )
    )
    patterns = patterns_result.scalars().all()
    
    if not patterns:
        raise HTTPException(status_code=400, detail="No confirmed patterns found for the provided keys")

    index_pattern = patterns[0].index_pattern
    
    index_owner_result = await db.execute(
        select(IndexOwner).filter(IndexOwner.index_pattern == index_pattern)
    )
    index_owner = index_owner_result.scalars().first()
    
    jira_settings = await _get_jira_settings(db)
    
    issue_key = await jira_service.create_issue(
        auth_token=auth_token,
        index_pattern=index_pattern,
        cache_keys=[p.cache_key for p in patterns],
        comment=payload.custom_message or "",
        settings=jira_settings,
        index_owner=index_owner
    )
    
    if not issue_key:
        raise HTTPException(status_code=500, detail="Failed to create Jira task")
        
    db_task = JiraTask(
        jira_issue_key=issue_key,
        index_pattern=index_pattern,
        status="open",
        author_name=user.username
    )
    db.add(db_task)
    await db.commit()
    
    return {"message": f"Создано задач для {len(patterns)} паттернов.", "issue_key": issue_key}

@router.get("/jira/tasks/{index_pattern}")
async def get_jira_tasks_by_index(
    index_pattern: str, 
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_viewer)
):
    tasks_result = await db.execute(
        select(JiraTask)
        .filter(JiraTask.index_pattern == index_pattern)
        .order_by(JiraTask.jira_issue_key)
    )
    tasks = tasks_result.scalars().all()
    return [
       {
           "id": t.id,
           "jira_issue_key": t.jira_issue_key,
           "index_pattern": t.index_pattern,
           "author_name": t.author_name,
           "created_at": t.created_at,
           "jira_url": f"https://jira.global.bcs/browse/{t.jira_issue_key}"
       }
       for t in tasks
    ]

@router.get("/jira/history")
async def get_jira_tasks_history(
    limit: int = 100, 
    page: int = 1, 
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_viewer)
):
    offset = (page - 1) * limit
    tasks_result = await db.execute(
        select(JiraTask)
        .order_by(JiraTask.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    tasks = tasks_result.scalars().all()
    total_result = await db.execute(select(JiraTask))
    total = len(total_result.scalars().all())
    
    return {
        "items": [
           {
               "id": t.id,
               "jira_issue_key": t.jira_issue_key,
               "index_pattern": t.index_pattern,
               "author_name": t.author_name,
               "created_at": t.created_at,
               "jira_url": f"https://jira.global.bcs/browse/{t.jira_issue_key}"
           }
           for t in tasks
        ],
        "total": total,
        "limit": limit,
        "page": page
    }

@router.post("/jira/create_all_confirmed")
async def create_all_confirmed_tasks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin)
):
    auth_token = _require_jira_token(user)

    patterns_result = await db.execute(
        select(PDNPattern).filter(PDNPattern.status == "confirmed")
    )
    patterns = patterns_result.scalars().all()
    
    if not patterns:
        return {"message": "Нет подтвержденных паттернов для создания задач"}
        
    by_index = {}
    for p in patterns:
        if p.index_pattern not in by_index:
            by_index[p.index_pattern] = []
        by_index[p.index_pattern].append(p.cache_key)
        
    created_count = 0
    jira_settings = await _get_jira_settings(db)
    
    for idx, keys in by_index.items():
        index_owner_result = await db.execute(
            select(IndexOwner).filter(IndexOwner.index_pattern == idx)
        )
        index_owner = index_owner_result.scalars().first()
        issue_key = await jira_service.create_issue(
            auth_token=auth_token,
            index_pattern=idx,
            cache_keys=keys,
            comment="Автоматическое создание задачи по всем подтверждённым ПДн",
            settings=jira_settings,
            index_owner=index_owner
        )
        if issue_key:
            db_task = JiraTask(
                jira_issue_key=issue_key,
                index_pattern=idx,
                status="open",
                author_name="system"
            )
            db.add(db_task)
            created_count += 1
            await asyncio.sleep(0.5) 
            
    await db.commit()
    
    return {"message": f"Задачи успешно созданы. Всего создано инцидентов: {created_count}."}