import psycopg
import pytest
from psycopg import sql

from app.db import connect, run_migrations
from helpers import TEST_DATABASE_URL, make_user


def _project(db, owner_id, max_size=3, accepting=True, skills=(), places=None) -> int:
    pid = db.execute(
        "INSERT INTO projects (owner_id, title, description, category, max_size, accepting) "
        "VALUES (%s, 'P', 'D', 'Course Project', %s, %s) RETURNING id", (owner_id, max_size, accepting)).fetchone()["id"]
    for i, skill in enumerate(skills):
        db.execute("INSERT INTO project_skills (project_id, name, position) VALUES (%s, %s, %s)", (pid, skill, i))
    for i, (name, uid) in enumerate(places if places is not None else [("Lead", owner_id)]):
        db.execute("INSERT INTO project_roles (project_id, name, user_id, position) VALUES (%s, %s, %s, %s)",
                   (pid, name, uid, i))
    return pid


def test_fresh_database_gets_schema_and_default_categories():
    fresh = "teamup_test_fresh"
    admin_url = psycopg.conninfo.make_conninfo(TEST_DATABASE_URL, dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(fresh)))
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(fresh)))
    try:
        with connect(psycopg.conninfo.make_conninfo(TEST_DATABASE_URL, dbname=fresh)) as conn:
            assert run_migrations(conn) == ["001_init.sql"]
            assert [r["name"] for r in conn.execute("SELECT name FROM categories ORDER BY created_at")] == [
                "Course Project", "Competition", "Senior Project", "Startup Idea", "Research"]
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(fresh)))


def test_match_score_rounds_half_up_and_ignores_case(db):
    u = make_user(db, "m@x.test", skills=["react"])
    p8 = _project(db, u, skills=[f"S{i}" for i in range(7)] + ["REACT"])
    assert db.execute("SELECT match_score(%s, %s) AS m", (p8, u)).fetchone()["m"] == 13  # 1/8 = 12.5 -> 13
    assert db.execute("SELECT match_score(%s, %s) AS m", (_project(db, u), u)).fetchone()["m"] == 0


def test_project_summary_status(db):
    o = make_user(db, "o@x.test")
    m = make_user(db, "m2@x.test")
    full = _project(db, o, max_size=2, places=(("Lead", o), ("Dev", m)))
    closed = _project(db, o, accepting=False, places=(("Lead", o), ("Dev", None)))
    rec = _project(db, o, places=(("Lead", o), ("Dev", None)))
    got = {r["project_id"]: (r["status"], r["member_count"], r["place_count"])
           for r in db.execute("SELECT * FROM project_summary")}
    assert got[full] == ("full", 2, 2) and got[closed] == ("closed", 1, 2) and got[rec] == ("recruiting", 1, 2)


def test_one_place_per_member_and_one_pending_per_person(db):
    o = make_user(db, "o3@x.test")
    p = _project(db, o, places=(("Lead", o), ("Dev", None)))
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute("UPDATE project_roles SET user_id = %s WHERE project_id = %s AND user_id IS NULL", (o, p))
    s = make_user(db, "s@x.test")
    db.execute("INSERT INTO requests (project_id, user_id, kind, role) VALUES (%s, %s, 'request', 'Dev')", (p, s))
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute("INSERT INTO requests (project_id, user_id, kind, role) VALUES (%s, %s, 'invitation', 'Dev')", (p, s))


def test_emails_must_be_lowercase(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO users (email) VALUES ('Upper@X.test')")
