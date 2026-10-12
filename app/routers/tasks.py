from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, commit_or_409, get_or_404
from app.database import get_db

router = APIRouter()


@router.get("", response_model=list[schemas.TaskRead])
def list_tasks(
    db: Session = Depends(get_db),
    project_id: int | None = Query(default=None, gt=0),
    status: schemas.TaskStatus | None = Query(default=None),
    priority: schemas.TaskPriority | None = Query(default=None),
    assignee_id: int | None = Query(default=None, gt=0),
    label_id: int | None = Query(default=None, gt=0),
):
    statement = select(models.Task)
    if project_id is not None:
        statement = statement.where(models.Task.project_id == project_id)
    if status is not None:
        statement = statement.where(models.Task.status == status)
    if priority is not None:
        statement = statement.where(models.Task.priority == priority)
    if assignee_id is not None:
        statement = statement.where(models.Task.assignee_id == assignee_id)
    if label_id is not None:
        statement = statement.where(models.Task.label_id == label_id)
    return db.scalars(statement.order_by(models.Task.id)).all()


@router.get("/{task_id}", response_model=schemas.TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Task, task_id, "Task")


@router.post("", response_model=schemas.TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(**payload.model_dump())
    db.add(task)
    commit_or_409(db)
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=schemas.TaskRead)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = get_or_404(db, models.Task, task_id, "Task")
    apply_updates(task, payload)
    commit_or_409(db)
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)) -> None:
    task = get_or_404(db, models.Task, task_id, "Task")
    db.delete(task)
    commit_or_409(db)
