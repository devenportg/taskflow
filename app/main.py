import logging
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.logging_config import configure_logging
from app.routers import comments, labels, projects, tasks, users

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TaskFlow API",
    version="1.0.0",
    description="REST API для управления задачами команды",
)

app.include_router(users.router, prefix="/v1/users", tags=["users"])
app.include_router(projects.router, prefix="/v1/projects", tags=["projects"])
app.include_router(labels.router, prefix="/v1/labels", tags=["labels"])
app.include_router(tasks.router, prefix="/v1/tasks", tags=["tasks"])
app.include_router(comments.router, prefix="/v1/comments", tags=["comments"])


@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    started_at = perf_counter()
    method = request.method
    path = request.url.path
    logger.debug("Request started method=%s path=%s", method, path)

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "Unhandled request error method=%s path=%s elapsed_ms=%.2f",
            method,
            path,
            elapsed_ms,
        )
        raise

    elapsed_ms = (perf_counter() - started_at) * 1000
    status_code = response.status_code
    log_message = "Request completed method=%s path=%s status=%s elapsed_ms=%.2f"
    log_args = (method, path, status_code, elapsed_ms)

    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error(log_message, *log_args)
    elif status_code >= status.HTTP_400_BAD_REQUEST:
        logger.warning(log_message, *log_args)
    else:
        logger.info(log_message, *log_args)

    return response


@app.get("/health", tags=["service"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.critical("Health check failed: database is unavailable")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    return {"status": "ok", "database": "up"}
