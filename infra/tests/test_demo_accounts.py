"""The demo students who get Cognito logins online, and the shared demo password."""
from pathlib import Path

from demo_accounts import demo_users, new_demo_password

SEED = Path(__file__).resolve().parents[2] / "backend" / "seed" / "demo.sql"


def test_reads_all_18_demo_students():
    users = demo_users(SEED)
    assert len(users) == 18
    assert users[0] == ("john.carter@student.uni.ac.th", "John Carter")  # the admin
    assert ("jack.scott@student.uni.ac.th", "Jack Scott") in users  # the suspended one
    assert len({email for email, _ in users}) == 18


def test_password_meets_the_pool_policy():
    passwords = [new_demo_password() for _ in range(50)]
    for password in passwords:
        assert len(password) == 16 and password.isascii() and password.isalnum()
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
    assert len(set(passwords)) == 50
