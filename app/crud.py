from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)

CONSTRAINT_MESSAGES: dict[str, str] = {
    "uq_users_email": "User with this email already exists",
    "uq_labels_name": "Label with this name already exists",
    "ck_users_role": "Role must be one of: operator, admin",
    "ck_labels_color": "Color must be in #RRGGBB format",
    "ck_tasks_status": "Status must be one of: open, in_progress, done",
    "ck_tasks_priority": "Priority must be one of: low, medium, high",
    "ck_comments_body": "Comment body must not be empty",
    "fk_tasks_project_id": "Project does not exist",
    "fk_tasks_assignee_id": "Assignee (user) does not exist",
    "fk_tasks_label_id": "Label does not exist",
    "fk_comments_task_id": "Task does not exist",
    "fk_comments_author_id": "Author (user) does not exist",
}


def get_or_404(db: Session, model: type[ModelT], obj_id: int, name: str) -> ModelT:
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{name} not found")
    return obj


def commit_or_409(db: Session, overrides: dict[str, str] | None = None) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        messages = {**CONSTRAINT_MESSAGES, **(overrides or {})}
        detail = messages.get(constraint, "Duplicate value or invalid reference")
        raise HTTPException(status.HTTP_409_CONFLICT, detail=detail) from exc


def apply_updates(obj: ModelT, payload: Any) -> None:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
