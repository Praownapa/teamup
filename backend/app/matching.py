"""Matching helpers. (The match *score* lives in the database: see match_score() in migrations/001_init.sql.)"""
import re

# Which open role does a student fit? (role-name pattern, skill pattern) pairs, checked case-insensitively.
FIT_RULES: list[tuple[str, str]] = [
    (r"front", r"react|javascript|vue|typescript|css|html"),
    (r"back", r"python|fastapi|node|sql|postgres|java|django"),
    (r"ui|ux|design", r"figma|ui|ux|design"),
    (r"cloud|devops", r"aws|docker|linux|kubernetes|cloud"),
    (r"data", r"python|pandas|sql|d3|analysis|machine learning"),
    (r"mobile", r"flutter|react native|swift|kotlin|firebase"),
    (r"\bml\b|machine|\bai\b", r"python|machine learning|nlp|pytorch|tensorflow"),
    (r"qa|test", r"pytest|test|selenium|qa"),
    (r"iot|hardware|robot", r"arduino|c\+\+|iot|cad"),
]


def suggest_role(open_roles: list[str], skills: list[str]) -> str:
    """The first open role the student's skills fit, else the first open role, else '—' (no open roles)."""
    for role in open_roles:
        for role_pattern, skill_pattern in FIT_RULES:
            if re.search(role_pattern, role, re.I) and any(re.search(skill_pattern, s, re.I) for s in skills):
                return role
    return open_roles[0] if open_roles else "—"
