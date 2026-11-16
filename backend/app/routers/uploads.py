"""Uploads API: project cover images.

The browser uploads in two steps (see the frontend's src/utils/upload.js):
  1. POST /api/uploads/presign  -> {upload_url, file_url}
  2. PUT the image bytes straight to upload_url, then save file_url with the project.

UPLOAD_MODE=s3     upload_url is a presigned Amazon S3 URL (valid 5 minutes); the image never passes
                   through this API. file_url is the object's public URL.
UPLOAD_MODE=local  for development without AWS: upload_url points back at this API, which stores the
                   file under UPLOAD_DIR and serves it from /api/uploads/files/...
UPLOAD_MODE=off    uploads are refused (503); projects simply use their category illustration.
"""
from __future__ import annotations

import re
import secrets
import time
import uuid
from pathlib import Path

import boto3
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..auth import current_user
from ..config import get_settings
from ..fields import Text

router = APIRouter(tags=["Uploads"])

TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
MEDIA_TYPES = {ext: content_type for content_type, ext in TYPES.items()}
MAX_BYTES = 5 * 1024 * 1024
LINK_SECONDS = 300
KEY_PATTERN = re.compile(r"^covers/\d+/[0-9a-f]{32}\.(png|jpg|webp)$")

# Local mode only: one-time upload links, key -> (token, content type, expiry time). Lost on restart.
_local_links: dict[str, tuple[str, str, float]] = {}


class PresignIn(BaseModel):
    filename: Text(200, 1)
    content_type: Text(100, 1)


@router.post("/uploads/presign", summary="Get a one-time URL for uploading a cover image")
def presign(body: PresignIn, user: dict = Depends(current_user)):
    settings = get_settings()
    if settings.upload_mode == "off":
        raise HTTPException(503, "Image uploads are not configured.")
    content_type = body.content_type.lower()
    ext = TYPES.get(content_type)
    if ext is None:
        raise HTTPException(400, "Only PNG, JPG or WebP images are allowed.")
    key = f"covers/{user['id']}/{uuid.uuid4().hex}.{ext}"
    if settings.upload_mode == "s3":
        s3 = boto3.client("s3", region_name=settings.s3_region, config=Config(signature_version="s3v4"))
        upload_url = s3.generate_presigned_url(
            "put_object", Params={"Bucket": settings.s3_bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=LINK_SECONDS)
        base = settings.public_file_base_url or f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com"
        return {"upload_url": upload_url, "file_url": f"{base.rstrip('/')}/{key}"}
    token = secrets.token_urlsafe(16)
    _local_links[key] = (token, content_type, time.monotonic() + LINK_SECONDS)
    return {"upload_url": f"/api/uploads/local/{key}?token={token}", "file_url": f"/api/uploads/files/{key}"}


@router.put("/uploads/local/{key:path}", include_in_schema=False)
async def receive_local_upload(key: str, token: str, request: Request):
    """Local mode stand-in for S3: accepts the PUT the browser would otherwise send to S3."""
    if get_settings().upload_mode != "local":
        raise HTTPException(404, "Not Found")
    link = _local_links.get(key)
    if link is None or not KEY_PATTERN.match(key) or not secrets.compare_digest(link[0], token) or time.monotonic() > link[2]:
        raise HTTPException(403, "Upload link is invalid or expired.")
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != link[1]:
        raise HTTPException(400, "Content-Type does not match the upload link.")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BYTES:
        raise HTTPException(413, "Image must be 5 MB or smaller.")
    data = await request.body()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image must be 5 MB or smaller.")
    path = Path(get_settings().upload_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    _local_links.pop(key, None)  # each link works once
    return Response(status_code=200)


@router.get("/uploads/files/{key:path}", include_in_schema=False)
def serve_local_upload(key: str):
    settings = get_settings()
    if settings.upload_mode != "local" or not KEY_PATTERN.match(key):
        raise HTTPException(404, "File not found.")
    path = Path(settings.upload_dir) / key
    if not path.is_file():
        raise HTTPException(404, "File not found.")
    return FileResponse(path, media_type=MEDIA_TYPES[path.suffix.lstrip(".")])
