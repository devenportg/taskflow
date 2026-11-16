"""End-to-end workflow against a separately running local API server."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url


@pytest.fixture
def live_api() -> Callable:
    base_url = os.getenv("TASKFLOW_E2E_BASE_URL")
    test_database_url = os.getenv("TASKFLOW_TEST_DATABASE_URL")
    if not base_url or not test_database_url:
        pytest.skip(
            "Для E2E задайте TASKFLOW_E2E_BASE_URL и TASKFLOW_TEST_DATABASE_URL; "
            "запустите API отдельно на тестовой PostgreSQL-БД."
        )

    parsed_db = make_url(test_database_url)
    if parsed_db.get_backend_name() != "postgresql" or not parsed_db.database:
        pytest.fail("TASKFLOW_TEST_DATABASE_URL должен указывать на PostgreSQL-БД.")
    if "test" not in parsed_db.database.lower():
        pytest.fail("Имя E2E-БД должно содержать 'test' — например taskflow_test.")

    parsed_http = urlsplit(base_url)
    if parsed_http.scheme != "http" or parsed_http.hostname not in {"localhost", "127.0.0.1"}:
        pytest.fail("Для безопасности E2E-тесты разрешены только к локальному HTTP-серверу.")

    base_url = base_url.rstrip("/")

    def request(method: str, path: str, payload: dict | None = None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(
            f"{base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urlopen(req, timeout=10) as response:
                raw = response.read()
                body = json.loads(raw.decode("utf-8")) if raw else None
                return response.status, body
        except HTTPError as exc:
            raw = exc.read()
            body = json.loads(raw.decode("utf-8")) if raw else None
            return exc.code, body
        except URLError as exc:
            pytest.fail(f"Не удалось обратиться к локальному API {base_url}: {exc}")

    return request


def test_team_member_completes_taskflow_lifecycle(live_api):
    """Полный сценарий по HTTP: создать, отфильтровать, обновить и удалить данные."""
    run = uuid4().hex[:10]
    created = {}

    try:
        status, user = live_api(
            "POST",
            "/v1/users",
            {"email": f"e2e-{run}@example.com", "display_name": "E2E Test User"},
        )
        assert status == 201, user
        created["user"] = user

        status, project = live_api(
            "POST",
            "/v1/projects",
            {"name": f"E2E project {run}", "description": "Full HTTP workflow"},
        )
        assert status == 201, project
        created["project"] = project

        status, label = live_api(
            "POST",
            "/v1/labels",
            {"name": f"E2E label {run}", "color": "#2563eb"},
        )
        assert status == 201, label
        created["label"] = label

        status, task = live_api(
            "POST",
            "/v1/tasks",
            {
                "project_id": project["id"],
                "assignee_id": user["id"],
                "label_id": label["id"],
                "title": "Prepare release",
                "description": "Complete the API scenario",
                "priority": "high",
            },
        )
        assert status == 201, task
        created["task"] = task
        assert task["status"] == "open"

        status, comment = live_api(
            "POST",
            "/v1/comments",
            {"task_id": task["id"], "author_id": user["id"], "body": "Work has started"},
        )
        assert status == 201, comment
        created["comment"] = comment

        status, tasks = live_api(
            "GET",
            f"/v1/tasks?project_id={project['id']}&status=open",
        )
        assert status == 200
        assert [item["id"] for item in tasks] == [task["id"]]

        status, comments = live_api("GET", f"/v1/comments?task_id={task['id']}")
        assert status == 200
        assert [item["id"] for item in comments] == [comment["id"]]

        status, updated = live_api(
            "PATCH",
            f"/v1/tasks/{task['id']}",
            {"status": "done"},
        )
        assert status == 200
        assert updated["status"] == "done"
        assert updated["title"] == "Prepare release"
        assert updated["assignee_id"] == user["id"]

        # RESTRICT: пользователя с комментарием удалить нельзя.
        status, _ = live_api("DELETE", f"/v1/users/{user['id']}")
        assert status == 409

        # CASCADE: удаление проекта удаляет задачу и комментарий.
        status, _ = live_api("DELETE", f"/v1/projects/{project['id']}")
        assert status == 204
        status, _ = live_api("GET", f"/v1/tasks/{task['id']}")
        assert status == 404
        status, _ = live_api("GET", f"/v1/comments/{comment['id']}")
        assert status == 404

        status, _ = live_api("DELETE", f"/v1/users/{user['id']}")
        assert status == 204
        status, health = live_api("GET", "/health")
        assert status == 200
        assert health == {"status": "ok", "database": "up"}

    finally:
        # Уборка уникальных тестовых записей, если сценарий упал на середине.
        project = created.get("project")
        if project:
            live_api("DELETE", f"/v1/projects/{project['id']}")
        label = created.get("label")
        if label:
            live_api("DELETE", f"/v1/labels/{label['id']}")
        user = created.get("user")
        if user:
            live_api("DELETE", f"/v1/users/{user['id']}")
