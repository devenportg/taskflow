# TaskFlow API

Практическое задание: REST API для управления задачами команды.
**Автор:** Моисеев Роман, группа П-311.

**Стек:** Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy 2, Alembic, Docker Compose.

Схема базы создаётся **только миграциями Alembic** — `Base.metadata.create_all()` в проекте не используется.

---

## Структура проекта

```text
.
├── app/
│   ├── main.py              # создание FastAPI, GET /health, подключение роутеров
│   ├── config.py            # настройки из окружения (DATABASE_URL)
│   ├── database.py          # Engine, SessionLocal, Base, зависимость get_db
│   ├── models.py            # пять ORM-моделей: users, projects, labels, tasks, comments
│   ├── schemas.py           # Pydantic-схемы Create / Update / Read
│   ├── crud.py              # общие операции: get_or_404, commit_or_409, apply_updates
│   └── routers/             # по файлу на ресурс: users, projects, labels, tasks, comments
├── alembic/
│   ├── env.py               # DATABASE_URL из окружения, target_metadata = Base.metadata
│   ├── script.py.mako       # шаблон для новых ревизий
│   └── versions/
│       └── 0001_create_initial_schema.py
├── scripts/smoke_test.py    # проверка API по сценарию из задания (49 проверок)
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
└── requirements.txt
```

---

## Быстрый старт (Docker Compose)

Требуется установленный Docker Desktop (Windows/macOS) или Docker Engine + Compose (Linux).

```bash
cp .env.example .env          # Windows: copy .env.example .env
docker compose up --build
```

Что произойдёт:

1. поднимется PostgreSQL 16 с volume `pgdata`;
2. Compose дождётся состояния `healthy` (healthcheck `pg_isready`);
3. в контейнере API выполнится `alembic upgrade head`;
4. запустится Uvicorn на `0.0.0.0:8000`.

Проверка:

```bash
curl http://localhost:8000/health
# {"status":"ok","database":"up"}
```

Откройте в браузере:

* **Swagger UI** — <http://localhost:8000/docs>;
* OpenAPI JSON — <http://localhost:8000/openapi.json>.

Остановка: `docker compose down` (данные сохраняются в volume).

> `docker compose down -v` удаляет и контейнеры, и volume с данными — используйте только для намеренного сброса.

---

## Примеры запросов

Создать пользователя:

```bash
curl -X POST http://localhost:8000/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email": "ivan@example.com", "display_name": "Иван Петров", "role": "admin"}'
```

```json
{"id": 1, "email": "ivan@example.com", "display_name": "Иван Петров", "role": "admin",
 "created_at": "2026-05-05T10:00:00.123456Z"}
```

Создать проект и метку:

```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "TaskFlow", "description": "Учебный проект"}'

curl -X POST http://localhost:8000/v1/labels \
  -H "Content-Type: application/json" \
  -d '{"name": "backend", "color": "#22c55e"}'
```

Создать задачу со ссылками на них (`201 Created`):

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "assignee_id": 1, "label_id": 1,
       "title": "Спроектировать схему БД", "priority": "high"}'
```

Добавить комментарий:

```bash
curl -X POST http://localhost:8000/v1/comments \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1, "author_id": 1, "body": "Схема готова"}'
```

Получить задачу и списки с фильтрами:

```bash
curl http://localhost:8000/v1/tasks/1
curl "http://localhost:8000/v1/tasks?project_id=1&status=open"
curl "http://localhost:8000/v1/comments?task_id=1"
```

Изменить статус задачи (`PATCH` меняет только переданные поля):

```bash
curl -X PATCH http://localhost:8000/v1/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

Удалить проект — вместе с ним удалятся задачи и их комментарии (`204 No Content`):

```bash
curl -X DELETE http://localhost:8000/v1/projects/1 -i
```

---

## Сценарий проверки из задания

Через `/docs` (или команды выше) по порядку:

1. создайте пользователя, проект и метку;
2. создайте задачу со ссылками на них;
3. добавьте к задаче комментарий;
4. получите задачу и списки с фильтрами `?project_id=1&status=open` и `?task_id=1`;
5. измените статус задачи на `done`;
6. удалите проект и убедитесь, что задачи и комментарии удалены;
7. перезапустите Compose (`docker compose down` → `docker compose up -d`) и убедитесь, что остальные данные сохранились.

---

## Локальный запуск без Docker

1. Поднимите PostgreSQL и создайте базу:

```sql
CREATE USER taskflow WITH PASSWORD 'taskflow';
CREATE DATABASE taskflow OWNER taskflow;
```

Альтернатива — взять базу из Compose, не поднимая API: `docker compose up -d db`.
Пользователь, пароль и база создаются автоматически из `POSTGRES_*`. Чтобы подключаться к ней с хоста
(Alembic, `psql`, смоук-тест), раскомментируйте `ports` в сервисе `db`; если порт 5432 занят локальным
PostgreSQL, укажите другой, например `"5433:5432"`, и поправьте `DATABASE_URL` в `.env`.

2. Виртуальное окружение и зависимости:

```bash
python -m venv .venv                     # Windows, если 3.12 не основная версия: py -3.12 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Файл `.env` в корне проекта (в Git он не попадает):

```dotenv
DATABASE_URL=postgresql+psycopg2://taskflow:change-me@localhost:5432/taskflow
```

4. Миграции и запуск:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Запуск из PyCharm

Интерпретатор — `.venv` из корня проекта. Рабочая директория может быть любой: `.env` ищется
по пути от `app/config.py`, а не от текущего каталога, поэтому настройки подхватываются всегда.
Смоук-тест запускается как обычный файл: `scripts/smoke_test.py` → Run.

### Если `pip install` падает с `ValueError: check_hostname requires server_hostname`

Это сетевая ошибка pip, а не проблема проекта: pip пытается скачать пакеты **через прокси**, у которого
некорректно задан адрес (прокси-клиент VPN, корпоративный прокси, `pip.ini`). В трейсбеке это видно по
строкам `_prepare_proxy` и `_connect_tls_proxy`.

Проверить, кто задаёт прокси:

```cmd
set | findstr /i proxy
pip config list
```

Лечение (вариант «прокси не нужен» — очистить переменные в текущем окне cmd):

```cmd
set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=
set NO_PROXY=
pip install -r requirements.txt
```

Если прокси нужен (VPN/прокси-клиент), адрес должен быть полным, со схемой `http://` и портом —
именно `http://`, а не `https://` для локального прокси-клиента:

```cmd
set HTTP_PROXY=http://127.0.0.1:10809
set HTTPS_PROXY=http://127.0.0.1:10809
pip install -r requirements.txt
```

Чтобы убрать насовсем: `Win+R` → `sysdm.cpl` → «Дополнительно» → «Переменные среды» — удалить
`HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY`; в VPN-клиенте снять галочку «системный прокси».

### Если падает с `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc2 in position 67`

Это ошибка не приложения, а связки «psycopg2 + PostgreSQL с русской локалью»: сервер отдаёт текст
ошибки в cp1251, psycopg2 не может его декодировать и настоящая причина (неверный пароль,
недоступная база) остаётся невидимой. Проще всего перевести сообщения сервера на английский —
в `psql` под суперпользователем:

```sql
ALTER SYSTEM SET lc_messages = 'C';
SELECT pg_reload_conf();
```

После этого вместо `UnicodeDecodeError` будет нормальный текст, например
`password authentication failed for user "taskflow"` — и причину видно сразу. Перезапуск сервера не нужен,
настройка действует для новых подключений.

### Если `pip install` пишет `Could not find a version that satisfies the requirement fastapi==0.143.0`

Значит виртуальное окружение создано **на старом Python**. Список версий, который печатает pip, — это не
весь PyPI, а только версии, совместимые с текущим интерпретатором. Если в списке самая новая `fastapi`
— `0.128.8`, то venv точно на Python 3.9: у `fastapi 0.129.0+` требование `Requires-Python >= 3.10`.

Минимальные требования зависимостей проекта:

| Пакет | Пин | Требует Python |
| --- | --- | --- |
| `fastapi` | 0.143.0 | ≥ 3.10 |
| `uvicorn[standard]` | 0.54.0 | ≥ 3.10 |
| `SQLAlchemy` | 2.1.4 | ≥ 3.11 |
| `alembic` | 1.20.0 | ≥ 3.10 |
| `psycopg2-binary` | 2.9.13 | ≥ 3.10 |
| `pydantic-settings` | 2.15.0 | ≥ 3.10 |

Лечение — пересоздать окружение на Python 3.12 (та же версия, что в `Dockerfile` и в задании):

```cmd
rmdir /s /q venv
py -3.12 -m venv venv
venv\Scripts\activate
python -V                       :: должно быть 3.12.x
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Если `py -3.12` не найден («Python 3.12 not found!»), значит 3.12 не установлена — `py -0p` покажет,
что есть на самом деле. Установка:

```cmd
winget install -e --id Python.Python.3.12      :: проще всего
```

Если `winget` недоступен — скачать установщик вручную. Важно: у ветки 3.12 больше не выходят сборки
с установщиком (она на этапе «только исправления безопасности»), поэтому **последний установщик — 3.12.10**:
<https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe> (≈26 МБ, страница релиза —
<https://www.python.org/downloads/release/python-31210/>). В установщике включить галочку
**«Add python.exe to PATH»**.

Подойдёт и любая версия 3.11 и выше (3.13, 3.14) — код проверялся на 3.13; 3.12 указана в задании,
поэтому по умолчанию ставим её. После установки **закрыть и открыть окно терминала заново** и проверить:

```cmd
py -0p                                        :: в списке должна появиться -3.12-64
```

---

## Миграции

```bash
alembic current          # текущая ревизия базы
alembic history          # история ревизий
alembic upgrade head     # применить все миграции
alembic downgrade base   # откатить всё
alembic downgrade -1     # откатить одну ревизию
```

Строка подключения берётся из `DATABASE_URL` (см. `alembic/env.py`), поэтому пароль не хранится в `alembic.ini`.

Проверка цикла миграций:

```bash
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

---

## Автоматическая проверка API

Скрипт проходит весь сценарий задания и печатает отчёт. Нужны база, доступная с хоста (`localhost:5432`),
и применённые миграции: `alembic upgrade head` → `python scripts/smoke_test.py`.
Работает через `TestClient` из FastAPI, поэтому требует пакет `httpx2` — он уже есть в `requirements.txt`.

```bash
# Linux / macOS
DATABASE_URL=postgresql+psycopg2://taskflow:change-me@localhost:5432/taskflow \
  python scripts/smoke_test.py

# Windows PowerShell
$env:DATABASE_URL = "postgresql+psycopg2://taskflow:change-me@localhost:5432/taskflow"
python scripts/smoke_test.py
```

Проверяются коды `200`, `201`, `204`, `404`, `409`, `422`, фильтры, частичное обновление и правила удаления (`CASCADE`, `SET NULL`, `RESTRICT`).

---

## Переменные окружения

| Переменная | Назначение | Пример |
|---|---|---|
| `POSTGRES_USER` | пользователь БД (сервис `db`) | `taskflow` |
| `POSTGRES_PASSWORD` | пароль БД | `change-me` |
| `POSTGRES_DB` | имя базы | `taskflow` |
| `DATABASE_URL` | строка подключения для запусков с хоста (Alembic, Uvicorn, смоук-тест) | `postgresql+psycopg2://taskflow:change-me@localhost:5432/taskflow` |

Внутри Compose `DATABASE_URL` собирается из `POSTGRES_*` с хостом `db`, поэтому менять её для контейнеров не нужно.

В репозиторий попадает только `.env.example`. Настоящий `.env` указан в `.gitignore` и в `.dockerignore`.

---

## Реализованные правила

| Требование | Где реализовано |
|---|---|
| Пять таблиц, типы и `NOT NULL` | `app/models.py`, миграция `0001` |
| Уникальность `users.email`, `labels.name` | `uq_users_email`, `uq_labels_name` |
| Допустимые значения `role`, `status`, `priority`, цвет `#RRGGBB` | `CHECK`-ограничения + `Literal` в схемах |
| `tasks.project_id` → `ON DELETE CASCADE` | `fk_tasks_project_id` |
| `tasks.assignee_id`, `tasks.label_id` → `ON DELETE SET NULL` | `fk_tasks_assignee_id`, `fk_tasks_label_id` |
| `comments.task_id` → `ON DELETE CASCADE` | `fk_comments_task_id` |
| `comments.author_id` → `ON DELETE RESTRICT` | `fk_comments_author_id` |
| `created_at` заполняет БД | `server_default=func.now()` |
| `updated_at` обновляется при изменении | `onupdate=func.now()` |
| Коды `201/204/200/404/409/422` | `app/routers/*.py`, `app/crud.py` |
| Ошибки БД не дают `500` | `commit_or_409()`: `IntegrityError` → `rollback()` → `409` с понятным текстом |
| Фильтры задач и комментариев | `GET /v1/tasks`, `GET /v1/comments` |
| Проверка БД в `/health` | `SELECT 1`, при недоступной БД — `503` |
