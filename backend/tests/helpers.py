"""Helpers shared by the test modules (conftest imports TEST_DATABASE_URL from here)."""
import os

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://teamup:teamup@localhost:5434/teamup_test")


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class Api:
    """Calls the API as one user, with a dev token (the tests run with AUTH_MODE=dev)."""

    def __init__(self, client, email: str):
        self.client = client
        self.headers = bearer(f"dev:{email}")

    def _call(self, method: str, path: str, **kw):
        headers = {**self.headers, **kw.pop("headers", {})}
        return self.client.request(method, "/api" + path, headers=headers, **kw)

    def get(self, path, **kw):
        return self._call("GET", path, **kw)

    def post(self, path, **kw):
        return self._call("POST", path, **kw)

    def put(self, path, **kw):
        return self._call("PUT", path, **kw)

    def patch(self, path, **kw):
        return self._call("PATCH", path, **kw)

    def delete(self, path, **kw):
        return self._call("DELETE", path, **kw)


def make_user(db, email, *, name=None, major="", year=1, skills=(), role="student", status="active",
              open_to_projects=True) -> int:
    """Insert a user directly with SQL (skills at level Intermediate) and return the id."""
    row = db.execute(
        "INSERT INTO users (email, name, major, year, role, status, open_to_projects) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (email.lower(), email.split("@")[0] if name is None else name, major, year, role, status, open_to_projects),
    ).fetchone()
    for i, skill in enumerate(skills):
        db.execute("INSERT INTO user_skills (user_id, name, level, position) VALUES (%s, %s, 'Intermediate', %s)",
                   (row["id"], skill, i))
    return row["id"]
