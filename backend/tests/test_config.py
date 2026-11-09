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
