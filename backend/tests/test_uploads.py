from dataclasses import replace

import app.routers.uploads as uploads
from app.config import get_settings

PNG = {"filename": "c.png", "content_type": "image/png"}


def test_local_upload_round_trip(api, client):
    r = api("u@x.test").post("/uploads/presign", json=PNG).json()
    assert r["file_url"].startswith("/api/uploads/files/covers/")
    assert client.put(r["upload_url"], content=b"\x89PNG", headers={"Content-Type": "image/jpeg"}).json()["detail"] == \
        "Content-Type does not match the upload link."
    assert client.put(r["upload_url"], content=b"\x89PNG", headers={"Content-Type": "image/png"}).status_code == 200
    reused = client.put(r["upload_url"], content=b"\x89PNG", headers={"Content-Type": "image/png"})  # links work once
    assert reused.status_code == 403 and reused.json()["detail"] == "Upload link is invalid or expired."
    got = client.get(r["file_url"])
    assert got.status_code == 200 and got.content == b"\x89PNG" and got.headers["content-type"] == "image/png"
    assert client.get("/api/uploads/files/../secrets.txt").status_code in (400, 404)
    assert client.get("/api/uploads/files/covers/1/not-a-real-key.png").status_code == 404


def test_presign_rejects_type_and_size(api, client):
    a = api("u@x.test")
    assert a.post("/uploads/presign", json={"filename": "x.gif", "content_type": "image/gif"}).json()["detail"] == \
        "Only PNG, JPG or WebP images are allowed."
    r = a.post("/uploads/presign", json=PNG).json()
    too_big = client.put(r["upload_url"], content=b"0" * (5 * 1024 * 1024 + 1), headers={"Content-Type": "image/png"})
    assert too_big.status_code == 413 and too_big.json()["detail"] == "Image must be 5 MB or smaller."


def test_off_and_s3_modes(api, monkeypatch):
    monkeypatch.setattr(uploads, "get_settings", lambda: replace(get_settings(), upload_mode="off"))
    assert api("u@x.test").post("/uploads/presign", json=PNG).json()["detail"] == "Image uploads are not configured."
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setattr(uploads, "get_settings", lambda: replace(get_settings(), upload_mode="s3", s3_bucket="teamup-test",
                                                                 s3_region="ap-southeast-1"))
    r = api("u@x.test").post("/uploads/presign", json=PNG).json()
    assert "teamup-test" in r["upload_url"] and "X-Amz-Signature=" in r["upload_url"]
    assert r["file_url"].startswith("https://teamup-test.s3.ap-southeast-1.amazonaws.com/covers/")
    # Regional host: the global one redirects for up to a day after a bucket is created, and browsers
    # refuse redirects on CORS uploads.
    assert r["upload_url"].startswith("https://teamup-test.s3.ap-southeast-1.amazonaws.com/covers/")
