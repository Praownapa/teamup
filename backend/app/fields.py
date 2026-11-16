"""Reusable Pydantic field types for request bodies."""
from typing import Annotated

from pydantic import StringConstraints


def Text(max_length: int, min_length: int = 0):
    """A string with surrounding spaces removed, then checked against the length limits."""
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length)]
