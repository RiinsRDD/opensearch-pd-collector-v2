import sys
import logging
from pathlib import Path
from loguru import logger
from app.core.config import settings

def setup_logging():
    # Remove default logger
    logger.remove()
    
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    run_log_path = settings.LOG_DIR / settings.RUN_LOG_NAME
    err_log_path = settings.LOG_DIR / settings.ERR_LOG_NAME

    # JSON Console logger for modern systems
    logger.add(
        sys.stdout,
        format="{message}",
        level="INFO",
        serialize=True,
        enqueue=True
    )
    
    # File logger for all runs (standard format)
    logger.add(
        run_log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="5 MB",
        retention="5 days",
        encoding="utf-8",
        enqueue=True
    )

    # File logger for errors only (standard format)
    logger.add(
        err_log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="5 MB",
        retention="5 days",
        encoding="utf-8",
        enqueue=True
    )
    
    # Intercept standard logging messages into Loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
