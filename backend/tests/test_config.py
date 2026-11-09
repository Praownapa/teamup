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
