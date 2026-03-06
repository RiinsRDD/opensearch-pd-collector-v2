from fastapi import FastAPI
from app.core.config import settings
from app.core.logger import setup_logging
from app.api.router import api_router
from loguru import logger

def create_app() -> FastAPI:
    setup_logging()
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting API: {settings.PROJECT_NAME} v{settings.VERSION}")
        
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down API")

    @app.get("/health")
    def health_check():
        return {"status": "ok", "project": settings.PROJECT_NAME}

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
