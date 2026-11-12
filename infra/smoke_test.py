"""Live smoke test of the deployed TeamUp (Jira: Test Deployed Application). Standard library only.

    python infra/smoke_test.py --site https://<id>.cloudfront.net --alb <load balancer DNS name> \
        --pool <user pool ID> --client <app client ID> --bucket <cover bucket>

JOHN_TOKEN and JACK_TOKEN (Cognito access tokens) come from the environment. infra/smoke-test.sh fills
all of this in. It prints PASS or FAIL for each check, and the exit code is the number of failed checks.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.message import Message

TIMEOUT = 15
PNG = base64.b64decode(  # a 1x1 transparent PNG
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


@dataclass
class Response:
    status: int
    headers: Message
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.body)


def request(method: str, url: str, *, token: str | None = None, body=None, content_type: str | None = None,
            timeout: float = TIMEOUT) -> Response:
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if isinstance(body, (dict, list)):
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    elif body is not None:
        data, headers["Content-Type"] = body, content_type
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, resp.headers, resp.read())
    except urllib.error.HTTPError as err:
        return Response(err.code, err.headers, err.read())


class Smoke:
    def __init__(self, args: argparse.Namespace, john: str, jack: str):
        self.site, self.alb, self.pool, self.client, self.bucket = \
            args.site.rstrip("/"), args.alb, args.pool, args.client, args.bucket
        self.john, self.jack = john, jack

    def get(self, path: str, token: str | None = None) -> Response:
        return request("GET", self.site + path, token=token)

    # 1-4: the website
    def home_page(self):
        r = self.get("/")
        assert r.status == 200 and 'id="root"' in r.text, f"status {r.status}"

    def deep_link(self):
        r = self.get("/projects/1")
        assert r.status == 200 and 'id="root"' in r.text, f"status {r.status}"

    def config_js(self):
        text = self.get("/config.js").text
        for expected in (f'COGNITO_USER_POOL_ID: "{self.pool}"', f'COGNITO_CLIENT_ID: "{self.client}"',
                         'USE_MOCK: "false"', 'AUTH_MODE: "cognito"'):
            assert expected in text, f"missing {expected}"

    def not_served_stale(self):
        for path in ("/", "/config.js"):
            self.get(path)
            cache = self.get(path).headers.get("X-Cache", "")
            assert cache != "Hit from cloudfront", f"{path} was served from the cache without checking ({cache})"

    # 5-11: the API through CloudFront
    def health_and_docs(self):
        r = self.get("/api/health")
        assert r.status == 200 and r.json() == {"status": "ok", "database": "ok"}, f"{r.status} {r.text[:200]}"
        assert self.get("/api/docs").status == 200, "Swagger page didn't load"

    def token_required(self):
        r = self.get("/api/users/me")
        assert r.status == 401, f"status {r.status}"

    def john_is_admin(self):
        r = self.get("/api/users/me", self.john)
        assert r.status == 200, f"status {r.status}: {r.text[:200]}"
        me = r.json()
        assert (me["email"], me["role"]) == ("john.carter@student.uni.ac.th", "admin"), f"{me['email']} {me['role']}"

    def search_with_query(self):
        r = self.get("/api/projects?q=Food", self.john)
        assert r.status == 200, f"status {r.status}: {r.text[:200]}"
        titles = [p["title"] for p in r.json()]
        assert "Campus Food Waste Tracker" in titles, f"titles {titles}"

    def dashboard(self):
        r = self.get("/api/users/me/dashboard", self.john)
        assert r.status == 200, f"status {r.status}: {r.text[:200]}"

    def admin_overview(self):
        r = self.get("/api/admin/overview?period=7d", self.john)
        assert r.status == 200, f"status {r.status}: {r.text[:200]}"

    def suspended_user(self):
        r = self.get("/api/users/me", self.jack)
        assert r.status == 403 and r.json().get("detail") == "Your account has been suspended.", \
            f"{r.status} {r.text[:200]}"

    # 12: a cover image, uploaded the browser's way and read back through CloudFront
    def cover_upload(self):
        r = request("POST", self.site + "/api/uploads/presign", token=self.john,
                    body={"filename": "smoke.png", "content_type": "image/png"})
        assert r.status == 200, f"presign: {r.status} {r.text[:200]}"
        links = r.json()
        regional = f"https://{self.bucket}.s3.ap-northeast-1.amazonaws.com/covers/"
        assert links["upload_url"].startswith(regional), f"upload_url {links['upload_url'][:90]}"
        assert links["file_url"].startswith(self.site + "/covers/"), f"file_url {links['file_url']}"
        put = request("PUT", links["upload_url"], body=PNG, content_type="image/png")
        assert put.status == 200, f"upload: {put.status} {put.text[:200]}"
        got = request("GET", links["file_url"])
        assert got.status == 200 and got.body == PNG, f"read back: {got.status}"

    # 13: nobody can skip CloudFront
    def load_balancer_refuses_direct(self):
        try:
            r = request("GET", f"http://{self.alb}/api/health", timeout=10)
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError):
            return  # the firewall dropped it: good
        assert r.status != 200, "the load balancer answered a request that didn't come through CloudFront"

    CHECKS = ("home_page", "deep_link", "config_js", "not_served_stale", "health_and_docs", "token_required",
              "john_is_admin", "search_with_query", "dashboard", "admin_overview", "suspended_user",
              "cover_upload", "load_balancer_refuses_direct")

    def run(self) -> int:
        failures = 0
        for number, name in enumerate(self.CHECKS, 1):
            try:
                getattr(self, name)()
                print(f"PASS {number:2} {name}")
            except Exception as err:  # every check runs, whatever the previous one did
                failures += 1
                print(f"FAIL {number:2} {name}: {type(err).__name__}: {err}")
        print(f"{len(self.CHECKS) - failures}/{len(self.CHECKS)} checks passed")
        return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Live smoke test of the deployed TeamUp")
    for flag in ("--site", "--alb", "--pool", "--client", "--bucket"):
        parser.add_argument(flag, required=True)
    args = parser.parse_args(argv)
    return Smoke(args, os.environ.get("JOHN_TOKEN", ""), os.environ.get("JACK_TOKEN", "")).run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
