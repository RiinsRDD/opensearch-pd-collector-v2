from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_tasks():
    return []

@router.post("/")
async def create_task(payload: dict):
    return {"message": "Задача создана в Jira (mock)"}
