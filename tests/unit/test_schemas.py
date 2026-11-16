import pytest
from pydantic import ValidationError

from app.schemas import (
    CommentCreate,
    LabelCreate,
    TaskCreate,
    TaskUpdate,
    UserCreate,
)


@pytest.mark.unit
def test_user_defaults_and_trims_text():
    user = UserCreate(
        email="roman@example.com",
        display_name="  Роман Моисеев  ",
    )

    assert user.role == "operator"
    assert user.display_name == "Роман Моисеев"


@pytest.mark.unit
def test_user_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", display_name="Роман")


@pytest.mark.unit
def test_create_schema_forbids_service_fields():
    with pytest.raises(ValidationError):
        UserCreate(
            email="roman@example.com",
            display_name="Роман",
            id=100,
        )


@pytest.mark.unit
def test_label_has_default_color_and_accepts_hex_color():
    default_label = LabelCreate(name="Backend")
    custom_label = LabelCreate(name="Urgent", color="#A1b2C3")

    assert default_label.color == "#6b7280"
    assert custom_label.color == "#A1b2C3"


@pytest.mark.unit
@pytest.mark.parametrize("color", ["red", "#123", "123456", "#gggggg", "#12345678"])
def test_label_rejects_invalid_color(color):
    with pytest.raises(ValidationError):
        LabelCreate(name="Color test", color=color)


@pytest.mark.unit
def test_task_defaults_and_positive_project_id():
    task = TaskCreate(project_id=3, title="Проверить API")

    assert task.status == "open"
    assert task.priority == "medium"

    with pytest.raises(ValidationError):
        TaskCreate(project_id=0, title="Неверный проект")


@pytest.mark.unit
def test_task_update_distinguishes_missing_field_from_explicit_null():
    no_changes = TaskUpdate()
    clear_assignee = TaskUpdate(assignee_id=None)

    assert no_changes.model_dump(exclude_unset=True) == {}
    assert clear_assignee.model_dump(exclude_unset=True) == {"assignee_id": None}


@pytest.mark.unit
def test_task_rejects_unknown_status():
    with pytest.raises(ValidationError):
        TaskCreate(project_id=1, title="Некорректный статус", status="closed")


@pytest.mark.unit
def test_comment_rejects_blank_body():
    with pytest.raises(ValidationError):
        CommentCreate(task_id=1, author_id=1, body="   ")
