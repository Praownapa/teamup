# TeamUp Frontend

React SPA with Vite, Cognito authentication adapter, mock API and Docker/Nginx deployment files. Reviewed 2026-10-30. Ready for team handoff and integration work; **not production acceptance or AWS deployment approval**. No GitHub push or AWS deployment was performed.

## Run locally

Use Node.js ^22.12.0, ^24.0.0 or >=26.0.0 and npm (Node 24 tested). Docker build uses Node 22.

```sh
npm install
npm test
npm run build
npm run dev
```

Open http://localhost:5173. Without local configuration the app uses mock data. Login accepts any syntactically valid email and any nonempty password. All mock logins use the same synthetic profile with admin access; data mutations live in memory and reset on full reload. Mock signup/reset/email/upload do not contact AWS. Do not use this mode for production access control.

`npm ci` reproduces the included lockfile. Commit `package-lock.json`; do not replace it with a freshly resolved dependency set without review.

## Run with the real backend (local, no AWS needed)

The FastAPI + PostgreSQL backend lives in [`backend/`](backend/README.md). Use three terminals:

1. Database: `cd backend` and `docker compose up -d db pgadmin` (PostgreSQL on port 5434, pgAdmin on http://localhost:5050).
2. API: in `backend/`, run `.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000 --env-file .env`. Setup is in [backend/README.md](backend/README.md). Swagger is at http://localhost:8000/api/docs.
3. Website: create `.env.local` with `VITE_USE_MOCK=false`, `VITE_AUTH_MODE=local` and `VITE_API_BASE_URL=/api`, then run `npm run dev`.

`VITE_AUTH_MODE=local` skips Cognito: any email and password signs in, and the backend (running with `AUTH_MODE=dev`) creates or loads that student. Demo logins include `john.carter@student.uni.ac.th` (admin). Use `VITE_AUTH_MODE=cognito` (the default) with a real user pool; the deployed site always uses Cognito.

## Configuration and switching to the real API

Priority: **explicit `window.__CONFIG__` runtime value > Vite `VITE_*` build value > default**. `public/config.js` is intentionally `{}` for local development. Default API base is `/api`, default local mock mode is true. Boolean values must be true/false; invalid mock settings fail rather than silently selecting another mode. API base trailing slashes are removed.

1. Copy `.env.example` to `.env.local`.
2. Set `VITE_USE_MOCK=false`, replace the Cognito placeholders, and use `VITE_API_BASE_URL=/api` for the local proxy.
3. Restart Vite after changing `.env.local`. For static hosting, Vite values are baked in at build time; rebuild after changes.
4. Run the backend on `http://localhost:8000`. Vite forwards `/api/...` unchanged. The backend must serve that prefix or the teams must explicitly agree a proxy rewrite.
5. Check browser Network requests and the integration checklist in `docs/HANDOFF.md`.

Docker rewrites `/config.js` at startup from `API_BASE_URL`, `USE_MOCK`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`; these explicit values override Vite build values. Docker defaults to **USE_MOCK=false**, so supply real Cognito IDs, or explicitly choose true for a demo. Nginx serves config with `no-store`. Restart containers after changing runtime values. The startup script accepts simple URL/identifier characters and rejects quotes, whitespace and other unsafe JS string characters.

All `VITE_*` values, runtime config and frontend bundles are public. User Pool ID / App Client ID identify public resources; **client secrets, AWS access keys, database credentials and private keys never belong here**.

## Cognito setup

- Email sign-in and email verification; App Client **without client secret**, with the auth flows required by Amplify enabled.
- Create custom attributes `student_id` and `major` in the User Pool (API names `custom:student_id` and `custom:major`). Use String for student_id to preserve leading zeros. Grant the App Client appropriate attribute read/write permissions. Frontend sends both at registration (major omitted only when empty).
- Password UI requires at least 8 characters, uppercase, lowercase and a digit. Match the pool policy; if symbols/MFA/custom challenges are required, extend the UI and tests. Extra sign-in challenges currently show a message, not an MFA flow.
- Create the `admin` group and assign admins deliberately. Backend checks authorization independently of the UI.
- Backend creates/loads its profile by verified Cognito `sub`. Profile name/major edits currently go to the backend, not back to Cognito; decide which store is authoritative and how to synchronize.
- Remember-me uses a sessionStorage marker and signs out on a later app load without it; this is not a guarantee that closing a browser destroys tokens. Test tab/browser restore behavior before setting a production session policy.

## API and handoff documents

- [Complete API methods, bodies and response rules](docs/API-CONTRACT.md)
- [Synthetic response examples](docs/RESPONSE-EXAMPLES.json)
- [Handoff and integration checklist](docs/HANDOFF.md)
- [Changes](CHANGELOG.md) and [test evidence / limitations](docs/TEST-REPORT.md)

`src/api/endpoints.js` defines 31 frontend functions mapped to 30 method/path entries (getTeam shares getProject). `src/api/mock.js` supplies example shapes. Admin calls `/admin/overview?period=...` relative to the base, not `/api/admin/stats`. There is no GET members endpoint and no POST `/requests`: use GET project detail and POST `/projects/{id}/requests`.

## Project map

`src/pages/` contains auth, dashboard, projects, teams and account/admin pages. `src/auth/` wraps Amplify and session/profile state. `src/api/` contains real/mock selection and HTTP errors. `src/utils/` contains loading, uploads, password and date helpers. `src/components/` and `src/styles/` contain UI and styling. `tests/` contains regression tests. `deploy/` contains templates, not a provisioned AWS environment. `backend/` contains the FastAPI API, database migrations, demo data and its pytest suite (see [backend/README.md](backend/README.md)).

## Deployed on AWS

TeamUp runs in the instructor's AWS account, which the whole class shares, in **Tokyo (`ap-northeast-1`)**:
**https://d2u84idlq1gpr5.cloudfront.net**. Everything is defined in [`infra/`](infra/) (CloudFormation templates and bash scripts), and every resource is named `des424-126-g07-teamup-*` and tagged `project=teamup`.

```
Browser
  ├─HTTPS─► CloudFront  https://d2u84idlq1gpr5.cloudfront.net
  │           ├─ /covers/*        ─► S3 bucket (private; readable only through CloudFront)
  │           └─ everything else  ─HTTP─► ALB (public subnets; accepts only our CloudFront)
  │                                         ├─ /api/*  ─► backend (ECS Fargate, FastAPI :8000) ─► RDS PostgreSQL 17 (private subnets)
  │                                         └─ other   ─► website (ECS Fargate, nginx :80)
  ├─HTTPS─► Cognito user pool (sign-up, sign-in, email codes, tokens)
  └─HTTPS─► S3 presigned PUT (cover upload; the backend hands out the URL)
```

| Stack | What it holds |
|---|---|
| `des424-126-g07-teamup-network` | TeamUp's own VPC: two public subnets (load balancer and containers), two private subnets (the database only, no route to the internet) and the firewall rules. No NAT gateway. |
| `des424-126-g07-teamup-data` | RDS PostgreSQL 17 with its generated password in Secrets Manager, the cover-image bucket, the Cognito user pool with its `admin` group, and the two image repositories (ECR). A stack policy stops any update from replacing them. |
| `des424-126-g07-teamup-app` | The ECS cluster with the backend and website services, the load balancer, CloudFront, the IAM roles and the logs. |

**Demo logins.** Every demo student in `backend/seed/demo.sql` has a Cognito login, and they all share one password. It's kept in AWS Systems Manager → Parameter Store (Tokyo) → `/des424-126-g07-teamup/demo-password` (click *Show decrypted value*), never in git. `john.carter@student.uni.ac.th` is the admin and `jack.scott@student.uni.ac.th` is suspended. Real sign-ups work too: Cognito emails a code.

**Commands.** Run these from the repository root in Git Bash, after signing in with `aws login --profile teamup` in PowerShell.

| Command | What it does |
|---|---|
| `bash infra/deploy.sh` | Creates or updates everything: the three stacks, both images (tagged with the git commit) and the demo accounts. Then it runs the smoke test. It needs Docker Desktop and a clean git tree, and it's safe to re-run. |
| `bash infra/smoke-test.sh` | 13 live checks of the deployed site (the deploy runs it too). |
| `bash infra/reset-demo-data.sh --yes` | Deletes all app data online and loads the demo data again, for example before the presentation. Cognito logins stay. |
| `bash infra/delete.sh` | A dry run that lists everything that would be deleted. `--really-delete` deletes it all, including the database (no copy is kept). |
| `infra/.venv/Scripts/python -m pytest infra -q` | Offline checks of the templates' security, cost and naming rules, plus cfn-lint. Set it up once with `python -m venv infra/.venv` and `infra/.venv/Scripts/python -m pip install -r infra/requirements-dev.txt`. |

**Where to find it in the AWS console.** Switch the region (top right) to **Asia Pacific (Tokyo)**. In Singapore you'd only see other groups' resources. Then:

- **CloudFormation → Stacks:** each stack's *Resources* tab links to everything it created.
- **ECS → Clusters → `des424-126-g07-teamup`:** the services, their tasks and their logs.
- **RDS → Databases → `des424-126-g07-teamup-db`**.
- **Cognito → User pools → `des424-126-g07-teamup-users`:** the users and the `admin` group.
- **CloudFront:** the distribution "TeamUp (des424-126-g07)". CloudFront is global, so it shows in any region.
- **VPC → Your VPCs → `des424-126-g07-teamup-vpc`**.
- **S3 → `des424-126-g07-teamup-covers-528301714999`**.
- **Resource Groups & Tag Editor:** search for the tag `project=teamup` to see every resource at once.

**Security.**
- The database accepts connections only from the backend containers and has no route to the internet.
- The load balancer only answers requests that come through our CloudFront.
- The deployed website always signs in with Cognito, and the backend runs `AUTH_MODE=cognito`, so dev tokens are rejected.
- The database and demo passwords are generated, and live only in Secrets Manager and Parameter Store.

**Cost.** About $3 a day while it runs: the load balancer, two small Fargate tasks, the micro database, four public IPv4 addresses and one secret. CloudFront, S3, Cognito and the logs are nearly free at this size. The account's $200/month budget is shared by the whole class, so delete the setup when it's no longer needed.

**Limitations.**
- The 5 MB cover-image limit is only checked in the browser, because a presigned upload can't enforce it.
- No email goes out through SES. Notifications are in-app. Cognito's built-in email sends the sign-up and password-reset codes, about 50 a day.

## Docker and deployment

The deployed setup is in **Deployed on AWS** above. The `deploy/` files below are the earlier frontend-only templates from the handoff.

```sh
docker build -t teamup-frontend .
docker run --rm -p 8080:80 -e USE_MOCK=true teamup-frontend
```

At handoff, Docker wasn't available in the review environment, so the container build and the AWS smoke tests were still pending. Both now run through `infra/` (see Deployed on AWS). Build uses `npm ci` only (lockfile failures must be fixed, not silently bypassed). Shell files use LF via `.gitattributes`.

For real ECS deployment: provision ECR/ECS, execution role, logging, networking/security groups, service/target group and HTTPS/ACM first. Replace placeholders in `deploy/task-definition.json`, register the task definition, create the service and configure ALB `/api/*` to the backend and the default rule to frontend; health path `/health`. Backend requests must keep the agreed `/api` prefix. `deploy/deploy.sh` builds/pushes both a timestamp/commit tag and `latest`, then forces an existing service deployment; it does not provision infrastructure or register a new revision. Its redeploy works only if the service points to the expected `latest` image. Prefer a separately reviewed immutable-tag task revision for production.

Same-origin ALB API calls do not need browser API CORS. A different API origin does. S3 PUT uploads need their own bucket CORS for allowed frontend origins, PUT and Content-Type; backend signs uploads and validates ownership, MIME/size, expiration and key scope. Never put S3 credentials in the browser. Configure how `file_url` remains readable.

## Before pushing GitHub

1. Extract the delivery ZIP to a fresh folder and run `npm ci`, `npm test`, `npm run build`.
2. Review `.gitignore`. `.env*` are excluded except `.env.example`; node_modules, dist, logs, common private-key files and `.aws/` are excluded. Do not add real credentials even to ignored example files or runtime config.
3. Initialize Git if needed (`git init`), then inspect `git status --short`, `git add --dry-run .` and `git diff --cached` after staging. Verify only intended source/docs/lockfile are staged.
4. If a secret was already committed, ignoring it does not remove it from history; revoke/rotate it and clean history before publishing. This ZIP has no Git history to audit.
5. Commit locally and create the desired GitHub repository. Push only when you choose to do so. No remote has been created or pushed by this review.

## Artwork provenance

Original source attributes illustrations to [unDraw](https://undraw.co/license) and avatars to DiceBear Notionists by Zoish. The original README called unDraw MIT; this was removed because unDraw has its own license. Review the upstream license and asset provenance before publication; authorship/license provenance was not independently established from the SVG files. Keep upstream notices.
