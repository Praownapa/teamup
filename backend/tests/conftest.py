"""Test setup: a fresh `teamup_test` database per run, the app in dev-auth mode, and per-test cleanup."""
import os
import tempfile

import psycopg
import pytest
from psycopg import sql

from helpers import TEST_DATABASE_URL, Api

UPLOAD_TMP = tempfile.mkdtemp(prefix="teamup-test-uploads-")
os.environ.update({
    "DATABASE_URL": TEST_DATABASE_URL,
    "AUTH_MODE": "dev",
    "UPLOAD_MODE": "local",
    "UPLOAD_DIR": UPLOAD_TMP,
    "SEED_DEMO_DATA": "false",
})


def _recreate_test_database() -> None:
    name = psycopg.conninfo.conninfo_to_dict(TEST_DATABASE_URL)["dbname"]
    admin_url = psycopg.conninfo.make_conninfo(TEST_DATABASE_URL, dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


_recreate_test_database()

from fastapi.testclient import TestClient  # noqa: E402  (env vars must be set before importing the app)

from app.config import get_settings  # noqa: E402
from app.db import connect  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()

DEFAULT_CATEGORIES = ["Course Project", "Competition", "Senior Project", "Startup Idea", "Research"]


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # runs the app lifespan: opens the pool and applies migrations
        yield c


@pytest.fixture(autouse=True)
def db(client):
    """Empty every table before each test and hand the test its own connection."""
    conn = connect(TEST_DATABASE_URL)
    tables = [r["tablename"] for r in conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'schema_migrations'")]
    if tables:
        conn.execute(sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(sql.SQL(", ").join(map(sql.Identifier, tables))))
    if "categories" in tables:
        for i, name in enumerate(DEFAULT_CATEGORIES):
            conn.execute("INSERT INTO categories (name, created_at) VALUES (%s, now() - make_interval(mins => %s))",
                         (name, len(DEFAULT_CATEGORIES) - i))
    yield conn
    conn.close()


@pytest.fixture
def api(client):
    return lambda email: Api(client, email)
