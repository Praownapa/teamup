from app.db import seed_demo
from helpers import new_project

JOHN = "john.carter@student.uni.ac.th"


def _count(db, table):
    return db.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


def test_seed_demo_once_and_force(db):
    assert seed_demo(db) is True
    assert seed_demo(db) is False
    assert (_count(db, "users"), _count(db, "projects"), _count(db, "requests"), _count(db, "reports")) == (18, 8, 6, 5)
    john = db.execute("SELECT * FROM users WHERE email = %s", (JOHN,)).fetchone()
    assert (john["id"], john["role"], john["student_id"]) == (1, "admin", "6600123456")
    assert db.execute("SELECT status FROM users WHERE id = 18").fetchone()["status"] == "suspended"
    assert seed_demo(db, force=True) is True and _count(db, "users") == 18


def test_seeded_ids_continue(db, api):
    seed_demo(db)
    assert new_project(api(JOHN))["id"] == 9


def test_seeded_project_one_matches_the_mock(db, api):
    seed_demo(db)
    john = api(JOHN)
    p = john.get("/projects/1").json()
    assert p["title"] == "Campus Food Waste Tracker" and p["my_role"] == "owner"
    assert [m["name"] for m in p["members"]] == ["John Carter", "Emma Wilson", "Lucas Brown", "Daniel Ortiz"]
    assert p["open_roles"] == ["Frontend Developer"] and (p["pending_requests"], p["pending_invitations"]) == (2, 1)
    assert p["match"] == 25  # John has React, the only one of React/FastAPI/PostgreSQL/AWS
    assert john.get("/users/me/counts").json() == {"pending_requests": 3, "unread_notifications": 3}
    sophia = api("sophia.martinez@student.uni.ac.th").get("/notifications").json()
    assert sophia[0]["text"] == "John Carter invited you to join Campus Food Waste Tracker as Frontend Developer."
