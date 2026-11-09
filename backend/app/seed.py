"""Load the demo data from the command line (run from the backend folder):

    python -m app.seed            # only if the database has no users yet
    python -m app.seed --reset    # DELETE ALL DATA, then load the demo data again

Uses DATABASE_URL (same as the API). Migrations are applied first, so it also works on an empty database.
"""
import argparse

from .config import get_settings
from .db import connect, run_migrations, seed_demo


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Load the TeamUp demo students, projects and requests.")
    parser.add_argument("--reset", action="store_true", help="delete ALL data first, then load the demo data")
    args = parser.parse_args(argv)
    with connect(get_settings().database_url) as conn:
        applied = run_migrations(conn)
        if applied:
            print("Applied migrations:", ", ".join(applied))
        if seed_demo(conn, force=args.reset):
            print("Demo data loaded. Admin login in dev mode: dev:john.carter@student.uni.ac.th")
        else:
            print("The database already has users, so nothing was loaded. Use --reset to wipe it and reload.")


if __name__ == "__main__":
    main()
