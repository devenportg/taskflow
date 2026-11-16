from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


def unique_id() -> str:
    return uuid4().hex[:10]


def create_user(client, tag: str | None = None) -> dict:
    tag = tag or unique_id()
    response = client.post(
        "/v1/users",
        json={"email": f"{tag}@example.com", "display_name": f"User {tag}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_project(client, tag: str | None = None) -> dict:
    tag = tag or unique_id()
    response = client.post(
        "/v1/projects",
        json={"name": f"Project {tag}", "description": "Integration test"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_label(client, tag: str | None = None) -> dict:
    tag = tag or unique_id()
    response = client.post("/v1/labels", json={"name": f"Label {tag}"})
    assert response.status_code == 201, response.text
    return response.json()


def create_task(client, project_id: int, **overrides) -> dict:
    payload = {"project_id": project_id, "title": f"Task {unique_id()}", **overrides}
    response = client.post("/v1/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_and_openapi_use_the_application(client):
    health = client.get("/health")
    docs = client.get("/docs")
    openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "up"}
    assert docs.status_code == 200
    assert openapi.status_code == 200
    assert "/v1/tasks" in openapi.json()["paths"]


def test_user_crud_filter_duplicate_and_not_found(client):
    tag = unique_id()
    payload = {"email": f"{tag}@example.com", "display_name": f"User {tag}"}

    created = client.post("/v1/users", json=payload)
    assert created.status_code == 201
    user = created.json()
    assert user["role"] == "operator"
    assert user["created_at"]

    assert client.get(f"/v1/users/{user['id']}").json()["email"] == payload["email"]
    assert any(item["id"] == user["id"] for item in client.get("/v1/users?role=operator").json())

    updated = client.patch(f"/v1/users/{user['id']}", json={"display_name": "Updated name"})
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Updated name"
    assert updated.json()["email"] == payload["email"]

    duplicate = client.post("/v1/users", json=payload)
    assert duplicate.status_code == 409

    deleted = client.delete(f"/v1/users/{user['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"/v1/users/{user['id']}").status_code == 404


def test_project_crud(client):
    tag = unique_id()
    created = client.post(
        "/v1/projects",
        json={"name": f"Project {tag}", "description": "Initial description"},
    )
    assert created.status_code == 201
    project = created.json()

    assert client.get(f"/v1/projects/{project['id']}").json()["name"] == f"Project {tag}"

    updated = client.patch(f"/v1/projects/{project['id']}", json={"description": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated"
    assert updated.json()["name"] == f"Project {tag}"

    assert client.delete(f"/v1/projects/{project['id']}").status_code == 204
    assert client.get(f"/v1/projects/{project['id']}").status_code == 404


def test_label_crud_and_delete_sets_task_label_to_null(client):
    project = create_project(client)
    label = create_label(client)
    assert label["color"] == "#6b7280"

    task = create_task(client, project["id"], label_id=label["id"])
    assert task["label_id"] == label["id"]

    updated = client.patch(f"/v1/labels/{label['id']}", json={"color": "#22c55e"})
    assert updated.status_code == 200
    assert updated.json()["color"] == "#22c55e"

    deleted = client.delete(f"/v1/labels/{label['id']}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    task_after_delete = client.get(f"/v1/tasks/{task['id']}")
    assert task_after_delete.status_code == 200
    assert task_after_delete.json()["label_id"] is None


def test_task_crud_filter_partial_update_and_not_found(client):
    project = create_project(client)
    task = create_task(client, project["id"], status="open", priority="high")
    other_task = create_task(client, project["id"], status="done")

    filtered = client.get(f"/v1/tasks?project_id={project['id']}&status=open")
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [task["id"]]

    updated = client.patch(f"/v1/tasks/{task['id']}", json={"status": "in_progress"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["title"] == task["title"]
    assert updated.json()["priority"] == "high"

    clear_assignee = client.patch(f"/v1/tasks/{task['id']}", json={"assignee_id": None})
    assert clear_assignee.status_code == 200
    assert clear_assignee.json()["assignee_id"] is None

    assert client.delete(f"/v1/tasks/{other_task['id']}").status_code == 204
    assert client.get("/v1/tasks/999999999").status_code == 404


def test_comment_crud_filter_and_author_restrict(client):
    user = create_user(client)
    project = create_project(client)
    task = create_task(client, project["id"])

    created = client.post(
        "/v1/comments",
        json={"task_id": task["id"], "author_id": user["id"], "body": "First comment"},
    )
    assert created.status_code == 201
    comment = created.json()

    filtered = client.get(f"/v1/comments?task_id={task['id']}")
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [comment["id"]]

    updated = client.patch(f"/v1/comments/{comment['id']}", json={"body": "Edited comment"})
    assert updated.status_code == 200
    assert updated.json()["body"] == "Edited comment"

    # Автор с комментариями не удаляется: для FK настроен RESTRICT.
    blocked = client.delete(f"/v1/users/{user['id']}")
    assert blocked.status_code == 409
    assert client.get(f"/v1/users/{user['id']}").status_code == 200

    assert client.delete(f"/v1/comments/{comment['id']}").status_code == 204
    assert client.delete(f"/v1/users/{user['id']}").status_code == 204
    assert client.get(f"/v1/comments/{comment['id']}").status_code == 404


def test_deleting_assignee_sets_task_assignee_to_null(client):
    user = create_user(client)
    project = create_project(client)
    task = create_task(client, project["id"], assignee_id=user["id"])

    assert client.delete(f"/v1/users/{user['id']}").status_code == 204

    response = client.get(f"/v1/tasks/{task['id']}")
    assert response.status_code == 200
    assert response.json()["assignee_id"] is None


def test_deleting_project_cascades_to_tasks_and_comments(client):
    user = create_user(client)
    project = create_project(client)
    task = create_task(client, project["id"])
    comment_response = client.post(
        "/v1/comments",
        json={"task_id": task["id"], "author_id": user["id"], "body": "Will be cascaded"},
    )
    assert comment_response.status_code == 201
    comment_id = comment_response.json()["id"]

    assert client.delete(f"/v1/projects/{project['id']}").status_code == 204
    assert client.get(f"/v1/tasks/{task['id']}").status_code == 404
    assert client.get(f"/v1/comments/{comment_id}").status_code == 404

    # Комментарий удалён вместе с задачей, поэтому автора уже можно удалить.
    assert client.delete(f"/v1/users/{user['id']}").status_code == 204


def test_invalid_payloads_and_missing_foreign_keys(client):
    invalid_email = client.post(
        "/v1/users",
        json={"email": "not-email", "display_name": "Bad email"},
    )
    assert invalid_email.status_code == 422

    missing_project = client.post("/v1/tasks", json={"title": "No project"})
    assert missing_project.status_code == 422

    invalid_status = client.post(
        "/v1/tasks",
        json={"project_id": 123456789, "title": "Bad status", "status": "closed"},
    )
    assert invalid_status.status_code == 422

    missing_foreign_key = client.post(
        "/v1/tasks",
        json={"project_id": 123456789, "title": "Missing project"},
    )
    assert missing_foreign_key.status_code == 409

    blank_comment = client.post(
        "/v1/comments",
        json={"task_id": 1, "author_id": 1, "body": "   "},
    )
    assert blank_comment.status_code == 422
