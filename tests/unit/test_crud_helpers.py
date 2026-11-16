from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app import models
from app.crud import apply_updates, commit_or_409, get_or_404
from app.schemas import TaskUpdate


class FakeSession:
    def __init__(self, result=None, commit_error=None):
        self.result = result
        self.commit_error = commit_error
        self.rolled_back = False

    def get(self, model, obj_id):
        return self.result

    def commit(self):
        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self):
        self.rolled_back = True


@pytest.mark.unit
def test_get_or_404_returns_existing_object():
    expected = SimpleNamespace(id=7)
    result = get_or_404(FakeSession(result=expected), models.User, 7, "User")

    assert result is expected


@pytest.mark.unit
def test_get_or_404_raises_http_404_for_missing_object():
    with pytest.raises(HTTPException) as error:
        get_or_404(FakeSession(), models.User, 777, "User")

    assert error.value.status_code == 404
    assert error.value.detail == "User not found"


@pytest.mark.unit
def test_apply_updates_changes_only_fields_that_were_sent():
    task = SimpleNamespace(title="Old title", status="open", assignee_id=12)

    apply_updates(task, TaskUpdate(status="done", assignee_id=None))

    assert task.title == "Old title"
    assert task.status == "done"
    assert task.assignee_id is None


@pytest.mark.unit
def test_commit_or_409_maps_named_constraint_to_conflict():
    original = SimpleNamespace(diag=SimpleNamespace(constraint_name="uq_users_email"))
    integrity_error = IntegrityError("INSERT", {}, original)
    session = FakeSession(commit_error=integrity_error)

    with pytest.raises(HTTPException) as error:
        commit_or_409(session)

    assert error.value.status_code == 409
    assert error.value.detail == "User with this email already exists"
    assert session.rolled_back is True


@pytest.mark.unit
def test_commit_or_409_uses_generic_message_for_unknown_constraint():
    original = SimpleNamespace(diag=SimpleNamespace(constraint_name="unknown_constraint"))
    integrity_error = IntegrityError("INSERT", {}, original)
    session = FakeSession(commit_error=integrity_error)

    with pytest.raises(HTTPException) as error:
        commit_or_409(session)

    assert error.value.status_code == 409
    assert error.value.detail == "Duplicate value or invalid reference"
    assert session.rolled_back is True
