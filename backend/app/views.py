"""View builders: turn database rows into the exact JSON shapes the screens expect.

The shapes match docs/RESPONSE-EXAMPLES.json and the view builders in the frontend's src/api/mock.js.
Each builder loads everything it needs with a few batched queries (one per kind of data), never one
query per row.
"""
from __future__ import annotations

from typing import Callable, Iterable, TypeVar

import psycopg
from fastapi import HTTPException

T = TypeVar("T")


def iso(value) -> str:
    """datetime/date -> ISO-8601 text; None -> ''."""
    return value.isoformat() if value is not None else ""


def brief(row: dict, prefix: str = "") -> dict:
    """The short student card used all over the UI: {id, name, major, year}."""
    return {"id": row[f"{prefix}id"], "name": row[f"{prefix}name"],
            "major": row[f"{prefix}major"], "year": row[f"{prefix}year"]}


def dedupe_by_name(items: Iterable[T], name: Callable[[T], str] = lambda item: item) -> list[T]:
    """Keep the first item for each name, comparing names case-insensitively ('React' == 'react')."""
    seen: set[str] = set()
    kept: list[T] = []
    for item in items:
        key = name(item).lower()
        if key not in seen:
            seen.add(key)
            kept.append(item)
    return kept


def get_visible_project(conn: psycopg.Connection, project_id: int, user: dict, lock: bool = False) -> dict:
    """The projects row, or 404. Removed projects are visible to admins only.

    lock=True adds FOR UPDATE: other transactions that also lock this project wait until we commit.
    Only meaningful inside `with conn.transaction():`.
    """
    query = "SELECT * FROM projects WHERE id = %s" + (" FOR UPDATE" if lock else "")
    row = conn.execute(query, (project_id,)).fetchone()
    if row is None or (row["removed_at"] is not None and user["role"] != "admin"):
        raise HTTPException(404, "Project not found.")
    return row


def project_views(conn: psycopg.Connection, viewer_id: int, project_ids: list[int]) -> list[dict]:
    """Full project views as seen by `viewer_id` (match, saved, my_role...), in the order of `project_ids`."""
    ids = list(project_ids)
    if not ids:
        return []
    params = {"viewer": viewer_id, "ids": ids}
    projects = conn.execute("""
        SELECT p.*, s.member_count, s.status, match_score(p.id, %(viewer)s) AS match,
               o.name AS owner_name, o.major AS owner_major, o.year AS owner_year,
               EXISTS (SELECT 1 FROM saved_projects sp WHERE sp.project_id = p.id AND sp.user_id = %(viewer)s) AS saved
        FROM projects p
        JOIN project_summary s ON s.project_id = p.id
        JOIN users o ON o.id = p.owner_id
        WHERE p.id = ANY(%(ids)s)""", params).fetchall()
    skills = conn.execute("""
        SELECT ps.project_id, ps.name,
               EXISTS (SELECT 1 FROM user_skills us
                       WHERE us.user_id = %(viewer)s AND lower(us.name) = lower(ps.name)) AS have
        FROM project_skills ps
        WHERE ps.project_id = ANY(%(ids)s)
        ORDER BY ps.project_id, ps.position""", params).fetchall()
    places = conn.execute("""
        SELECT r.project_id, r.name AS role, r.user_id, u.name, u.major, u.year
        FROM project_roles r
        LEFT JOIN users u ON u.id = r.user_id
        WHERE r.project_id = ANY(%(ids)s)
        ORDER BY r.project_id, r.position, r.id""", params).fetchall()
    member_ids = list({p["user_id"] for p in places if p["user_id"] is not None})
    member_skills: dict[int, list[str]] = {}
    for row in conn.execute("SELECT user_id, name FROM user_skills WHERE user_id = ANY(%s) ORDER BY user_id, position",
                            (member_ids,)):
        member_skills.setdefault(row["user_id"], []).append(row["name"])
    pending = {row["project_id"]: row for row in conn.execute("""
        SELECT project_id,
               count(*) FILTER (WHERE kind = 'request') AS requests,
               count(*) FILTER (WHERE kind = 'invitation') AS invitations
        FROM requests
        WHERE status = 'pending' AND project_id = ANY(%(ids)s)
        GROUP BY project_id""", params)}
    my_requests = {row["project_id"]: row for row in conn.execute("""
        SELECT id, project_id, role, status FROM requests
        WHERE user_id = %(viewer)s AND kind = 'request' AND status = 'pending' AND project_id = ANY(%(ids)s)""", params)}

    views: dict[int, dict] = {}
    for p in projects:
        mine = my_requests.get(p["id"])
        counts = pending.get(p["id"])
        views[p["id"]] = {
            "id": p["id"], "title": p["title"], "category": p["category"], "course": p["course"],
            "description": p["description"], "cover_url": p["cover_url"],
            "owner": {"id": p["owner_id"], "name": p["owner_name"], "major": p["owner_major"], "year": p["owner_year"]},
            "max_size": p["max_size"], "accepting": p["accepting"], "status": p["status"],
            "created_at": iso(p["created_at"]), "duration": p["duration"], "meeting": p["meeting"],
            "deadline": iso(p["deadline"]), "saved": p["saved"], "skills": [], "match": p["match"],
            "roles": [], "members": [], "open_roles": [],
            "my_role": "owner" if p["owner_id"] == viewer_id else None,
            "my_request": {"id": mine["id"], "role": mine["role"], "status": mine["status"]} if mine else None,
            "pending_requests": counts["requests"] if counts else 0,
            "pending_invitations": counts["invitations"] if counts else 0,
        }
    for s in skills:
        views[s["project_id"]]["skills"].append([s["name"], s["have"]])
    for place in places:
        view = views[place["project_id"]]
        if place["user_id"] is None:
            view["roles"].append({"name": place["role"], "user": None})
            view["open_roles"].append(place["role"])
            continue
        person = {"id": place["user_id"], "name": place["name"], "major": place["major"], "year": place["year"]}
        view["roles"].append({"name": place["role"], "user": person})
        view["members"].append({**person, "role": place["role"], "owner": place["user_id"] == view["owner"]["id"],
                                "skills": member_skills.get(place["user_id"], [])})
        if place["user_id"] == viewer_id and view["my_role"] is None:
            view["my_role"] = "member"
    return [views[i] for i in ids if i in views]


def project_view(conn: psycopg.Connection, viewer_id: int, project_id: int) -> dict:
    views = project_views(conn, viewer_id, [project_id])
    if not views:
        raise HTTPException(404, "Project not found.")
    return views[0]
