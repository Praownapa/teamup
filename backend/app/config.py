"""Settings, read from environment variables (see backend/.env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping

from psycopg.conninfo import make_conninfo

DEFAULT_DATABASE_URL = "postgresql://teamup:teamup@localhost:5434/teamup"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    auth_mode: str = "cognito"      # "cognito" = real Cognito tokens, "dev" = local test tokens
    cognito_region: str = ""
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    upload_mode: str = "off"        # "off", "local" or "s3"
    upload_dir: str = "uploads"
    s3_bucket: str = ""
    s3_region: str = ""
    public_file_base_url: str = ""
    seed_demo_data: bool = False


def _choice(value: str, allowed: tuple[str, ...], message: str) -> str:
    value = value.strip().lower()
    if value not in allowed:
        raise ValueError(message)
    return value


def _database_url(env: Mapping[str, str]) -> str:
    """DATABASE_URL when it is set (local development). In AWS the connection comes in parts (DB_*),
    because the password comes from Secrets Manager and may contain characters that would break a
    postgresql:// URL. make_conninfo turns the parts into a libpq "key=value" string with safe quoting."""
    url = env.get("DATABASE_URL", "").strip()
    if url:
        return url
    host = env.get("DB_HOST", "").strip()
    if not host:
        return DEFAULT_DATABASE_URL
    name, user = env.get("DB_NAME", "").strip(), env.get("DB_USER", "").strip()
    password = env.get("DB_PASSWORD", "")  # not stripped: every character belongs to the password
    if not (name and user and password):
        raise ValueError("DB_HOST needs DB_NAME, DB_USER and DB_PASSWORD.")
    parts = {"host": host, "port": env.get("DB_PORT", "").strip() or "5432",
             "dbname": name, "user": user, "password": password}
    sslmode = env.get("DB_SSLMODE", "").strip()
    if sslmode:
        parts["sslmode"] = sslmode
    return make_conninfo(**parts)


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env

    def get(key: str, default: str = "") -> str:
        return env.get(key, default).strip()

    return Settings(
        database_url=_database_url(env),
        auth_mode=_choice(get("AUTH_MODE", "cognito"), ("cognito", "dev"), "AUTH_MODE must be cognito or dev"),
        cognito_region=get("COGNITO_REGION"),
        cognito_user_pool_id=get("COGNITO_USER_POOL_ID"),
        cognito_client_id=get("COGNITO_CLIENT_ID"),
        upload_mode=_choice(get("UPLOAD_MODE", "off"), ("off", "local", "s3"), "UPLOAD_MODE must be off, local or s3"),
        upload_dir=get("UPLOAD_DIR") or "uploads",
        s3_bucket=get("S3_BUCKET"),
        s3_region=get("S3_REGION"),
        public_file_base_url=get("PUBLIC_FILE_BASE_URL"),
        seed_demo_data=get("SEED_DEMO_DATA").lower() in ("true", "1", "yes"),
    )


def check_settings(settings: Settings) -> list[str]:
    """Problems that would make the running API fail in confusing ways (e.g. every login rejected)."""
    problems = []
    if settings.auth_mode == "cognito" and not (
            settings.cognito_region and settings.cognito_user_pool_id and settings.cognito_client_id):
        problems.append("AUTH_MODE=cognito needs COGNITO_REGION, COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID.")
    if settings.upload_mode == "s3" and not (settings.s3_bucket and settings.s3_region):
        problems.append("UPLOAD_MODE=s3 needs S3_BUCKET and S3_REGION.")
    return problems


@lru_cache
def get_settings() -> Settings:
    return load_settings()
