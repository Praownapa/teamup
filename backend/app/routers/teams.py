"""Team Management API (Jira: Develop Team Management API).

The owner changes members' roles and removes members; a member can leave. The team itself is read
with GET /projects/{id} (the team page and the project page share one view).
"""
from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from ..auth import current_user
from ..db import get_conn
from ..fields import Text
from ..notify import notify, transaction
from ..places import free_place, member_ids
from ..views import get_visible_project, project_view

router = APIRouter(tags=["Team Management"])


class RoleChangeIn(BaseModel):
    role: Text(60, 1)


def _locked_project_for_owner(conn: psycopg.Connection, owner: dict, project_id: int) -> dict:
    project = get_visible_project(conn, project_id, owner, lock=True)
    if project["owner_id"] != owner["id"]:
        raise HTTPException(403, "Only the project owner can do that.")
    return project


# ---------------------------------------------------------------- services
def change_member_role(conn: psycopg.Connection, owner: dict, project_id: int, member_id: int, role: str) -> None:
    with conn.transaction():
        project = _locked_project_for_owner(conn, owner, project_id)
        if member_id == project["owner_id"]:
            raise HTTPException(400, "The owner's role can't be changed here.")
        current = conn.execute("SELECT id, name FROM project_roles WHERE project_id = %s AND user_id = %s",
                               (project_id, member_id)).fetchone()
        if current is None:
            raise HTTPException(404, "That student isn't on this team.")
        if current["name"] == role:
            return
        target = conn.execute("""
            SELECT id FROM project_roles WHERE project_id = %s AND user_id IS NULL AND name = %s
            ORDER BY position, id LIMIT 1""", (project_id, role)).fetchone()
        if target:  # move into the open place with that name (free the old place first: one place per person)
            conn.execute("UPDATE project_roles SET user_id = NULL WHERE id = %s", (current["id"],))
            conn.execute("UPDATE project_roles SET user_id = %s WHERE id = %s", (member_id, target["id"]))
        else:  # no open place with that name: rename the member's place
            conn.execute("UPDATE project_roles SET name = %s WHERE id = %s", (role, current["id"]))
        notify(conn, member_id, "team", f"Your role in {project['title']} is now {role}.")


def remove_member(conn: psycopg.Connection, owner: dict, project_id: int, member_id: int) -> None:
    with transaction(conn):  # also sends the notification email, after the commit
        project = _locked_project_for_owner(conn, owner, project_id)
        if member_id == project["owner_id"]:
            raise HTTPException(400, "The owner can't be removed from their own project.")
        if member_id not in member_ids(conn, project_id):
            raise HTTPException(404, "That student isn't on this team.")
        free_place(conn, project_id, member_id)
        notify(conn, member_id, "team", f"You were removed from {project['title']}.",
               email="team", subject=f"You were removed from {project['title']}")


def leave_team(conn: psycopg.Connection, user: dict, project_id: int) -> None:
    with conn.transaction():
        project = get_visible_project(conn, project_id, user, lock=True)
        if project["owner_id"] == user["id"]:
            raise HTTPException(400, "Owners can't leave their own project.")
        if user["id"] not in member_ids(conn, project_id):
            raise HTTPException(404, "You're not on this team.")
        free_place(conn, project_id, user["id"])
        notify(conn, project["owner_id"], "team", f"{user['name']} left {project['title']}.")


# ---------------------------------------------------------------- routes (/members/me must come before /members/{user_id})
@router.delete("/projects/{project_id}/members/me", status_code=204, summary="Leave a team I'm a member of")
def leave(project_id: int, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    leave_team(conn, user, project_id)
    return Response(status_code=204)


@router.patch("/projects/{project_id}/members/{user_id}", summary="Change a member's role (owner only)")
def change_role(project_id: int, user_id: int, body: RoleChangeIn, user: dict = Depends(current_user),
                conn: psycopg.Connection = Depends(get_conn)):
    change_member_role(conn, user, project_id, user_id, body.role)
    return project_view(conn, user["id"], project_id)


@router.delete("/projects/{project_id}/members/{user_id}", summary="Remove a member (owner only)")
def remove(project_id: int, user_id: int, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    remove_member(conn, user, project_id, user_id)
    return project_view(conn, user["id"], project_id)
