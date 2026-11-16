# TeamUp backend

FastAPI + PostgreSQL API for the TeamUp frontend in this repository. It serves every endpoint in
[`docs/API-CONTRACT.md`](../docs/API-CONTRACT.md), with the response shapes of
[`docs/RESPONSE-EXAMPLES.json`](../docs/RESPONSE-EXAMPLES.json), under the `/api` prefix.

- Python 3.12, FastAPI, psycopg 3 (plain SQL, no ORM), PostgreSQL 17
- Swagger UI: **http://localhost:8000/api/docs**
- Design: [`docs/superpowers/specs/2026-11-09-teamup-backend-design.md`](../docs/superpowers/specs/2026-11-09-teamup-backend-design.md)

## Run it locally

Needs Docker Desktop and Python 3.12. Run these commands from this `backend/` folder (PowerShell shown; Git Bash works too with `/` paths).

```powershell
docker compose up -d db pgadmin                      # PostgreSQL on localhost:5434, pgAdmin on localhost:5050
C:\Python312\python.exe -m venv .venv                # once
.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .env.example .env                               # once; local settings (dev login, local uploads, demo data)
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000 --env-file .env
```

On startup the API creates or updates the tables (`migrations/`). Because `SEED_DEMO_DATA=true`, it also loads the demo data the first time.

- Reload the demo data from scratch (**deletes everything**): `.venv\Scripts\python -m app.seed --reset`
- Stop the database: `docker compose down` (your data is kept). `docker compose down -v` also deletes the data.

PostgreSQL runs on host port **5434**, because 5432 and 5433 were already used by other projects on the development machine.

### Use the real backend from the website

In the repository root, create `.env.local`:

```
VITE_USE_MOCK=false
VITE_AUTH_MODE=local
VITE_API_BASE_URL=/api
```

Then run `npm run dev` and open http://localhost:5173. In local mode, any email and any password logs in, so try a demo student from the list below. Registering a new email works too. Vite forwards `/api` requests to the API on port 8000.

## Try the API in Swagger

1. Open http://localhost:8000/api/docs and click **Authorize**.
2. Enter a dev token, which is `dev:` followed by an email, for example `dev:john.carter@student.uni.ac.th`.
3. Open any endpoint, then click **Try it out** and **Execute**.

A dev token for an email that doesn't exist yet creates a new student. You can also pass details, such as `dev:email=new%40x.test&name=New%20Person&student_id=0012345678`.

Demo students (all emails end in `@student.uni.ac.th`):

| Login | Who | Good for showing |
|---|---|---|
| `john.carter` | Admin; owns *Campus Food Waste Tracker* | Accepting the 2 pending join requests, Henry's invitation, Admin page |
| `sophia.martinez` | Has John's invitation | Accepting an invitation |
| `oliver.smith` | Owns *AI Study Buddy Chatbot*; asked to join John's project | Cancelling a request, owner view |
| `henry.moore` | Owns *Mobile Health Reminder* | Invitations sent |
| `emma.wilson` | Backend Developer on John's team | Member view, leaving a team |
| `jack.scott` | Suspended | Every request gets "Your account has been suspended." |

Dev tokens work only when the API runs with `AUTH_MODE=dev`, which is local only. In AWS it runs with `AUTH_MODE=cognito` and rejects them.

## Look at the database (pgAdmin)

Open http://localhost:5050. The server **TeamUp (local)** is already registered; its password is `teamup`. The tables are under *Databases → teamup → Schemas → public*. Use *Query Tool* to run SQL, for example:

```sql
SELECT p.title, r.name AS role, u.name AS member
FROM project_roles r JOIN projects p ON p.id = r.project_id LEFT JOIN users u ON u.id = r.user_id
ORDER BY p.id, r.position;
```

## Configuration

| Variable | Meaning | Local (`.env`) | AWS |
|---|---|---|---|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://teamup:teamup@localhost:5434/teamup` | not used (see `DB_*`) |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE` | Database connection in parts, used when `DATABASE_URL` is empty; any password characters work | — | RDS address; user and password from Secrets Manager; `require` |
| `AUTH_MODE` | `cognito` (verify Cognito tokens) or `dev` (test tokens) | `dev` | `cognito` (the default) |
| `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID` | The user pool whose tokens are accepted | — | required |
| `UPLOAD_MODE` | `off`, `local` (files in `UPLOAD_DIR`) or `s3` | `local` | `s3` |
| `UPLOAD_DIR` | Folder for local uploads | `uploads` | — |
| `S3_BUCKET`, `S3_REGION`, `PUBLIC_FILE_BASE_URL` | Where cover images go and how they are read back | — | required for `s3` |
| `SEED_DEMO_DATA` | Load the demo data at startup if the database is empty | `true` | as wanted |
| `EMAIL_MODE` | `off`, `log` (print each email to the terminal) or `ses` (send through Amazon SES) | `log` | `ses` once a team address is set |
| `EMAIL_FROM`, `EMAIL_REGION` | The sender address (verified in SES) and the SES region | — | the team address; Tokyo |
| `EMAIL_DEMO_INBOX` | Where emails for the made-up demo addresses (`@student.uni.ac.th`) go. Empty: they aren't sent | — | the team address |
| `APP_URL` | The site's address, for the links in emails | `http://localhost:5173` | the CloudFront address |

If `AUTH_MODE=cognito`, `UPLOAD_MODE=s3` or `EMAIL_MODE=ses` is missing any of its settings, the API refuses to start and logs which variables are missing. Otherwise every login would just be rejected without explanation.

## Tests

```powershell
.venv\Scripts\python -m pytest
```

The tests use a separate `teamup_test` database, recreated on every run, so the `db` container must be running. They cover every endpoint, the permission rules, the Cognito token checks (with a locally generated key), two people accepting for the last place at the same time, and a contract check: every key in `docs/RESPONSE-EXAMPLES.json` must appear in the real responses.

## How the backend works

```
browser ──HTTP──> FastAPI route (app/routers/*.py)
                    ├─ Pydantic model checks the JSON body ............ 422 if invalid
                    ├─ Depends(current_user) in app/auth.py ............ 401 / 403
                    ├─ SQL inside `with conn.transaction():` ........... 404 / 409 rules
                    └─ view builder (app/views.py) builds the JSON the screens expect
```

**Worked example: an owner accepts a join request** (`PATCH /api/requests/{id}`, in `app/routers/requests.py`):

1. FastAPI parses `{"status": "accepted"}` into `RespondIn`. Any other value gets an automatic 422.
2. `current_user` checks the token and loads the owner's `users` row.
3. `respond_to_request` opens a transaction and:
   1. Runs `SELECT … FROM projects … FOR UPDATE`. This locks the project, so a second acceptance for the same project waits here.
   2. Locks the request, then checks that the caller is the owner (403) and that the request is still pending (409).
   3. Checks that the team isn't full (409) and puts the student in an open place for that role. That's an `UPDATE project_roles … SET user_id`.
   4. Marks the request accepted and writes the notifications.
   5. If the team is now full, rejects everyone else who is still waiting.
4. COMMIT. Either all of it is saved or none of it.
5. `request_views` builds the response JSON.

The match score is SQL too: `match_score(project_id, user_id)` in `migrations/001_init.sql`. Team status (`recruiting`, `full` or `closed`) is the view `project_summary`.

## Where things are (Jira tickets)

| Jira ticket | Files |
|---|---|
| Develop User Authentication and Profile API | `app/auth.py`, `app/routers/users.py` |
| Develop Project Management API | `app/routers/projects.py` |
| Develop Search and Matching API | `app/routers/search.py`, `app/matching.py`, `match_score()` in `migrations/001_init.sql` |
| Develop Join Request and Invitation API | `app/routers/requests.py`, `app/places.py` |
| Develop Team Management API | `app/routers/teams.py`, `app/places.py` |
| Set Up Database | `migrations/001_init.sql`, `seed/demo.sql`, `app/db.py`, `docker-compose.yml` |
| Integrate Front-end and Back-end | `src/auth/cognito.js` (local login), `src/config-values.js`, `src/pages/Projects.jsx` (categories), `tests/test_contract.py` |

Also: `app/routers/notifications.py`, `app/routers/admin.py`, `app/routers/uploads.py`, and the view builders in `app/views.py`.

## Known limitations

- Only five events send email, following the student's email switches: a join request (to the owner), the owner's answer (to the student), an invitation (to the student), the student's answer (to the owner) and a removal (to the removed member). The rest are in-app only, and the weekly digest isn't built. Emails go out on a background thread after the change is saved (`app/notify.py`, `app/mailer.py`). A failed email is logged, not retried.
- A presigned S3 upload link can't enforce the 5 MB limit. The browser checks the size, and the local upload mode enforces it.
- The local upload links are kept in memory: they're lost when the API restarts, and they need a single API process.
- `AUTH_MODE=dev` must never be used in AWS. Anyone could claim any email.
