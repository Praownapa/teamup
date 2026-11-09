from app.notify import notify
from helpers import make_user, new_project


def test_me_view_defaults(api):
    me = api("me@x.test").get("/users/me").json()
    assert (me["role"], me["status"], me["year"], me["skills"], me["interests"], me["teams"]) == (
        "student", "active", 1, [], [], [])
    assert me["notify"] == {"invitations": True, "requests": True, "team": True, "digest": False}
    assert me["stats"] == {"teams": 0, "projects": 0, "skills": 0}


def test_put_me_is_partial_and_ignores_privileged_fields(api):
    a = api("me@x.test")
    a.put("/users/me", json={"bio": "Hi"})
    me = a.put("/users/me", json={"name": "New Name", "role": "admin", "status": "suspended", "email": "z@z.z",
                                   "student_id": "1"}).json()
    assert (me["bio"], me["name"], me["role"], me["status"], me["email"]) == ("Hi", "New Name", "student", "active", "me@x.test")
    assert a.put("/users/me", json={"notify": {"requests": False}}).json()["notify"] == {
        "invitations": True, "requests": False, "team": True, "digest": False}


def test_put_me_dedupes_skills_case_insensitively(api):
    me = api("me@x.test").put("/users/me", json={
        "skills": [{"name": " React ", "level": "Advanced"}, {"name": "react", "level": "Beginner"},
                   {"name": "SQL", "level": "Beginner"}],
        "interests": ["AI", "ai", "IoT"]}).json()
    assert me["skills"] == [{"name": "React", "level": "Advanced"}, {"name": "SQL", "level": "Beginner"}]
    assert me["interests"] == ["AI", "IoT"]


def test_put_me_validates(api):
    a = api("me@x.test")
    for bad in ({"year": 7}, {"skills": [{"name": "X", "level": "Expert"}]}, {"bio": "x" * 401}, {"name": ""}):
        assert a.put("/users/me", json=bad).status_code == 422, bad


def test_public_profile_teams_and_stats(api):
    o = api("o@x.test")
    p = new_project(o)
    me = o.get("/users/me").json()
    assert me["teams"] == [{"id": p["id"], "title": "Test Project", "is_owner": True, "status": "recruiting"}]
    assert me["stats"] == {"teams": 1, "projects": 1, "skills": 0}
    pub = api("x@x.test").get(f"/users/{me['id']}").json()
    assert set(pub) == {"id", "name", "major", "year", "bio", "skills", "interests", "teams"}
    assert pub["teams"] == [{"id": p["id"], "title": "Test Project"}]
    assert api("x@x.test").get("/users/999").json() == {"detail": "Student not found."}


def test_counts_and_dashboard(db, api):
    o = api("o@x.test")
    mine = new_project(o)
    o_id = mine["owner"]["id"]
    b = make_user(db, "b@x.test", skills=["React", "Python"])
    other = new_project(api("b@x.test"), title="Other")
    db.execute("INSERT INTO requests (project_id, user_id, kind, role) VALUES (%s, %s, 'request', 'Frontend Developer')",
               (mine["id"], b))
    db.execute("INSERT INTO requests (project_id, user_id, by_id, kind, role) "
               "VALUES (%s, %s, %s, 'invitation', 'Frontend Developer')", (other["id"], o_id, b))
    for i in range(5):
        notify(db, o_id, "team", f"n{i}")
    assert o.get("/users/me/counts").json() == {"pending_requests": 2, "unread_notifications": 5}
    d = o.get("/users/me/dashboard").json()
    assert d["stats"] == {"teams": 1, "pending": 1, "invitations": 1, "matches": 0, "unread": 5}
    assert [p["id"] for p in d["recommended"]] == [other["id"]]
    assert [p["id"] for p in d["my_teams"]] == [mine["id"]]
    assert [n["text"] for n in d["activity"]] == ["n4", "n3", "n2", "n1"]
