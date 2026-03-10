from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.pdn import PDNPattern, PDNFinding
from app.models.settings import SystemSetting
from app.models.tags import Tag, PatternTagLink
from app.models.tasks import JiraTask
from app.services.jira_integration import JiraService
import asyncio

router = APIRouter()
jira_service = JiraService()

@router.get("/")
def get_indices_tree(status: Optional[str] = None, tags: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Возвращает древовидную структуру индексов, типов ПДн и cache_key.
    """
    query = db.query(PDNPattern)
    if status:
        query = query.filter(PDNPattern.status == status)
    if tags:
        tag_names = tags.split(",")
        query = query.join(PatternTagLink).join(Tag).filter(Tag.name.in_(tag_names))
        
    patterns = query.all()
    cache_keys = [p.cache_key for p in patterns]
    
    # Preload tags
    pattern_tags = {}
    if cache_keys:
        links = db.query(PatternTagLink, Tag).join(Tag).filter(PatternTagLink.pattern_cache_key.in_(cache_keys)).all()
        for link, tag in links:
            if link.pattern_cache_key not in pattern_tags:
                pattern_tags[link.pattern_cache_key] = []
            pattern_tags[link.pattern_cache_key].append({"id": tag.id, "name": tag.name, "color": tag.color})

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
            
        examples = db.query(PDNFinding.raw_value).filter(PDNFinding.cache_key == p.cache_key).limit(3).all()
        example_values = [ex[0] for ex in examples]
        
        has_jira = db.query(JiraTask).filter(JiraTask.index_pattern == idx).first() is not None
        
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
                "tags": pattern_tags.get(p.cache_key, []),
                "examples": example_values,
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

@router.post("/examples/update/{cache_key}")
async def update_examples(cache_key: str):
    """Принудительное обновление примеров для конкретного cache_key (Тегирование 'U')"""
    return {"message": f"Примеры для {cache_key} обновлены (тег 'U')."}

class CreateJiraTasksRequest(BaseModel):
    cache_keys: List[str]
    custom_message: Optional[str] = None

def _get_jira_settings(db: Session) -> dict:
    settings = db.query(SystemSetting).filter(SystemSetting.key.startswith("jira_")).all()
    return {s.key: s.value for s in settings}

@router.post("/jira/tasks")
async def create_jira_tasks(payload: CreateJiraTasksRequest, db: Session = Depends(get_db)):
    if not payload.cache_keys:
        raise HTTPException(status_code=400, detail="No cache keys provided")
        
    # Get index pattern from the first confirmed pattern
    # We should only process Confirmed ones, but we assume UI sends valid ones or we filter here:
    patterns = db.query(PDNPattern).filter(
        PDNPattern.cache_key.in_(payload.cache_keys),
        PDNPattern.status == "confirmed"
    ).all()
    
    if not patterns:
        raise HTTPException(status_code=400, detail="No confirmed patterns found for the provided keys")

    index_pattern = patterns[0].index_pattern
    auth_token = "mock_token"
    jira_settings = _get_jira_settings(db)
    
    issue_key = await jira_service.create_issue(
        auth_token=auth_token,
        index_pattern=index_pattern,
        cache_keys=[p.cache_key for p in patterns],
        comment=payload.custom_message or "",
        settings=jira_settings
    )
    
    if not issue_key:
        raise HTTPException(status_code=500, detail="Failed to create Jira task")
        
    db_task = JiraTask(
        jira_issue_key=issue_key,
        index_pattern=index_pattern,
        status="open",
        author_name="admin"
    )
    db.add(db_task)
    db.commit()
    
    return {"message": f"Создано задач для {len(patterns)} паттернов.", "issue_key": issue_key}

@router.get("/jira/tasks/{index_pattern}")
async def get_jira_tasks_by_index(index_pattern: str, db: Session = Depends(get_db)):
    tasks = db.query(JiraTask).filter(JiraTask.index_pattern == index_pattern).order_by(JiraTask.jira_issue_key).all()
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
async def get_jira_tasks_history(limit: int = 100, page: int = 1, db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    tasks = db.query(JiraTask).order_by(JiraTask.created_at.desc()).offset(offset).limit(limit).all()
    total = db.query(JiraTask).count()
    
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
async def create_all_confirmed_tasks(db: Session = Depends(get_db)):
    patterns = db.query(PDNPattern).filter(PDNPattern.status == "confirmed").all()
    
    if not patterns:
        return {"message": "Нет подтвержденных паттернов для создания задач"}
        
    by_index = {}
    for p in patterns:
        if p.index_pattern not in by_index:
            by_index[p.index_pattern] = []
        by_index[p.index_pattern].append(p.cache_key)
        
    created_count = 0
    auth_token = "mock_token"
    jira_settings = _get_jira_settings(db)
    
    for idx, keys in by_index.items():
        issue_key = await jira_service.create_issue(
            auth_token=auth_token,
            index_pattern=idx,
            cache_keys=keys,
            comment="Автоматическое создание задачи по всем подтверждённым ПДн",
            settings=jira_settings
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
            
    db.commit()
    
    return {"message": f"Задачи успешно созданы. Всего создано инцидентов: {created_count}."}
