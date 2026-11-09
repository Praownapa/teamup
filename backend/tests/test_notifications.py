from app.notify import notify


def test_notifications_are_private_and_markable(db, api):
    a, b = api("a@x.test"), api("b@x.test")
    aid, bid = a.get("/users/me").json()["id"], b.get("/users/me").json()["id"]
    notify(db, aid, "team", "first")
    notify(db, aid, "team", "second")
    notify(db, bid, "team", "theirs")
    mine = a.get("/notifications").json()
    assert [n["text"] for n in mine] == ["second", "first"] and all(n["unread"] for n in mine)
    theirs = b.get("/notifications").json()[0]["id"]
    assert a.post(f"/notifications/{theirs}/read").json() == {"detail": "Notification not found."}
    assert a.post(f"/notifications/{mine[0]['id']}/read").status_code == 204
    assert [n["unread"] for n in a.get("/notifications").json()] == [False, True]
    assert a.post("/notifications/read-all").status_code == 204
    assert a.get("/users/me/counts").json()["unread_notifications"] == 0
    assert b.get("/users/me/counts").json()["unread_notifications"] == 1
