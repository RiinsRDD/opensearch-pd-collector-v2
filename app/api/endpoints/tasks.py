from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_viewer
from app.api.endpoints.indices_tree import get_jira_tasks_history
from app.db.session import get_db
from app.models.user import User

router = APIRouter()

REMOVED_CREATE_DETAIL = (
    "Creating Jira issues is POST /api/v1/indices/jira/tasks. "
    "This /tasks POST alias has been removed."
)


@router.get("/")
async def get_tasks(
    limit: int = 100,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_viewer),
):
    """Same payload as GET /indices/jira/history. The Tasks page uses that path."""
    return await get_jira_tasks_history(limit=limit, page=page, db=db, _=user)


@router.post("/")
async def create_task():
    raise HTTPException(status_code=410, detail=REMOVED_CREATE_DETAIL)
