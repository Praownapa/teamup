# TeamUp Backend: Design

Date: 2026-11-09. Status: draft, waiting for approval.
Covers the backend, the database and the frontend integration. AWS deployment gets its own design once this runs locally.

## Why

TeamUp's screens are finished, but they run on fake in-browser data (`src/api/mock.js`). The group needs a working online app for the final demo. The roadmap puts the backend and database first, then the integration, then AWS. This work covers the user's Jira tickets: the Auth/Profile, Project Management, Search & Matching, Join Request & Invitation and Team Management APIs, Set Up Database, and Integrate Front-end and Back-end. The user's teammates will judge the result in the final presentation, which summarizes each member's contribution. That means the user needs to understand and explain this code, especially the database.

Treat the deadline as tomorrow. If time runs short, the core user journeys come before completeness (see Priority order).

## Goals

- A FastAPI backend in `backend/` that implements all 30 method/path entries in `docs/API-CONTRACT.md` and returns the shapes in `docs/RESPONSE-EXAMPLES.json`, so the existing screens work without redesign.
- Behavior follows `src/api/mock.js`, plus the server rules it skips: ownership and permission checks, a hard team-size limit, no duplicate pending requests or invitations, atomic acceptance, and blocking of suspended users and removed projects.
- PostgreSQL with plain, readable SQL that the user can present table by table and query by query.
- Swagger at `/api/docs`, where every endpoint can be tried as any demo user (the roadmap's "Test the APIs using Swagger or Postman").
- The frontend runs against the real backend and database on the user's machine, before any AWS access exists.
- Demo data, so the app doesn't start empty.
- The backend is ready to containerize for ECS: Dockerfile, environment-variable config, a health check, and migrations that run on startup.

## Non-goals (for this design)

- AWS provisioning and deployment. That's the next design, against an instructor-provided account whose limits are still unknown. Testing the real Cognito login end to end also waits for that account; until then the `cognito` mode is covered by automated tests with locally generated tokens.
- Sending email through SES. In-app notifications are built; email preferences are stored but nothing is sent. The UI copy that promises email stays as it is.
- The weekly digest, the "new matching projects" notification, real-time push, pagination, profile photos, MFA, and a university-email domain rule.
- Changing the API contract (routes, verbs, field names, numeric IDs).

## Anti-goals (a failure even if it works)

- ORM or framework magic the user can't explain. No hidden SQL.
- Any route that trusts identity, role or ownership from the request body.
- Dev/local login reachable in the deployed app.
- Breaking the existing frontend tests or mock mode.

## Decided by the user

- The backend lives in a `backend/` folder of this repo.
- Claude writes the code and explains the FastAPI parts. The user knows SQL and has no FastAPI experience.
- Build every endpoint the frontend calls, including notifications, admin, dashboard/counts and uploads.
- Deployment goes to an instructor-provided AWS account (credentials still pending), after the backend works locally.
- Stack, from the group's roadmap: FastAPI, PostgreSQL, Cognito, then RDS/ECR/ECS Fargate/ALB.

## Architecture

```
Browser (React, Vite dev server :5173)
   │  /api/*  (Vite proxy, already configured)
   ▼
FastAPI (uvicorn :8000) ──► PostgreSQL (Docker locally, RDS later)
   │
   └─ verifies Cognito access tokens (JWKS); on first visit reads the
      user's attributes from Cognito GetUser
```

All routes are served under `/api`: Vite keeps the prefix, and the planned ALB routes `/api/*` to the backend. Requests are same-origin in both places, so no CORS config is needed.

## Code layout (mapped to the Jira tickets)

```
backend/
  app/
    main.py            app setup, routers, /api/health, /api/docs
    config.py          settings from environment variables
    db.py              connection pool, migration runner, seed runner
    auth.py            token checking (cognito | dev), current-user dependency   ← Auth & Profile
    views.py           builds the JSON shapes the screens expect
    matching.py        role-fit heuristic (match score itself is a SQL function)  ← Search & Matching
    notifications.py   helper that writes notification rows
    routers/
      users.py         /users/me, /users/{id}, counts, dashboard                 ← Auth & Profile
      projects.py      create, detail, update, save, report                       ← Project Management
      search.py        GET /projects, /projects/filters, recommendations          ← Search & Matching
      requests.py      join requests, invitations, respond, cancel, list          ← Join Request & Invitation
      teams.py         change role, remove member, leave team                     ← Team Management
      notifications.py, uploads.py, admin.py
  migrations/001_init.sql                                                         ← Set Up Database
  seed/demo.sql
  tests/
  requirements.txt, requirements-dev.txt, Dockerfile, docker-compose.yml, .env.example, README.md
```

Swagger groups endpoints by tag in the same order, so the docs page mirrors the tickets.

Stack details: Python 3.12, FastAPI with sync endpoints, psycopg 3 with psycopg-pool, Pydantic request models, PyJWT for token checks, httpx for the Cognito GetUser call, boto3 for S3 presigning, pytest. Versions are pinned in `requirements.txt` at install time. Local PostgreSQL 17 runs via `docker-compose.yml`.

## Database

One migration file creates everything. The runner records applied files in `schema_migrations` and runs on app startup under a Postgres advisory lock, so two containers can't migrate at once.

| Table | Purpose / key columns |
|---|---|
| `users` | `id`, `cognito_sub` (unique, nullable for demo users), `email` (unique, case-insensitive), `name`, `student_id` (text, keeps leading zeros), `major`, `year` (1–6, default 1), `role` (`student`/`admin`), `status` (`active`/`suspended`), `bio`, `portfolio`, `open_to_projects`, four `notify_*` booleans, `created_at` |
| `user_skills` | `user_id`, `name`, `level` (`Beginner`/`Intermediate`/`Advanced`), `position`; unique per user on `lower(name)` |
| `user_interests` | `user_id`, `name`, `position`; unique per user on `lower(name)` |
| `categories` | `name` (case-insensitive unique), `created_at` |
| `projects` | `id`, `owner_id`, `title`, `description`, `category` (text label), `course`, `cover_url`, `max_size` (2–10), `accepting`, `deadline` (date, nullable), `duration`, `meeting`, `created_at`, `removed_at` (set when an admin removes it) |
| `project_skills` | required skills; unique per project on `lower(name)` |
| `project_roles` | one row per team place: `project_id`, `name`, `user_id` (NULL = open spot), `position`. Partial unique index on (`project_id`, `user_id`) where `user_id` is not NULL, so one person holds at most one place |
| `requests` | join requests and invitations: `project_id`, `user_id` (the student), `by_id` (inviter, NULL for join requests), `kind` (`request`/`invitation`), `role`, `message`, `status` (`pending`/`accepted`/`rejected`), `created_at`, `responded_at`. Partial unique index on (`project_id`, `user_id`) where status is `pending` |
| `saved_projects` | (`user_id`, `project_id`) primary key |
| `reports` | `project_id`, `reporter_id`, `reason`, `status` (`open`/`removed`/`dismissed`), `created_at`, `resolved_at`, `resolved_by`. One open report per reporter per project |
| `notifications` | `user_id` (recipient), `kind` (`request`/`invite`/`accepted`/`declined`/`team`), `text`, `request_id` (FK, ON DELETE CASCADE), `unread`, `created_at` |

The team is the set of `project_roles` rows that have a `user_id`. The owner always holds one place. A project is `full` when its members number at least `max_size`. Otherwise it's `recruiting` when `accepting` is true, and `closed` when it isn't. This lives in a SQL view, `project_summary` (member count, status).

The match score is a SQL function, `match_score(project_id, user_id)`: the share of the project's required skills the user has, matched case-insensitively on exact names and rounded half-up like JS `Math.round`. It's 0 when the project has no required skills. Search, project views, dashboard and recommendations all use it.

Demo data (`seed/demo.sql`) recreates the mock's 18 students, 6 projects, requests, saved project, categories and user 1's notifications. Emails are friendlier: `firstname.lastname@student.uni.ac.th`. User 1, John Carter, is the admin. Two extra spam-like projects with open reports give the admin page something to moderate. Dates are relative to the seeding time, so the demo looks current on any day. Seeding happens with `python -m app.seed`, or on startup when `SEED_DEMO_DATA=true` and the `users` table is empty.

## Authentication and authorization

Every route except `/api/health` and the docs requires `Authorization: Bearer <token>`. `AUTH_MODE` selects how the token is checked:

- **`cognito` (default; the only mode for AWS).** Verify the RS256 signature with the pool's JWKS (cached), `iss`, `exp`, `token_use == "access"` and `client_id`. Identity comes from `sub`. On the first request for an unknown `sub`, call Cognito `GetUser` with the same access token. It needs no AWS credentials and returns `email`, `name`, `custom:student_id` and `custom:major`. Then insert the profile with `INSERT … ON CONFLICT DO NOTHING`, so two simultaneous first requests create exactly one user. If a row with that email exists and has no `cognito_sub` yet, link it instead. Admin is decided by the `admin` Cognito group (the `cognito:groups` claim), and the `users.role` column is updated to match on each request.
- **`dev` (local only).** The token is `dev:<email>`, or `dev:email=…&name=…&student_id=…&major=…` URL-encoded. The user is looked up by email and created on first use from the other fields. A missing name defaults to the part of the email before the @, and a missing student ID to "". Admin is decided by `users.role`, which makes seeded John Carter an admin. Startup logs a loud warning in this mode. In `cognito` mode, dev tokens are rejected.

Rules applied on every request:
- Suspended users get 403 "Your account has been suspended." on every endpoint.
- Admin routes return 403 for non-admins.
- Removed projects are hidden from lists, search, dashboards and profiles, and return 404 to non-admins.
- Missing or invalid tokens get 401 (the frontend then redirects to /login). Permission failures get 403, missing records 404, business-rule conflicts 409 (duplicate, full team, already handled, role taken), and bad input 400/422. Errors use FastAPI's `{"detail": "..."}`, which `src/api/error-message.js` already displays.

## API behavior

Shapes and routes are exactly those in `docs/API-CONTRACT.md` and `docs/RESPONSE-EXAMPLES.json`. The rules below are the ones that go beyond, or differ from, `mock.js`.

**Profile (Auth & Profile).** `PUT /users/me` is a partial update. It changes only the fields present among: name, major, year, bio (≤400), portfolio, open_to_projects, skills, interests and notify (notify keys are merged). Any other field, such as role, status, email or student_id, is ignored. Skills and interests are replaced as whole lists. `GET /users/{id}` returns only the public fields (no email or student ID). Counts and dashboard follow `mock.js` exactly.

**Projects (Project Management).** Create validates what the form validates:
- title required, ≤80 characters; description required, ≤2000
- category must exist in `categories`
- at least 1 skill and at least 1 named role; each role 1–4 spots
- `max_size` 2–10, with owner + spots ≤ `max_size`
- blank duration/meeting stored as `—` (as in the mock); blank deadline is NULL and returned as `""`

The owner's place uses `owner_role`, or "Project Owner" if blank. `PATCH` is owner-only and accepts title, description, category, course, cover_url, duration, meeting, deadline and accepting, with the same validation. Save toggles a row. Reporting is not allowed on your own project, and reporting again replaces your open report's reason.

**Search & Matching.** `GET /projects` does its filtering and sorting in SQL:
- `q` matches title, description or skill names (case-insensitive)
- `categories` and `skills` are comma lists; every listed skill must be a substring of some required skill
- `role` must be an exact open role
- `recruiting=true` means status recruiting; `spots=true` means at least 2 open places
- sort is `match`, `newest` or `spots`, with newest-first as the tie-break

Then it builds the full project views. Filters return all categories with project counts, plus the sorted distinct open role names.

Recommendations are owner-only. Candidates are active users who are open to projects and not on the team. Each gets a `match` score and a suggested `fits` role from a keyword heuristic that extends the mock's (front-end, back-end, UI/UX, cloud, data, mobile, ML, QA, hardware). It falls back to the first open role, or `—` when there's none. Each also gets the `invited` flag. The list drops candidates with match 0 and no fit, and is sorted by match.

**Join requests and invitations.**
- Join: the project must be `recruiting`, the role must be one of its open roles, the requester can't be the owner or a member, the message is ≤500, and there's at most one pending request or invitation per person per project. The unique index enforces this, so a duplicate is a 409; if the person already has a pending invitation, the message points them to their invitations.
- Invite: owner-only. The invitee must be active and open to projects, and not a member. The team must not be full, and the role must be open. Invitations are allowed while recruitment is paused (the "invitation only" setting).
- List: returns everything where the viewer is the student, the inviter or the project owner. `type` is computed per viewer exactly as in `mock.js`.
- Cancel: only the applicant can cancel, only a pending join request, and it deletes the row (the UI has no "cancelled" status). Notifications about it disappear through the cascade.
- Respond: owners respond to join requests, invitees to invitations, and the request must still be pending.
- Accept runs in one transaction:
  1. Lock the request and the project rows (`SELECT … FOR UPDATE`) and re-check the rules.
  2. If the team is full, return 409.
  3. Put the person in an open place with the requested role name. If none is open and the project has fewer places than `max_size`, add a place with that name. Otherwise return 409 "That role has already been filled."
  4. Mark the request accepted.
  5. If the team is now full, reject every other pending request and invitation for the project and notify those people.
  6. Write the notifications, then commit.

  Two simultaneous acceptances for the last place produce exactly one member and one 409. Responding marks that request's notifications as read.

**Team management.** All owner-only except leave:
- Change role: move the member to an open place with that name if one exists, otherwise rename their place (as in the mock).
- Remove: frees the place, notifies the removed person, and returns the full project view.
- Leave: members only (the owner can't leave), frees the place, notifies the owner, and returns 204.
- Owners can't change their own role or remove themselves through the member endpoints.

**Notifications** are written in the same transaction as the event, with the mock's wording:
- `request`: to the owner, on a new join request (with `request_id`).
- `invite`: to the invitee, on an invitation (with `request_id`).
- `accepted`: to the applicant, when their request is accepted.
- `declined`: to the applicant on rejection or auto-rejection; to the owner when an invitee declines.
- `team`: to the owner when an invitation is accepted; to other members when someone joins; to the person removed; to the owner when someone leaves; to a member whose role changed; to the owner when an admin removes their project.

List shows the viewer's own notifications, newest first (up to 100). Read and read-all only affect the viewer's own rows.

**Admin.**
- Overview `stats`:
  - totals: students = users, projects = non-removed projects, teams = projects with at least 2 members, reports = projects with open reports
  - `deltas`: counts created within the period (7d / 30d / semester = 120 days); teams are approximated as qualifying projects created in the period
- `activity` buckets: 7 daily buckets for 7d, 5 weekly buckets for 30d, 16 weekly for semester. The labels go in the `week` field.
- Reports are grouped one row per project:
  - `id` is the latest report's id, `reason` the latest reason, `reporters` the count, `created_at` the latest
  - resolving that id resolves every open report on the project
  - `removed` sets `removed_at`, rejects the project's pending requests and notifies the owner
- Users list: as in the mock. Admins and yourself can't be suspended.
- Categories: adding is idempotent. Deleting only removes the option; existing projects keep their label.

**Uploads.** `POST /uploads/presign` accepts PNG, JPEG and WebP. `UPLOAD_MODE` selects the mode:
- `s3` (AWS): boto3 returns a presigned PUT URL (5 minutes) for `covers/<user_id>/<uuid>.<ext>`, plus a public `file_url` (bucket URL, or `PUBLIC_FILE_BASE_URL`).
- `local` (development): returns `/api/uploads/local/<key>` for the PUT (5 MB limit, type checked) and `/api/uploads/files/<key>` to read it. Files are stored in `backend/uploads/`, which is gitignored.
- `off`: returns 503 "Image uploads are not configured."

A presigned PUT can't enforce the 5 MB limit. That's documented as a known limitation.

## Frontend integration changes

Kept small, and mock mode keeps working:
1. `src/config-values.js`: add `authMode` (`cognito` | `local`, default `cognito`, from `AUTH_MODE` / `VITE_AUTH_MODE`, validated), with matching tests in `tests/config.test.js`.
2. `src/auth/cognito.js`: in `local` mode, sign-in and sign-up accept anything, registration details are kept in localStorage, `getAccessToken()` returns the `dev:` token, and Amplify isn't configured. Sign-up returns `needsConfirm: false`, so registration goes to login and then the Welcome step. `currentUser()` returns no groups, so the admin menu comes from `profile.role`, which the existing `isAdmin` check already reads.
3. `src/pages/Projects.jsx` (CreateProject): load categories from `GET /projects/filters`, falling back to the current list. This fixes the gap in the handoff.
4. `.env.example`: document `VITE_AUTH_MODE`. `vite.config.js`: limit Vitest to `tests/**`. `.dockerignore`: exclude `backend/`. `.gitignore`: add `backend/.venv/`, `backend/uploads/`, `__pycache__/` and `.pytest_cache/`.
5. Root `README.md`: how to run frontend and backend together.

## Local development and testing

- Where the data lives: locally, in a named Docker volume, so it survives restarts (`docker compose down -v` wipes it); in AWS later, in Amazon RDS for PostgreSQL. The same migration file creates the tables in both.
- `docker-compose.yml` also runs pgAdmin at http://localhost:5050, with the TeamUp database pre-registered, so the user can browse tables and confirm that data is saved (a roadmap item).
- `docker compose up -d db` (in `backend/`) starts PostgreSQL. A venv plus `uvicorn app.main:app --reload --port 8000` runs the API, and `npm run dev` runs the frontend with `.env.local` set to `VITE_USE_MOCK=false` and `VITE_AUTH_MODE=local`.
- pytest runs against a real PostgreSQL test database (`teamup_test`, recreated per run and truncated between tests) using FastAPI's test client and dev tokens. Required coverage:
  - auth: dev and Cognito, the latter with a locally generated RSA key/JWKS and a mocked GetUser
  - happy path and key rule failures for every endpoint
  - permission checks for owner, member, outsider and admin
  - the last-place concurrency test
  - a contract test that compares response keys with `docs/RESPONSE-EXAMPLES.json`
- Existing `npm test` and `npm run build` must still pass.

## What the deployment design will rely on

- `backend/Dockerfile`: python:3.12-slim, non-root, uvicorn on port 8000.
- All config through environment variables: `DATABASE_URL`, `AUTH_MODE`, `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `UPLOAD_MODE`, `S3_BUCKET`, `S3_REGION`, `PUBLIC_FILE_BASE_URL`, `SEED_DEMO_DATA`.
- Health check at `GET /api/health`, which also checks the database.
- Logs go to stdout. Migrations run on startup.

## Priority order (if time runs short)

1. Schema, demo data, auth, profile/counts/dashboard, projects (create, detail, search, filters), join/invite/respond/cancel/list, team management, notifications, and the frontend local mode, plus integration of login, profile, project creation and team management (the roadmap's named features).
2. Recommendations, admin, uploads, reports.
3. Extra tests, docs polish.

## Calls Claude made (please check)

- Plain SQL with psycopg instead of an ORM. The match score and team status live in the database as a SQL function and a view.
- A dev token mode for Swagger and local work, plus a frontend `local` login mode, so the integration doesn't wait for the AWS account.
- Accepting into a role whose places are all taken returns 409 instead of the mock's silent switch to another role.
- Cancelling a join request deletes it, as the mock does.
- Admin comes from the Cognito `admin` group in AWS, and from the database role locally.
- Suspended users are blocked on every endpoint; removed projects disappear for non-admins.
- Demo data uses friendlier emails, adds two reported spam projects, and uses dates relative to the seeding time.
- Deadlines are informational only; nothing is enforced by date.
- Admin metrics definitions and chart buckets as described above.
- No email sending in this phase.

## Left to the builder

Exact DDL, indexes and constraint names; module internals; query structure; the exact notification wording beyond the examples above; the test fixture design; demo data details beyond what's listed; library versions (pinned at install).
