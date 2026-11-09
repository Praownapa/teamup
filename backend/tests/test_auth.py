import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.auth as auth
from app.auth import admin_user, current_user, fetch_cognito_attributes, parse_dev_token, user_for_dev
from app.config import Settings
from app.db import connect
from helpers import (TEST_CLIENT_ID, TEST_DATABASE_URL, TEST_ISSUER, TEST_POOL_ID, TEST_PUBLIC_KEY, TEST_REGION,
                     bearer, make_access_token, make_user)


@pytest.fixture
def whoami(client):
    """A tiny app with two routes guarded by the real dependencies (the main pool is open via `client`)."""
    mini = FastAPI()

    @mini.get("/whoami")
    def who(user: dict = Depends(current_user)):
        return {"id": user["id"], "role": user["role"]}

    @mini.get("/admin-only")
    def admin_only(user: dict = Depends(admin_user)):
        return {"id": user["id"], "role": user["role"]}

    return TestClient(mini)


@pytest.fixture
def cognito_env(monkeypatch):
    """Cognito mode against a fake pool: real RS256 checks with the test key; GetUser returns env.attrs."""
    env = SimpleNamespace(attrs={}, getuser_calls=0, jwks_urls=[])

    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=TEST_PUBLIC_KEY)

    def fake_jwk_client(url):
        env.jwks_urls.append(url)
        return FakeJWKClient()

    def fake_fetch(access_token, region):
        env.getuser_calls += 1
        return dict(env.attrs)

    settings = Settings(database_url=TEST_DATABASE_URL, auth_mode="cognito", cognito_region=TEST_REGION,
                        cognito_user_pool_id=TEST_POOL_ID, cognito_client_id=TEST_CLIENT_ID)
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(auth, "get_jwk_client", fake_jwk_client)
    monkeypatch.setattr(auth, "fetch_cognito_attributes", fake_fetch)
    return env


def test_parse_dev_token_forms():
    assert parse_dev_token("dev:Emma@X.test") == {"email": "emma@x.test", "name": "", "student_id": "", "major": ""}
    assert parse_dev_token("dev:email=a%40x.test&name=A+B&student_id=0012345678&major=Data+Science") == {
        "email": "a@x.test", "name": "A B", "student_id": "0012345678", "major": "Data Science"}
    for bad in ["", "abc", "dev:", "dev:not-an-email"]:
        with pytest.raises(HTTPException) as e:
            parse_dev_token(bad)
        assert e.value.status_code == 401


def test_user_for_dev_creates_then_reuses(db):
    u1 = user_for_dev(db, parse_dev_token("dev:new@x.test"))
    assert (u1["name"], u1["year"], u1["role"], u1["student_id"]) == ("new", 1, "student", "")
    assert user_for_dev(db, parse_dev_token("dev:email=new%40x.test&name=Other"))["id"] == u1["id"]


def test_parallel_first_requests_create_one_user(db):
    ids, barrier = [], threading.Barrier(2)

    def go():
        with connect(TEST_DATABASE_URL) as c:
            barrier.wait()
            ids.append(user_for_dev(c, parse_dev_token("dev:race@x.test"))["id"])

    threads = [threading.Thread(target=go) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ids) == 2 and len(set(ids)) == 1
    assert db.execute("SELECT count(*) AS n FROM users WHERE email = 'race@x.test'").fetchone()["n"] == 1


def test_missing_token_suspended_and_admin(db, whoami):
    assert whoami.get("/whoami").json() == {"detail": "Not authenticated."}
    make_user(db, "s@x.test", status="suspended")
    r = whoami.get("/whoami", headers=bearer("dev:s@x.test"))
    assert r.status_code == 403 and r.json()["detail"] == "Your account has been suspended."
    make_user(db, "boss@x.test", role="admin")
    assert whoami.get("/admin-only", headers=bearer("dev:boss@x.test")).status_code == 200
    assert whoami.get("/admin-only", headers=bearer("dev:pleb@x.test")).json()["detail"] == "Admin access required."


def test_cognito_bootstrap_and_group_sync(db, whoami, cognito_env):
    cognito_env.attrs = {"email": "C@X.test", "name": "Cee Gee", "custom:student_id": "0099887766",
                         "custom:major": "Data Science", "email_verified": "true"}
    assert whoami.get("/whoami", headers=bearer(make_access_token("sub-1", ["admin"]))).json()["role"] == "admin"
    row = db.execute("SELECT * FROM users WHERE cognito_sub = 'sub-1'").fetchone()
    assert (row["email"], row["name"], row["student_id"], row["major"]) == ("c@x.test", "Cee Gee", "0099887766", "Data Science")
    assert whoami.get("/whoami", headers=bearer(make_access_token("sub-1", []))).json()["role"] == "student"
    assert cognito_env.getuser_calls == 1  # Cognito is asked only when the profile is first created
    assert set(cognito_env.jwks_urls) == {f"{TEST_ISSUER}/.well-known/jwks.json"}


def test_cognito_links_existing_profile_by_verified_email(db, whoami, cognito_env):
    uid = make_user(db, "link@x.test")
    cognito_env.attrs = {"email": "link@x.test", "email_verified": "true"}
    assert whoami.get("/whoami", headers=bearer(make_access_token("sub-9"))).json()["id"] == uid


def test_cognito_rejects_bad_tokens(whoami, cognito_env):
    for tok in [make_access_token("s", client_id="other"), make_access_token("s", token_use="id"),
                make_access_token("s", exp=int(time.time()) - 10), make_access_token("s", iss="https://evil.example"),
                "dev:a@x.test"]:
        r = whoami.get("/whoami", headers=bearer(tok))
        assert r.status_code == 401 and r.json()["detail"] == "Invalid or expired token."


def test_fetch_cognito_attributes_sends_a_get_user_request(monkeypatch):
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["target"] = self.headers["X-Amz-Target"]
            seen["type"] = self.headers["Content-Type"]
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            reply = json.dumps({"Username": "u", "UserAttributes": [
                {"Name": "email", "Value": "a@x.test"}, {"Name": "custom:major", "Value": "IT"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-amz-json-1.1")
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            self.wfile.write(reply)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    monkeypatch.setattr(auth, "COGNITO_IDP_URL", f"http://127.0.0.1:{server.server_port}/?region={{region}}")
    try:
        assert fetch_cognito_attributes("tok-123", "ap-southeast-1") == {"email": "a@x.test", "custom:major": "IT"}
    finally:
        server.server_close()
    assert seen == {"target": "AWSCognitoIdentityProviderService.GetUser", "type": "application/x-amz-json-1.1",
                    "body": {"AccessToken": "tok-123"}}
