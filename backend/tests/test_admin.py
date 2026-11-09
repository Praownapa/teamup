from helpers import add_member, make_user, new_project


def test_admin_routes_require_admin(api):
    s = api("s@x.test")
    for r in (s.get("/admin/overview"), s.patch("/admin/reports/1", json={"status": "dismissed"}),
              s.patch("/admin/users/1", json={"status": "active"}), s.post("/admin/categories", json={"name": "X"}),
              s.delete("/admin/categories/X")):
        assert r.status_code == 403 and r.json()["detail"] == "Admin access required."


def test_overview_counts_and_buckets(db, api):
    make_user(db, "admin@x.test", role="admin")
    ad, o = api("admin@x.test"), api("o@x.test")
    pid = new_project(o)["id"]
    add_member(o, api("m@x.test"), pid, "Frontend Developer")
    for period, n, first in (("7d", 7, None), ("30d", 5, "W1"), ("semester", 16, "W1")):
        d = ad.get("/admin/overview", params={"period": period}).json()
        assert len(d["activity"]) == n
        if first:
            assert d["activity"][0]["week"] == first
    d = ad.get("/admin/overview").json()
    assert {k: d["stats"][k] for k in ("students", "projects", "teams", "reports")} == {
        "students": 3, "projects": 1, "teams": 1, "reports": 0}
    assert d["stats"]["deltas"] == {"students": 3, "projects": 1, "teams": 1}
    assert sum(a["requests"] for a in d["activity"]) == 1 and sum(a["projects"] for a in d["activity"]) == 1
    assert next(u for u in d["users"] if u["email"] == "m@x.test")["projects"] == 1
    assert ad.get("/admin/overview", params={"period": "year"}).status_code == 422


def test_remove_report_hides_project_and_notifies(db, api):
    make_user(db, "admin@x.test", role="admin")
    ad, o = api("admin@x.test"), api("o@x.test")
    pid = new_project(o)["id"]
    api("r1@x.test").post(f"/projects/{pid}/reports", json={"reason": "Spam / scam"})
    api("r2@x.test").post(f"/projects/{pid}/reports", json={"reason": "Misleading info"})
    api("s@x.test").post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})
    rep = ad.get("/admin/overview").json()["reports"]
    assert len(rep) == 1 and (rep[0]["reporters"], rep[0]["reason"], rep[0]["owner"], rep[0]["project"]) == (
        2, "Misleading info", "o", "Test Project")
    assert ad.patch(f"/admin/reports/{rep[0]['id']}", json={"status": "removed"}).status_code == 204
    assert api("x@x.test").get(f"/projects/{pid}").status_code == 404
    assert o.get("/notifications").json()[0]["text"] == "Your project Test Project was removed by an administrator."
    assert api("s@x.test").get("/requests").json() == [] and ad.get("/admin/overview").json()["reports"] == []
    assert ad.patch(f"/admin/reports/{rep[0]['id']}", json={"status": "dismissed"}).json()["detail"] == \
        "This report has already been handled."
    assert ad.patch("/admin/reports/999", json={"status": "dismissed"}).json()["detail"] == "Report not found."


def test_dismissing_a_report_keeps_the_project(db, api):
    make_user(db, "admin@x.test", role="admin")
    ad = api("admin@x.test")
    pid = new_project(api("o@x.test"))["id"]
    api("r1@x.test").post(f"/projects/{pid}/reports", json={"reason": "Spam / scam"})
    rid = ad.get("/admin/overview").json()["reports"][0]["id"]
    assert ad.patch(f"/admin/reports/{rid}", json={"status": "dismissed"}).status_code == 204
    assert api("x@x.test").get(f"/projects/{pid}").status_code == 200
    assert ad.get("/admin/overview").json()["reports"] == []


def test_user_status_rules(db, api):
    aid = make_user(db, "admin@x.test", role="admin")
    ad = api("admin@x.test")
    sid = api("s@x.test").get("/users/me").json()["id"]
    assert ad.patch(f"/admin/users/{sid}", json={"status": "suspended"}).status_code == 204
    assert api("s@x.test").get("/users/me").status_code == 403
    assert ad.patch(f"/admin/users/{aid}", json={"status": "suspended"}).json()["detail"] == "You can't change your own status."
    other_admin = make_user(db, "admin2@x.test", role="admin")
    assert ad.patch(f"/admin/users/{other_admin}", json={"status": "suspended"}).json()["detail"] == \
        "Administrators can't be suspended."
    assert ad.patch("/admin/users/999", json={"status": "active"}).json()["detail"] == "Student not found."
    assert ad.patch(f"/admin/users/{sid}", json={"status": "active"}).status_code == 204
    assert api("s@x.test").get("/users/me").status_code == 200


def test_categories(api, db):
    make_user(db, "admin@x.test", role="admin")
    ad = api("admin@x.test")
    new_project(api("o@x.test"), category="Research")
    assert ad.post("/admin/categories", json={"name": "Hackathon"}).status_code == 204
    assert ad.post("/admin/categories", json={"name": "hackathon"}).status_code == 204
    names = [c["name"] for c in ad.get("/projects/filters").json()["categories"]]
    assert names[-1] == "Hackathon" and names.count("Hackathon") == 1
    assert ad.delete("/admin/categories/Research").status_code == 204
    assert "Research" not in [c["name"] for c in ad.get("/projects/filters").json()["categories"]]
    assert ad.get("/projects").json()[0]["category"] == "Research"
    assert ad.post("/admin/categories", json={"name": "UI/UX"}).status_code == 204
    assert ad.delete("/admin/categories/UI%2FUX").status_code == 204
    assert "UI/UX" not in [c["name"] for c in ad.get("/projects/filters").json()["categories"]]
