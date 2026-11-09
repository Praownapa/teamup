from helpers import VALID_PROJECT, make_user, new_project


def test_create_project_returns_full_view(api):
    p = new_project(api("owner@x.test"))
    oid = p["owner"]["id"]
    assert p["owner"] == {"id": oid, "name": "owner", "major": "", "year": 1}
    assert p["my_role"] == "owner" and p["status"] == "recruiting"
    assert [r["name"] for r in p["roles"]] == ["Lead", "Frontend Developer", "Backend Developer"]
    assert p["roles"][1]["user"] is None
    assert p["open_roles"] == ["Frontend Developer", "Backend Developer"]
    assert p["members"] == [{"id": oid, "name": "owner", "major": "", "year": 1, "role": "Lead", "owner": True, "skills": []}]
    assert p["skills"] == [["React", False], ["Python", False]] and p["match"] == 0
    assert (p["duration"], p["meeting"], p["deadline"], p["cover_url"], p["saved"], p["my_request"]) == ("—", "—", "", "", False, None)
    assert (p["pending_requests"], p["pending_invitations"]) == (0, 0)


def test_create_validation(api):
    a = api("o@x.test")
    r = a.post("/projects", json={**VALID_PROJECT, "max_size": 2, "roles": [{"name": "Dev", "spots": 2}]})
    assert r.status_code == 400
    assert r.json()["detail"] == "Your roles need 3 people (including you) but the maximum team size is 2."
    assert a.post("/projects", json={**VALID_PROJECT, "category": "Nope"}).json()["detail"] == "Unknown category."
    for bad in ({"skills": []}, {"title": "x" * 81}, {"max_size": 11}, {"roles": [{"name": "Dev", "spots": 5}]},
                {"deadline": "soon"}):
        assert a.post("/projects", json={**VALID_PROJECT, **bad}).status_code == 422, bad
    assert new_project(a, owner_role="")["roles"][0]["name"] == "Project Owner"


def test_get_project_404_422_and_removed(db, api):
    p = new_project(api("o@x.test"))
    other = api("x@x.test")
    assert other.get("/projects/999").json() == {"detail": "Project not found."}
    assert other.get("/projects/abc").status_code == 422
    db.execute("UPDATE projects SET removed_at = now() WHERE id = %s", (p["id"],))
    assert other.get(f"/projects/{p['id']}").status_code == 404
    make_user(db, "admin@x.test", role="admin")
    assert api("admin@x.test").get(f"/projects/{p['id']}").status_code == 200


def test_patch_is_owner_only_and_updates_status(api):
    o, x = api("o@x.test"), api("x@x.test")
    p = new_project(o)
    assert x.patch(f"/projects/{p['id']}", json={"accepting": False}).json()["detail"] == "Only the project owner can do that."
    assert o.patch(f"/projects/{p['id']}", json={"accepting": False}).json()["status"] == "closed"
    assert o.patch(f"/projects/{p['id']}", json={"title": ""}).status_code == 422


def test_toggle_save(api):
    x = api("x@x.test")
    pid = new_project(api("o@x.test"))["id"]
    assert x.post(f"/projects/{pid}/save").json() == {"saved": True}
    assert x.get(f"/projects/{pid}").json()["saved"] is True
    assert x.post(f"/projects/{pid}/save").json() == {"saved": False}


def test_report_rules(db, api):
    o, x = api("o@x.test"), api("x@x.test")
    pid = new_project(o)["id"]
    assert o.post(f"/projects/{pid}/reports", json={"reason": "Spam / scam"}).json()["detail"] == "You can't report your own project."
    assert x.post(f"/projects/{pid}/reports", json={"reason": "Spam / scam"}).json() == {"ok": True}
    x.post(f"/projects/{pid}/reports", json={"reason": "Misleading info"})
    assert [r["reason"] for r in db.execute("SELECT reason FROM reports WHERE status = 'open'")] == ["Misleading info"]


def test_create_dedupes_skills_case_insensitively(api):
    p = new_project(api("o@x.test"), skills=["React", " react ", "SQL"])
    assert p["skills"] == [["React", False], ["SQL", False]]
