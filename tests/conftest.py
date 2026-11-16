"""Fixtures для тестов TaskFlow.

Интеграционные тесты используют отдельную PostgreSQL-БД из
TASKFLOW_TEST_DATABASE_URL. Перед ними к этой БД применяется Alembic migration;
рабочий DATABASE_URL из .env не используется.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db
from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def test_engine():
    database_url = os.getenv("TASKFLOW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Для DB-тестов задайте TASKFLOW_TEST_DATABASE_URL на отдельную "
            "базу PostgreSQL с 'test' в имени, например taskflow_test."
        )

    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        pytest.fail("TASKFLOW_TEST_DATABASE_URL должен указывать на PostgreSQL.")
    if not url.database or "test" not in url.database.lower():
        pytest.fail(
            "Имя базы в TASKFLOW_TEST_DATABASE_URL должно содержать 'test'. "
            "Это защита от случайного запуска тестов на рабочей базе."
        )

    # Запускаем миграции отдельным процессом: Alembic читает DATABASE_URL
    # при импорте настроек, поэтому передаём тестовый URL в окружении subprocess.
    migration_env = os.environ.copy()
    migration_env["DATABASE_URL"] = database_url
    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=migration_env,
        capture_output=True,
        text=True,
        check=False,
    )
    if migration.returncode != 0:
        pytest.fail(
            "Не удалось применить Alembic-миграции к тестовой БД.\n"
            f"STDOUT:\n{migration.stdout}\nSTDERR:\n{migration.stderr}"
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def test_connection(test_engine) -> Generator:
    """Откатывает данные теста, включая записи после db.commit() в API."""
    connection = test_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(test_connection) -> Generator[TestClient, None, None]:
    testing_sessions = sessionmaker(
        bind=test_connection,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_sessions()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
