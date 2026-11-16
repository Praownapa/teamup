"""Sending email: the SES call, the log mode, a failing email, and delivery on a background thread."""
import logging
from dataclasses import replace

import app.mailer as mailer
from app.config import Settings
from app.mailer import Email

SES = Settings(auth_mode="dev", email_mode="ses", email_from="team.inbox@example.com", email_region="ap-northeast-1")
EMAIL = Email(to="sam@x.test", subject="Hello", body="Hi sam,\n\nHello.\n")


class FakeSes:
    """Stands in for the boto3 SES client; refuses the addresses in `fail_for` like an unverified address."""

    def __init__(self, fail_for=()):
        self.calls, self.fail_for = [], set(fail_for)

    def send_email(self, **kwargs):
        if kwargs["Destination"]["ToAddresses"][0] in self.fail_for:
            raise RuntimeError("MessageRejected: Email address is not verified.")
        self.calls.append(kwargs)
        return {"MessageId": "test-message"}


def test_ses_send_call(monkeypatch):
    fake = FakeSes()
    monkeypatch.setattr(mailer, "_ses", lambda region: fake)
    mailer.send(SES, EMAIL)
    assert fake.calls == [{
        "FromEmailAddress": "TeamUp <team.inbox@example.com>",
        "Destination": {"ToAddresses": ["sam@x.test"]},
        "Content": {"Simple": {"Subject": {"Data": "Hello", "Charset": "UTF-8"},
                               "Body": {"Text": {"Data": "Hi sam,\n\nHello.\n", "Charset": "UTF-8"}}}},
    }]


def test_log_mode_only_logs(monkeypatch, caplog):
    def no_ses(region):
        raise AssertionError("log mode must not call SES")
    monkeypatch.setattr(mailer, "_ses", no_ses)
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        mailer.send(replace(SES, email_mode="log"), EMAIL)
    assert "sam@x.test" in caplog.text and "Hello" in caplog.text


def test_a_failed_email_is_logged_and_the_others_still_go(monkeypatch, caplog):
    fake = FakeSes(fail_for={"bad@x.test"})
    monkeypatch.setattr(mailer, "_ses", lambda region: fake)
    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        mailer.send_all(SES, [replace(EMAIL, to="bad@x.test"), EMAIL])  # must not raise
    assert [c["Destination"]["ToAddresses"] for c in fake.calls] == [["sam@x.test"]]
    assert "Email to bad@x.test failed" in caplog.text


def test_deliver_sends_on_a_background_thread(monkeypatch):
    fake = FakeSes()
    monkeypatch.setattr(mailer, "_ses", lambda region: fake)
    monkeypatch.setattr(mailer, "get_settings", lambda: SES)
    assert mailer.deliver([]) is None  # nothing to send, no thread work
    mailer.deliver([EMAIL]).result(timeout=10)
    assert len(fake.calls) == 1
