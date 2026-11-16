# Тесты TaskFlow API

Набор разделён на три уровня:

- `tests/unit/` — проверяет схемы Pydantic и вспомогательные CRUD-функции без запуска PostgreSQL;
- `tests/integration/` — проверяет эндпоинты FastAPI вместе с настоящей PostgreSQL;
- `tests/e2e/` — проходит полный сценарий по настоящему HTTP через отдельно запущенный Uvicorn: пользователь, проект, метка, задача, комментарий, фильтрация, обновление и удаление.

Integration-тесты используют `TestClient` и PostgreSQL. E2E-тест обращается к локальному Uvicorn по HTTP, который должен быть запущен отдельно и подключён к тестовой базе.

## Установка зависимостей

Из корня проекта:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Unit-тесты

База данных не нужна:

```powershell
.\.venv\Scripts\python.exe -m pytest -m unit -v
```

## PostgreSQL для integration и e2e

Тесты намеренно не используют `DATABASE_URL` из `.env`. Для них нужна отдельная база PostgreSQL с именем, содержащим `test`, например `taskflow_test`.

Создать базу можно от имени администратора PostgreSQL:

```sql
CREATE DATABASE taskflow_test OWNER taskflow;
```

Убедитесь, что в `.env` у роли `taskflow` установлен пароль, и подключайтесь к **отдельной** тестовой базе:

```powershell
$env:TASKFLOW_TEST_DATABASE_URL = "postgresql+psycopg2://taskflow:change-me@localhost:5432/taskflow_test"
```

Если пароль отличается, замените `change-me` на свой. Не публикуйте пароль в отчёте или скриншотах.

Перед integration-тестами фикстура применяет Alembic-миграции к указанной тестовой БД. Она не удаляет таблицы. Каждая проверка работает внутри транзакции, которая откатывается после теста. Используйте только отдельную тестовую базу, например `taskflow_test`, **не рабочую базу `taskflow`**. E2E-сервер и integration-тесты могут использовать эту же БД: схема создаётся миграциями, а не `create_all`.

Запуск интеграционных тестов:

```powershell
.\.venv\Scripts\python.exe -m pytest -m integration -v
```

### E2E: запуск через настоящий HTTP-сервер

Откройте **первое** окно PowerShell в корне проекта и укажите тестовую БД, затем примените миграции и запустите API:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://taskflow:change-me@localhost:5432/taskflow_test"
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Оставьте сервер запущенным. Откройте **второе** окно PowerShell в корне проекта, задайте URL тестовой БД и локального API и выполните E2E-тест:

```powershell
$env:TASKFLOW_TEST_DATABASE_URL = "postgresql+psycopg2://taskflow:change-me@localhost:5432/taskflow_test"
$env:TASKFLOW_E2E_BASE_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m pytest -m e2e -v
```

После проверки остановите Uvicorn сочетанием **Ctrl+C**. Убедитесь, что в обоих окнах указана именно тестовая БД `taskflow_test`, а не рабочая `taskflow`.

Запуск всего набора:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Если `TASKFLOW_TEST_DATABASE_URL` не задан, unit-тесты выполнятся, а DB-тесты будут пропущены с пояснением.

## Полезные команды

```powershell
# Запустить конкретный файл
.\.venv\Scripts\python.exe -m pytest tests\unit\test_schemas.py -v

# Запустить конкретный тест
.\.venv\Scripts\python.exe -m pytest tests\integration\test_api_resources.py::test_task_crud_filter_partial_update_and_not_found -v

# Остановиться после первой ошибки
.\.venv\Scripts\python.exe -m pytest -x -v

# Отчёт о покрытии (если установлен pytest-cov)
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```
