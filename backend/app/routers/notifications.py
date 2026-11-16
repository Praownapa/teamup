"""Notifications API: the signed-in user's in-app notifications."""
from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response

from ..auth import current_user
from ..db import get_conn
from ..views import notification_view

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", summary="My notifications, newest first")
def list_notifications(user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    rows = conn.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT 100",
                        (user["id"],))
    return [notification_view(r) for r in rows]


@router.post("/notifications/read-all", status_code=204, summary="Mark all my notifications as read")
def mark_all_read(user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    conn.execute("UPDATE notifications SET unread = false WHERE user_id = %s AND unread", (user["id"],))
    return Response(status_code=204)


@router.post("/notifications/{notification_id}/read", status_code=204, summary="Mark one of my notifications as read")
def mark_read(notification_id: int, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    # "AND user_id = ..." means you can only ever touch your own notifications.
    updated = conn.execute("UPDATE notifications SET unread = false WHERE id = %s AND user_id = %s",
                           (notification_id, user["id"])).rowcount
    if not updated:
        raise HTTPException(404, "Notification not found.")
    return Response(status_code=204)
