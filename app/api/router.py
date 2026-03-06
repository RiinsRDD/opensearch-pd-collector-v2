from fastapi import APIRouter
from app.api.endpoints import settings, indices_tree, tasks, scanner, auth

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(indices_tree.router, prefix="/indices", tags=["indices"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(scanner.router, prefix="/scanner", tags=["scanner"])
