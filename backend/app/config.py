"""Settings, read from environment variables (see backend/.env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping

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


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env

    def get(key: str, default: str = "") -> str:
        return env.get(key, default).strip()

    return Settings(
        database_url=get("DATABASE_URL") or DEFAULT_DATABASE_URL,
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


@lru_cache
def get_settings() -> Settings:
    return load_settings()
