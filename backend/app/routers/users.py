"""User Authentication & Profile API (Jira: Develop User Authentication and Profile API).

Sign-in itself happens in Cognito (see app/auth.py). These endpoints serve the signed-in user's
profile, their menu badge counts and dashboard, and other students' public profiles.
"""
from __future__ import annotations

from typing import Literal

import psycopg
from fastapi import APIRouter, Depends
from psycopg import sql
from pydantic import BaseModel, ConfigDict, Field

from ..auth import current_user
from ..db import get_conn
from ..fields import Text
from ..views import dedupe_by_name, me_view, notification_view, project_views, public_user_view

router = APIRouter(tags=["Users & Profile"])


class SkillIn(BaseModel):
    name: Text(50, 1)
    level: Literal["Beginner", "Intermediate", "Advanced"]


class NotifyIn(BaseModel):
    invitations: bool | None = None
    requests: bool | None = None
    team: bool | None = None
    digest: bool | None = None


class ProfileUpdate(BaseModel):
    """Send only the fields you want to change. Anything else (role, status, email, student_id...) is ignored."""
    model_config = ConfigDict(extra="ignore")

    name: Text(100, 1) | None = None
    major: Text(100) | None = None
    year: int | None = Field(None, ge=1, le=6)
    bio: Text(400) | None = None
    portfolio: Text(200) | None = None
    open_to_projects: bool | None = None
    skills: list[SkillIn] | None = Field(None, max_length=30)
    interests: list[Text(50, 1)] | None = Field(None, max_length=20)
    notify: NotifyIn | None = None


def _pending_counts(conn: psycopg.Connection, user_id: int) -> dict:
    """Join requests waiting for this owner, invitations waiting for this student, unread notifications."""
    return conn.execute("""
        SELECT
          (SELECT count(*) FROM requests r JOIN projects p ON p.id = r.project_id
           WHERE r.status = 'pending' AND r.kind = 'request' AND p.owner_id = %(me)s AND p.removed_at IS NULL) AS pending,
          (SELECT count(*) FROM requests r JOIN projects p ON p.id = r.project_id
           WHERE r.status = 'pending' AND r.kind = 'invitation' AND r.user_id = %(me)s AND p.removed_at IS NULL) AS invitations,
          (SELECT count(*) FROM notifications WHERE user_id = %(me)s AND unread) AS unread""", {"me": user_id}).fetchone()


@router.get("/users/me", summary="My profile")
def get_me(user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    return me_view(conn, user["id"])


@router.put("/users/me", summary="Update my profile (only the fields sent change)")
def update_me(body: ProfileUpdate, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    data = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}  # null = unchanged
    columns = {k: data[k] for k in ("name", "major", "year", "bio", "portfolio", "open_to_projects") if k in data}
    for key, value in data.get("notify", {}).items():
        if value is not None:
            columns[f"notify_{key}"] = value
    with conn.transaction():
        if columns:
            # Column names come from the fixed list above, never from the request.
            assignments = sql.SQL(", ").join(sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k)) for k in columns)
            conn.execute(sql.SQL("UPDATE users SET {} WHERE id = {}").format(assignments, sql.Placeholder("id")),
                         {**columns, "id": user["id"]})
        if "skills" in data:  # the whole list is replaced
            conn.execute("DELETE FROM user_skills WHERE user_id = %s", (user["id"],))
            for position, skill in enumerate(dedupe_by_name(data["skills"], lambda s: s["name"])):
                conn.execute("INSERT INTO user_skills (user_id, name, level, position) VALUES (%s, %s, %s, %s)",
                             (user["id"], skill["name"], skill["level"], position))
        if "interests" in data:
            conn.execute("DELETE FROM user_interests WHERE user_id = %s", (user["id"],))
            for position, interest in enumerate(dedupe_by_name(data["interests"])):
                conn.execute("INSERT INTO user_interests (user_id, name, position) VALUES (%s, %s, %s)",
                             (user["id"], interest, position))
    return me_view(conn, user["id"])


@router.get("/users/me/counts", summary="Numbers for the menu badges")
def get_counts(user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    c = _pending_counts(conn, user["id"])
    return {"pending_requests": c["pending"] + c["invitations"], "unread_notifications": c["unread"]}


@router.get("/users/me/dashboard", summary="Everything the dashboard shows")
def get_dashboard(user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    me = user["id"]
    my_projects = [r["id"] for r in conn.execute("""
        SELECT p.id FROM project_roles r JOIN projects p ON p.id = r.project_id
        WHERE r.user_id = %s AND p.removed_at IS NULL
        ORDER BY p.created_at DESC, p.id DESC""", (me,))]
    # Recruiting projects I'm not on yet, best match first.
    others = conn.execute("""
        SELECT p.id, match_score(p.id, %(me)s) AS match
        FROM projects p JOIN project_summary s ON s.project_id = p.id
        WHERE p.removed_at IS NULL AND s.status = 'recruiting'
          AND NOT EXISTS (SELECT 1 FROM project_roles r WHERE r.project_id = p.id AND r.user_id = %(me)s)
        ORDER BY match DESC, p.created_at DESC, p.id DESC""", {"me": me}).fetchall()
    c = _pending_counts(conn, me)
    activity = conn.execute("SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT 4",
                            (me,)).fetchall()
    return {
        "stats": {"teams": len(my_projects), "pending": c["pending"], "invitations": c["invitations"],
                  "matches": sum(1 for o in others if o["match"] >= 50), "unread": c["unread"]},
        "recommended": project_views(conn, me, [o["id"] for o in others[:2]]),
        "my_teams": project_views(conn, me, my_projects),
        "activity": [notification_view(n) for n in activity],
    }


@router.get("/users/{user_id}", summary="Another student's public profile")
def get_user(user_id: int, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    return public_user_view(conn, user_id)
