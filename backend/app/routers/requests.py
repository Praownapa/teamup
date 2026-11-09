"""Join Request & Invitation API (Jira: Develop Join Request and Invitation API).

A *join request* is started by a student ("I'd like to join as Frontend Developer"); the project owner
accepts or declines it. An *invitation* is started by the owner; the invited student accepts or declines.
Both live in the `requests` table (column `kind`).

Accepting is the delicate part: two owners' browser tabs (or two invitees) could accept at the same
moment for the last open place. Every change runs in one transaction that first locks the project row
(SELECT ... FOR UPDATE), so those transactions take turns and the second one sees the team is full.
Lock order is always: project row first, then request rows.
"""
from __future__ import annotations

from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from ..auth import current_user
from ..db import get_conn
from ..fields import Text
from ..notify import notify
from ..places import member_ids, open_role_names, take_open_place
from ..views import get_visible_project, project_view, request_views

router = APIRouter(tags=["Join Requests & Invitations"])


class JoinIn(BaseModel):
    role: Text(60, 1)
    message: Text(500) = ""


class InviteIn(BaseModel):
    user_id: int
    role: Text(60, 1)


class RespondIn(BaseModel):
    status: Literal["accepted", "rejected"]


def _name(conn: psycopg.Connection, user_id: int) -> str:
    return conn.execute("SELECT name FROM users WHERE id = %s", (user_id,)).fetchone()["name"]


def _pending_kind(conn: psycopg.Connection, project_id: int, user_id: int) -> str | None:
    row = conn.execute("SELECT kind FROM requests WHERE project_id = %s AND user_id = %s AND status = 'pending'",
                       (project_id, user_id)).fetchone()
    return row["kind"] if row else None


# ---------------------------------------------------------------- services (also called directly by tests)
def create_join_request(conn: psycopg.Connection, user: dict, project_id: int, role: str, message: str) -> None:
    with conn.transaction():
        project = get_visible_project(conn, project_id, user, lock=True)
        if project["owner_id"] == user["id"]:
            raise HTTPException(400, "You own this project.")
        if user["id"] in member_ids(conn, project_id):
            raise HTTPException(409, "You're already on this team.")
        status = conn.execute("SELECT status FROM project_summary WHERE project_id = %s", (project_id,)).fetchone()["status"]
        if status != "recruiting":
            raise HTTPException(409, "This team is no longer accepting requests.")
        if role not in open_role_names(conn, project_id):
            raise HTTPException(400, "That role isn't open in this project.")
        pending = _pending_kind(conn, project_id, user["id"])
        if pending == "invitation":
            raise HTTPException(409, "You've already been invited to this project. Check your invitations.")
        if pending:
            raise HTTPException(409, "You already have a pending request for this project.")
        request_id = conn.execute(
            "INSERT INTO requests (project_id, user_id, kind, role, message) VALUES (%s, %s, 'request', %s, %s) RETURNING id",
            (project_id, user["id"], role, message)).fetchone()["id"]
        notify(conn, project["owner_id"], "request", f"{user['name']} requested to join {project['title']} as {role}.",
               request_id)


def create_invitation(conn: psycopg.Connection, owner: dict, project_id: int, invitee_id: int, role: str) -> None:
    with conn.transaction():
        project = get_visible_project(conn, project_id, owner, lock=True)
        if project["owner_id"] != owner["id"]:
            raise HTTPException(403, "Only the project owner can do that.")
        invitee = conn.execute("SELECT * FROM users WHERE id = %s", (invitee_id,)).fetchone()
        if invitee is None:
            raise HTTPException(404, "Student not found.")
        if invitee["status"] != "active":
            raise HTTPException(400, "This student's account is suspended.")
        if not invitee["open_to_projects"]:
            raise HTTPException(400, "This student isn't open to new projects.")
        members = member_ids(conn, project_id)
        if invitee_id in members:
            raise HTTPException(409, "This student is already on the team.")
        if len(members) >= project["max_size"]:
            raise HTTPException(409, "The team is already full.")
        if role not in open_role_names(conn, project_id):
            raise HTTPException(400, "That role isn't open in this project.")
        if _pending_kind(conn, project_id, invitee_id):
            raise HTTPException(409, "This student already has a pending request or invitation for this project.")
        request_id = conn.execute(
            "INSERT INTO requests (project_id, user_id, by_id, kind, role) VALUES (%s, %s, %s, 'invitation', %s) RETURNING id",
            (project_id, invitee_id, owner["id"], role)).fetchone()["id"]
        notify(conn, invitee_id, "invite", f"{owner['name']} invited you to join {project['title']} as {role}.", request_id)


def respond_to_request(conn: psycopg.Connection, user: dict, request_id: int, accept: bool) -> None:
    with conn.transaction():
        found = conn.execute("SELECT project_id FROM requests WHERE id = %s", (request_id,)).fetchone()
        if found is None:
            raise HTTPException(404, "Request not found.")
        project = get_visible_project(conn, found["project_id"], user, lock=True)  # 1) lock the project
        req = conn.execute("SELECT * FROM requests WHERE id = %s FOR UPDATE", (request_id,)).fetchone()  # 2) the request
        if req is None:
            raise HTTPException(404, "Request not found.")
        if req["kind"] == "request" and user["id"] != project["owner_id"]:
            raise HTTPException(403, "Only the project owner can respond to this request.")
        if req["kind"] == "invitation" and user["id"] != req["user_id"]:
            raise HTTPException(403, "Only the invited student can respond to this invitation.")
        if req["status"] != "pending":
            raise HTTPException(409, "This request has already been handled.")
        title, student = project["title"], _name(conn, req["user_id"])

        if not accept:
            conn.execute("UPDATE requests SET status = 'rejected', responded_at = now() WHERE id = %s", (request_id,))
            if req["kind"] == "request":
                notify(conn, req["user_id"], "declined", f"Your request to join {title} was declined.")
            else:
                notify(conn, project["owner_id"], "declined", f"{student} declined your invitation to join {title}.")
        else:
            members = member_ids(conn, project["id"])
            if req["user_id"] in members:
                raise HTTPException(409, "This student is already on the team.")
            if len(members) >= project["max_size"]:
                raise HTTPException(409, "The team is already full.")
            role = take_open_place(conn, project, req["user_id"], req["role"])
            conn.execute("UPDATE requests SET status = 'accepted', responded_at = now() WHERE id = %s", (request_id,))
            if req["kind"] == "request":
                notify(conn, req["user_id"], "accepted", f"Your request to join {title} was accepted. Say hi to your new team!")
            else:
                notify(conn, project["owner_id"], "team", f"{student} accepted your invitation and joined {title} as {role}.")
            for member in members:  # the rest of the team (the owner already knows)
                if member != project["owner_id"]:
                    notify(conn, member, "team", f"{student} joined {title} as {role}.")
            if len(members) + 1 >= project["max_size"]:
                # The team is now full: decline everyone else who is still waiting.
                rejected = conn.execute("""
                    UPDATE requests SET status = 'rejected', responded_at = now()
                    WHERE project_id = %s AND status = 'pending' RETURNING id, user_id, kind""", (project["id"],)).fetchall()
                for r in rejected:
                    if r["kind"] == "request":
                        notify(conn, r["user_id"], "declined", f"Your request to join {title} was declined. The team is now complete.")
                    else:
                        notify(conn, r["user_id"], "declined",
                               f"Your invitation to join {title} was withdrawn because the team is now complete.")
                conn.execute("UPDATE notifications SET unread = false WHERE request_id = ANY(%s)", ([r["id"] for r in rejected],))
        conn.execute("UPDATE notifications SET unread = false WHERE request_id = %s", (request_id,))


def cancel_request(conn: psycopg.Connection, user: dict, request_id: int) -> None:
    with conn.transaction():
        found = conn.execute("SELECT project_id FROM requests WHERE id = %s", (request_id,)).fetchone()
        if found is None:
            raise HTTPException(404, "Request not found.")
        get_visible_project(conn, found["project_id"], user, lock=True)
        req = conn.execute("SELECT * FROM requests WHERE id = %s FOR UPDATE", (request_id,)).fetchone()
        if req is None:
            raise HTTPException(404, "Request not found.")
        if req["kind"] != "request" or req["user_id"] != user["id"]:
            raise HTTPException(403, "Only the student who sent this request can cancel it.")
        if req["status"] != "pending":
            raise HTTPException(409, "Only pending requests can be cancelled.")
        conn.execute("DELETE FROM requests WHERE id = %s", (request_id,))  # its notifications go with it (ON DELETE CASCADE)


# ---------------------------------------------------------------- routes
@router.post("/projects/{project_id}/requests", summary="Ask to join a project")
def request_to_join(project_id: int, body: JoinIn, user: dict = Depends(current_user),
                    conn: psycopg.Connection = Depends(get_conn)):
    create_join_request(conn, user, project_id, body.role, body.message)
    return project_view(conn, user["id"], project_id)


@router.post("/projects/{project_id}/invitations", summary="Invite a student to my project (owner only)")
def invite_student(project_id: int, body: InviteIn, user: dict = Depends(current_user),
                   conn: psycopg.Connection = Depends(get_conn)):
    create_invitation(conn, user, project_id, body.user_id, body.role)
    return {"ok": True}


@router.get("/requests", summary="My join requests and invitations (sent and received)")
def list_requests(user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    rows = conn.execute("""
        SELECT r.id FROM requests r JOIN projects p ON p.id = r.project_id
        WHERE p.removed_at IS NULL AND (r.user_id = %(me)s OR r.by_id = %(me)s OR p.owner_id = %(me)s)
        ORDER BY r.created_at DESC, r.id DESC""", {"me": user["id"]})
    return request_views(conn, user["id"], [r["id"] for r in rows])


@router.patch("/requests/{request_id}", summary="Accept or decline a join request or invitation")
def respond(request_id: int, body: RespondIn, user: dict = Depends(current_user),
            conn: psycopg.Connection = Depends(get_conn)):
    respond_to_request(conn, user, request_id, body.status == "accepted")
    return request_views(conn, user["id"], [request_id])[0]


@router.delete("/requests/{request_id}", status_code=204, summary="Cancel my pending join request")
def cancel(request_id: int, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    cancel_request(conn, user, request_id)
    return Response(status_code=204)
