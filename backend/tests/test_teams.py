from helpers import add_member, new_project


def _id(api_user):
    return api_user.get("/users/me").json()["id"]


def test_change_role_moves_or_renames(api):
    o, m = api("o@x.test"), api("m@x.test")
    pid = new_project(o)["id"]
    add_member(o, m, pid, "Frontend Developer")
    mid = _id(m)
    v = o.patch(f"/projects/{pid}/members/{mid}", json={"role": "Backend Developer"}).json()
    assert next(x["role"] for x in v["members"] if x["id"] == mid) == "Backend Developer"
    assert v["open_roles"] == ["Frontend Developer"]
    v = o.patch(f"/projects/{pid}/members/{mid}", json={"role": "Tech Lead"}).json()
    assert [r["name"] for r in v["roles"]] == ["Lead", "Frontend Developer", "Tech Lead"]
    assert m.get("/notifications").json()[0]["text"] == "Your role in Test Project is now Tech Lead."


def test_member_endpoint_rules(api):
    o, m = api("o@x.test"), api("m@x.test")
    pid = new_project(o)["id"]
    add_member(o, m, pid, "Frontend Developer")
    oid, mid = _id(o), _id(m)
    assert m.patch(f"/projects/{pid}/members/{mid}", json={"role": "X"}).json()["detail"] == "Only the project owner can do that."
    assert o.patch(f"/projects/{pid}/members/{oid}", json={"role": "X"}).json()["detail"] == "The owner's role can't be changed here."
    assert o.delete(f"/projects/{pid}/members/{oid}").json()["detail"] == "The owner can't be removed from their own project."
    assert o.delete(f"/projects/{pid}/members/999").json()["detail"] == "That student isn't on this team."


def test_remove_member_returns_view_and_notifies(api):
    o, m = api("o@x.test"), api("m@x.test")
    pid = new_project(o)["id"]
    add_member(o, m, pid, "Frontend Developer")
    r = o.delete(f"/projects/{pid}/members/{_id(m)}")
    assert r.status_code == 200 and [x["id"] for x in r.json()["members"]] == [_id(o)]
    assert m.get("/notifications").json()[0]["text"] == "You were removed from Test Project."


def test_members_me_route_not_shadowed_and_leave_rules(api):
    o, m = api("o@x.test"), api("m@x.test")
    pid = new_project(o)["id"]
    add_member(o, m, pid, "Frontend Developer")
    assert o.delete(f"/projects/{pid}/members/me").json()["detail"] == "Owners can't leave their own project."
    assert api("x@x.test").delete(f"/projects/{pid}/members/me").json()["detail"] == "You're not on this team."
    assert m.delete(f"/projects/{pid}/members/me").status_code == 204
    assert o.get("/notifications").json()[0]["text"] == "m left Test Project."
    assert m.get(f"/projects/{pid}").json()["my_role"] is None
