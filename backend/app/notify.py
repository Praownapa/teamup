"""In-app notifications: the one helper every feature uses to tell someone that something happened.

Call it inside the same transaction as the change it describes, so the notification is saved
only if the change is.
"""
import psycopg


def notify(conn: psycopg.Connection, user_id: int, kind: str, text: str, request_id: int | None = None) -> None:
    """kind is one of: request, invite, accepted, declined, team, match (see the notifications table)."""
    conn.execute("INSERT INTO notifications (user_id, kind, text, request_id) VALUES (%s, %s, %s, %s)",
                 (user_id, kind, text, request_id))
