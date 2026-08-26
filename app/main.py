from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.logger import setup_logging
from app.api.router import api_router
from app.services.scheduler import scheduler_service
from app.core.metrics import metrics_endpoint, http_requests_total, http_request_duration
from loguru import logger
import time
import uuid
import logging

def create_app() -> FastAPI:
    setup_logging()
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
    )

    app.include_router(api_router, prefix="/api/v1")
    app.get("/metrics")(metrics_endpoint)

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Metrics middleware
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        http_request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response

    # Exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "details": [],
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": 422,
                    "message": "Validation error",
                    "details": exc.errors(),
                    "request_id": getattr(request.state, "request_id", "unknown"),
                }
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": 422,
                    "message": "Validation error",
                    "details": exc.errors(),
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error", extra={"request_id": getattr(request.state, "request_id", "unknown")})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal database error",
                    "details": [],
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception", extra={"request_id": getattr(request.state, "request_id", "unknown")})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal server error",
                    "details": [],
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            }
        )

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting API: {settings.PROJECT_NAME} v{settings.VERSION}")
        scheduler_service.start()
        job = scheduler_service.scheduler.get_job("hourly_scan_job")
        if job:
            logger.info(f"Next scheduled scan: {job.next_run_time}")
            from app.core.metrics import scheduler_job_status, scheduler_last_run
            scheduler_job_status.labels(job_id="hourly_scan_job").set(1)
            scheduler_last_run.labels(job_id="hourly_scan_job").set(job.next_run_time.timestamp())
        
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down API")
        scheduler_service.stop()
        from app.core.metrics import scheduler_job_status
        scheduler_job_status.labels(job_id="hourly_scan_job").set(0)

    @app.get("/health")
    def health_check():
        return {"status": "ok", "project": settings.PROJECT_NAME}

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)