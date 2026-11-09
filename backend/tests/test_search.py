from helpers import make_user, new_project


def ids(response):
    assert response.status_code == 200, response.text
    return [p["id"] for p in response.json()]


def test_search_q_category_skills_role(api):
    o = api("o@x.test")
    a = new_project(o, title="Alpha Bot", category="Competition", skills=["React", "Python"])
    b = new_project(o, title="Beta", description="robotics alpha", skills=["C++"], roles=[{"name": "Hardware", "spots": 1}])
    x = api("x@x.test")
    assert sorted(ids(x.get("/projects", params={"q": "ALPHA"}))) == sorted([a["id"], b["id"]])
    assert ids(x.get("/projects", params={"q": "c++"})) == [b["id"]]
    assert ids(x.get("/projects", params={"categories": "Competition,Research"})) == [a["id"]]
    assert ids(x.get("/projects", params={"skills": "reac,pyth"})) == [a["id"]]
    assert ids(x.get("/projects", params={"role": "Hardware"})) == [b["id"]]


def test_q_is_literal_and_handles_thai(api):
    o = api("o@x.test")
    p1 = new_project(o, title="100% Done")
    new_project(o, title="1000 Done")
    th = new_project(o, title="ระบบจองห้องประชุม")
    x = api("x@x.test")
    assert ids(x.get("/projects", params={"q": "100%"})) == [p1["id"]]
    assert ids(x.get("/projects", params={"q": "_"})) == []
    assert ids(x.get("/projects", params={"q": "จอง"})) == [th["id"]]


def test_recruiting_spots_and_sorts(db, api):
    o = api("o@x.test")
    closed = new_project(o, title="Closed", accepting=False)
    big = new_project(o, title="Big", max_size=6, roles=[{"name": "Dev", "spots": 4}])
    small = new_project(o, title="Small", max_size=2, roles=[{"name": "Dev", "spots": 1}])
    db.execute("UPDATE projects SET created_at = now() - interval '1 day' WHERE id = %s", (big["id"],))
    make_user(db, "x@x.test", skills=["React", "Python"])
    x = api("x@x.test")
    assert closed["id"] not in ids(x.get("/projects", params={"recruiting": "true"}))
    assert small["id"] not in ids(x.get("/projects", params={"spots": "true"}))
    assert ids(x.get("/projects", params={"sort": "spots"}))[0] == big["id"]
    assert ids(x.get("/projects", params={"sort": "newest"}))[-1] == big["id"]
    assert ids(x.get("/projects", params={"sort": "bogus"})) == ids(x.get("/projects"))


def test_filters_endpoint(api):
    o = api("o@x.test")
    new_project(o)
    new_project(o, category="Research", roles=[{"name": "Analyst", "spots": 1}])
    f = api("x@x.test").get("/projects/filters").json()
    assert f["categories"][0] == {"name": "Course Project", "count": 1}
    assert {"name": "Research", "count": 1} in f["categories"] and len(f["categories"]) == 5
    assert f["roles"] == ["Analyst", "Backend Developer", "Frontend Developer"]


def test_recommendations(db, api):
    o = api("o@x.test")
    p = new_project(o)
    fit = make_user(db, "fit@x.test", skills=["React"])
    make_user(db, "away@x.test", skills=["React"], open_to_projects=False)
    make_user(db, "sus@x.test", skills=["React"], status="suspended")
    assert api("x@x.test").get(f"/projects/{p['id']}/recommendations").json()["detail"] == "Only the project owner can do that."
    recs = o.get(f"/projects/{p['id']}/recommendations").json()
    names = [r["name"] for r in recs]
    assert recs[0] == {"id": fit, "name": "fit", "major": "", "year": 1, "match": 50, "fits": "Frontend Developer",
                       "invited": False, "skills": [["React", True]]}
    assert "away" not in names and "sus" not in names and "o" not in names  # unavailable, suspended, on the team
    assert next(r for r in recs if r["name"] == "x")["fits"] == "Frontend Developer"  # no skills: first open role


def test_removed_projects_are_hidden_from_search_and_filters(db, api):
    o = api("o@x.test")
    keep = new_project(o)
    gone = new_project(o, title="Gone", category="Research", roles=[{"name": "Analyst", "spots": 1}])
    db.execute("UPDATE projects SET removed_at = now() WHERE id = %s", (gone["id"],))
    x = api("x@x.test")
    assert ids(x.get("/projects")) == [keep["id"]]
    f = x.get("/projects/filters").json()
    assert {"name": "Research", "count": 0} in f["categories"] and "Analyst" not in f["roles"]
