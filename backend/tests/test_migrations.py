from app.db import run_migrations


def test_run_migrations_applies_new_files_once(db, tmp_path):
    (tmp_path / "900_a.sql").write_text("CREATE TABLE zz_a (id int);")
    (tmp_path / "901_b.sql").write_text("CREATE TABLE zz_b (id int);")
    try:
        assert run_migrations(db, tmp_path) == ["900_a.sql", "901_b.sql"]
        assert run_migrations(db, tmp_path) == []
    finally:
        db.execute("DROP TABLE IF EXISTS zz_a, zz_b")
        db.execute("DELETE FROM schema_migrations WHERE version LIKE '90%'")
