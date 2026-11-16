"""Notifications: the one helper every feature uses to tell someone that something happened, in the app
and, for some events, by email.

Call notify() inside the same transaction as the change it describes, so the notification is saved only if
the change is. Code whose notifications send email starts that transaction with `transaction(conn)` instead
of `conn.transaction()`: it hands the queued emails to the mailer only once the transaction has committed,
so nobody is emailed about a change that was rolled back.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

import psycopg

from . import mailer
from .config import get_settings

_outbox: ContextVar[list | None] = ContextVar("email_outbox", default=None)


@contextmanager
def transaction(conn: psycopg.Connection) -> Iterator[None]:
    """conn.transaction() that also sends the emails notify() queued inside it, after the commit."""
    if _outbox.get() is not None:  # inside another one: the outer transaction sends them
        with conn.transaction():
            yield
        return
    outbox: list[mailer.Email] = []
    token = _outbox.set(outbox)
    try:
        with conn.transaction():
            yield
    finally:
        _outbox.reset(token)
    mailer.deliver(outbox)  # only reached when the transaction committed


def notify(conn: psycopg.Connection, user_id: int, kind: str, text: str, request_id: int | None = None, *,
           email: str | None = None, subject: str = "") -> None:
    """kind is one of: request, invite, accepted, declined, team, match (see the notifications table).

    email names the Account-page switch that covers this message ("requests", "invitations" or "team"):
    if the student has it on, they also get the text by email, with this subject. None = in-app only."""
    conn.execute("INSERT INTO notifications (user_id, kind, text, request_id) VALUES (%s, %s, %s, %s)",
                 (user_id, kind, text, request_id))
    if email is None:
        return
    if email not in mailer.SWITCH_LABELS:
        raise ValueError(f"Unknown email switch: {email}")
    outbox = _outbox.get()
    if outbox is None:
        raise RuntimeError("notify(email=...) must run inside notify.transaction(conn), "
                           "so the email is only sent after the commit.")
    settings = get_settings()
    if settings.email_mode == "off":
        return
    user = conn.execute("SELECT name, email, notify_requests, notify_invitations, notify_team FROM users WHERE id = %s",
                        (user_id,)).fetchone()
    if user is None or not user[f"notify_{email}"]:
        return
    composed = mailer.compose(settings, user["name"], user["email"], kind, email, subject, text)
    if composed is not None:
        outbox.append(composed)
