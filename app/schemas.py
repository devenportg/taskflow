from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserRole = Literal["operator", "admin"]
TaskStatus = Literal["open", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]

COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class CreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(CreateSchema):
    email: EmailStr = Field(max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    role: UserRole = "operator"


class UserUpdate(UpdateSchema):
    email: EmailStr | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None


class UserRead(ReadSchema):
    id: int
    email: str
    display_name: str
    role: UserRole
    created_at: datetime


class ProjectCreate(CreateSchema):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectUpdate(UpdateSchema):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class ProjectRead(ReadSchema):
    id: int
    name: str
    description: str | None
    created_at: datetime


class LabelCreate(CreateSchema):
    name: str = Field(min_length=1, max_length=64)
    color: str = Field(default="#6b7280", pattern=COLOR_PATTERN)


class LabelUpdate(UpdateSchema):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)


class LabelRead(ReadSchema):
    id: int
    name: str
    color: str


class TaskCreate(CreateSchema):
    project_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus = "open"
    priority: TaskPriority = "medium"
    assignee_id: int | None = Field(default=None, gt=0)
    label_id: int | None = Field(default=None, gt=0)


class TaskUpdate(UpdateSchema):
    project_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = Field(default=None, gt=0)
    label_id: int | None = Field(default=None, gt=0)


class TaskRead(ReadSchema):
    id: int
    project_id: int
    assignee_id: int | None
    label_id: int | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime


class CommentCreate(CreateSchema):
    task_id: int = Field(gt=0)
    author_id: int = Field(gt=0)
    body: str = Field(min_length=1)


class CommentUpdate(UpdateSchema):
    body: str | None = Field(default=None, min_length=1)


class CommentRead(ReadSchema):
    id: int
    task_id: int
    author_id: int
    body: str
    created_at: datetime
