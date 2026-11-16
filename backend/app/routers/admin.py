"""Admin API: platform numbers, moderation of reported projects, user suspension and categories.

Every route depends on `admin_user`, so non-admins get 403 no matter how they call it.
"""
from __future__ import annotations

from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from ..auth import admin_user
from ..db import get_conn
from ..fields import Text
from ..notify import notify
from ..views import brief, iso
from .search import category_counts

router = APIRouter(tags=["Admin"])

# period -> (how far back the "+N" numbers look, number of chart buckets, size of one bucket)
PERIODS = {"7d": ("7 days", 7, "1 day"), "30d": ("30 days", 5, "7 days"), "semester": ("120 days", 16, "7 days")}


class ResolveIn(BaseModel):
    status: Literal["removed", "dismissed"]


class UserStatusIn(BaseModel):
    status: Literal["suspended", "active"]


class CategoryIn(BaseModel):
    name: Text(50, 1)


@router.get("/admin/overview", summary="Admin dashboard data")
def overview(period: Literal["7d", "30d", "semester"] = "30d", admin: dict = Depends(admin_user),
             conn: psycopg.Connection = Depends(get_conn)):
    window, buckets, step = PERIODS[period]
    p = {"window": window, "n": buckets, "step": step}
    s = conn.execute("""
        SELECT
          (SELECT count(*) FROM users) AS students,
          (SELECT count(*) FROM projects WHERE removed_at IS NULL) AS projects,
          (SELECT count(*) FROM projects pr JOIN project_summary ps ON ps.project_id = pr.id
           WHERE pr.removed_at IS NULL AND ps.member_count >= 2) AS teams,
          (SELECT count(DISTINCT r.project_id) FROM reports r JOIN projects pr ON pr.id = r.project_id
           WHERE r.status = 'open' AND pr.removed_at IS NULL) AS reports,
          (SELECT count(*) FROM users WHERE created_at >= now() - %(window)s::interval) AS new_students,
          (SELECT count(*) FROM projects WHERE removed_at IS NULL AND created_at >= now() - %(window)s::interval) AS new_projects,
          (SELECT count(*) FROM projects pr JOIN project_summary ps ON ps.project_id = pr.id
           WHERE pr.removed_at IS NULL AND ps.member_count >= 2
             AND pr.created_at >= now() - %(window)s::interval) AS new_teams""", p).fetchone()
    # One row per chart bar, oldest first: join requests and new projects created in that bucket.
    activity = conn.execute("""
        WITH buckets AS (
          SELECT i, date_trunc('day', now()) - (%(n)s - 1 - i) * %(step)s::interval AS start
          FROM generate_series(0, %(n)s - 1) AS i)
        SELECT b.i, to_char(b.start, 'Dy') AS day,
               (SELECT count(*) FROM requests r WHERE r.kind = 'request'
                  AND r.created_at >= b.start AND r.created_at < b.start + %(step)s::interval) AS requests,
               (SELECT count(*) FROM projects pr
                WHERE pr.created_at >= b.start AND pr.created_at < b.start + %(step)s::interval) AS projects
        FROM buckets b ORDER BY b.i""", p).fetchall()
    reports = conn.execute("""
        SELECT (array_agg(r.id ORDER BY r.created_at DESC, r.id DESC))[1] AS id, pr.title AS project, o.name AS owner,
               (array_agg(r.reason ORDER BY r.created_at DESC, r.id DESC))[1] AS reason,
               count(*) AS reporters, max(r.created_at) AS created_at
        FROM reports r
        JOIN projects pr ON pr.id = r.project_id
        JOIN users o ON o.id = pr.owner_id
        WHERE r.status = 'open' AND pr.removed_at IS NULL
        GROUP BY pr.id, pr.title, o.name
        ORDER BY max(r.created_at) DESC""").fetchall()
    users = conn.execute("""
        SELECT u.id, u.name, u.major, u.year, u.email, u.student_id, u.role, u.status,
               (SELECT count(*) FROM project_roles r JOIN projects pr ON pr.id = r.project_id
                WHERE r.user_id = u.id AND pr.removed_at IS NULL) AS projects
        FROM users u ORDER BY u.id""").fetchall()
    return {
        "stats": {"students": s["students"], "projects": s["projects"], "teams": s["teams"], "reports": s["reports"],
                  "deltas": {"students": s["new_students"], "projects": s["new_projects"], "teams": s["new_teams"]}},
        "activity": [{"week": a["day"] if step == "1 day" else f"W{a['i'] + 1}", "requests": a["requests"],
                      "projects": a["projects"]} for a in activity],
        "categories": category_counts(conn),
        "reports": [{"id": r["id"], "project": r["project"], "owner": r["owner"], "reason": r["reason"],
                     "reporters": r["reporters"], "created_at": iso(r["created_at"]), "status": "open"} for r in reports],
        "users": [{**brief(u), "email": u["email"], "student_id": u["student_id"], "role": u["role"],
                   "status": u["status"], "projects": u["projects"]} for u in users],
    }


@router.patch("/admin/reports/{report_id}", status_code=204, summary="Remove the reported project, or dismiss the report")
def resolve_report(report_id: int, body: ResolveIn, admin: dict = Depends(admin_user),
                   conn: psycopg.Connection = Depends(get_conn)):
    with conn.transaction():
        found = conn.execute("SELECT project_id FROM reports WHERE id = %s", (report_id,)).fetchone()
        if found is None:
            raise HTTPException(404, "Report not found.")
        project = conn.execute("SELECT * FROM projects WHERE id = %s FOR UPDATE", (found["project_id"],)).fetchone()
        report = conn.execute("SELECT status FROM reports WHERE id = %s FOR UPDATE", (report_id,)).fetchone()
        if report["status"] != "open":
            raise HTTPException(409, "This report has already been handled.")
        # Every open report about this project is settled together.
        conn.execute("""UPDATE reports SET status = %s, resolved_at = now(), resolved_by = %s
                        WHERE project_id = %s AND status = 'open'""", (body.status, admin["id"], project["id"]))
        if body.status == "removed":
            conn.execute("UPDATE projects SET removed_at = now() WHERE id = %s AND removed_at IS NULL", (project["id"],))
            rejected = conn.execute("""UPDATE requests SET status = 'rejected', responded_at = now()
                                       WHERE project_id = %s AND status = 'pending' RETURNING id""", (project["id"],)).fetchall()
            conn.execute("UPDATE notifications SET unread = false WHERE request_id = ANY(%s)", ([r["id"] for r in rejected],))
            notify(conn, project["owner_id"], "team", f"Your project {project['title']} was removed by an administrator.")
    return Response(status_code=204)


@router.patch("/admin/users/{user_id}", status_code=204, summary="Suspend or reactivate a user")
def set_user_status(user_id: int, body: UserStatusIn, admin: dict = Depends(admin_user),
                    conn: psycopg.Connection = Depends(get_conn)):
    target = conn.execute("SELECT id, role FROM users WHERE id = %s", (user_id,)).fetchone()
    if target is None:
        raise HTTPException(404, "Student not found.")
    if target["id"] == admin["id"]:
        raise HTTPException(400, "You can't change your own status.")
    if body.status == "suspended" and target["role"] == "admin":
        raise HTTPException(400, "Administrators can't be suspended.")
    conn.execute("UPDATE users SET status = %s WHERE id = %s", (body.status, user_id))
    return Response(status_code=204)


@router.post("/admin/categories", status_code=204, summary="Add a project category")
def add_category(body: CategoryIn, admin: dict = Depends(admin_user), conn: psycopg.Connection = Depends(get_conn)):
    conn.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", (body.name,))
    return Response(status_code=204)


@router.delete("/admin/categories/{name:path}", status_code=204, summary="Delete a category (existing projects keep their label)")
def delete_category(name: str, admin: dict = Depends(admin_user), conn: psycopg.Connection = Depends(get_conn)):
    conn.execute("DELETE FROM categories WHERE lower(name) = lower(%s)", (name,))
    return Response(status_code=204)
