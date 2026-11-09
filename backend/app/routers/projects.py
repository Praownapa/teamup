"""Project Management API (Jira: Develop Project Management API).

Create a project, read it, edit it (owner only), save it to your list, and report it to the admins.

FastAPI notes for readers new to it:
- `@router.post("/projects", ...)` registers the function below as the handler for POST /api/projects.
- The `body: ProjectCreate` parameter makes FastAPI parse the JSON body into that Pydantic model and
  validate it first; invalid input gets an automatic 422 response listing the problems.
- `Depends(current_user)` / `Depends(get_conn)` inject the signed-in user and a database connection.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg import sql
from pydantic import BaseModel, Field, StringConstraints, field_validator

from ..auth import current_user
from ..db import get_conn
from ..views import dedupe_by_name, get_visible_project, project_view

router = APIRouter(tags=["Projects"])


def Text(max_length: int, min_length: int = 0):
    """A string with surrounding spaces removed and a length limit."""
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length)]


def _check_deadline(value: str | None) -> str | None:
    if value:
        date.fromisoformat(value)  # raises ValueError -> 422 for anything that isn't YYYY-MM-DD
    return value


class RoleIn(BaseModel):
    name: Text(60, 1)
    spots: int = Field(1, ge=1, le=4)


class ProjectCreate(BaseModel):
    title: Text(80, 1)
    description: Text(2000, 1)
    category: Text(50, 1)
    course: Text(100) = ""
    cover_url: Text(500) = ""
    skills: list[Text(50, 1)] = Field(min_length=1, max_length=20)
    owner_role: Text(60) = ""
    roles: list[RoleIn] = Field(min_length=1, max_length=10)
    max_size: int = Field(ge=2, le=10)
    deadline: Text(10) = ""
    duration: Text(100) = ""
    meeting: Text(100) = ""
    accepting: bool = True

    _deadline = field_validator("deadline")(_check_deadline)


class ProjectUpdate(BaseModel):
    """PATCH: send only the fields you want to change."""
    title: Text(80, 1) | None = None
    description: Text(2000, 1) | None = None
    category: Text(50, 1) | None = None
    course: Text(100) | None = None
    cover_url: Text(500) | None = None
    deadline: Text(10) | None = None
    duration: Text(100) | None = None
    meeting: Text(100) | None = None
    accepting: bool | None = None

    _deadline = field_validator("deadline")(_check_deadline)


class ReportIn(BaseModel):
    reason: Text(100, 1)


def canonical_category(conn: psycopg.Connection, name: str) -> str:
    """The category's stored spelling (matching ignores case), or 400 if it doesn't exist."""
    row = conn.execute("SELECT name FROM categories WHERE lower(name) = lower(%s)", (name,)).fetchone()
    if row is None:
        raise HTTPException(400, "Unknown category.")
    return row["name"]


@router.post("/projects", status_code=201, summary="Create a project")
def create_project(body: ProjectCreate, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    needed = 1 + sum(role.spots for role in body.roles)  # +1: the owner holds a place too
    if needed > body.max_size:
        raise HTTPException(400, f"Your roles need {needed} people (including you) but the maximum team size is {body.max_size}.")
    with conn.transaction():  # the project, its skills and its places are saved together or not at all
        category = canonical_category(conn, body.category)
        project_id = conn.execute("""
            INSERT INTO projects (owner_id, title, description, category, course, cover_url, max_size, accepting,
                                  deadline, duration, meeting)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (user["id"], body.title, body.description, category, body.course, body.cover_url, body.max_size,
             body.accepting, date.fromisoformat(body.deadline) if body.deadline else None,
             body.duration or "—", body.meeting or "—")).fetchone()["id"]
        for position, skill in enumerate(dedupe_by_name(body.skills)):
            conn.execute("INSERT INTO project_skills (project_id, name, position) VALUES (%s, %s, %s)",
                         (project_id, skill, position))
        places = [(body.owner_role or "Project Owner", user["id"])]
        places += [(role.name, None) for role in body.roles for _ in range(role.spots)]
        for position, (name, holder) in enumerate(places):
            conn.execute("INSERT INTO project_roles (project_id, name, user_id, position) VALUES (%s, %s, %s, %s)",
                         (project_id, name, holder, position))
    return project_view(conn, user["id"], project_id)


@router.get("/projects/{project_id}", summary="Project details (the team page uses this too)")
def get_project(project_id: int, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    get_visible_project(conn, project_id, user)
    return project_view(conn, user["id"], project_id)


@router.patch("/projects/{project_id}", summary="Edit a project (owner only)")
def update_project(project_id: int, body: ProjectUpdate, user: dict = Depends(current_user),
                   conn: psycopg.Connection = Depends(get_conn)):
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    with conn.transaction():
        project = get_visible_project(conn, project_id, user, lock=True)
        if project["owner_id"] != user["id"]:
            raise HTTPException(403, "Only the project owner can do that.")
        if "category" in changes:
            changes["category"] = canonical_category(conn, changes["category"])
        if "deadline" in changes:
            changes["deadline"] = date.fromisoformat(changes["deadline"]) if changes["deadline"] else None
        for key in ("duration", "meeting"):
            if key in changes:
                changes[key] = changes[key] or "—"
        if changes:
            # Column names come from the ProjectUpdate fields above, never from user input.
            assignments = sql.SQL(", ").join(sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k)) for k in changes)
            conn.execute(sql.SQL("UPDATE projects SET {} WHERE id = {}").format(assignments, sql.Placeholder("id")),
                         {**changes, "id": project_id})
    return project_view(conn, user["id"], project_id)


@router.post("/projects/{project_id}/save", summary="Save or unsave a project for later")
def toggle_save(project_id: int, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    with conn.transaction():
        get_visible_project(conn, project_id, user)
        removed = conn.execute("DELETE FROM saved_projects WHERE user_id = %s AND project_id = %s",
                               (user["id"], project_id)).rowcount
        if not removed:
            conn.execute("INSERT INTO saved_projects (user_id, project_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                         (user["id"], project_id))
    return {"saved": not removed}


@router.post("/projects/{project_id}/reports", summary="Report a project to the admins")
def report_project(project_id: int, body: ReportIn, user: dict = Depends(current_user),
                   conn: psycopg.Connection = Depends(get_conn)):
    project = get_visible_project(conn, project_id, user)
    if project["owner_id"] == user["id"]:
        raise HTTPException(400, "You can't report your own project.")
    # One open report per person per project: reporting again just updates the reason.
    conn.execute("""
        INSERT INTO reports (project_id, reporter_id, reason) VALUES (%s, %s, %s)
        ON CONFLICT (project_id, reporter_id) WHERE status = 'open'
        DO UPDATE SET reason = EXCLUDED.reason, created_at = now()""", (project_id, user["id"], body.reason))
    return {"ok": True}
