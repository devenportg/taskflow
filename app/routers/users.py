from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import apply_updates, commit_or_409, get_or_404
from app.database import get_db

router = APIRouter()


@router.get("", response_model=list[schemas.UserRead])
def list_users(
    db: Session = Depends(get_db),
    role: schemas.UserRole | None = Query(default=None),
):
    statement = select(models.User)
    if role is not None:
        statement = statement.where(models.User.role == role)
    return db.scalars(statement.order_by(models.User.id)).all()


@router.get("/{user_id}", response_model=schemas.UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.User, user_id, "User")


@router.post("", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = models.User(**payload.model_dump())
    db.add(user)
    commit_or_409(db)
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db)):
    user = get_or_404(db, models.User, user_id, "User")
    apply_updates(user, payload)
    commit_or_409(db)
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    user = get_or_404(db, models.User, user_id, "User")
    db.delete(user)
    commit_or_409(
        db,
        overrides={"fk_comments_author_id": "User has comments and cannot be deleted"},
    )
