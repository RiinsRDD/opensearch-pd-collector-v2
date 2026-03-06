from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login():
    return {"access_token": "mock_token", "token_type": "bearer"}

@router.get("/me")
async def get_current_user():
    return {"username": "admin", "role": "admin"}
