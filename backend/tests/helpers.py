"""Helpers shared by the test modules (conftest imports TEST_DATABASE_URL from here)."""
import os
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://teamup:teamup@localhost:5434/teamup_test")

# A fake Cognito user pool for the cognito-mode tests: tokens are signed with this throwaway key pair.
TEST_REGION = "ap-southeast-1"
TEST_POOL_ID = "ap-southeast-1_TEST"
TEST_ISSUER = f"https://cognito-idp.{TEST_REGION}.amazonaws.com/{TEST_POOL_ID}"
TEST_CLIENT_ID = "client123"
TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TEST_PUBLIC_KEY = TEST_PRIVATE_KEY.public_key()


def make_access_token(sub: str, groups=(), **overrides) -> str:
    """A Cognito-style access token; override any claim (client_id, token_use, exp, iss...)."""
    now = int(time.time())
    claims = {"sub": sub, "iss": TEST_ISSUER, "client_id": TEST_CLIENT_ID, "token_use": "access",
              "scope": "aws.cognito.signin.user.admin", "username": sub, "iat": now, "exp": now + 3600}
    if groups:
        claims["cognito:groups"] = list(groups)
    claims.update(overrides)
    return jwt.encode(claims, TEST_PRIVATE_KEY, algorithm="RS256", headers={"kid": "test-key"})


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


VALID_PROJECT = {
    "title": "Test Project", "description": "A test project.", "category": "Course Project", "course": "",
    "cover_url": "", "skills": ["React", "Python"], "owner_role": "Lead",
    "roles": [{"name": "Frontend Developer", "spots": 1}, {"name": "Backend Developer", "spots": 1}],
    "max_size": 4, "deadline": "", "duration": "", "meeting": "", "accepting": True,
}


def new_project(owner: Api, **overrides) -> dict:
    """Create a project through the API as `owner` and return its view."""
    r = owner.post("/projects", json={**VALID_PROJECT, **overrides})
    assert r.status_code == 201, r.text
    return r.json()
