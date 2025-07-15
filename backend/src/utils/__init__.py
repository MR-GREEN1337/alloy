from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
import time
import sys
import json

from src.db.postgresql import postgres_db
from src.core.settings import get_settings
from src.db.models import rebuild_all_models # <-- IMPORT THE FIX

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
    """
    Configures logging.
    Uses a structured JSON format for non-development environments
    and Loguru's default, human-friendly format for development.
    """
    logger.remove()
    
    if settings.ENVIRONMENT != "development":
        # For production, staging, etc., use the JSON formatter
        log_format = JsonLogFormatter().format
        logger.add(sys.stderr, level="INFO", format=log_format)
    else:
        # For local development, use the default, colorful Loguru format
        logger.add(sys.stderr, level="INFO")

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- SETUP PHASE ---
    setup_logging()
    logger.info(f"Starting up in {settings.ENVIRONMENT} mode...")
    start_time = time.time()
    
    # Resolve all model relationships before touching the database.
    rebuild_all_models()

    try:
        await postgres_db.create_db_and_tables()
        logger.info("Database connection and tables verified.")

        # CORE FIX: In development, after recreating the schema, the connection
        # pool may contain stale connections with invalid prepared statement
        # caches. Disposing the pool forces new, clean connections to be made.
        if settings.ENVIRONMENT == "development":
            logger.warning("DEV MODE: Disposing connection pool to clear caches after schema rebuild.")
            await postgres_db.engine.dispose()
            logger.info("Connection pool disposed successfully.")

    except Exception as e:
        logger.critical(f"Database connection failed: {e}")
        if settings.FAIL_FAST:
            raise RuntimeError("Database connection failed.") from e

    logger.info(f"Startup complete in {time.time() - start_time:.2f}s")
    
    # --- APPLICATION RUNNING ---
    yield
    
    # --- SHUTDOWN PHASE ---
    logger.info("Shutting down...")