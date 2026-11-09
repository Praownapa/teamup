# TeamUp Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A FastAPI + PostgreSQL backend in `backend/` that serves all 30 endpoints the TeamUp frontend calls, plus the small frontend changes needed to run the real app locally without Cognito.

**Architecture:** Sync FastAPI endpoints under `/api`, one router per Jira area. psycopg 3 connections run in autocommit mode; every write is wrapped in an explicit `with conn.transaction():`. All SQL is hand-written with placeholders. Team status is a SQL view and the match score a SQL function. View builders in `app/views.py` produce the exact JSON shapes of `docs/RESPONSE-EXAMPLES.json`.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, psycopg 3 + psycopg-pool, Pydantic v2, PyJWT[crypto], httpx, boto3, pytest; PostgreSQL 17 + pgAdmin in Docker; React/Vite frontend (existing).

**Spec:** `docs/superpowers/specs/2026-11-09-teamup-backend-design.md`

## Global Constraints

- Python 3.12 (`C:\Python312\python.exe`), venv at `backend/.venv`. Direct dependencies pinned with `==` in `backend/requirements.txt`, dev-only ones in `backend/requirements-dev.txt`.
- All routes under `/api`; Swagger at `/api/docs`, OpenAPI at `/api/openapi.json`, app title `TeamUp API`. Router tags, in include order: `Users & Profile`, `Search & Matching`, `Projects`, `Join Requests & Invitations`, `Team Management`, `Notifications`, `Uploads`, `Admin`.
- No ORM. Values reach SQL only through psycopg placeholders. The only string-built SQL fragments are whitelisted `ORDER BY` clauses.
- Connections: `autocommit=True`, `row_factory=dict_row`. Writes use `with conn.transaction():`.
- Lock order inside any transaction: **project row first** (`SELECT … FROM projects … FOR UPDATE`), then request rows. Never the reverse; the reverse deadlocks when a team fills.
- Errors: `HTTPException(status_code, detail="<readable sentence>")`, using the exact messages quoted in the tasks. Status codes: 401 auth, 403 permission, 404 missing, 409 conflict, 400 business-rule input, 422 schema validation.
- Response shapes, paths, verbs and 204s exactly as `docs/API-CONTRACT.md`. Numeric IDs. Lists are bare arrays. Datetimes are ISO strings (`datetime.isoformat()`), and a missing deadline is `""`.
- Environment variables (exact names): `DATABASE_URL`, `AUTH_MODE` (`cognito`|`dev`, default `cognito`), `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `UPLOAD_MODE` (`off`|`local`|`s3`, default `off`), `UPLOAD_DIR` (default `uploads`), `S3_BUCKET`, `S3_REGION`, `PUBLIC_FILE_BASE_URL`, `SEED_DEMO_DATA` (default false).
- Default DB URL `postgresql://teamup:teamup@localhost:5432/teamup`; test DB `postgresql://teamup:teamup@localhost:5432/teamup_test` (override with `TEST_DATABASE_URL`).
- Emails are stored lowercase. Default categories (in this order): `Course Project`, `Competition`, `Senior Project`, `Startup Idea`, `Research`.
- Frontend: mock mode stays the default. `npm test` and `npm run build` must pass after every frontend task.
- Commits: one per task on branch `feature/backend`, conventional messages ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push.
- Run backend commands from `backend/` in Git Bash: `.venv/Scripts/python -m pytest -q`. PostgreSQL must be up (`docker compose up -d db`).

## Review Focus

1. **A brand-new user's parallel first requests** (AuthProvider calls `/users/me` and `/users/me/counts` at the same moment right after login) must create exactly one profile and both succeed. Test: Task 3 `test_parallel_first_requests_create_one_user`.
2. **Search text containing `%`, `_` or Thai script** must match literally and case-insensitively, not as LIKE wildcards. Test: Task 6 `test_q_is_literal_and_handles_thai`.
3. **Skill names that differ only by case or surrounding spaces** count as one skill when saving and when matching. Tests: Task 5 `test_put_me_dedupes_skills_case_insensitively`, Task 2 `test_match_score_rounds_half_up_and_ignores_case`.
4. **Stale actions from an out-of-date screen** get a readable error: responding to a cancelled request is 404, responding twice is 409, cancelling an accepted request is 409. Test: Task 7 `test_stale_actions_are_readable`.
5. **Bad or removed IDs in URLs** get 422/404 with readable detail, never 500. Tests: Task 4 `test_get_project_404_422_and_removed`, Task 8 `test_members_me_route_not_shadowed_and_leave_rules`.

## File Map

```
backend/
  app/__init__.py
  app/config.py          Settings, load_settings, get_settings                   (T1)
  app/db.py              connect, pool, get_conn, run_migrations, seed_demo      (T1, T12)
  app/main.py            create_app, lifespan, /api/health                       (T1, grows per router)
  app/auth.py            dev + Cognito token checks, current_user, admin_user    (T3)
  app/views.py           JSON view builders                                      (T4, T5, T7)
  app/notify.py          notify()                                                (T5)
  app/places.py          team-place helpers                                      (T6, T7)
  app/matching.py        suggest_role()                                          (T6)
  app/seed.py            `python -m app.seed [--reset]`                          (T12)
  app/routers/__init__.py
  app/routers/{users,projects,search,requests,teams,notifications,admin,uploads}.py
  migrations/001_init.sql                                                        (T2)
  seed/demo.sql                                                                  (T12)
  tests/conftest.py, tests/helpers.py, tests/test_*.py
  requirements.txt, requirements-dev.txt, pytest.ini, docker-compose.yml, .env.example (T1)
  Dockerfile, .dockerignore, README.md                                           (T15)
Frontend: src/config-values.js, src/auth/cognito.js (T13); src/pages/Projects.jsx, vite.config.js,
          .dockerignore, .env.example, README.md (T14, T15); tests/config.test.js, tests/cognito-local.test.js (T13)
Root .gitignore (T1)
```

---

### Task 1: Backend skeleton, config, database plumbing, test harness

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/routers/__init__.py`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/pytest.ini`, `backend/docker-compose.yml`, `backend/.env.example`, `backend/tests/conftest.py`, `backend/tests/helpers.py`
- Modify: `.gitignore` (append `backend/.venv/`, `backend/uploads/`, `__pycache__/`, `.pytest_cache/`)
- Test: `backend/tests/test_config.py`, `backend/tests/test_health.py`, `backend/tests/test_migrations.py`

**Interfaces:**
- Produces:
  - `config.py`: `Settings` (frozen dataclass; fields `database_url, auth_mode, cognito_region, cognito_user_pool_id, cognito_client_id, upload_mode, upload_dir, s3_bucket, s3_region, public_file_base_url, seed_demo_data`), `load_settings(env: Mapping[str, str] | None = None) -> Settings`, `get_settings() -> Settings` (`functools.lru_cache`).
  - `db.py`: `MIGRATIONS_DIR: Path`, `connect(database_url: str) -> psycopg.Connection`, `open_pool(database_url: str) -> None`, `close_pool() -> None`, `get_pool() -> ConnectionPool`, `get_conn() -> Iterator[psycopg.Connection]` (FastAPI dependency), `run_migrations(conn, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]`.
  - `main.py`: `create_app() -> FastAPI`, `app`.
  - `pytest.ini`: `testpaths = tests`, `pythonpath = .`, `addopts = -q`.
  - `tests/conftest.py`: fixtures `client` (session TestClient), `db` (autouse, function: truncates every public table except `schema_migrations`, re-inserts the default categories if `categories` exists, yields an autocommit dict-row connection), `api` (factory `api(email) -> Api`).
  - `tests/helpers.py`: `TEST_DATABASE_URL` (env `TEST_DATABASE_URL` or the default; conftest imports it from here), `bearer(token: str) -> dict`, `class Api(client, email)` with `get/post/put/patch/delete(path, **kw)` that prefix `/api` and send `Authorization: Bearer dev:<email>`.

- [ ] **Step 1: Start Docker Desktop and create the environment.** If `docker info` fails, run `Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'` and poll `docker info` until it succeeds. Then: `C:\Python312\python.exe -m venv backend/.venv`; `backend/.venv/Scripts/python -m pip install fastapi "uvicorn[standard]" "psycopg[binary]" psycopg-pool "pyjwt[crypto]" httpx boto3 pytest`; write the installed versions with `==` (from `pip show`) into `requirements.txt` (runtime) and `requirements-dev.txt` (`-r requirements.txt` plus pytest).
- [ ] **Step 2: Write `docker-compose.yml`.**
  - `db`: `postgres:17`; `POSTGRES_USER/PASSWORD/DB` = `teamup/teamup/teamup`; port `5432:5432`; named volume `teamup-db`; `pg_isready` healthcheck.
  - `pgadmin`: `dpage/pgadmin4`, pinned to the newest major tag that `docker pull` confirms; port `5050:80`; `PGADMIN_CONFIG_SERVER_MODE='False'`, `PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED='False'`; `servers.json` mounted, pre-registering host `db`, user `teamup`, database `teamup`.
  - Run `docker compose up -d db pgadmin` and check http://localhost:5050 loads.
- [ ] **Step 3: Write the failing tests.**

```python
# tests/test_config.py
def test_defaults():
    s = load_settings({})
    assert (s.auth_mode, s.upload_mode, s.upload_dir, s.seed_demo_data) == ("cognito", "off", "uploads", False)
    assert s.database_url == "postgresql://teamup:teamup@localhost:5432/teamup"
def test_reads_and_normalizes_values():
    s = load_settings({"AUTH_MODE": " DEV ", "UPLOAD_MODE": "local", "SEED_DEMO_DATA": "true"})
    assert (s.auth_mode, s.upload_mode, s.seed_demo_data) == ("dev", "local", True)
def test_rejects_unknown_modes():
    for env in ({"AUTH_MODE": "magic"}, {"UPLOAD_MODE": "ftp"}):
        with pytest.raises(ValueError): load_settings(env)

# tests/test_health.py
def test_health_reports_database_ok(client):
    r = client.get("/api/health"); assert r.status_code == 200 and r.json() == {"status": "ok", "database": "ok"}
def test_docs_are_served_under_api(client):
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").json()["info"]["title"] == "TeamUp API"

# tests/test_migrations.py
def test_run_migrations_applies_new_files_once(db, tmp_path):
    (tmp_path / "900_a.sql").write_text("CREATE TABLE zz_a (id int);"); (tmp_path / "901_b.sql").write_text("CREATE TABLE zz_b (id int);")
    try:
        assert run_migrations(db, tmp_path) == ["900_a.sql", "901_b.sql"]
        assert run_migrations(db, tmp_path) == []
    finally:
        db.execute("DROP TABLE IF EXISTS zz_a, zz_b"); db.execute("DELETE FROM schema_migrations WHERE version LIKE '90%'")
```

- [ ] **Step 4: Run them and confirm they fail.** `.venv/Scripts/python -m pytest -q` fails with import errors.
- [ ] **Step 5: Implement.**
  - `config.py`: values are stripped and lowercased for the two modes. `SEED_DEMO_DATA` is true for `true`/`1`/`yes`. An invalid mode raises `ValueError("AUTH_MODE must be cognito or dev")` / `ValueError("UPLOAD_MODE must be off, local or s3")`.
  - `db.py`: the pool is `psycopg_pool.ConnectionPool(min_size=1, max_size=10, kwargs={"autocommit": True, "row_factory": dict_row}, open=True)`. `run_migrations`, inside one transaction:
    1. `SELECT pg_advisory_xact_lock(424242)`
    2. `CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())`
    3. Execute each not-yet-applied `*.sql` file in sorted order (whole file, no parameters, so multi-statement works) and insert its name.
  - `main.py`:
    - The lifespan calls `open_pool(settings.database_url)`, runs migrations on a pool connection, logs a `WARNING` that starts `AUTH_MODE=dev` when in dev mode, and finally calls `close_pool()`.
    - `FastAPI(title="TeamUp API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)`.
    - `GET /api/health` runs `SELECT 1`. It returns 503 `{"status": "error", "database": "unavailable"}` on failure.
  - `conftest.py` (env and database setup):
    - Before importing `app`, set `DATABASE_URL=TEST_DATABASE_URL`, `AUTH_MODE=dev`, `UPLOAD_MODE=local`, `UPLOAD_DIR=<tmp dir>`, `SEED_DEMO_DATA=false`.
    - Recreate the test database by connecting to the `postgres` database with autocommit and running `DROP DATABASE IF EXISTS teamup_test WITH (FORCE)` followed by `CREATE DATABASE teamup_test`.
    - Then call `get_settings.cache_clear()`.
- [ ] **Step 6: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes (6 passed).
- [ ] **Step 7: Commit.** `git add .gitignore backend && git commit -m "feat(backend): app skeleton, config, db pool, migrations runner, test harness"`

---

### Task 2: Database schema (Set Up Database)

**Files:**
- Create: `backend/migrations/001_init.sql`
- Test: `backend/tests/test_schema.py`

**Interfaces:**
- Produces:
  - **Tables and columns** (as in the spec's Database section):
    - `users`: identity `id`; `cognito_sub text UNIQUE` (nullable); `email text UNIQUE NOT NULL CHECK (email = lower(email))`; `name`, `student_id`, `major` (text NOT NULL DEFAULT `''`); `year smallint NOT NULL DEFAULT 1 CHECK (1..6)`; `role` (`student`|`admin`); `status` (`active`|`suspended`); `bio`, `portfolio` (text NOT NULL DEFAULT `''`); `open_to_projects bool DEFAULT true`; `notify_invitations`, `notify_requests`, `notify_team` (default true); `notify_digest` (default false); `created_at`.
    - `user_skills`: `user_id`, `name`, `level`, `position`, unique `(user_id, lower(name))`.
    - `user_interests`: `user_id`, `name`, `position`, unique `(user_id, lower(name))`.
    - `categories`: `name` (unique on `lower(name)`), `created_at`. The 5 defaults are inserted with increasing `created_at`.
    - `projects`: identity `id`, `owner_id`, `title`, `description`, `category`, `course`, `cover_url`, `max_size smallint CHECK (2..10)`, `accepting`, `deadline date`, `duration`, `meeting`, `created_at`, `removed_at`.
    - `project_skills`: `project_id`, `name`, `position`, unique `(project_id, lower(name))`.
    - `project_roles`: identity `id`, `project_id`, `name`, `user_id` (nullable), `position`. Partial unique index on `(project_id, user_id)` where `user_id IS NOT NULL`.
    - `requests`: identity `id`, `project_id`, `user_id`, `by_id` (nullable), `kind` (`request`|`invitation`), `role`, `message`, `status` (`pending`|`accepted`|`rejected`), `created_at`, `responded_at`. Partial unique index on `(project_id, user_id)` where `status = 'pending'`.
    - `saved_projects`: primary key `(user_id, project_id)`.
    - `reports`: identity `id`, `project_id`, `reporter_id`, `reason`, `status` (`open`|`removed`|`dismissed`), `created_at`, `resolved_at`, `resolved_by`. Partial unique index on `(project_id, reporter_id)` where `status = 'open'`.
    - `notifications`: identity `id`, `user_id`, `kind` (`request`|`invite`|`accepted`|`declined`|`team`|`match`), `text`, `request_id` (references `requests` ON DELETE CASCADE), `unread` (default true), `created_at`.
  - **Rules:** project children cascade on project delete. Indexes on `projects(owner_id)`, `project_roles(project_id)`, `project_roles(user_id)`, `requests(project_id, status)`, `requests(user_id)`, `notifications(user_id, created_at DESC)`.
  - **View** `project_summary(project_id, member_count int, place_count int, status text)`.
  - **Function** `match_score(p_project_id integer, p_user_id integer) RETURNS integer`.

The function body is fixed: half-up rounding to match JS `Math.round`, and 0 when the project has no skills.

```sql
CREATE FUNCTION match_score(p_project_id integer, p_user_id integer) RETURNS integer LANGUAGE sql STABLE AS $$
  SELECT CASE WHEN count(*) = 0 THEN 0
              ELSE floor(100.0 * count(us.user_id) / count(*) + 0.5)::int END
  FROM project_skills ps
  LEFT JOIN user_skills us ON us.user_id = p_user_id AND lower(us.name) = lower(ps.name)
  WHERE ps.project_id = p_project_id
$$;
CREATE VIEW project_summary AS
  SELECT p.id AS project_id, count(r.user_id)::int AS member_count, count(r.id)::int AS place_count,
         CASE WHEN count(r.user_id) >= p.max_size THEN 'full' WHEN p.accepting THEN 'recruiting' ELSE 'closed' END AS status
  FROM projects p LEFT JOIN project_roles r ON r.project_id = p.id GROUP BY p.id;
```

- [ ] **Step 1: Write the failing tests** in `tests/test_schema.py`, using a local helper `_project(db, owner_id, max_size=3, accepting=True, skills=(), places=None) -> int` that inserts directly with SQL. `places` is a sequence of `(name, user_id_or_None)` and defaults to `[("Lead", owner_id)]`.

```python
def test_default_categories_exist(db):
    assert [r["name"] for r in db.execute("SELECT name FROM categories ORDER BY created_at")] == ["Course Project", "Competition", "Senior Project", "Startup Idea", "Research"]
def test_match_score_rounds_half_up_and_ignores_case(db):
    u = make_user(db, "m@x.test", skills=["react"])
    p8 = _project(db, u, skills=[f"S{i}" for i in range(7)] + ["REACT"])
    assert db.execute("SELECT match_score(%s, %s) AS m", (p8, u)).fetchone()["m"] == 13   # 1/8 = 12.5 -> 13
    assert db.execute("SELECT match_score(%s, %s) AS m", (_project(db, u), u)).fetchone()["m"] == 0
def test_project_summary_status(db):
    o = make_user(db, "o@x.test"); m = make_user(db, "m2@x.test")
    full = _project(db, o, max_size=2, places=(("Lead", o), ("Dev", m)))
    closed = _project(db, o, accepting=False, places=(("Lead", o), ("Dev", None)))
    rec = _project(db, o, places=(("Lead", o), ("Dev", None)))
    got = {r["project_id"]: (r["status"], r["member_count"], r["place_count"]) for r in db.execute("SELECT * FROM project_summary")}
    assert got[full] == ("full", 2, 2) and got[closed] == ("closed", 1, 2) and got[rec] == ("recruiting", 1, 2)
def test_one_place_per_member_and_one_pending_per_person(db):
    o = make_user(db, "o3@x.test"); p = _project(db, o, places=(("Lead", o), ("Dev", None)))
    with pytest.raises(psycopg.errors.UniqueViolation): db.execute("UPDATE project_roles SET user_id=%s WHERE project_id=%s AND user_id IS NULL", (o, p))
    s = make_user(db, "s@x.test")
    db.execute("INSERT INTO requests (project_id, user_id, kind, role) VALUES (%s,%s,'request','Dev')", (p, s))
    with pytest.raises(psycopg.errors.UniqueViolation): db.execute("INSERT INTO requests (project_id, user_id, kind, role) VALUES (%s,%s,'invitation','Dev')", (p, s))
def test_emails_must_be_lowercase(db):
    with pytest.raises(psycopg.errors.CheckViolation): db.execute("INSERT INTO users (email) VALUES ('Upper@X.test')")
```

  Add `make_user(db, email, *, name=None, major="", year=1, skills=(), role="student", status="active", open_to_projects=True) -> int` to `tests/helpers.py`. It inserts the user (name defaults to the part before `@`) and the skills at level `Intermediate`, and returns the id.
- [ ] **Step 2: Run and confirm the failure.** `.venv/Scripts/python -m pytest tests/test_schema.py -q` fails (relation "categories" does not exist).
- [ ] **Step 3: Write `migrations/001_init.sql`** with the tables, constraints, indexes, view, function and default categories above.
- [ ] **Step 4: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(db): initial PostgreSQL schema, project_summary view, match_score function"`

---

### Task 3: Authentication (Auth & Profile ticket, part 1)

**Files:**
- Create: `backend/app/auth.py`
- Test: `backend/tests/test_auth.py` (+ add `make_access_token`, `TEST_ISSUER`, `TEST_CLIENT_ID`, the test RSA key pair to `tests/helpers.py`)

**Interfaces:**
- Consumes: `get_settings`, `Settings`, `get_conn`.
- Produces:
  - `bearer_scheme = HTTPBearer(auto_error=False)`
  - `parse_dev_token(token: str) -> dict`, with keys `email, name, student_id, major` (all str; email lowercased)
  - `get_jwk_client(jwks_url: str) -> jwt.PyJWKClient` (lru_cache; tests monkeypatch `app.auth.get_jwk_client`)
  - `verify_cognito_token(token: str, settings: Settings) -> dict` (claims)
  - `fetch_cognito_attributes(access_token: str, region: str) -> dict[str, str]` (tests monkeypatch it)
  - `user_for_dev(conn, ident: dict) -> dict` and `user_for_cognito(conn, claims: dict, token: str, settings: Settings) -> dict`. Both return the full `users` row.
  - `current_user(...) -> dict` (users row) and `admin_user(user=Depends(current_user)) -> dict`.
- Fixed messages:
  - 401 `"Not authenticated."` (no bearer) and `"Invalid or expired token."` (anything else wrong)
  - 403 `"Your account has been suspended."` and `"Admin access required."`
  - 502 `"Could not load your profile from Cognito."`

- [ ] **Step 1: Write the failing tests.**
  - The `whoami` fixture builds a mini `FastAPI()` with `GET /whoami` (depends on `current_user`) and `GET /admin-only` (depends on `admin_user`), both returning `{"id", "role"}`, wrapped in `TestClient`. It depends on `client`, so the pool is open.
  - The `cognito_env` fixture monkeypatches:
    - `app.auth.get_settings` to `Settings(auth_mode="cognito", cognito_region="ap-southeast-1", cognito_user_pool_id="ap-southeast-1_TEST", cognito_client_id="client123", …)`
    - `app.auth.get_jwk_client` to a fake whose `get_signing_key_from_jwt` returns `SimpleNamespace(key=TEST_PUBLIC_KEY)`
    - `app.auth.fetch_cognito_attributes` to return `cognito_env.attrs`, a dict the test sets

```python
def test_parse_dev_token_forms():
    assert parse_dev_token("dev:Emma@X.test") == {"email": "emma@x.test", "name": "", "student_id": "", "major": ""}
    assert parse_dev_token("dev:email=a%40x.test&name=A+B&student_id=0012345678&major=Data+Science") == {"email": "a@x.test", "name": "A B", "student_id": "0012345678", "major": "Data Science"}
    for bad in ["", "abc", "dev:", "dev:not-an-email"]:
        with pytest.raises(HTTPException) as e: parse_dev_token(bad)
        assert e.value.status_code == 401
def test_user_for_dev_creates_then_reuses(db):
    u1 = user_for_dev(db, parse_dev_token("dev:new@x.test"))
    assert (u1["name"], u1["year"], u1["role"], u1["student_id"]) == ("new", 1, "student", "")
    assert user_for_dev(db, parse_dev_token("dev:email=new%40x.test&name=Other"))["id"] == u1["id"]
def test_parallel_first_requests_create_one_user(db):
    ids, barrier = [], threading.Barrier(2)
    def go():
        with connect(TEST_DATABASE_URL) as c: barrier.wait(); ids.append(user_for_dev(c, parse_dev_token("dev:race@x.test"))["id"])
    ts = [threading.Thread(target=go) for _ in range(2)]; [t.start() for t in ts]; [t.join() for t in ts]
    assert len(set(ids)) == 1 and db.execute("SELECT count(*) AS n FROM users WHERE email='race@x.test'").fetchone()["n"] == 1
def test_missing_token_suspended_and_admin(db, whoami):
    assert whoami.get("/whoami").json() == {"detail": "Not authenticated."}
    make_user(db, "s@x.test", status="suspended")
    r = whoami.get("/whoami", headers=bearer("dev:s@x.test")); assert r.status_code == 403 and r.json()["detail"] == "Your account has been suspended."
    make_user(db, "boss@x.test", role="admin")
    assert whoami.get("/admin-only", headers=bearer("dev:boss@x.test")).status_code == 200
    assert whoami.get("/admin-only", headers=bearer("dev:pleb@x.test")).json()["detail"] == "Admin access required."
def test_cognito_bootstrap_and_group_sync(db, whoami, cognito_env):
    cognito_env.attrs = {"email": "C@X.test", "name": "Cee Gee", "custom:student_id": "0099887766", "custom:major": "Data Science", "email_verified": "true"}
    assert whoami.get("/whoami", headers=bearer(make_access_token("sub-1", ["admin"]))).json()["role"] == "admin"
    row = db.execute("SELECT * FROM users WHERE cognito_sub='sub-1'").fetchone()
    assert (row["email"], row["name"], row["student_id"], row["major"]) == ("c@x.test", "Cee Gee", "0099887766", "Data Science")
    assert whoami.get("/whoami", headers=bearer(make_access_token("sub-1", []))).json()["role"] == "student"
def test_cognito_links_existing_profile_by_verified_email(db, whoami, cognito_env):
    uid = make_user(db, "link@x.test"); cognito_env.attrs = {"email": "link@x.test", "email_verified": "true"}
    assert whoami.get("/whoami", headers=bearer(make_access_token("sub-9"))).json()["id"] == uid
def test_cognito_rejects_bad_tokens(whoami, cognito_env):
    for tok in [make_access_token("s", client_id="other"), make_access_token("s", token_use="id"),
                make_access_token("s", exp=int(time.time()) - 10), make_access_token("s", iss="https://evil.example"), "dev:a@x.test"]:
        r = whoami.get("/whoami", headers=bearer(tok)); assert r.status_code == 401 and r.json()["detail"] == "Invalid or expired token."
```

- [ ] **Step 2: Run and confirm the failure.** `.venv/Scripts/python -m pytest tests/test_auth.py -q`
- [ ] **Step 3: Implement `app/auth.py`.**
  - `verify_cognito_token`:
    - issuer `https://cognito-idp.{region}.amazonaws.com/{pool_id}`; JWKS at `{issuer}/.well-known/jwks.json`
    - `jwt.decode(..., algorithms=["RS256"], issuer=issuer, options={"require": ["exp", "iss", "sub", "token_use", "client_id"], "verify_aud": False})`
    - then require `token_use == "access"` and `client_id == settings.cognito_client_id`
    - any `jwt.PyJWTError`/`jwt.PyJWKClientError` gives 401
  - `fetch_cognito_attributes` POSTs `{"AccessToken": token}` to `https://cognito-idp.{region}.amazonaws.com/` with headers `Content-Type: application/x-amz-json-1.1` and `X-Amz-Target: AWSCognitoIdentityProviderService.GetUser` (5 s timeout), and returns `{Name: Value}` from `UserAttributes`.
  - `user_for_cognito`, in this order:
    1. select by `cognito_sub`
    2. else fetch the attributes
    3. if `email_verified == "true"`, run `UPDATE users SET cognito_sub=… WHERE email=… AND cognito_sub IS NULL RETURNING *`
    4. else `INSERT … ON CONFLICT DO NOTHING RETURNING *`, then re-select by sub; if still nothing, 409 `"An account with this email already exists."`
    5. finally sync `role` from `cognito:groups`: `admin` when the group is present, otherwise `student`; update only when changed.
  - `user_for_dev` selects by email, else does `INSERT … ON CONFLICT (email) DO NOTHING` and re-selects. The name defaults to the part before `@`.
  - `current_user` dispatches on `get_settings().auth_mode` (called at request time) and then applies the suspension check.
- [ ] **Step 4: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(auth): Cognito access-token verification, dev tokens, profile bootstrap"`

---

### Task 4: Project Management API

**Files:**
- Create: `backend/app/views.py`, `backend/app/routers/projects.py`
- Modify: `backend/app/main.py` (include the projects router with prefix `/api`)
- Test: `backend/tests/test_projects.py` (+ `VALID_PROJECT`, `new_project` in `tests/helpers.py`)

**Interfaces:**
- Consumes: `current_user`, `get_conn`.
- Produces:
  - `views.iso(value) -> str` (`""` for None)
  - `views.brief(row: dict, prefix: str = "") -> dict`, giving `{"id","name","major","year"}`
  - `views.get_visible_project(conn, project_id: int, user: dict, lock: bool = False) -> dict` (projects row). It raises 404 `"Project not found."` when missing, or when removed and `user["role"] != "admin"`. `lock=True` adds `FOR UPDATE`.
  - `views.project_views(conn, viewer_id: int, project_ids: list[int]) -> list[dict]`, which preserves the input order using batch queries (projects + summary + owner + `match_score` + saved; skills with `have`; roles left-joined to users; member skills; pending counts; viewer's pending join request).
  - `views.project_view(conn, viewer_id: int, project_id: int) -> dict`
  - Project view keys, exactly: `id, title, category, course, description, cover_url, owner, max_size, accepting, status, created_at, duration, meeting, deadline, saved, skills ([[name, have]]), match, roles ([{name, user}]), members ([{id,name,major,year,role,owner,skills}] in place order), open_roles, my_role ("owner"|"member"|None), my_request ({id,role,status}|None), pending_requests, pending_invitations`.
  - Routes:
    - `POST /projects` (201): `ProjectCreate` returns the view
    - `GET /projects/{project_id}`
    - `PATCH /projects/{project_id}`: `ProjectUpdate`, owner only, returns the view
    - `POST /projects/{project_id}/save`: `{"saved": bool}`
    - `POST /projects/{project_id}/reports`: `ReportIn {reason: 1..100}`, returns `{"ok": True}`
  - `ProjectCreate`:
    - title 1..80 and description 1..2000 (both stripped)
    - category 1..50; course ≤100; cover_url ≤500
    - skills: 1..20 items, each stripped 1..50
    - owner_role ≤60; roles: 1..10 `RoleIn{name 1..60 stripped, spots 1..4 = 1}`
    - max_size 2..10; deadline `""` or `YYYY-MM-DD`; duration/meeting ≤100; accepting = True
  - `ProjectUpdate`: the same fields minus skills/owner_role/roles/max_size, all optional.
- Fixed messages:
  - 400 `"Your roles need {n} people (including you) but the maximum team size is {max}."`
  - 400 `"Unknown category."`
  - 403 `"Only the project owner can do that."`
  - 400 `"You can't report your own project."`

- [ ] **Step 1: Write the failing tests.** `VALID_PROJECT = {"title": "Test Project", "description": "A test project.", "category": "Course Project", "course": "", "cover_url": "", "skills": ["React", "Python"], "owner_role": "Lead", "roles": [{"name": "Frontend Developer", "spots": 1}, {"name": "Backend Developer", "spots": 1}], "max_size": 4, "deadline": "", "duration": "", "meeting": "", "accepting": True}`. `new_project(owner: Api, **overrides) -> dict` posts it, asserts 201 and returns the JSON.

```python
def test_create_project_returns_full_view(api):
    p = new_project(api("owner@x.test")); oid = p["owner"]["id"]
    assert p["owner"] == {"id": oid, "name": "owner", "major": "", "year": 1} and p["my_role"] == "owner" and p["status"] == "recruiting"
    assert [r["name"] for r in p["roles"]] == ["Lead", "Frontend Developer", "Backend Developer"] and p["roles"][1]["user"] is None
    assert p["open_roles"] == ["Frontend Developer", "Backend Developer"]
    assert p["members"] == [{"id": oid, "name": "owner", "major": "", "year": 1, "role": "Lead", "owner": True, "skills": []}]
    assert p["skills"] == [["React", False], ["Python", False]] and p["match"] == 0
    assert (p["duration"], p["meeting"], p["deadline"], p["cover_url"], p["saved"], p["my_request"]) == ("—", "—", "", "", False, None)
    assert (p["pending_requests"], p["pending_invitations"]) == (0, 0)
def test_create_validation(api):
    a = api("o@x.test")
    r = a.post("/projects", json={**VALID_PROJECT, "max_size": 2, "roles": [{"name": "Dev", "spots": 2}]})
    assert r.status_code == 400 and r.json()["detail"] == "Your roles need 3 people (including you) but the maximum team size is 2."
    assert a.post("/projects", json={**VALID_PROJECT, "category": "Nope"}).json()["detail"] == "Unknown category."
    for bad in ({"skills": []}, {"title": "x" * 81}, {"max_size": 11}, {"roles": [{"name": "Dev", "spots": 5}]}, {"deadline": "soon"}):
        assert a.post("/projects", json={**VALID_PROJECT, **bad}).status_code == 422
    assert new_project(a, owner_role="")["roles"][0]["name"] == "Project Owner"
def test_get_project_404_422_and_removed(db, api):
    p = new_project(api("o@x.test")); other = api("x@x.test")
    assert other.get("/projects/999").json() == {"detail": "Project not found."}
    assert other.get("/projects/abc").status_code == 422
    db.execute("UPDATE projects SET removed_at = now() WHERE id = %s", (p["id"],))
    assert other.get(f"/projects/{p['id']}").status_code == 404
    make_user(db, "admin@x.test", role="admin"); assert api("admin@x.test").get(f"/projects/{p['id']}").status_code == 200
def test_patch_is_owner_only_and_updates_status(api):
    o, x = api("o@x.test"), api("x@x.test"); p = new_project(o)
    assert x.patch(f"/projects/{p['id']}", json={"accepting": False}).json()["detail"] == "Only the project owner can do that."
    assert o.patch(f"/projects/{p['id']}", json={"accepting": False}).json()["status"] == "closed"
    assert o.patch(f"/projects/{p['id']}", json={"title": ""}).status_code == 422
def test_toggle_save(api):
    x = api("x@x.test"); pid = new_project(api("o@x.test"))["id"]
    assert x.post(f"/projects/{pid}/save").json() == {"saved": True} and x.get(f"/projects/{pid}").json()["saved"] is True
    assert x.post(f"/projects/{pid}/save").json() == {"saved": False}
def test_report_rules(db, api):
    o, x = api("o@x.test"), api("x@x.test"); pid = new_project(o)["id"]
    assert o.post(f"/projects/{pid}/reports", json={"reason": "Spam / scam"}).json()["detail"] == "You can't report your own project."
    assert x.post(f"/projects/{pid}/reports", json={"reason": "Spam / scam"}).json() == {"ok": True}
    x.post(f"/projects/{pid}/reports", json={"reason": "Misleading info"})
    assert [r["reason"] for r in db.execute("SELECT reason FROM reports WHERE status='open'")] == ["Misleading info"]
```

- [ ] **Step 2: Run and confirm the failure.** `.venv/Scripts/python -m pytest tests/test_projects.py -q`
- [ ] **Step 3: Implement.**
  - Create runs in one transaction:
    1. insert the project; blank duration/meeting become `—`, a blank deadline becomes NULL
    2. insert skills, deduplicated case-insensitively, keeping the first spelling and order
    3. insert places: the owner's at position 0 with `owner_role or "Project Owner"`, then `spots` open places per role in order
  - The category check is case-insensitive; store the canonical name from `categories`.
  - Save toggles a row (delete if present, else insert).
  - Report: `INSERT … ON CONFLICT (project_id, reporter_id) WHERE status = 'open' DO UPDATE SET reason = EXCLUDED.reason, created_at = now()`.
  - All routes use `get_visible_project` first.
- [ ] **Step 4: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): project management endpoints and project view builder"`

---

### Task 5: Users & Profile API (Auth & Profile ticket, part 2)

**Files:**
- Create: `backend/app/notify.py`, `backend/app/routers/users.py`
- Modify: `backend/app/views.py` (add `me_view`, `public_user_view`, `notification_view`), `backend/app/main.py` (include the users router first)
- Test: `backend/tests/test_users.py`

**Interfaces:**
- Consumes: `project_views`, `current_user`.
- Produces:
  - `notify(conn, user_id: int, kind: str, text: str, request_id: int | None = None) -> None`
  - `views.me_view(conn, user_id: int) -> dict`, with keys `id, name, email, student_id, major, year, role, status, bio, portfolio, open_to_projects, skills [{name,level}], interests [str], notify {invitations,requests,team,digest}, teams [{id,title,is_owner,status}], stats {teams,projects,skills}`. Teams cover non-removed projects where the user holds a place, newest first.
  - `views.public_user_view(conn, user_id: int) -> dict`, with keys exactly `id, name, major, year, bio, skills, interests, teams [{id,title}]` (non-removed projects only); 404 `"Student not found."`.
  - `views.notification_view(row) -> dict`, giving `{id, kind, text, created_at, unread, request_id}`.
  - Routes (declare `/users/me*` before `/users/{user_id}`):
    - `GET /users/me`
    - `PUT /users/me` (`ProfileUpdate`)
    - `GET /users/me/counts`
    - `GET /users/me/dashboard`
    - `GET /users/{user_id}`
  - `ProfileUpdate` (`extra="ignore"`, all optional):
    - name 1..100; major ≤100; year 1..6; bio ≤400; portfolio ≤200; open_to_projects
    - skills: ≤30 `SkillIn{name stripped 1..50, level Literal["Beginner","Intermediate","Advanced"]}`
    - interests: ≤20 strings 1..50
    - notify: `NotifyIn` with 4 optional bools, merged into the stored values
  - Only fields present in the body change (`model_dump(exclude_unset=True)`). Skill and interest lists are replaced whole, deduplicated case-insensitively (first wins, names stripped).
  - Counts: `pending_requests` = pending join requests on non-removed projects the viewer owns + pending invitations to the viewer. `unread_notifications` = the viewer's unread rows.
  - Dashboard, as in `mock.js`, over non-removed projects only:
    - `stats {teams, pending, invitations, matches, unread}`, where matches = recruiting projects the viewer isn't on with match ≥ 50
    - `recommended`: top 2 of those by match, newest as tie-break
    - `my_teams`: views of the viewer's projects, newest first
    - `activity`: the latest 4 notification views

- [ ] **Step 1: Write the failing tests.**

```python
def test_me_view_defaults(api):
    me = api("me@x.test").get("/users/me").json()
    assert (me["role"], me["status"], me["year"], me["skills"], me["interests"], me["teams"]) == ("student", "active", 1, [], [], [])
    assert me["notify"] == {"invitations": True, "requests": True, "team": True, "digest": False} and me["stats"] == {"teams": 0, "projects": 0, "skills": 0}
def test_put_me_is_partial_and_ignores_privileged_fields(api):
    a = api("me@x.test"); a.put("/users/me", json={"bio": "Hi"})
    me = a.put("/users/me", json={"name": "New Name", "role": "admin", "status": "suspended", "email": "z@z.z", "student_id": "1"}).json()
    assert (me["bio"], me["name"], me["role"], me["status"], me["email"]) == ("Hi", "New Name", "student", "active", "me@x.test")
    assert a.put("/users/me", json={"notify": {"requests": False}}).json()["notify"] == {"invitations": True, "requests": False, "team": True, "digest": False}
def test_put_me_dedupes_skills_case_insensitively(api):
    me = api("me@x.test").put("/users/me", json={"skills": [{"name": " React ", "level": "Advanced"}, {"name": "react", "level": "Beginner"}, {"name": "SQL", "level": "Beginner"}], "interests": ["AI", "ai", "IoT"]}).json()
    assert me["skills"] == [{"name": "React", "level": "Advanced"}, {"name": "SQL", "level": "Beginner"}] and me["interests"] == ["AI", "IoT"]
def test_put_me_validates(api):
    a = api("me@x.test")
    for bad in ({"year": 7}, {"skills": [{"name": "X", "level": "Expert"}]}, {"bio": "x" * 401}, {"name": ""}):
        assert a.put("/users/me", json=bad).status_code == 422
def test_public_profile_teams_and_stats(api):
    o = api("o@x.test"); p = new_project(o); me = o.get("/users/me").json()
    assert me["teams"] == [{"id": p["id"], "title": "Test Project", "is_owner": True, "status": "recruiting"}] and me["stats"] == {"teams": 1, "projects": 1, "skills": 0}
    pub = api("x@x.test").get(f"/users/{me['id']}").json()
    assert set(pub) == {"id", "name", "major", "year", "bio", "skills", "interests", "teams"} and pub["teams"] == [{"id": p["id"], "title": "Test Project"}]
    assert api("x@x.test").get("/users/999").json() == {"detail": "Student not found."}
def test_counts_and_dashboard(db, api):
    o = api("o@x.test"); mine = new_project(o); o_id = mine["owner"]["id"]
    b = make_user(db, "b@x.test", skills=["React", "Python"]); other = new_project(api("b@x.test"), title="Other")
    db.execute("INSERT INTO requests (project_id, user_id, kind, role) VALUES (%s,%s,'request','Frontend Developer')", (mine["id"], b))
    db.execute("INSERT INTO requests (project_id, user_id, by_id, kind, role) VALUES (%s,%s,%s,'invitation','Frontend Developer')", (other["id"], o_id, b))
    for i in range(5): notify(db, o_id, "team", f"n{i}")
    assert o.get("/users/me/counts").json() == {"pending_requests": 2, "unread_notifications": 5}
    d = o.get("/users/me/dashboard").json()
    assert d["stats"] == {"teams": 1, "pending": 1, "invitations": 1, "matches": 0, "unread": 5}
    assert [p["id"] for p in d["recommended"]] == [other["id"]] and [p["id"] for p in d["my_teams"]] == [mine["id"]]
    assert [n["text"] for n in d["activity"]] == ["n4", "n3", "n2", "n1"]
```

- [ ] **Step 2: Run and confirm the failure.** `.venv/Scripts/python -m pytest tests/test_users.py -q`
- [ ] **Step 3: Implement** the views, `notify`, and the routes. The `PUT` runs in one transaction.
- [ ] **Step 4: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): profile, public profile, counts and dashboard endpoints"`

---

### Task 6: Search & Matching API

**Files:**
- Create: `backend/app/matching.py`, `backend/app/places.py`, `backend/app/routers/search.py`
- Modify: `backend/app/main.py` (include the search router **before** the projects router)
- Test: `backend/tests/test_search.py`, `backend/tests/test_matching.py`

**Interfaces:**
- Consumes: `project_views`, `get_visible_project`, `current_user`.
- Produces:
  - `places.member_ids(conn, project_id: int) -> list[int]`
  - `places.open_role_names(conn, project_id: int) -> list[str]`: distinct names of open places, ordered by first position
  - `matching.FIT_RULES: list[tuple[str, str]]`
  - `matching.suggest_role(open_roles: list[str], skills: list[str]) -> str`
  - Routes:
    - `GET /projects` (query `q, categories, skills, role, recruiting, spots, sort`, all strings, default `""` except `sort="match"`)
    - `GET /projects/filters`
    - `GET /projects/{project_id}/recommendations`
- Rules:
  - Search runs in SQL:
    - Non-removed projects only.
    - `q` uses `ILIKE` with `%`, `_` and `\` escaped (`ESCAPE '\'`) over title, description or any skill.
    - `categories` is an exact comma list (empties dropped).
    - `skills`: every comma item must be an `ILIKE` substring of some required skill.
    - `role`: an exact open place name.
    - `recruiting=true` means status recruiting; `spots=true` means `max_size - member_count >= 2`.
  - Sort: `match` (default and fallback) is `match_score DESC`; `newest` is `created_at DESC`; `spots` is open places `DESC`. The tie-break is always `created_at DESC, id DESC`.
  - Filters: all categories (ordered by `created_at`) with counts of non-removed projects, plus the sorted distinct open place names of non-removed projects.
  - Recommendations:
    - Owner only (403 `"Only the project owner can do that."`).
    - Candidates: active, `open_to_projects`, holding no place in the project.
    - Each gets `{id, name, major, year, match, fits, invited, skills [[name, in_project_skills]]}`.
    - `invited` = a pending invitation exists.
    - Keep `match > 0 or fits != "—"`, sort by match DESC then name, limit 50.

`suggest_role` walks the open roles in order and returns the first role whose name matches a rule's role pattern while some skill matches that rule's skill pattern (case-insensitive `re.search`). Otherwise it returns `open_roles[0]`, or `"—"` when there are none. The rules, fixed:

```python
FIT_RULES = [(r"front", r"react|javascript|vue|typescript|css|html"), (r"back", r"python|fastapi|node|sql|postgres|java|django"),
             (r"ui|ux|design", r"figma|ui|ux|design"), (r"cloud|devops", r"aws|docker|linux|kubernetes|cloud"),
             (r"data", r"python|pandas|sql|d3|analysis|machine learning"), (r"mobile", r"flutter|react native|swift|kotlin|firebase"),
             (r"\bml\b|machine|\bai\b", r"python|machine learning|nlp|pytorch|tensorflow"), (r"qa|test", r"pytest|test|selenium|qa"),
             (r"iot|hardware|robot", r"arduino|c\+\+|iot|cad")]
```

- [ ] **Step 1: Write the failing tests.**

```python
# test_matching.py
def test_suggest_role():
    assert suggest_role(["Backend Developer", "Frontend Developer"], ["React"]) == "Frontend Developer"
    assert suggest_role(["UI/UX Designer"], ["Figma"]) == "UI/UX Designer"
    assert suggest_role(["Data Analyst", "Hardware"], ["Arduino"]) == "Hardware"
    assert suggest_role(["Data Analyst"], ["Figma"]) == "Data Analyst" and suggest_role([], ["React"]) == "—"

# test_search.py (helper: ids(resp) -> [p["id"] for p in resp.json()])
def test_search_q_category_skills_role(api):
    o = api("o@x.test")
    a = new_project(o, title="Alpha Bot", category="Competition", skills=["React", "Python"])
    b = new_project(o, title="Beta", description="robotics alpha", skills=["C++"], roles=[{"name": "Hardware", "spots": 1}])
    x = api("x@x.test")
    assert sorted(ids(x.get("/projects", params={"q": "ALPHA"}))) == sorted([a["id"], b["id"]])
    assert ids(x.get("/projects", params={"q": "c++"})) == [b["id"]]
    assert ids(x.get("/projects", params={"categories": "Competition,Research"})) == [a["id"]]
    assert ids(x.get("/projects", params={"skills": "reac,pyth"})) == [a["id"]]
    assert ids(x.get("/projects", params={"role": "Hardware"})) == [b["id"]]
def test_q_is_literal_and_handles_thai(api):
    o = api("o@x.test"); p1 = new_project(o, title="100% Done"); new_project(o, title="1000 Done"); th = new_project(o, title="ระบบจองห้องประชุม")
    x = api("x@x.test")
    assert ids(x.get("/projects", params={"q": "100%"})) == [p1["id"]] and ids(x.get("/projects", params={"q": "_"})) == []
    assert ids(x.get("/projects", params={"q": "จอง"})) == [th["id"]]
def test_recruiting_spots_and_sorts(db, api):
    o = api("o@x.test")
    closed = new_project(o, title="Closed", accepting=False)
    big = new_project(o, title="Big", max_size=6, roles=[{"name": "Dev", "spots": 4}])
    small = new_project(o, title="Small", max_size=2, roles=[{"name": "Dev", "spots": 1}])
    db.execute("UPDATE projects SET created_at = now() - interval '1 day' WHERE id = %s", (big["id"],))
    make_user(db, "x@x.test", skills=["React", "Python"]); x = api("x@x.test")
    assert closed["id"] not in ids(x.get("/projects", params={"recruiting": "true"}))
    assert small["id"] not in ids(x.get("/projects", params={"spots": "true"}))
    assert ids(x.get("/projects", params={"sort": "spots"}))[0] == big["id"]
    assert ids(x.get("/projects", params={"sort": "newest"}))[-1] == big["id"]
    assert ids(x.get("/projects", params={"sort": "bogus"})) == ids(x.get("/projects"))
def test_filters_endpoint(api):
    o = api("o@x.test"); new_project(o); new_project(o, category="Research", roles=[{"name": "Analyst", "spots": 1}])
    f = api("x@x.test").get("/projects/filters").json()
    assert f["categories"][0] == {"name": "Course Project", "count": 1} and {"name": "Research", "count": 1} in f["categories"] and len(f["categories"]) == 5
    assert f["roles"] == ["Analyst", "Backend Developer", "Frontend Developer"]
def test_recommendations(db, api):
    o = api("o@x.test"); p = new_project(o)
    fit = make_user(db, "fit@x.test", skills=["React"]); make_user(db, "away@x.test", skills=["React"], open_to_projects=False)
    make_user(db, "sus@x.test", skills=["React"], status="suspended")
    assert api("x@x.test").get(f"/projects/{p['id']}/recommendations").json()["detail"] == "Only the project owner can do that."
    recs = o.get(f"/projects/{p['id']}/recommendations").json(); names = [r["name"] for r in recs]
    assert recs[0] == {"id": fit, "name": "fit", "major": "", "year": 1, "match": 50, "fits": "Frontend Developer", "invited": False, "skills": [["React", True]]}
    assert "away" not in names and "sus" not in names and "o" not in names          # unavailable, suspended, already on the team
    assert next(r for r in recs if r["name"] == "x")["fits"] == "Frontend Developer"  # no skills: falls back to the first open role
```
- [ ] **Step 2: Run and confirm the failure.** `.venv/Scripts/python -m pytest tests/test_search.py tests/test_matching.py -q`
- [ ] **Step 3: Implement** `matching.py`, `places.py` and `routers/search.py`. Build the WHERE/ORDER BY from fixed fragments and placeholders only.
- [ ] **Step 4: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): project search, filter options and teammate recommendations"`

---

### Task 7: Join Request & Invitation API

**Files:**
- Create: `backend/app/routers/requests.py`
- Modify: `backend/app/places.py` (add `take_open_place`, `free_place`), `backend/app/views.py` (add `request_views`), `backend/app/main.py`
- Test: `backend/tests/test_requests.py` (+ `add_member(owner: Api, member: Api, project_id: int, role: str) -> None` in `tests/helpers.py`: the member requests, the owner accepts, and both responses are asserted 200)

**Interfaces:**
- Consumes: `get_visible_project(lock=True)`, `places.member_ids/open_role_names`, `notify`, `project_view`.
- Produces:
  - `places.take_open_place(conn, project: dict, user_id: int, role: str) -> str`: fills the first open place named `role` (by position). Otherwise, if `place_count < max_size`, it appends a place with that name. Otherwise it raises 409 `"That role has already been filled."`.
  - `places.free_place(conn, project_id: int, user_id: int) -> None`
  - `views.request_views(conn, viewer_id: int, request_ids: list[int]) -> list[dict]`, with keys `id, type, kind, status, role, message, created_at, project {id,title,open_spots}, student, by, match`. Type: an invitation is `"invitation"` when the viewer is the student, else `"sent"`; a request is `"sent"` when the viewer is the student, else `"received"`.
  - Services:
    - `create_join_request(conn, user, project_id, role, message) -> None`
    - `create_invitation(conn, owner, project_id, invitee_id, role) -> None`
    - `respond_to_request(conn, user, request_id, accept: bool) -> None`
    - `cancel_request(conn, user, request_id) -> None`
  - Routes:
    - `POST /projects/{id}/requests` (`JoinIn{role, message ≤500 = ""}`): returns the project view
    - `POST /projects/{id}/invitations` (`InviteIn{user_id, role}`): returns `{"ok": True}`
    - `GET /requests`: rows where the viewer is the student, the inviter or the project owner, on non-removed projects only, newest first
    - `PATCH /requests/{id}` (`RespondIn{status: Literal["accepted","rejected"]}`): returns the request view from the responder's side
    - `DELETE /requests/{id}`: 204
- Fixed messages:
  - 404 `"Request not found."`
  - 400 `"You own this project."` and 409 `"You're already on this team."`
  - 409 `"This team is no longer accepting requests."`
  - 400 `"That role isn't open in this project."`
  - 409 `"You already have a pending request for this project."` and 409 `"You've already been invited to this project. Check your invitations."`
  - 404 `"Student not found."`, 400 `"This student isn't open to new projects."`, 400 `"This student's account is suspended."`
  - 409 `"This student is already on the team."`, 409 `"The team is already full."`
  - 409 `"This student already has a pending request or invitation for this project."`
  - 403 `"Only the project owner can respond to this request."` and 403 `"Only the invited student can respond to this invitation."`
  - 409 `"This request has already been handled."`
  - 403 `"Only the student who sent this request can cancel it."` and 409 `"Only pending requests can be cancelled."`
- Notifications (exact text):
  - New request, to the owner: `request` "{student} requested to join {title} as {role}." (with `request_id`)
  - New invitation, to the invitee: `invite` "{owner} invited you to join {title} as {role}." (with `request_id`)
  - Request accepted, to the student: `accepted` "Your request to join {title} was accepted. Say hi to your new team!"
  - Request rejected: `declined` "Your request to join {title} was declined."
  - Invitation accepted, to the owner: `team` "{student} accepted your invitation and joined {title} as {role}."
  - Invitation declined, to the owner: `declined` "{student} declined your invitation to join {title}."
  - Someone joined, to the other members (not the new member, the actor, or the owner already told): `team` "{student} joined {title} as {role}."
  - Auto-rejected when full: `declined` "Your request to join {title} was declined. The team is now complete." (requests) / "Your invitation to join {title} was withdrawn because the team is now complete." (invitations)
  - Responding, or auto-rejecting, marks that request's notifications read.

`respond_to_request` must lock in this order:
1. Read `project_id` from the request without a lock (404 if missing).
2. `get_visible_project(..., lock=True)`.
3. `SELECT … FROM requests WHERE id=%s FOR UPDATE`.
4. Check the actor, then check status pending.
5. On accept, check membership and capacity, call `take_open_place`, update the request, auto-reject when it is now full, and notify.

The create functions also lock the project row first, then pre-check duplicates (the unique index stays as a safety net).

- [ ] **Step 1: Write the failing tests.**

```python
def test_join_flow_and_rules(db, api):
    o, s = api("o@x.test"), api("s@x.test"); p = new_project(o); pid = p["id"]
    v = s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer", "message": "hi"}).json()
    assert v["my_request"]["role"] == "Frontend Developer" and v["my_request"]["status"] == "pending"
    assert o.get("/notifications").json()[0]["text"] == "s requested to join Test Project as Frontend Developer."
    assert s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}).json()["detail"] == "You already have a pending request for this project."
    assert o.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}).json()["detail"] == "You own this project."
    assert api("t@x.test").post(f"/projects/{pid}/requests", json={"role": "Chef"}).json()["detail"] == "That role isn't open in this project."
    assert api("t@x.test").post(f"/projects/{pid}/requests", json={"role": "Frontend Developer", "message": "x" * 501}).status_code == 422
    o.patch(f"/projects/{pid}", json={"accepting": False})
    assert api("t@x.test").post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}).json()["detail"] == "This team is no longer accepting requests."
def test_invitation_rules(db, api):
    o = api("o@x.test"); p = new_project(o, accepting=False); pid = p["id"]
    i = make_user(db, "i@x.test"); away = make_user(db, "away@x.test", open_to_projects=False)
    assert api("x@x.test").post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Frontend Developer"}).json()["detail"] == "Only the project owner can do that."
    assert o.post(f"/projects/{pid}/invitations", json={"user_id": away, "role": "Frontend Developer"}).json()["detail"] == "This student isn't open to new projects."
    assert o.post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Frontend Developer"}).json() == {"ok": True}   # allowed while paused
    assert o.post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Backend Developer"}).json()["detail"] == "This student already has a pending request or invitation for this project."
    assert api("i@x.test").post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}).status_code == 409
    inv = api("i@x.test").get("/notifications").json()[0]; assert inv["kind"] == "invite" and inv["request_id"]
def test_list_types_per_viewer(db, api):
    o, s = api("o@x.test"), api("s@x.test"); pid = new_project(o)["id"]; i = make_user(db, "i@x.test")
    s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}); o.post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Backend Developer"})
    assert sorted(r["type"] for r in o.get("/requests").json()) == ["received", "sent"]
    assert [r["type"] for r in s.get("/requests").json()] == ["sent"] and [r["type"] for r in api("i@x.test").get("/requests").json()] == ["invitation"]
    inv = api("i@x.test").get("/requests").json()[0]; assert inv["by"]["id"] == o.get("/users/me").json()["id"] and inv["project"]["open_spots"] == 3
def test_accept_and_reject_permissions_and_notifications(db, api):
    o, s, t = api("o@x.test"), api("s@x.test"), api("t@x.test"); pid = new_project(o)["id"]
    s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}); t.post(f"/projects/{pid}/requests", json={"role": "Backend Developer"})
    rs, rt = (next(r["id"] for r in o.get("/requests").json() if r["student"]["name"] == n) for n in ("s", "t"))
    assert s.patch(f"/requests/{rs}", json={"status": "accepted"}).json()["detail"] == "Only the project owner can respond to this request."
    assert o.patch(f"/requests/{rs}", json={"status": "accepted"}).json()["status"] == "accepted"
    assert o.get(f"/projects/{pid}").json()["open_roles"] == ["Backend Developer"]
    assert s.get("/notifications").json()[0]["text"] == "Your request to join Test Project was accepted. Say hi to your new team!"
    o.patch(f"/requests/{rt}", json={"status": "rejected"}); assert t.get("/notifications").json()[0]["kind"] == "declined"
def test_stale_actions_are_readable(api):
    o, s = api("o@x.test"), api("s@x.test"); pid = new_project(o)["id"]
    s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}); rid = s.get("/requests").json()[0]["id"]
    assert o.get("/notifications").json()[0]["request_id"] == rid
    assert o.delete(f"/requests/{rid}").json()["detail"] == "Only the student who sent this request can cancel it."
    assert s.delete(f"/requests/{rid}").status_code == 204 and o.get("/notifications").json() == []     # cascade removed it
    assert o.patch(f"/requests/{rid}", json={"status": "accepted"}).json() == {"detail": "Request not found."}
    s.post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"}); rid = s.get("/requests").json()[0]["id"]
    o.patch(f"/requests/{rid}", json={"status": "accepted"})
    assert o.patch(f"/requests/{rid}", json={"status": "rejected"}).json()["detail"] == "This request has already been handled."
    assert s.delete(f"/requests/{rid}").json()["detail"] == "Only pending requests can be cancelled."
def test_filling_team_rejects_the_rest(db, api):
    o = api("o@x.test"); pid = new_project(o, max_size=2, roles=[{"name": "Dev", "spots": 1}])["id"]; i = make_user(db, "i@x.test")
    api("a@x.test").post(f"/projects/{pid}/requests", json={"role": "Dev"}); api("b@x.test").post(f"/projects/{pid}/requests", json={"role": "Dev"})
    o.post(f"/projects/{pid}/invitations", json={"user_id": i, "role": "Dev"})
    ra = next(r["id"] for r in o.get("/requests").json() if r["student"]["name"] == "a")
    o.patch(f"/requests/{ra}", json={"status": "accepted"})
    assert o.get(f"/projects/{pid}").json()["status"] == "full"
    assert {r["status"] for r in o.get("/requests").json() if r["id"] != ra} == {"rejected"}
    assert api("b@x.test").get("/notifications").json()[0]["text"] == "Your request to join Test Project was declined. The team is now complete."
    assert api("i@x.test").get("/notifications").json()[0]["text"] == "Your invitation to join Test Project was withdrawn because the team is now complete."
def test_taken_role_adds_place_only_with_capacity(api):
    o = api("o@x.test"); roomy = new_project(o, max_size=4, roles=[{"name": "Dev", "spots": 1}])["id"]
    tight = new_project(o, title="Tight", max_size=3, roles=[{"name": "Dev", "spots": 1}, {"name": "QA", "spots": 1}])["id"]
    for pid in (roomy, tight):
        for n in ("a", "b"): api(f"{n}{pid}@x.test").post(f"/projects/{pid}/requests", json={"role": "Dev"})
    def accept_all(pid): return [o.patch(f"/requests/{r['id']}", json={"status": "accepted"}) for r in o.get("/requests").json() if r["project"]["id"] == pid and r["status"] == "pending"]
    assert [r.status_code for r in accept_all(roomy)] == [200, 200] and len(o.get(f"/projects/{roomy}").json()["members"]) == 3
    res = accept_all(tight); assert sorted(r.status_code for r in res) == [200, 409] and "That role has already been filled." in [r.json().get("detail") for r in res]
def test_two_acceptances_for_last_place_produce_one_member(db, api):
    o = api("o@x.test"); pid = new_project(o, max_size=2, roles=[{"name": "Dev", "spots": 1}])["id"]
    for n in ("a", "b"): api(f"{n}@x.test").post(f"/projects/{pid}/requests", json={"role": "Dev"})
    owner = db.execute("SELECT * FROM users WHERE email='o@x.test'").fetchone(); rids = [r["id"] for r in o.get("/requests").json()]
    results, barrier = [], threading.Barrier(2)
    def go(rid):
        with connect(TEST_DATABASE_URL) as c:
            barrier.wait()
            try: respond_to_request(c, owner, rid, True); results.append("ok")
            except HTTPException as e: results.append(e.status_code)
    ts = [threading.Thread(target=go, args=(r,)) for r in rids]; [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(map(str, results)) == ["409", "ok"]
    assert db.execute("SELECT member_count FROM project_summary WHERE project_id=%s", (pid,)).fetchone()["member_count"] == 2
```

- [ ] **Step 2: Run and confirm the failure.** `.venv/Scripts/python -m pytest tests/test_requests.py -q`
- [ ] **Step 3: Implement** `places.take_open_place/free_place`, `views.request_views`, the services and the routes, following the lock order.
- [ ] **Step 4: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): join requests and invitations with atomic acceptance"`

---

### Task 8: Team Management API

**Files:**
- Create: `backend/app/routers/teams.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_teams.py`

**Interfaces:**
- Consumes: `get_visible_project(lock=True)`, `places.member_ids/free_place`, `notify`, `project_view`, test helper `add_member`.
- Produces:
  - Services: `change_member_role(conn, owner, project_id, member_id, role) -> None`, `remove_member(conn, owner, project_id, member_id) -> None`, `leave_team(conn, user, project_id) -> None`.
  - Routes, declared in this order:
    - `DELETE /projects/{project_id}/members/me`: 204
    - `PATCH /projects/{project_id}/members/{user_id}` (`RoleChangeIn{role stripped 1..60}`): returns the view
    - `DELETE /projects/{project_id}/members/{user_id}`: returns the view
- Rules:
  - Change role: free the member's current place, then fill the first open place named `role`. If there isn't one, rename the current place. Freeing first matters because of the unique index.
- Fixed messages:
  - 403 `"Only the project owner can do that."`
  - 400 `"The owner's role can't be changed here."`
  - 400 `"The owner can't be removed from their own project."`
  - 404 `"That student isn't on this team."`
  - 400 `"Owners can't leave their own project."`
  - 404 `"You're not on this team."`
- Notifications:
  - To the member: `team` "Your role in {title} is now {role}."
  - To the removed person: `team` "You were removed from {title}."
  - To the owner: `team` "{name} left {title}."

- [ ] **Step 1: Write the failing tests.**

```python
def test_change_role_moves_or_renames(api):
    o, m = api("o@x.test"), api("m@x.test"); pid = new_project(o)["id"]; add_member(o, m, pid, "Frontend Developer"); mid = m.get("/users/me").json()["id"]
    v = o.patch(f"/projects/{pid}/members/{mid}", json={"role": "Backend Developer"}).json()
    assert next(x["role"] for x in v["members"] if x["id"] == mid) == "Backend Developer" and v["open_roles"] == ["Frontend Developer"]
    v = o.patch(f"/projects/{pid}/members/{mid}", json={"role": "Tech Lead"}).json()
    assert [r["name"] for r in v["roles"]] == ["Lead", "Frontend Developer", "Tech Lead"]
    assert m.get("/notifications").json()[0]["text"] == "Your role in Test Project is now Tech Lead."
def test_member_endpoint_rules(api):
    o, m = api("o@x.test"), api("m@x.test"); pid = new_project(o)["id"]; add_member(o, m, pid, "Frontend Developer")
    oid, mid = o.get("/users/me").json()["id"], m.get("/users/me").json()["id"]
    assert m.patch(f"/projects/{pid}/members/{mid}", json={"role": "X"}).json()["detail"] == "Only the project owner can do that."
    assert o.patch(f"/projects/{pid}/members/{oid}", json={"role": "X"}).json()["detail"] == "The owner's role can't be changed here."
    assert o.delete(f"/projects/{pid}/members/{oid}").json()["detail"] == "The owner can't be removed from their own project."
    assert o.delete(f"/projects/{pid}/members/999").json()["detail"] == "That student isn't on this team."
def test_remove_member_returns_view_and_notifies(api):
    o, m = api("o@x.test"), api("m@x.test"); pid = new_project(o)["id"]; add_member(o, m, pid, "Frontend Developer"); mid = m.get("/users/me").json()["id"]
    r = o.delete(f"/projects/{pid}/members/{mid}"); assert r.status_code == 200 and [x["id"] for x in r.json()["members"]] == [o.get("/users/me").json()["id"]]
    assert m.get("/notifications").json()[0]["text"] == "You were removed from Test Project."
def test_members_me_route_not_shadowed_and_leave_rules(api):
    o, m = api("o@x.test"), api("m@x.test"); pid = new_project(o)["id"]; add_member(o, m, pid, "Frontend Developer")
    assert o.delete(f"/projects/{pid}/members/me").json()["detail"] == "Owners can't leave their own project."
    assert api("x@x.test").delete(f"/projects/{pid}/members/me").json()["detail"] == "You're not on this team."
    assert m.delete(f"/projects/{pid}/members/me").status_code == 204
    assert o.get("/notifications").json()[0]["text"] == "m left Test Project." and m.get(f"/projects/{pid}").json()["my_role"] is None
```

  In the last test, the owner's newest notification after the leave is "m left Test Project.": the join request's notification is older.
- [ ] **Step 2: Run and confirm the failure.** `.venv/Scripts/python -m pytest tests/test_teams.py -q`
- [ ] **Step 3: Implement** the services and routes.
- [ ] **Step 4: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): team management endpoints"`

---

### Task 9: Notifications API

**Files:**
- Create: `backend/app/routers/notifications.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_notifications.py`

**Interfaces:**
- Consumes: `notification_view`, `notify`.
- Produces:
  - `GET /notifications`: the viewer's own, `created_at DESC, id DESC`, limit 100
  - `POST /notifications/{id}/read`: 204; 404 `"Notification not found."` unless it's the viewer's
  - `POST /notifications/read-all`: 204, viewer's rows only

- [ ] **Step 1: Write the failing tests.**

```python
def test_notifications_are_private_and_markable(db, api):
    a, b = api("a@x.test"), api("b@x.test"); aid, bid = a.get("/users/me").json()["id"], b.get("/users/me").json()["id"]
    notify(db, aid, "team", "first"); notify(db, aid, "team", "second"); notify(db, bid, "team", "theirs")
    mine = a.get("/notifications").json(); assert [n["text"] for n in mine] == ["second", "first"] and all(n["unread"] for n in mine)
    theirs = b.get("/notifications").json()[0]["id"]
    assert a.post(f"/notifications/{theirs}/read").json() == {"detail": "Notification not found."}
    assert a.post(f"/notifications/{mine[0]['id']}/read").status_code == 204 and [n["unread"] for n in a.get("/notifications").json()] == [False, True]
    assert a.post("/notifications/read-all").status_code == 204 and b.get("/users/me/counts").json()["unread_notifications"] == 1
```

- [ ] **Step 2: Run and confirm the failure.** Then **Step 3: Implement**, **Step 4: Run** `.venv/Scripts/python -m pytest -q` and confirm it passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): notification list and read endpoints"`

---

### Task 10: Admin API

**Files:**
- Create: `backend/app/routers/admin.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin.py`

**Interfaces:**
- Consumes: `admin_user`, `notify`, `brief`.
- Produces:
  - Routes:
    - `GET /admin/overview?period=` (`Literal["7d","30d","semester"]`, default `"30d"`)
    - `PATCH /admin/reports/{report_id}` (`ResolveIn{status: Literal["removed","dismissed"]}`): 204
    - `PATCH /admin/users/{user_id}` (`UserStatusIn{status: Literal["suspended","active"]}`): 204
    - `POST /admin/categories` (`CategoryIn{name stripped 1..50}`): 204
    - `DELETE /admin/categories/{name}`: 204
  - Overview, `stats`:
    - `students` = all users; `projects` = non-removed projects
    - `teams` = non-removed projects with member_count ≥ 2
    - `reports` = non-removed projects with ≥ 1 open report
    - `deltas {students, projects, teams}` = the same, counting only rows created in the last 7 / 30 / 120 days
  - Overview, `activity`, oldest first:
    - `7d`: 7 daily buckets labelled with `to_char(day, 'Dy')`
    - `30d`: 5 weekly buckets labelled `W1..W5`
    - `semester`: 16 weekly buckets `W1..W16`
    - each bucket is `{week, requests (kind='request' created in bucket), projects (created in bucket)}`
  - Overview, the rest:
    - `categories`: as filters
    - `reports`: one row per project with open reports, `{id: latest report id, project: title, owner: owner name, reason: latest reason, reporters: count, created_at: latest, status: "open"}`, newest first
    - `users`: `[{id,name,major,year,email,student_id,role,status,projects (places held in non-removed projects)}]` by id
- Rules:
  - Resolving a report sets every open report of its project. `removed` also sets `removed_at`, rejects the project's pending requests and invitations (marking their notifications read), and notifies the owner with `team` "Your project {title} was removed by an administrator."
  - Category add is `ON CONFLICT DO NOTHING`; delete is by `lower(name)` and leaves project labels alone.
- Fixed messages: 404 `"Report not found."`, 409 `"This report has already been handled."`, 404 `"Student not found."`, 400 `"Administrators can't be suspended."`, 400 `"You can't change your own status."`

- [ ] **Step 1: Write the failing tests.**

```python
def test_admin_routes_require_admin(api):
    s = api("s@x.test")
    for r in (s.get("/admin/overview"), s.patch("/admin/reports/1", json={"status": "dismissed"}), s.patch("/admin/users/1", json={"status": "active"}),
              s.post("/admin/categories", json={"name": "X"}), s.delete("/admin/categories/X")):
        assert r.status_code == 403 and r.json()["detail"] == "Admin access required."
def test_overview_counts_and_buckets(db, api):
    make_user(db, "admin@x.test", role="admin"); ad = api("admin@x.test"); o = api("o@x.test"); pid = new_project(o)["id"]
    add_member(o, api("m@x.test"), pid, "Frontend Developer")
    for period, n, first in (("7d", 7, None), ("30d", 5, "W1"), ("semester", 16, "W1")):
        d = ad.get("/admin/overview", params={"period": period}).json(); assert len(d["activity"]) == n
        if first: assert d["activity"][0]["week"] == first
    d = ad.get("/admin/overview").json()
    assert {k: d["stats"][k] for k in ("students", "projects", "teams", "reports")} == {"students": 3, "projects": 1, "teams": 1, "reports": 0}
    assert d["stats"]["deltas"] == {"students": 3, "projects": 1, "teams": 1} and sum(a["requests"] for a in d["activity"]) == 1
    assert next(u for u in d["users"] if u["email"] == "m@x.test")["projects"] == 1
    assert ad.get("/admin/overview", params={"period": "year"}).status_code == 422
def test_remove_report_hides_project_and_notifies(db, api):
    make_user(db, "admin@x.test", role="admin"); ad = api("admin@x.test"); o = api("o@x.test"); pid = new_project(o)["id"]
    api("r1@x.test").post(f"/projects/{pid}/reports", json={"reason": "Spam / scam"}); api("r2@x.test").post(f"/projects/{pid}/reports", json={"reason": "Misleading info"})
    api("s@x.test").post(f"/projects/{pid}/requests", json={"role": "Frontend Developer"})
    rep = ad.get("/admin/overview").json()["reports"]; assert len(rep) == 1 and (rep[0]["reporters"], rep[0]["reason"], rep[0]["owner"]) == (2, "Misleading info", "o")
    assert ad.patch(f"/admin/reports/{rep[0]['id']}", json={"status": "removed"}).status_code == 204
    assert api("x@x.test").get(f"/projects/{pid}").status_code == 404 and o.get("/notifications").json()[0]["text"] == "Your project Test Project was removed by an administrator."
    assert api("s@x.test").get("/requests").json() == [] and ad.get("/admin/overview").json()["reports"] == []
    assert ad.patch(f"/admin/reports/{rep[0]['id']}", json={"status": "dismissed"}).json()["detail"] == "This report has already been handled."
def test_user_status_rules(db, api):
    aid = make_user(db, "admin@x.test", role="admin"); ad = api("admin@x.test"); sid = api("s@x.test").get("/users/me").json()["id"]
    assert ad.patch(f"/admin/users/{sid}", json={"status": "suspended"}).status_code == 204
    assert api("s@x.test").get("/users/me").status_code == 403
    assert ad.patch(f"/admin/users/{aid}", json={"status": "suspended"}).json()["detail"] in ("Administrators can't be suspended.", "You can't change your own status.")
    other_admin = make_user(db, "admin2@x.test", role="admin")
    assert ad.patch(f"/admin/users/{other_admin}", json={"status": "suspended"}).json()["detail"] == "Administrators can't be suspended."
    assert ad.patch(f"/admin/users/{sid}", json={"status": "active"}).status_code == 204 and api("s@x.test").get("/users/me").status_code == 200
def test_categories(api, db):
    make_user(db, "admin@x.test", role="admin"); ad = api("admin@x.test"); new_project(api("o@x.test"), category="Research")
    assert ad.post("/admin/categories", json={"name": "Hackathon"}).status_code == 204 and ad.post("/admin/categories", json={"name": "hackathon"}).status_code == 204
    assert [c["name"] for c in ad.get("/projects/filters").json()["categories"]][-1] == "Hackathon"
    assert ad.delete("/admin/categories/Research").status_code == 204
    assert "Research" not in [c["name"] for c in ad.get("/projects/filters").json()["categories"]] and ad.get("/projects").json()[0]["category"] == "Research"
```

- [ ] **Step 2: Run and confirm the failure.** Then **Step 3: Implement** (buckets via `generate_series`), **Step 4: Run** `.venv/Scripts/python -m pytest -q` and confirm it passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): admin overview, moderation, user status and categories"`

---

### Task 11: Uploads API

**Files:**
- Create: `backend/app/routers/uploads.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_uploads.py`

**Interfaces:**
- Consumes: `current_user`, `get_settings`.
- Produces:
  - `POST /uploads/presign` (`PresignIn{filename ≤200, content_type}`) returns `{"upload_url", "file_url"}`.
  - Local mode only: `PUT /uploads/local/{key:path}?token=` (async; no bearer, because the browser PUTs the file without one) and `GET /uploads/files/{key:path}` (no auth).
- Rules:
  - Allowed types: `image/png→png`, `image/jpeg→jpg`, `image/webp→webp`, otherwise 400 `"Only PNG, JPG or WebP images are allowed."`.
  - `off` mode: 503 `"Image uploads are not configured."`.
  - Key `covers/{user_id}/{uuid4().hex}.{ext}`; valid keys match `^covers/\d+/[0-9a-f]{32}\.(png|jpg|webp)$`.
  - Local mode:
    - One-time tokens live in memory for 300 s: `upload_url = /api/uploads/local/{key}?token=…`, `file_url = /api/uploads/files/{key}`.
    - The PUT checks the token (403 `"Upload link is invalid or expired."`) and that the Content-Type equals the presigned type (400 `"Content-Type does not match the upload link."`).
    - Body ≤ 5 MB (413 `"Image must be 5 MB or smaller."`); the file is written under `UPLOAD_DIR`.
  - S3 mode: `boto3.client("s3", region_name=S3_REGION).generate_presigned_url("put_object", Params={"Bucket", "Key", "ContentType"}, ExpiresIn=300)`; `file_url = (PUBLIC_FILE_BASE_URL or f"https://{bucket}.s3.{region}.amazonaws.com").rstrip("/") + "/" + key`.

- [ ] **Step 1: Write the failing tests.** The upload settings come from monkeypatching `app.routers.uploads.get_settings` with `dataclasses.replace(get_settings(), upload_mode=…, …)`.

```python
def test_local_upload_round_trip(api, client):
    a = api("u@x.test"); r = a.post("/uploads/presign", json={"filename": "c.png", "content_type": "image/png"}).json()
    assert r["file_url"].startswith("/api/uploads/files/covers/")
    assert client.put(r["upload_url"], content=b"\x89PNG", headers={"Content-Type": "image/jpeg"}).status_code == 400
    assert client.put(r["upload_url"], content=b"\x89PNG", headers={"Content-Type": "image/png"}).status_code == 200
    assert client.put(r["upload_url"], content=b"\x89PNG", headers={"Content-Type": "image/png"}).status_code == 403   # token used
    got = client.get(r["file_url"]); assert got.status_code == 200 and got.content == b"\x89PNG"
    assert client.get("/api/uploads/files/../secrets.txt").status_code in (400, 404)
def test_presign_rejects_type_and_size(api, client):
    a = api("u@x.test")
    assert a.post("/uploads/presign", json={"filename": "x.gif", "content_type": "image/gif"}).json()["detail"] == "Only PNG, JPG or WebP images are allowed."
    r = a.post("/uploads/presign", json={"filename": "c.png", "content_type": "image/png"}).json()
    assert client.put(r["upload_url"], content=b"0" * (5 * 1024 * 1024 + 1), headers={"Content-Type": "image/png"}).status_code == 413
def test_off_and_s3_modes(api, monkeypatch):
    import app.routers.uploads as up
    monkeypatch.setattr(up, "get_settings", lambda: replace(get_settings(), upload_mode="off"))
    assert api("u@x.test").post("/uploads/presign", json={"filename": "c.png", "content_type": "image/png"}).json()["detail"] == "Image uploads are not configured."
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test"); monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setattr(up, "get_settings", lambda: replace(get_settings(), upload_mode="s3", s3_bucket="teamup-test", s3_region="ap-southeast-1"))
    r = api("u@x.test").post("/uploads/presign", json={"filename": "c.png", "content_type": "image/png"}).json()
    assert "teamup-test" in r["upload_url"] and "X-Amz-Signature=" in r["upload_url"]
    assert r["file_url"].startswith("https://teamup-test.s3.ap-southeast-1.amazonaws.com/covers/")
```

- [ ] **Step 2: Run and confirm the failure.** Then **Step 3: Implement**, **Step 4: Run** `.venv/Scripts/python -m pytest -q` and confirm it passes.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): cover image uploads (local and S3 presigned)"`

---

### Task 12: Demo data, seed command, and contract check

**Files:**
- Create: `backend/seed/demo.sql`, `backend/app/seed.py`
- Modify: `backend/app/db.py` (add `SEED_FILE`, `seed_demo`), `backend/app/main.py` (seed on startup when `SEED_DEMO_DATA`)
- Test: `backend/tests/test_seed.py`, `backend/tests/test_contract.py`

**Interfaces:**
- Produces:
  - `db.SEED_FILE: Path`
  - `db.seed_demo(conn, force: bool = False) -> bool`: returns False without changes when users exist and `force` is False. When `force` is True it truncates all app tables first. It runs `demo.sql` (one transaction) and returns True.
  - `python -m app.seed [--reset]` connects with `DATABASE_URL`, runs migrations, and seeds (`--reset` means force). It prints what happened.
- Demo data (ported from `src/api/mock.js`; times relative to `now()`, deadlines relative to `current_date`):
  - **Users:** the mock's 18 users with their names, majors, years, skills (users 2–18 at `Intermediate`) and statuses (18 Jack Scott suspended). Emails are `firstname.lastname@student.uni.ac.th`. Student IDs: user 1 `6600123456`, others `6600000000 + id*111` as text.
  - **User 1, John Carter:** `admin`, with the mock's bio, portfolio, levelled skills, interests and notify `{invitations: t, requests: t, team: f, digest: t}`.
  - **Projects:** the mock's 6, with their places/occupants, skills, accepting flags, durations and meetings. `created_at` offsets: 26 d, 9 d, 14 d, 3 d, 5 h, 40 d. Deadline offsets: +21, +1, +36, +11, +22, −39 days.
  - **Extra projects:**
    - 7 "CRYPTO PUMP GROUP" (owner 18, `Startup Idea`, not accepting), with open `Spam / scam` reports from users 3, 4 and 5
    - 8 "Easy A — We Do Your Assignment" (owner 14, `Course Project`, not accepting), with open `Academic dishonesty` reports from users 2 and 6
  - **Requests:** the mock's 6 with the same statuses, roles, messages and ages.
  - **Saved:** (1, 2).
  - **Notifications:** user 1 gets the mock's 7 (same kinds, texts, request links, read states and ages). User 6 Sophia gets an unread `invite` linked to request 6: "John Carter invited you to join Campus Food Waste Tracker as Frontend Developer."
  - **Categories:** the 5 defaults `ON CONFLICT DO NOTHING`.
  - **Sequences:** reset with `setval(pg_get_serial_sequence(...), max(id))` for every identity table.

- [ ] **Step 1: Write the failing tests.**

```python
# test_seed.py
def test_seed_demo_once_and_force(db):
    assert seed_demo(db) is True and seed_demo(db) is False
    one = lambda q: db.execute(q).fetchone()["n"]
    assert (one("SELECT count(*) n FROM users"), one("SELECT count(*) n FROM projects"), one("SELECT count(*) n FROM requests")) == (18, 8, 6)
    assert db.execute("SELECT role FROM users WHERE email='john.carter@student.uni.ac.th'").fetchone()["role"] == "admin"
    assert seed_demo(db, force=True) is True and one("SELECT count(*) n FROM users") == 18
def test_seeded_ids_continue(db, api):
    seed_demo(db); assert new_project(api("john.carter@student.uni.ac.th"))["id"] == 9

# test_contract.py
EXAMPLES = json.loads((REPO_ROOT / "docs/RESPONSE-EXAMPLES.json").read_text(encoding="utf-8"))
CALLS = {"getMe": "/users/me", "getCounts": "/users/me/counts", "getDashboard": "/users/me/dashboard", "listProjects": "/projects",
         "listFilterOptions": "/projects/filters", "listRequests": "/requests", "listNotifications": "/notifications",
         "adminOverview": "/admin/overview?period=30d", "getProject": "/projects/1", "getUser": "/users/2", "getRecommendedStudents": "/projects/1/recommendations"}
def missing_keys(example, actual, path=""):
    # keys present in the example but absent in the actual response; recurse into dicts, and into first elements of non-empty lists; skip when actual is None
    ...
@pytest.mark.parametrize("name", CALLS)
def test_responses_carry_every_example_key(db, api, name):
    seed_demo(db); r = api("john.carter@student.uni.ac.th").get(CALLS[name]); assert r.status_code == 200
    assert missing_keys(EXAMPLES[name], r.json()) == []
```

  The `missing_keys` body is the one algorithm the test needs: it walks example dicts, reports `path.key` for keys absent in `actual`, recurses when both values are dicts, or both are non-empty lists (comparing first elements), and stops when the actual value is `None`.
- [ ] **Step 2: Run and confirm the failure.** `.venv/Scripts/python -m pytest tests/test_seed.py tests/test_contract.py -q`
- [ ] **Step 3: Implement** `demo.sql`, `seed_demo`, `app/seed.py` and the startup seeding.
- [ ] **Step 4: Run and confirm everything passes.** `.venv/Scripts/python -m pytest -q` passes (all tasks so far).
- [ ] **Step 5: Commit.** `git commit -m "feat(db): demo data, seed command and response contract tests"`

---

### Task 13: Frontend local login mode (Integrate Front-end and Back-end, part 1)

**Files:**
- Modify: `src/config-values.js`, `src/auth/cognito.js`
- Test: `tests/config.test.js` (add cases), `tests/cognito-local.test.js` (new)

**Interfaces:**
- Produces:
  - `resolveConfig(...).authMode` (`'cognito' | 'local'`, from `rt.AUTH_MODE ?? env.VITE_AUTH_MODE ?? 'cognito'`, trimmed and lowercased; anything else throws `'AUTH_MODE must be cognito or local.'`).
  - `export function buildDevToken({ email, name, studentId, major }) -> string`, which returns `'dev:' + new URLSearchParams(entries with non-empty values in order email, name, student_id, major)`.
  - In local mode (`!config.useMock && config.authMode === 'local'`), using the localStorage keys `teamup_local_user` (signed-in email) and `teamup_local_profiles` (JSON `{email: {name, studentId, major}}`):
    - `Amplify.configure` is not called.
    - `signIn` stores the lowercased email and returns `{ done: true }`.
    - `signUp` stores the profile under the lowercased email and returns `{ needsConfirm: false }`.
    - `confirmSignUp`, `resendCode`, `forgotPassword` and `confirmForgotPassword` return `true`.
    - `signOut` clears the user.
    - `currentUser` returns `{ email, name, groups: [] }` or `null`.
    - `getAccessToken` returns `buildDevToken(...)` or `null`.

- [ ] **Step 1: Write the failing tests.**

```js
// tests/config.test.js (inside 'configuration precedence')
it('defaults auth to cognito and reads local', () => {
  expect(resolveConfig().authMode).toBe('cognito');
  expect(resolveConfig({}, { VITE_AUTH_MODE: ' Local ' }).authMode).toBe('local');
  expect(() => resolveConfig({}, { VITE_AUTH_MODE: 'magic' })).toThrow('AUTH_MODE must be cognito or local.');
});
// tests/cognito-local.test.js
import { it, expect, vi, beforeEach } from 'vitest';
vi.mock('../src/config', () => ({ config: { useMock: false, authMode: 'local', cognito: { userPoolId: '', userPoolClientId: '' } } }));
vi.mock('aws-amplify', () => ({ Amplify: { configure: vi.fn() } }));
vi.mock('aws-amplify/auth', () => ({ signUp: vi.fn(), signIn: vi.fn(), confirmSignUp: vi.fn(), signOut: vi.fn(), fetchAuthSession: vi.fn(), getCurrentUser: vi.fn(), resetPassword: vi.fn(), confirmResetPassword: vi.fn(), resendSignUpCode: vi.fn() }));
import { Amplify } from 'aws-amplify';
import { signIn as awsSignIn } from 'aws-amplify/auth';
import { buildDevToken, signUp, signIn, signOut, currentUser, getAccessToken } from '../src/auth/cognito';
beforeEach(() => { const m = new Map(); vi.stubGlobal('localStorage', { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) }); });
it('encodes a dev token', () => expect(buildDevToken({ email: 'a@x.test', name: 'A B', studentId: '0012345678', major: '' })).toBe('dev:email=a%40x.test&name=A+B&student_id=0012345678'));
it('registers and signs in without Cognito', async () => {
  expect(await signUp({ email: 'New@Example.test', password: 'x', name: 'New Person', studentId: '0012345678', major: 'Data Science' })).toEqual({ needsConfirm: false });
  expect(await signIn('new@example.test', 'anything')).toEqual({ done: true });
  expect(await getAccessToken()).toBe('dev:email=new%40example.test&name=New+Person&student_id=0012345678&major=Data+Science');
  expect(await currentUser()).toEqual({ email: 'new@example.test', name: 'New Person', groups: [] });
  expect(awsSignIn).not.toHaveBeenCalled(); expect(Amplify.configure).not.toHaveBeenCalled();
});
it('signs out locally', async () => { await signIn('a@x.test', 'p'); await signOut(); expect(await currentUser()).toBeNull(); expect(await getAccessToken()).toBeNull(); });
```

- [ ] **Step 2: Run and confirm the failure.** `npm test` fails in the 2 new places.
- [ ] **Step 3: Implement** in `config-values.js` and `cognito.js`. Existing Cognito and mock branches stay unchanged.
- [ ] **Step 4: Run and confirm everything passes.** `npm test` (all files pass) and `npm run build` (succeeds).
- [ ] **Step 5: Commit.** `git commit -m "feat(frontend): local login mode for running against the real backend without Cognito"`

---

### Task 14: Frontend integration fixes (Integrate Front-end and Back-end, part 2)

**Files:**
- Modify: `src/pages/Projects.jsx` (CreateProject), `vite.config.js`, `.dockerignore`, `.env.example`

**Interfaces:**
- Consumes: `api.listFilterOptions()` (`{categories: [{name, count}], roles}`).

- [ ] **Step 1: Load categories in CreateProject** with `useAsync(() => api.listFilterOptions())`. Options are `opts.data?.categories.map(c => c.name)`, falling back to `CATEGORIES`. When the loaded list doesn't include the current `f.category`, set it to the first loaded name. Mock mode keeps working because its `listFilterOptions` returns the same shape.
- [ ] **Step 2: Add `test: { include: ['tests/**/*.test.js'] }`** to `vite.config.js`. Add `backend` to `.dockerignore`. In `.env.example`, add `VITE_AUTH_MODE=cognito` with a comment explaining `local` (real backend, no Cognito, development only).
- [ ] **Step 3: Verify.** `npm test` (all pass, and only `tests/` files are collected, as `npx vitest list` confirms) and `npm run build` (succeeds).
- [ ] **Step 4: Commit.** `git commit -m "fix(frontend): load Create Project categories from the API; isolate vitest and docker context from backend"`

---

### Task 15: Backend container and documentation

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`, `backend/README.md`
- Modify: `README.md` (root: a "Run with the real backend" section and a project-map line for `backend/`)

- [ ] **Step 1: Write `backend/Dockerfile`.**
  - `python:3.12-slim`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`
  - install `requirements.txt` with `--no-cache-dir`; copy `app/`, `migrations/`, `seed/`
  - non-root user `app`; `EXPOSE 8000`
  - `HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"`
  - `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]`

  `.dockerignore` excludes `.venv`, `tests`, `uploads`, `__pycache__`, `.pytest_cache` and `.env*`.
- [ ] **Step 2: Verify the image.**
  1. `docker build -t teamup-backend backend`
  2. `docker run -d --name teamup-api-check -p 8001:8000 -e DATABASE_URL=postgresql://teamup:teamup@host.docker.internal:5432/teamup -e AUTH_MODE=dev teamup-backend`
  3. `curl -s http://localhost:8001/api/health` must give `{"status":"ok","database":"ok"}`
  4. `docker rm -f teamup-api-check`
- [ ] **Step 3: Write `backend/README.md`:**
  - quick start (compose, venv, `.env`, uvicorn command, seed/reset)
  - environment variable table
  - pgAdmin (http://localhost:5050, password `teamup`)
  - Swagger usage with dev tokens (`dev:john.carter@student.uni.ac.th` is the admin, plus a table of demo logins)
  - running tests
  - "How the backend works" for the presentation: request → router → `current_user` dependency → SQL in a transaction → view builder, with one worked example (accepting a join request)
  - the Jira-ticket-to-file map
  - known limitations (no SES email, presigned PUT can't enforce size, dev mode never in AWS)

  Root README: the 3-terminal local run (db, API, `npm run dev` with `VITE_USE_MOCK=false` and `VITE_AUTH_MODE=local`).
- [ ] **Step 4: Commit.** `git commit -m "docs: backend README, container image, and root run instructions"`

---

### Task 16: End-to-end run in the browser (Integrate Front-end and Back-end, part 3)

**Files:**
- Create (gitignored, not committed): `backend/.env` (`AUTH_MODE=dev`, `UPLOAD_MODE=local`, `SEED_DEMO_DATA=true`) and `.env.local` (`VITE_USE_MOCK=false`, `VITE_AUTH_MODE=local`)
- Modify: whatever the run exposes, each fix with a regression test in the matching backend test file or `tests/`

- [ ] **Step 1: Start the stack.** `docker compose up -d db pgadmin`. Then `.venv/Scripts/python -m uvicorn app.main:app --port 8000 --env-file .env` (background), then `npm run dev` (background). Check `curl -s localhost:5173/api/health` returns `{"status":"ok","database":"ok"}`, which shows the Vite proxy is wired.
- [ ] **Step 2: Drive the journeys in a real browser** (use the `run` skill), checking that each page renders without console errors:
  1. Register a new student, go through Welcome (pick skills), and land on the dashboard.
  2. Edit the profile and save; after a reload the values persist.
  3. Create a project with a cover image; it shows on Explore with filters and sorts working.
  4. Log in as `sophia.martinez@student.uni.ac.th` and accept John's invitation; the team page shows her.
  5. Log in as John: accept Oliver's request, change a member's role, remove a member, toggle recruitment, and read notifications.
  6. As John, open Admin: change periods, remove a reported project, suspend and reactivate a user, and add/delete a category.
- [ ] **Step 3: Confirm persistence in the database.** For example, `docker compose exec db psql -U teamup -c "SELECT id, title FROM projects ORDER BY id DESC LIMIT 3"` lists the project from step 2.3, and `SELECT status FROM requests WHERE id = 6` gives `accepted`.
- [ ] **Step 4: Fix anything the run exposed.** Write a failing regression test first, then fix it, then rerun.
- [ ] **Step 5: Run the final checks.** `.venv/Scripts/python -m pytest -q`, `npm test` and `npm run build` must all pass. Stop the background servers.
- [ ] **Step 6: Commit the fixes.** `git commit -m "fix: issues found in end-to-end run"`, only if there were any.
