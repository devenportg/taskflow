"""Проверка API по сценарию из задания.

Запуск (нужны PostgreSQL и применённые миграции):

    python scripts/smoke_test.py
"""

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

client = TestClient(app)

RUN = uuid4().hex[:8]

checks = 0
failures: list[str] = []


def check(condition: bool, title: str) -> None:
    global checks
    checks += 1
    if condition:
        print(f"  [OK]   {title}")
    else:
        print(f"  [FAIL] {title}")
        failures.append(title)


def section(title: str) -> None:
    print(f"\n{title}")


def main() -> int:
    section("1. Служебный эндпоинт")
    response = client.get("/health")
    check(response.status_code == 200, f"GET /health -> {response.status_code}")
    check(response.json().get("database") == "up", "в /health видно, что БД доступна")

    section("2. POST возвращает 201 и созданную запись")
    response = client.post(
        "/v1/users",
        json={"email": f"ivan.{RUN}@example.com", "display_name": "Иван Петров", "role": "admin"},
    )
    check(response.status_code == 201, f"POST /v1/users -> {response.status_code}")
    user = response.json()
    check(user.get("id") is not None and user.get("created_at") is not None, "в ответе есть id и created_at")
    check(user.get("role") == "admin", "роль сохранена")

    response = client.post("/v1/projects", json={"name": f"TaskFlow {RUN}", "description": "Учебный проект"})
    check(response.status_code == 201, f"POST /v1/projects -> {response.status_code}")
    project = response.json()

    response = client.post("/v1/labels", json={"name": f"backend-{RUN}", "color": "#22c55e"})
    check(response.status_code == 201, f"POST /v1/labels -> {response.status_code}")
    label = response.json()

    response = client.post("/v1/labels", json={"name": f"default-color-{RUN}"})
    check(response.json().get("color") == "#6b7280", "цвет метки по умолчанию #6b7280")

    section("3. Задача со ссылками на созданные записи")
    response = client.post(
        "/v1/tasks",
        json={
            "project_id": project["id"],
            "assignee_id": user["id"],
            "label_id": label["id"],
            "title": "Спроектировать схему БД",
            "description": "Пять таблиц и миграция",
            "priority": "high",
        },
    )
    check(response.status_code == 201, f"POST /v1/tasks -> {response.status_code}")
    task = response.json()
    check(task.get("status") == "open", "статус по умолчанию open")
    check(task.get("priority") == "high", "приоритет сохранён")
    check(task.get("updated_at") is not None, "updated_at заполнен")

    section("4. Комментарий к задаче")
    response = client.post(
        "/v1/comments",
        json={"task_id": task["id"], "author_id": user["id"], "body": "Схема готова"},
    )
    check(response.status_code == 201, f"POST /v1/comments -> {response.status_code}")

    section("5. GET, фильтры и документация")
    response = client.get(f"/v1/tasks/{task['id']}")
    check(response.status_code == 200, f"GET /v1/tasks/{task['id']} -> {response.status_code}")

    response = client.get(f"/v1/tasks?project_id={project['id']}&status=open")
    check(response.status_code == 200 and len(response.json()) == 1, "фильтр project_id + status отдал задачу")

    response = client.get("/v1/tasks?project_id=999")
    check(response.json() == [], "фильтр по несуществующему проекту вернул пустой список")

    response = client.get(f"/v1/comments?task_id={task['id']}")
    check(response.status_code == 200 and len(response.json()) == 1, "фильтр комментариев по task_id")

    response = client.get("/docs")
    check(response.status_code == 200, f"GET /docs -> {response.status_code}")
    response = client.get("/openapi.json")
    check(response.status_code == 200 and len(response.json()["paths"]) == 11, "OpenAPI описал все ресурсы")

    section("6. PATCH меняет только переданные поля")
    response = client.patch(f"/v1/tasks/{task['id']}", json={"status": "done"})
    check(response.status_code == 200, f"PATCH /v1/tasks/{task['id']} -> {response.status_code}")
    updated = response.json()
    check(updated["status"] == "done", "статус изменён на done")
    check(updated["title"] == task["title"], "название не затёрто")
    check(updated["assignee_id"] == user["id"], "исполнитель не затёрт")
    check(updated["updated_at"] >= task["updated_at"], "updated_at обновился")

    response = client.patch(f"/v1/tasks/{task['id']}", json={"assignee_id": None})
    check(response.json()["assignee_id"] is None, "PATCH с null очищает исполнителя")

    section("7. Ошибки: 404, 422, 409")
    check(client.get("/v1/tasks/9999").status_code == 404, "несуществующая задача -> 404")
    check(client.get("/v1/users/9999").status_code == 404, "несуществующий пользователь -> 404")
    check(
        client.post("/v1/tasks", json={"title": "Без проекта"}).status_code == 422,
        "отсутствует обязательное поле -> 422",
    )
    check(
        client.post("/v1/tasks", json={"project_id": 0, "title": "Плохой id"}).status_code == 422,
        "project_id = 0 -> 422",
    )
    check(
        client.post("/v1/tasks", json={"project_id": project["id"], "title": "x", "status": "closed"}).status_code
        == 422,
        "недопустимый статус -> 422",
    )
    check(
        client.post("/v1/users", json={"email": "не-почта", "display_name": "Тест"}).status_code == 422,
        "некорректный email -> 422",
    )
    check(
        client.post("/v1/users", json={"email": f"ivan.{RUN}@example.com", "display_name": "Дубль"}).status_code == 409,
        "повторный email -> 409 (а не 500)",
    )
    check(
        client.post("/v1/labels", json={"name": f"backend-{RUN}", "color": "#000000"}).status_code == 409,
        "повторное имя метки -> 409",
    )
    check(
        client.post("/v1/tasks", json={"project_id": 4242, "title": "Проекта нет"}).status_code == 409,
        "несуществующий внешний ключ -> 409",
    )
    check(
        client.post("/v1/comments", json={"task_id": task["id"], "author_id": user["id"], "body": "   "}).status_code
        == 422,
        "пустой комментарий -> 422",
    )
    check(
        client.post("/v1/users", json={"email": f"x.{RUN}@example.com", "display_name": "X", "id": 10}).status_code == 422,
        "служебное поле id в теле -> 422",
    )
    check(
        client.post("/v1/tasks", json={"project_id": project["id"], "title": "t", "created_at": "2020-01-01"}).status_code
        == 422,
        "служебное поле created_at в теле -> 422",
    )

    section("8. Правила удаления (SET NULL и RESTRICT)")
    response = client.delete(f"/v1/labels/{label['id']}")
    check(response.status_code == 204, f"DELETE /v1/labels -> {response.status_code}, тела нет")
    check(response.content == b"", "204 без тела")
    task_after_label_delete = client.get(f"/v1/tasks/{task['id']}").json()
    check(task_after_label_delete["label_id"] is None, "удаление метки обнулило label_id (SET NULL)")
    check(task_after_label_delete["title"] == task["title"], "сама задача осталась")

    check(
        client.delete(f"/v1/users/{user['id']}").status_code == 409,
        "пользователя с комментариями удалить нельзя -> 409 (RESTRICT)",
    )
    check(client.get(f"/v1/users/{user['id']}").status_code == 200, "пользователь остался в базе")

    section("9. CASCADE: удаление проекта уносит задачи и комментарии")
    response = client.delete(f"/v1/projects/{project['id']}")
    check(response.status_code == 204, f"DELETE /v1/projects -> {response.status_code}")
    check(client.get(f"/v1/tasks/{task['id']}").status_code == 404, "задача удалена вместе с проектом")
    check(client.get(f"/v1/comments?task_id={task['id']}").json() == [], "комментарии удалены вместе с задачей")

    section("10. Уборка тестовых данных")
    comment_left = client.get(f"/v1/comments?author_id={user['id']}").json()
    if comment_left:
        client.delete(f"/v1/comments/{comment_left[0]['id']}")
    check(client.delete(f"/v1/users/{user['id']}").status_code == 204, "пользователь без комментариев удалён")
    check(client.delete(f"/v1/users/{user['id']}").status_code == 404, "повторное удаление -> 404")

    for label_item in client.get("/v1/labels").json():
        if label_item["name"].endswith(RUN):
            client.delete(f"/v1/labels/{label_item['id']}")
    for project_item in client.get("/v1/projects").json():
        if project_item["name"].endswith(RUN):
            client.delete(f"/v1/projects/{project_item['id']}")
    leftover = [item for item in client.get("/v1/users").json() if item["email"].endswith(RUN + "@example.com")]
    for user_item in leftover:
        client.delete(f"/v1/users/{user_item['id']}")
    check(
        all(f".{RUN}@" not in item["email"] for item in client.get("/v1/users").json()),
        "тестовые данные убраны, база осталась чистой",
    )

    print(f"\nИтого проверок: {checks}, провалов: {len(failures)}")
    if failures:
        print("Провалены:")
        for title in failures:
            print(f"  - {title}")
        return 1
    print("Все проверки пройдены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
