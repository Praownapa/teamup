"""Team places. Every project has one project_roles row per place in its team; user_id NULL means open."""
import psycopg


def member_ids(conn: psycopg.Connection, project_id: int) -> list[int]:
    return [r["user_id"] for r in conn.execute(
        "SELECT user_id FROM project_roles WHERE project_id = %s AND user_id IS NOT NULL ORDER BY position, id",
        (project_id,))]


def open_role_names(conn: psycopg.Connection, project_id: int) -> list[str]:
    """Distinct names of the open places, in the order they first appear."""
    rows = conn.execute("SELECT name FROM project_roles WHERE project_id = %s AND user_id IS NULL ORDER BY position, id",
                        (project_id,))
    return list(dict.fromkeys(r["name"] for r in rows))
