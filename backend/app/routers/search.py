"""Search & Matching API (Jira: Develop Search and Matching API).

Explore projects with search, filters and sorting; list the filter options; and recommend students
to a project owner. The match score comes from the SQL function match_score(project_id, user_id).
"""
from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg import sql

from ..auth import current_user
from ..db import get_conn
from ..matching import suggest_role
from ..places import open_role_names
from ..views import brief, get_visible_project, project_views

router = APIRouter(tags=["Search & Matching"])

# The only ORDER BY choices. Anything else falls back to "match".
SORTS = {
    "match": sql.SQL("match_score(p.id, %(viewer)s) DESC"),
    "newest": sql.SQL("p.created_at DESC"),
    "spots": sql.SQL("(p.max_size - s.member_count) DESC"),
}

SEARCH = sql.SQL("""
    SELECT p.id
    FROM projects p
    JOIN project_summary s ON s.project_id = p.id
    WHERE p.removed_at IS NULL
      -- text search in the title, the description or any required skill
      AND (%(q)s = '' OR p.title ILIKE %(q_like)s OR p.description ILIKE %(q_like)s
           OR EXISTS (SELECT 1 FROM project_skills ps WHERE ps.project_id = p.id AND ps.name ILIKE %(q_like)s))
      -- the category is one of the chosen ones
      AND (cardinality(%(cats)s::text[]) = 0 OR p.category = ANY(%(cats)s::text[]))
      -- every chosen skill appears (as part of a name) among the project's required skills
      AND NOT EXISTS (SELECT 1 FROM unnest(%(skills)s::text[]) AS wanted(pattern)
                      WHERE NOT EXISTS (SELECT 1 FROM project_skills ps
                                        WHERE ps.project_id = p.id AND ps.name ILIKE wanted.pattern))
      -- the chosen role is still open
      AND (%(role)s = '' OR EXISTS (SELECT 1 FROM project_roles r
                                    WHERE r.project_id = p.id AND r.user_id IS NULL AND r.name = %(role)s))
      AND (NOT %(recruiting)s OR s.status = 'recruiting')
      AND (NOT %(spots)s OR p.max_size - s.member_count >= 2)
    ORDER BY {order}, p.created_at DESC, p.id DESC""")


def _contains(text: str) -> str:
    """An ILIKE pattern matching `text` anywhere, with %, _ and backslash treated as plain characters."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _comma_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


@router.get("/projects", summary="Search, filter and sort projects")
def list_projects(q: str = "", categories: str = "", skills: str = "", role: str = "", recruiting: str = "",
                  spots: str = "", sort: str = "match", user: dict = Depends(current_user),
                  conn: psycopg.Connection = Depends(get_conn)):
    params = {
        "viewer": user["id"], "q": q.strip(), "q_like": _contains(q.strip()), "cats": _comma_list(categories),
        "skills": [_contains(s) for s in _comma_list(skills)], "role": role.strip(),
        "recruiting": recruiting == "true", "spots": spots == "true",
    }
    query = SEARCH.format(order=SORTS.get(sort, SORTS["match"]))
    ids = [row["id"] for row in conn.execute(query, params)]
    return project_views(conn, user["id"], ids)


@router.get("/projects/filters", summary="Options for the Explore filters")
def list_filter_options(user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    categories = conn.execute("""
        SELECT c.name, count(p.id) AS count
        FROM categories c
        LEFT JOIN projects p ON p.category = c.name AND p.removed_at IS NULL
        GROUP BY c.name, c.created_at
        ORDER BY c.created_at, c.name""").fetchall()
    roles = conn.execute("""
        SELECT DISTINCT r.name
        FROM project_roles r JOIN projects p ON p.id = r.project_id
        WHERE r.user_id IS NULL AND p.removed_at IS NULL
        ORDER BY r.name""").fetchall()
    return {"categories": [{"name": c["name"], "count": c["count"]} for c in categories],
            "roles": [r["name"] for r in roles]}


@router.get("/projects/{project_id}/recommendations", summary="Students recommended for my project (owner only)")
def recommendations(project_id: int, user: dict = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)):
    project = get_visible_project(conn, project_id, user)
    if project["owner_id"] != user["id"]:
        raise HTTPException(403, "Only the project owner can do that.")
    open_roles = open_role_names(conn, project_id)
    wanted = {r["name"].lower() for r in conn.execute("SELECT name FROM project_skills WHERE project_id = %s",
                                                       (project_id,))}
    # Active students who are open to projects and not on this team yet, best match first.
    candidates = conn.execute("""
        SELECT u.id, u.name, u.major, u.year, match_score(%(pid)s, u.id) AS match,
               EXISTS (SELECT 1 FROM requests q WHERE q.project_id = %(pid)s AND q.user_id = u.id
                       AND q.kind = 'invitation' AND q.status = 'pending') AS invited
        FROM users u
        WHERE u.status = 'active' AND u.open_to_projects
          AND NOT EXISTS (SELECT 1 FROM project_roles r WHERE r.project_id = %(pid)s AND r.user_id = u.id)
        ORDER BY match DESC, u.name, u.id""", {"pid": project_id}).fetchall()
    skills: dict[int, list[str]] = {}
    for row in conn.execute("SELECT user_id, name FROM user_skills WHERE user_id = ANY(%s) ORDER BY user_id, position",
                            ([c["id"] for c in candidates],)):
        skills.setdefault(row["user_id"], []).append(row["name"])
    results = []
    for c in candidates:
        names = skills.get(c["id"], [])
        fits = suggest_role(open_roles, names)
        if c["match"] > 0 or fits != "—":
            results.append({**brief(c), "match": c["match"], "fits": fits, "invited": c["invited"],
                            "skills": [[name, name.lower() in wanted] for name in names]})
        if len(results) == 50:
            break
    return results
