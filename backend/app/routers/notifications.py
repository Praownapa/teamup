"""Notifications API: the signed-in user's in-app notifications."""
from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from ..auth import current_user
from ..db import get_conn
from ..views import notification_view

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", summary="My notifications, newest first")
def list_notifications(user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    rows = conn.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT 100",
                        (user["id"],))
    return [notification_view(r) for r in rows]
