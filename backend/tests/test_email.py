"""Email notifications for the five events in the requirements: who gets which email, the email switches
on the Account page, the demo students' made-up addresses, and that nothing is sent for a change that
wasn't saved. Emails are captured where they're handed to the mailer, which happens after the commit."""
from dataclasses import replace

import pytest
from psycopg import sql

import app.mailer as mailer
import app.notify as notify
from app.config import get_settings
from app.mailer import Email
from helpers import make_user, new_project

TEAM_INBOX = "team.inbox@example.com"
SITE = "https://teamup.example"
LABELS = {"requests": "Email for request updates", "invitations": "Email for invitations",
          "team": "Email for team updates"}


@pytest.fixture
def sent(monkeypatch):
    """Emails handed to the mailer (captured instead of sent), with email switched on as in AWS."""
    captured: list[Email] = []
    monkeypatch.setattr(mailer, "deliver", captured.extend)
    monkeypatch.setattr(notify, "get_settings", lambda: replace(
        get_settings(), email_mode="ses", email_from=TEAM_INBOX, email_region="ap-northeast-1",
        email_demo_inbox=TEAM_INBOX, app_url=SITE))
    return captured


def _received(owner, student_name):
    return next(r["id"] for r in owner.get("/requests").json() if r["student"]["name"] == student_name)


def _invitation(student):
    (invitation,) = [r for r in student.get("/requests").json() if r["type"] == "invitation"]
    return invitation["id"]


def _five_events(db, api, switched_off=None):
    """The five events from the requirements, in order: one email each, unless a switch is off."""
    owner, sam = api("owner@x.test"), api("sam@x.test")
    pid = new_project(owner)["id"]
    sam_id = sam.get("/users/me").json()["id"]
    ivy_id = make_user(db, "ivy@x.test")
    if switched_off:
        db.execute(sql.SQL("UPDATE users SET {} = false").format(sql.Identifier(f"notify_{switched_off}")))
    sam.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})                         # 1
    owner.patch(f"/requests/{_received(owner, 'sam')}", json={"status": "accepted"})                  # 2
    owner.post(f"/projects/{pid}/invitations", json={"user_id": ivy_id, "role": "Backend Developer"})  # 3
    ivy = api("ivy@x.test")
    ivy.patch(f"/requests/{_invitation(ivy)}", json={"status": "rejected"})                           # 4
    owner.delete(f"/projects/{pid}/members/{sam_id}")                                                 # 5


def test_each_of_the_five_events_sends_one_email(db, api, sent):
    _five_events(db, api)
    assert [(e.to, e.subject) for e in sent] == [
        ("owner@x.test", "New join request for Test Project"),              # 1. join request -> the owner
        ("sam@x.test", "Your request to join Test Project was accepted"),  # 2. owner answers -> the student
        ("ivy@x.test", "owner invited you to join Test Project"),          # 3. invitation -> the student
        ("owner@x.test", "ivy declined your invitation to Test Project"),  # 4. student answers -> the owner
        ("sam@x.test", "You were removed from Test Project"),              # 5. removed -> the member
    ]
    links = [e.body.split("Open TeamUp: ")[1].split("\n")[0] for e in sent]
    assert links == [f"{SITE}/requests", f"{SITE}/teams", f"{SITE}/requests?tab=invitation", f"{SITE}/requests",
                     f"{SITE}/teams"]
    switches = [key for e in sent for key, label in LABELS.items() if f'"{label}"' in e.body]
    assert switches == ["requests", "requests", "invitations", "invitations", "team"]


def test_email_text(api, sent):
    owner, sam = api("owner@x.test"), api("sam@x.test")
    pid = new_project(owner)["id"]
    sam.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer", "message": "Hi!"})
    assert sent == [Email(
        to="owner@x.test",
        subject="New join request for Test Project",
        body=("Hi owner,\n\n"
              "sam requested to join Test Project as Frontend Developer.\n\n"
              f"Open TeamUp: {SITE}/requests\n\n"
              'You get this email because "Email for request updates" is on in your TeamUp account settings.\n'))]


def test_the_other_answers_are_emailed_too(db, api, sent):
    owner, sam = api("owner@x.test"), api("sam@x.test")
    pid = new_project(owner)["id"]
    ivy_id = make_user(db, "ivy@x.test")
    sam.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})
    owner.post(f"/projects/{pid}/invitations", json={"user_id": ivy_id, "role": "Backend Developer"})
    sent.clear()
    owner.patch(f"/requests/{_received(owner, 'sam')}", json={"status": "rejected"})
    ivy = api("ivy@x.test")
    ivy.patch(f"/requests/{_invitation(ivy)}", json={"status": "accepted"})
    assert [(e.to, e.subject) for e in sent] == [
        ("sam@x.test", "Your request to join Test Project was declined"),
        ("owner@x.test", "ivy accepted your invitation to Test Project")]
    assert "ivy accepted your invitation and joined Test Project as Backend Developer." in sent[1].body


def test_students_declined_because_the_team_filled_up_get_an_email(api, sent):
    owner, sam, tia = api("owner@x.test"), api("sam@x.test"), api("tia@x.test")
    pid = new_project(owner, max_size=2, roles=[{"name": "Dev", "spots": 1}])["id"]
    sam.post(f"/projects/{pid}/requests", json={"role": "Dev"})
    tia.post(f"/projects/{pid}/requests", json={"role": "Dev"})
    sent.clear()
    owner.patch(f"/requests/{_received(owner, 'sam')}", json={"status": "accepted"})
    assert [(e.to, e.subject) for e in sent] == [
        ("sam@x.test", "Your request to join Test Project was accepted"),
        ("tia@x.test", "Your request to join Test Project was declined")]
    assert "Your request to join Test Project was declined. The team is now complete." in sent[1].body


@pytest.mark.parametrize("switch", ["requests", "invitations", "team"])
def test_each_switch_turns_off_only_its_own_emails(db, api, sent, switch):
    _five_events(db, api, switched_off=switch)
    assert len(sent) == {"requests": 3, "invitations": 3, "team": 4}[switch]
    assert not any(LABELS[switch] in e.body for e in sent)
    assert len(api("owner@x.test").get("/notifications").json()) == 2  # the in-app notifications still arrive


def test_demo_students_emails_go_to_the_team_inbox(api, sent, monkeypatch):
    owner, sam = api("john.carter@student.uni.ac.th"), api("sam@x.test")
    pid = new_project(owner)["id"]
    sam.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})
    (email,) = sent
    assert email.to == TEAM_INBOX
    assert email.subject == "[for john.carter@student.uni.ac.th] New join request for Test Project"
    assert email.body.startswith("Demo copy: TeamUp would send this email to john.carter@student.uni.ac.th, "
                                 "a made-up demo address.\n\nHi john.carter,\n\n")
    # Without a team inbox, the made-up addresses are never emailed at all.
    monkeypatch.setattr(notify, "get_settings", lambda: replace(
        get_settings(), email_mode="ses", email_from=TEAM_INBOX, email_region="ap-northeast-1", app_url=SITE))
    sent.clear()
    api("tia@x.test").post(f"/projects/{pid}/requests", json={"role": "Backend Developer"})
    assert sent == []


def test_nothing_is_sent_for_a_change_that_was_rolled_back(db, sent):
    sam = make_user(db, "sam@x.test")
    with pytest.raises(RuntimeError, match="the change failed"):
        with notify.transaction(db):
            notify.notify(db, sam, "team", "Something happened.", email="team", subject="Something happened")
            raise RuntimeError("the change failed")
    assert sent == []
    assert db.execute("SELECT count(*) AS n FROM notifications").fetchone()["n"] == 0
    with notify.transaction(db):
        notify.notify(db, sam, "team", "Something happened.", email="team", subject="Something happened")
    assert [e.to for e in sent] == ["sam@x.test"]


def test_an_inner_transaction_leaves_sending_to_the_outer_one(db, sent):
    sam = make_user(db, "sam@x.test")
    with notify.transaction(db):
        with notify.transaction(db):
            notify.notify(db, sam, "team", "One.", email="team", subject="One")
        assert sent == []  # not yet: the outer transaction could still roll back
    assert [e.subject for e in sent] == ["One"]


def test_email_needs_the_transaction_helper(db, sent):
    sam = make_user(db, "sam@x.test")
    with pytest.raises(RuntimeError, match="notify.transaction"):
        with db.transaction():
            notify.notify(db, sam, "team", "x", email="team", subject="x")
    with pytest.raises(ValueError):
        with notify.transaction(db):
            notify.notify(db, sam, "team", "x", email="digest", subject="x")  # not an event switch


def test_no_emails_when_email_is_off(db, api, sent, monkeypatch):
    monkeypatch.setattr(notify, "get_settings", lambda: replace(get_settings(), email_mode="off"))
    _five_events(db, api)
    assert sent == []
