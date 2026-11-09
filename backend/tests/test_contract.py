"""Every key the frontend's example responses contain must also be in the real responses."""
import json
from pathlib import Path

import pytest

from app.db import seed_demo

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = json.loads((REPO_ROOT / "docs" / "RESPONSE-EXAMPLES.json").read_text(encoding="utf-8"))
CALLS = {
    "getMe": "/users/me", "getCounts": "/users/me/counts", "getDashboard": "/users/me/dashboard",
    "listProjects": "/projects", "listFilterOptions": "/projects/filters", "listRequests": "/requests",
    "listNotifications": "/notifications", "adminOverview": "/admin/overview?period=30d", "getProject": "/projects/1",
    "getUser": "/users/2", "getRecommendedStudents": "/projects/1/recommendations",
}


def missing_keys(example, actual, path=""):
    """Keys present in `example` but absent from `actual` (dicts recursively, lists by their first item)."""
    missing = []
    if isinstance(example, dict) and isinstance(actual, dict):
        for key, value in example.items():
            here = f"{path}.{key}" if path else key
            if key not in actual:
                missing.append(here)
            elif actual[key] is not None:
                missing += missing_keys(value, actual[key], here)
    elif isinstance(example, list) and isinstance(actual, list) and example and actual:
        missing += missing_keys(example[0], actual[0], f"{path}[0]")
    return missing


def test_missing_keys_finds_nested_gaps():
    assert missing_keys({"a": 1, "b": {"c": 2}, "d": [{"e": 3}]}, {"a": 1, "b": {}, "d": [{}]}) == ["b.c", "d[0].e"]


@pytest.mark.parametrize("name", CALLS)
def test_responses_carry_every_example_key(db, api, name):
    seed_demo(db)
    r = api("john.carter@student.uni.ac.th").get(CALLS[name])
    assert r.status_code == 200, r.text
    assert missing_keys(EXAMPLES[name], r.json()) == []
