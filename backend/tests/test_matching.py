from app.matching import suggest_role


def test_suggest_role():
    assert suggest_role(["Backend Developer", "Frontend Developer"], ["React"]) == "Frontend Developer"
    assert suggest_role(["UI/UX Designer"], ["Figma"]) == "UI/UX Designer"
    assert suggest_role(["Data Analyst", "Hardware"], ["Arduino"]) == "Hardware"
    assert suggest_role(["Data Analyst"], ["Figma"]) == "Data Analyst"
    assert suggest_role([], ["React"]) == "—"
