"""The demo students who get Cognito logins online, and their shared demo password.

    python infra/demo_accounts.py users backend/seed/demo.sql   # prints email<TAB>name, one per line
    python infra/demo_accounts.py password                      # prints a new random demo password

The seed file stays the one list of demo students: every '<x>@student.uni.ac.th', '<Name>' pair in it.
infra/demo-accounts.sh creates their Cognito accounts; on first sign-in the backend links each account to
its seeded profile by email.
"""
from __future__ import annotations

import re
import secrets
import string
import sys
from pathlib import Path

_PAIR = re.compile(r"'([a-z0-9.]+@student\.uni\.ac\.th)',\s*'([^']+)'")
# Letters and digits without the look-alikes 0/O and 1/l/I, so the password is easy to type in a demo.
_ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")


def demo_users(seed_sql: Path) -> list[tuple[str, str]]:
    """(email, name) for each demo student, in the seed file's order."""
    users: dict[str, str] = {}
    for email, name in _PAIR.findall(Path(seed_sql).read_text(encoding="utf-8")):
        users.setdefault(email, name)
    return list(users.items())


def new_demo_password() -> str:
    """16 letters and digits, with at least one upper-case letter, one lower-case letter and one digit
    (the user pool's password rule)."""
    while True:
        password = "".join(secrets.choice(_ALPHABET) for _ in range(16))
        if (any(c.islower() for c in password) and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)):
            return password


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "users":
        for email, name in demo_users(Path(argv[1])):
            print(f"{email}\t{name}")
        return 0
    if argv == ["password"]:
        print(new_demo_password())
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
