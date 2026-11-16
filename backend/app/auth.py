"""Who is calling? Checks the bearer token on every request and loads (or creates) the caller's profile.

AUTH_MODE=cognito (the default, and the only mode for AWS)
    The frontend sends a Cognito *access token* (a signed JWT). We check its signature with the user
    pool's public keys (JWKS), its issuer, expiry, type and app client, and identify the user by the
    token's `sub` claim. Access tokens don't contain the email or custom attributes, so the first time
    we see a user we ask Cognito's GetUser API (authorised by the same token) for them.

AUTH_MODE=dev (local development only)
    The token is "dev:<email>", or "dev:email=...&name=...&student_id=...&major=..." (URL-encoded).
    Anyone can claim any email, which is why this mode must never run in AWS.

FastAPI note: route functions declare `user: dict = Depends(current_user)`. FastAPI calls current_user
first (which itself gets the Authorization header and a database connection injected), and the route
only runs if no HTTPException was raised.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from functools import lru_cache

import jwt
import psycopg
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings
from .db import get_conn

bearer_scheme = HTTPBearer(auto_error=False,
                           description="A Cognito access token, or `dev:<email>` when the API runs with AUTH_MODE=dev.")
COGNITO_IDP_URL = "https://cognito-idp.{region}.amazonaws.com/"
INVALID_TOKEN = "Invalid or expired token."


def _unauthorized(detail: str = INVALID_TOKEN) -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


# ---------------------------------------------------------------- dev mode
def parse_dev_token(token: str) -> dict:
    """'dev:a@x.test' or 'dev:email=a%40x.test&name=A+B&student_id=..&major=..' -> identity fields."""
    if not token.startswith("dev:"):
        raise _unauthorized()
    body = token[len("dev:"):]
    fields = dict(urllib.parse.parse_qsl(body)) if "=" in body else {"email": body}
    email = fields.get("email", "").strip().lower()
    local, _, domain = email.partition("@")
    if not local or not domain:
        raise _unauthorized()
    return {"email": email, "name": fields.get("name", "").strip(),
            "student_id": fields.get("student_id", "").strip(), "major": fields.get("major", "").strip()}


def user_for_dev(conn: psycopg.Connection, ident: dict) -> dict:
    row = conn.execute("SELECT * FROM users WHERE email = %s", (ident["email"],)).fetchone()
    if row:
        return row
    # ON CONFLICT: if two first requests arrive at once, only one insert wins; both then read the same row.
    conn.execute(
        "INSERT INTO users (email, name, student_id, major) VALUES (%s, %s, %s, %s) ON CONFLICT (email) DO NOTHING",
        (ident["email"], ident["name"] or ident["email"].split("@")[0], ident["student_id"], ident["major"]))
    return conn.execute("SELECT * FROM users WHERE email = %s", (ident["email"],)).fetchone()


# ---------------------------------------------------------------- cognito mode
@lru_cache(maxsize=4)
def get_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    """Downloads and caches the user pool's public signing keys."""
    return jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600, timeout=5)


def verify_cognito_token(token: str, settings: Settings) -> dict:
    issuer = f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}"
    try:
        key = get_jwk_client(f"{issuer}/.well-known/jwks.json").get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=issuer,
                            options={"require": ["exp", "iss", "sub", "token_use", "client_id"], "verify_aud": False})
    except jwt.PyJWTError as e:  # bad signature, expired, wrong issuer, malformed, keys unavailable...
        raise _unauthorized() from e
    if claims["token_use"] != "access" or claims["client_id"] != settings.cognito_client_id:
        raise _unauthorized()
    return claims


def fetch_cognito_attributes(access_token: str, region: str) -> dict[str, str]:
    """Cognito GetUser: returns the signed-in user's attributes (email, name, custom:student_id, ...)."""
    request = urllib.request.Request(
        COGNITO_IDP_URL.format(region=region), method="POST",
        data=json.dumps({"AccessToken": access_token}).encode(),
        headers={"Content-Type": "application/x-amz-json-1.1",
                 "X-Amz-Target": "AWSCognitoIdentityProviderService.GetUser"})
    with urllib.request.urlopen(request, timeout=5) as response:
        body = json.load(response)
    return {a["Name"]: a["Value"] for a in body.get("UserAttributes", [])}


def user_for_cognito(conn: psycopg.Connection, claims: dict, token: str, settings: Settings) -> dict:
    sub = claims["sub"]
    row = conn.execute("SELECT * FROM users WHERE cognito_sub = %s", (sub,)).fetchone()
    if row is None:
        try:
            attrs = fetch_cognito_attributes(token, settings.cognito_region)
        except Exception as e:  # network error, HTTP error from Cognito, unexpected reply
            raise HTTPException(502, "Could not load your profile from Cognito.") from e
        email = attrs.get("email", "").strip().lower()
        if not email:
            raise HTTPException(502, "Could not load your profile from Cognito.")
        if attrs.get("email_verified") == "true":
            # Cognito has verified this person owns the email, so a profile with that email is theirs:
            # one created before Cognito (demo/dev), or one whose Cognito account was deleted and re-created.
            row = conn.execute("UPDATE users SET cognito_sub = %s WHERE email = %s RETURNING *", (sub, email)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (cognito_sub, email, name, student_id, major) VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (sub, email, attrs.get("name", "").strip() or email.split("@")[0],
                 attrs.get("custom:student_id", "").strip(), attrs.get("custom:major", "").strip()))
            row = conn.execute("SELECT * FROM users WHERE cognito_sub = %s", (sub,)).fetchone()
            if row is None:
                raise HTTPException(409, "An account with this email already exists.")
    # The Cognito "admin" group decides who is an admin; keep users.role in step with it.
    role = "admin" if "admin" in (claims.get("cognito:groups") or []) else "student"
    if row["role"] != role:
        row = conn.execute("UPDATE users SET role = %s WHERE id = %s RETURNING *", (role, row["id"])).fetchone()
    return row


# ---------------------------------------------------------------- dependencies used by the routes
def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
                 conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """The signed-in user's `users` row. 401 without a valid token, 403 when suspended."""
    if credentials is None:
        raise _unauthorized("Not authenticated.")
    settings = get_settings()
    if settings.auth_mode == "dev":
        user = user_for_dev(conn, parse_dev_token(credentials.credentials))
    else:
        claims = verify_cognito_token(credentials.credentials, settings)
        user = user_for_cognito(conn, claims, credentials.credentials, settings)
    if user["status"] == "suspended":
        raise HTTPException(403, "Your account has been suspended.")
    return user


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required.")
    return user
