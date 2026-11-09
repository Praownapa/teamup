"""Team places. Every project has one project_roles row per place in its team; user_id NULL means open.

Callers that change places do so inside a transaction that has already locked the project row
(see get_visible_project(..., lock=True)), so two requests can never fill the same place.
"""
import psycopg
from fastapi import HTTPException


def take_open_place(conn: psycopg.Connection, project: dict, user_id: int, role: str) -> str:
    """Put the user in the first open place named `role`. If none is open but the project has fewer
    places than max_size, add a place with that name. Returns the role name taken; 409 if impossible."""
    row = conn.execute("""
        UPDATE project_roles SET user_id = %(uid)s
        WHERE id = (SELECT id FROM project_roles
                    WHERE project_id = %(pid)s AND user_id IS NULL AND name = %(role)s
                    ORDER BY position, id LIMIT 1)
        RETURNING name""", {"uid": user_id, "pid": project["id"], "role": role}).fetchone()
    if row:
        return row["name"]
    places = conn.execute("SELECT count(*) AS n, coalesce(max(position), -1) AS last FROM project_roles WHERE project_id = %s",
                          (project["id"],)).fetchone()
    if places["n"] < project["max_size"]:
        conn.execute("INSERT INTO project_roles (project_id, name, user_id, position) VALUES (%s, %s, %s, %s)",
                     (project["id"], role, user_id, places["last"] + 1))
        return role
    raise HTTPException(409, "That role has already been filled.")


def free_place(conn: psycopg.Connection, project_id: int, user_id: int) -> None:
    conn.execute("UPDATE project_roles SET user_id = NULL WHERE project_id = %s AND user_id = %s", (project_id, user_id))


def member_ids(conn: psycopg.Connection, project_id: int) -> list[int]:
    return [r["user_id"] for r in conn.execute(
        "SELECT user_id FROM project_roles WHERE project_id = %s AND user_id IS NOT NULL ORDER BY position, id",
        (project_id,))]


def open_role_names(conn: psycopg.Connection, project_id: int) -> list[str]:
    """Distinct names of the open places, in the order they first appear."""
    rows = conn.execute("SELECT name FROM project_roles WHERE project_id = %s AND user_id IS NULL ORDER BY position, id",
                        (project_id,))
    return list(dict.fromkeys(r["name"] for r in rows))
