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
