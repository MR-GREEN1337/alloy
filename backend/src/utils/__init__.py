from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
import time
import sys
import json

from src.db.postgresql import postgres_db
from src.core.settings import get_settings

settings = get_settings()

# --- Structured Logging Configuration ---
class JsonLogFormatter:
    def format(self, record):
        log_object = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "source": {
                "name": record["name"],
                "file": record["file"].path,
                "line": record["line"],
            },
        }
        if record["extra"]:
            log_object["extra"] = record["extra"]
        if record["exception"]:
            log_object["exception"] = str(record["exception"])
            
        return json.dumps(log_object) + "\n"

def setup_logging():
    logger.remove()
    log_format = JsonLogFormatter().format if settings.ENVIRONMENT != "development" else None
    logger.add(sys.stderr, level="INFO", format=log_format)

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"Starting up in {settings.ENVIRONMENT} mode...")
    start_time = time.time()
    
    try:
        await postgres_db.create_db_and_tables()
        logger.info("Database connection and tables verified.")
    except Exception as e:
        logger.critical(f"Database connection failed: {e}")
        if settings.FAIL_FAST:
            raise RuntimeError("Database connection failed.") from e

    logger.info(f"Startup complete in {time.time() - start_time:.2f}s")
    yield
    logger.info("Shutting down...")