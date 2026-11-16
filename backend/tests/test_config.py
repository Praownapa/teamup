import pytest

from app.config import load_settings


def test_defaults():
    s = load_settings({})
    assert (s.auth_mode, s.upload_mode, s.upload_dir, s.seed_demo_data) == ("cognito", "off", "uploads", False)
    assert s.database_url == "postgresql://teamup:teamup@localhost:5434/teamup"


def test_reads_and_normalizes_values():
    s = load_settings({"AUTH_MODE": " DEV ", "UPLOAD_MODE": "local", "SEED_DEMO_DATA": "true"})
    assert (s.auth_mode, s.upload_mode, s.seed_demo_data) == ("dev", "local", True)


def test_rejects_unknown_modes():
    for env in ({"AUTH_MODE": "magic"}, {"UPLOAD_MODE": "ftp"}):
        with pytest.raises(ValueError):
            load_settings(env)


def test_check_settings_requires_cognito_and_s3_details():
    from app.config import Settings, check_settings
    assert check_settings(Settings(auth_mode="dev")) == []
    assert check_settings(Settings(auth_mode="cognito")) == [
        "AUTH_MODE=cognito needs COGNITO_REGION, COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID."]
    assert check_settings(Settings(auth_mode="cognito", cognito_region="r", cognito_user_pool_id="p",
                                   cognito_client_id="c")) == []
    assert check_settings(Settings(auth_mode="dev", upload_mode="s3")) == ["UPLOAD_MODE=s3 needs S3_BUCKET and S3_REGION."]


def test_startup_refuses_incomplete_configuration(monkeypatch):
    import app.main as main
    from app.config import Settings
    from fastapi.testclient import TestClient
    monkeypatch.setattr(main, "get_settings", lambda: Settings(auth_mode="cognito"))

    def must_not_open(url):
        raise AssertionError("the database pool must not be opened with a broken configuration")

    monkeypatch.setattr(main, "open_pool", must_not_open)  # also keeps the session's shared pool untouched
    monkeypatch.setattr(main, "close_pool", lambda: None)
    with pytest.raises(RuntimeError, match="AUTH_MODE=cognito needs"):
        with TestClient(main.create_app()):
            pass


# In AWS the connection arrives in parts (DB_*): the password comes from Secrets Manager, and a
# generated password can contain characters that would break a postgresql:// URL.
PARTS = {"DB_HOST": "db.example.internal", "DB_NAME": "teamup", "DB_USER": "teamup",
         "DB_PASSWORD": "p@ss:w/rd?#% 'q\\x", "DB_SSLMODE": "require"}


def test_database_settings_from_parts():
    from psycopg.conninfo import conninfo_to_dict
    assert conninfo_to_dict(load_settings(PARTS).database_url) == {
        "host": "db.example.internal", "port": "5432", "dbname": "teamup", "user": "teamup",
        "password": "p@ss:w/rd?#% 'q\\x", "sslmode": "require"}


def test_database_url_wins_over_parts():
    assert load_settings({**PARTS, "DATABASE_URL": "postgresql://a:b@h/x"}).database_url == "postgresql://a:b@h/x"


def test_db_host_needs_name_user_and_password():
    with pytest.raises(ValueError, match="DB_HOST needs DB_NAME, DB_USER and DB_PASSWORD."):
        load_settings({"DB_HOST": "h", "DB_NAME": "teamup", "DB_USER": "teamup"})


def test_sslmode_is_optional():
    from psycopg.conninfo import conninfo_to_dict
    parts = {k: v for k, v in PARTS.items() if k != "DB_SSLMODE"}
    info = conninfo_to_dict(load_settings(parts).database_url)
    assert info["host"] == "db.example.internal" and "sslmode" not in info
