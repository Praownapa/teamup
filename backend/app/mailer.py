"""Email: write the email for a notification, and send it through Amazon SES (or print it to the log).

notify() (app/notify.py) writes the email next to each in-app notification that has one and queues it.
Once the transaction has committed, the queue comes here and deliver() sends it on a background thread.
So a slow or failing email never delays or breaks the action that caused it: a failure is only logged.
"""
from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.config import Config

from .config import Settings, get_settings

log = logging.getLogger("uvicorn.error")

DEMO_DOMAIN = "student.uni.ac.th"  # the demo students' made-up addresses (backend/seed/demo.sql)

# The email switches on the Account page (users.notify_<key>), with the label students see there.
SWITCH_LABELS = {"requests": "Email for request updates", "invitations": "Email for invitations",
                 "team": "Email for team updates"}

# The page of the website where each kind of notification is dealt with.
LINKS = {"request": "/requests", "invite": "/requests?tab=invitation", "declined": "/requests",
         "accepted": "/teams", "team": "/teams"}

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email")


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


def compose(settings: Settings, name: str, address: str, kind: str, switch: str, subject: str,
            text: str) -> Email | None:
    """The email for one notification, or None if it must not be sent: a made-up demo address with no
    team inbox to send it to instead. Demo addresses are never emailed themselves."""
    note = ""
    if address.lower().endswith("@" + DEMO_DOMAIN):
        if not settings.email_demo_inbox:
            return None
        note = f"Demo copy: TeamUp would send this email to {address}, a made-up demo address.\n\n"
        subject = f"[for {address}] {subject}"
        address = settings.email_demo_inbox
    link = f"Open TeamUp: {settings.app_url}{LINKS.get(kind, '/')}\n\n" if settings.app_url else ""
    body = (f"{note}Hi {name},\n\n{text}\n\n{link}"
            f'You get this email because "{SWITCH_LABELS[switch]}" is on in your TeamUp account settings.\n')
    return Email(address, subject, body)


@lru_cache
def _ses(region: str):
    # Short timeouts and few retries: a stuck SES call mustn't tie up the sending threads for long.
    return boto3.client("sesv2", region_name=region, config=Config(
        connect_timeout=5, read_timeout=10, retries={"max_attempts": 3, "mode": "standard"}))


def send(settings: Settings, email: Email) -> None:
    """Send one email now. Raises if SES refuses it."""
    if settings.email_mode == "ses":
        _ses(settings.email_region).send_email(
            FromEmailAddress=f"TeamUp <{settings.email_from}>",
            Destination={"ToAddresses": [email.to]},
            Content={"Simple": {"Subject": {"Data": email.subject, "Charset": "UTF-8"},
                                "Body": {"Text": {"Data": email.body, "Charset": "UTF-8"}}}})
    elif settings.email_mode == "log":
        log.info("Email (EMAIL_MODE=log, not sent) to %s: %s\n%s", email.to, email.subject, email.body)


def send_all(settings: Settings, emails: list[Email]) -> None:
    """Send each email. One that fails is logged, and the rest still go."""
    for email in emails:
        try:
            send(settings, email)
        except Exception:
            log.exception("Email to %s failed: %s", email.to, email.subject)


def deliver(emails: list[Email]) -> Future | None:
    """Send these emails on a background thread. Only called once the change they describe is saved."""
    if not emails:
        return None
    return _executor.submit(send_all, get_settings(), list(emails))
