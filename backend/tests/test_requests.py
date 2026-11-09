import threading

from fastapi import HTTPException

from app.db import connect
from app.routers.requests import respond_to_request
from helpers import TEST_DATABASE_URL, make_user, new_project


def _request_id(owner, student_name):
    return next(r["id"] for r in owner.get("/requests").json() if r["student"]["name"] == student_name)


def test_join_flow_and_rules(db, api):
    o, s = api("o@x.test"), api("s@x.test")
    pid = new_project(o)["id"]
    v = s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer", "message": "hi"}).json()
    assert v["my_request"]["role"] == "Frontend Developer" and v["my_request"]["status"] == "pending"
    assert o.get("/notifications").json()[0]["text"] == "s requested to join Test Project as Frontend Developer."
    assert s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}).json()["detail"] == \
        "You already have a pending request for this project."
    assert o.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}).json()["detail"] == "You own this project."
    t = api("t@x.test")
    assert t.post(f"/projects/{pid}/requests", json={"role": "Chef"}).json()["detail"] == "That role isn't open in this project."
    assert t.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer", "message": "x" * 501}).status_code == 422
    o.patch(f"/projects/{pid}", json={"accepting": False})
    assert t.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}).json()["detail"] == \
        "This team is no longer accepting requests."


def test_invitation_rules(db, api):
    o = api("o@x.test")
    pid = new_project(o, accepting=False)["id"]
    i = make_user(db, "i@x.test")
    away = make_user(db, "away@x.test", open_to_projects=False)
    assert api("x@x.test").post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Frontend Developer"}).json()[
        "detail"] == "Only the project owner can do that."
    assert o.post(f"/projects/{pid}/invitations", json={"user_id": away, "role": "Frontend Developer"}).json()["detail"] == \
        "This student isn't open to new projects."
    assert o.post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Frontend Developer"}).json() == {"ok": True}
    assert o.post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Backend Developer"}).json()["detail"] == \
        "This student already has a pending request or invitation for this project."
    assert api("i@x.test").post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}).status_code == 409
    inv = api("i@x.test").get("/notifications").json()[0]
    assert inv["kind"] == "invite" and inv["request_id"]
    assert inv["text"] == "o invited you to join Test Project as Frontend Developer."


def test_list_types_per_viewer(db, api):
    o, s = api("o@x.test"), api("s@x.test")
    pid = new_project(o)["id"]
    i = make_user(db, "i@x.test")
    s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})
    o.post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Backend Developer"})
    assert sorted(r["type"] for r in o.get("/requests").json()) == ["received", "sent"]
    assert [r["type"] for r in s.get("/requests").json()] == ["sent"]
    assert [r["type"] for r in api("i@x.test").get("/requests").json()] == ["invitation"]
    inv = api("i@x.test").get("/requests").json()[0]
    assert inv["by"]["id"] == o.get("/users/me").json()["id"] and inv["project"]["open_spots"] == 3


def test_accept_and_reject_permissions_and_notifications(db, api):
    o, s, t = api("o@x.test"), api("s@x.test"), api("t@x.test")
    pid = new_project(o)["id"]
    s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})
    t.post(f"/projects/{pid}/requests", json={"role": "Backend Developer"})
    rs, rt = _request_id(o, "s"), _request_id(o, "t")
    assert s.patch(f"/requests/{rs}", json={"status": "accepted"}).json()["detail"] == \
        "Only the project owner can respond to this request."
    assert o.patch(f"/requests/{rs}", json={"status": "accepted"}).json()["status"] == "accepted"
    assert o.get(f"/projects/{pid}").json()["open_roles"] == ["Backend Developer"]
    assert s.get("/notifications").json()[0]["text"] == "Your request to join Test Project was accepted. Say hi to your new team!"
    o.patch(f"/requests/{rt}", json={"status": "rejected"})
    assert t.get("/notifications").json()[0]["kind"] == "declined"


def test_stale_actions_are_readable(api):
    o, s = api("o@x.test"), api("s@x.test")
    pid = new_project(o)["id"]
    s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})
    rid = s.get("/requests").json()[0]["id"]
    assert o.get("/notifications").json()[0]["request_id"] == rid
    assert o.delete(f"/requests/{rid}").json()["detail"] == "Only the student who sent this request can cancel it."
    assert s.delete(f"/requests/{rid}").status_code == 204 and o.get("/notifications").json() == []  # cascade removed it
    assert o.patch(f"/requests/{rid}", json={"status": "accepted"}).json() == {"detail": "Request not found."}
    s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})
    rid = s.get("/requests").json()[0]["id"]
    o.patch(f"/requests/{rid}", json={"status": "accepted"})
    assert o.patch(f"/requests/{rid}", json={"status": "rejected"}).json()["detail"] == "This request has already been handled."
    assert s.delete(f"/requests/{rid}").json()["detail"] == "Only pending requests can be cancelled."


def test_filling_team_rejects_the_rest(db, api):
    o = api("o@x.test")
    pid = new_project(o, max_size=2, roles=[{"name": "Dev", "spots": 1}])["id"]
    i = make_user(db, "i@x.test")
    api("a@x.test").post(f"/projects/{pid}/requests", json={"role": "Dev"})
    api("b@x.test").post(f"/projects/{pid}/requests", json={"role": "Dev"})
    o.post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Dev"})
    ra = _request_id(o, "a")
    o.patch(f"/requests/{ra}", json={"status": "accepted"})
    assert o.get(f"/projects/{pid}").json()["status"] == "full"
    assert {r["status"] for r in o.get("/requests").json() if r["id"] != ra} == {"rejected"}
    assert api("b@x.test").get("/notifications").json()[0]["text"] == \
        "Your request to join Test Project was declined. The team is now complete."
    assert api("i@x.test").get("/notifications").json()[0]["text"] == \
        "Your invitation to join Test Project was withdrawn because the team is now complete."


def test_taken_role_adds_place_only_with_capacity(api):
    o = api("o@x.test")
    roomy = new_project(o, max_size=4, roles=[{"name": "Dev", "spots": 1}])["id"]
    tight = new_project(o, title="Tight", max_size=3, roles=[{"name": "Dev", "spots": 1}, {"name": "QA", "spots": 1}])["id"]
    for pid in (roomy, tight):
        for n in ("a", "b"):
            api(f"{n}{pid}@x.test").post(f"/projects/{pid}/requests", json={"role": "Dev"})

    def accept_all(pid):
        pending = [r for r in o.get("/requests").json() if r["project"]["id"] == pid and r["status"] == "pending"]
        return [o.patch(f"/requests/{r['id']}", json={"status": "accepted"}) for r in pending]

    assert [r.status_code for r in accept_all(roomy)] == [200, 200]
    assert len(o.get(f"/projects/{roomy}").json()["members"]) == 3
    res = accept_all(tight)
    assert sorted(r.status_code for r in res) == [200, 409]
    assert "That role has already been filled." in [r.json().get("detail") for r in res]


def test_two_acceptances_for_last_place_produce_one_member(db, api):
    o = api("o@x.test")
    pid = new_project(o, max_size=2, roles=[{"name": "Dev", "spots": 1}])["id"]
    for n in ("a", "b"):
        api(f"{n}@x.test").post(f"/projects/{pid}/requests", json={"role": "Dev"})
    owner = db.execute("SELECT * FROM users WHERE email = 'o@x.test'").fetchone()
    rids = [r["id"] for r in o.get("/requests").json()]
    results, barrier = [], threading.Barrier(2)

    def go(rid):
        with connect(TEST_DATABASE_URL) as c:
            barrier.wait()
            try:
                respond_to_request(c, owner, rid, True)
                results.append("ok")
            except HTTPException as e:
                results.append(e.status_code)

    threads = [threading.Thread(target=go, args=(r,)) for r in rids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(map(str, results)) == ["409", "ok"]
    assert db.execute("SELECT member_count FROM project_summary WHERE project_id = %s", (pid,)).fetchone()["member_count"] == 2
