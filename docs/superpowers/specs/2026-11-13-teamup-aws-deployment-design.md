# TeamUp AWS Deployment: Design

Date: 2026-11-13. Status: draft, waiting for approval.
Puts TeamUp online in the instructor's AWS account for the final presentation. Builds on the backend design (`2026-11-09-teamup-backend-design.md`) and its code on branch `feature/backend` (PR #1, not merged yet).

## Why

The final presentation is on **Tuesday 2026-11-17**. The group needs TeamUp running online on the AWS services in its roadmap, and the team will test that online version before then. This covers the user's Jira tickets Set Up Cloud Environment, Deploy Database, Deploy Back-end, Deploy Front-end and Test Deployed Application.

Claude runs the deployment. The user checks it afterwards in the AWS console. The presentation summarizes each member's contribution, so the user has to explain this setup. Every piece must be easy to find in the console and simple to explain.

Timeline: online by **Saturday 2026-11-14**, so the team can test over the weekend and on Monday. If time runs short, follow the priority order at the end.

## Constraints: a shared account

- Account `528301714999` is shared by 49 IAM users: every DES424 and DES431 group plus some research projects. Their resources sit next to ours.
- We work as IAM user `des424-126-g07`. Its group policy allows everything except managing IAM users and groups, and SageMaker.
- Claude uses the AWS CLI profile `teamup`, which signs in with the console login through `aws login`. Its credentials are temporary. When they expire, the user runs `aws login --profile teamup` again in their own PowerShell window. The CLI is installed at `C:\Program Files\Amazon\AWSCLIV2\aws.exe` and isn't on the PATH of Claude's Bash tool.
- The account has one $200/month budget alert that covers everyone, so cost matters.
- Region: **Tokyo, `ap-northeast-1`** (2 of its 5 VPCs used). The profile's default region is Singapore, so every command and script passes the region explicitly.
- Images are built with Docker Desktop on the user's Windows PC (x86-64).

## Goals

- TeamUp online at one HTTPS address that serves the website, the API under `/api` and the cover images.
- Real Cognito sign-up (with an email code) and sign-in. The backend runs with `AUTH_MODE=cognito`.
- The demo data online, with Cognito logins for the demo students. The presentation signs in as John Carter (admin), Sophia Martinez and the rest, and walks through the demo flows in `backend/README.md`.
- The database in RDS PostgreSQL, unreachable from the internet.
- Everything defined in CloudFormation templates in the repo. One command creates or updates the whole setup, and one command deletes it.
- Every resource is recognizably ours, by name and by tag.
- A "Deployed on AWS" section in the README with the architecture diagram and a tour of where each piece is in the console. The user can present it and explain it.
- An automated smoke test of the live site, plus a manual checklist for the team.

## Non-goals

- A custom domain or our own TLS certificate. The CloudFront address is used as it is.
- Email through SES. Notifications stay in-app, as they are locally. Cognito's built-in email sends the sign-up and password-reset codes.
- A CI/CD pipeline. Claude runs the deploys from the user's PC.
- Auto scaling, a Multi-AZ database, a staging environment, WAF, alarms and dashboards.
- Limiting sign-up to university email addresses.
- Changing the API or the screens beyond what deployment needs.

## Anti-goals (a failure even if it works)

- Changing, using or deleting anything we didn't create. That includes the shared `ecsTaskExecutionRole`, every default VPC, and all other groups' resources.
- Taking shared quota that others may need, such as another VPC, without asking the user.
- Costs nobody notices: something billable that isn't in this design, anything left behind after deletion, or expensive options (NAT gateway, Multi-AZ, large instances). Anything billable that isn't listed here needs the user's OK first.
- Dev or local login reachable online. The backend never runs with `AUTH_MODE=dev` in AWS, and the website always uses Cognito.
- The database reachable from the internet, or passwords and keys in git.
- A setup the user can't find in the console or explain.

## Decided by the user

- Region Tokyo (`ap-northeast-1`), in TeamUp's own VPC.
- The final presentation is Tuesday 2026-11-17, and the team tests the online app before then.
- The presentation uses the demo accounts, such as John.
- Claude deploys everything. The user checks it later in the AWS console.
- The services come from the group's roadmap: Cognito, RDS, ECR, ECS Fargate and ALB, plus S3 for cover images.

## Claude's calls (the user can change any of these)

- **One HTTPS address from CloudFront** (`https://<id>.cloudfront.net`), with no domain to buy.
- **The website runs as a container** built from the teammate's existing `Dockerfile`, `nginx.conf` and `docker-entrypoint.sh`. It sits behind the same load balancer, which routes `/api/*` to the backend, as the teammate's `nginx.conf` expects. Static hosting on S3 isn't used.
- **No NAT gateway** (about $45/month). The containers run in public subnets with public IPs, and their firewall rules only let the load balancer in. The database is in private subnets.
- **CloudFormation plus bash scripts** in a new `infra/` folder. The teammate's `deploy/` folder stays untouched.
- **Names start with `des424-126-g07-teamup`.** Every resource that supports tags gets `project=teamup` and `owner=des424-126-g07`.
- **Sizes:** backend 0.5 vCPU and 1 GB, website 0.25 vCPU and 0.5 GB, one copy of each. Database `db.t4g.micro` with 20 GB of gp3 storage in a single availability zone.
- **Demo logins:** all 18 demo students from `backend/seed/demo.sql` get Cognito accounts that share one demo password. The password is generated at deploy time, shown to the user, stored in SSM Parameter Store as a SecureString, and never written to git. John Carter is in the Cognito `admin` group. `jack.scott` stays suspended.
- **Real sign-ups stay open**, so teammates can also test with their own email addresses.
- **A reset command** puts the demo data back, for example right before the presentation. The user decides whether and when to run it.
- **Swagger stays reachable** at `/api/docs`.
- **It runs around the clock** until the user says to delete it. Deleting doesn't keep a final database snapshot.
- **Small changes to existing code:** listed under "Changes to existing code" below, including one line in the teammate's `docker-entrypoint.sh`.
- **The work goes on branch `feature/aws-deploy`** (based on `feature/backend`) and into its own PR.

## Architecture

```
Browser
  ├─HTTPS─► CloudFront  https://<id>.cloudfront.net
  │           ├─ /covers/*        ─► S3 bucket (private; readable only through CloudFront)
  │           └─ everything else  ─HTTP─► ALB (public subnets; accepts only our CloudFront)
  │                                         ├─ /api/*  ─► backend (ECS Fargate, FastAPI :8000) ─► RDS PostgreSQL 17 (private subnets)
  │                                         └─ other   ─► website (ECS Fargate, nginx :80)
  ├─HTTPS─► Cognito user pool (sign-up, sign-in, email codes, tokens)
  └─HTTPS─► S3 presigned PUT (cover upload; the backend hands out the URL)

backend ─HTTPS─► Cognito (token keys, GetUser) · Secrets Manager (DB password, at start) · CloudWatch Logs
```

### Network

- TeamUp's own VPC in Tokyo, across two availability zones: two public subnets (load balancer and containers) and two private subnets (database only, with no route to the internet). There's an internet gateway and no NAT gateway.
- Firewall rules (security groups):
  - Load balancer: HTTP only, and only from CloudFront. It accepts nothing sent directly to it, including requests through someone else's CloudFront distribution.
  - Backend containers: port 8000, from the load balancer only.
  - Website containers: port 80, from the load balancer only.
  - Database: port 5432, from the backend containers only.
- The containers reach ECR, CloudWatch Logs, Secrets Manager, Cognito and S3 through their public IPs.

### CloudFront and the load balancer

- Viewers are redirected from HTTP to HTTPS.
- `/api/*` is never cached. Every method the API uses, the `Authorization` header, query strings and request bodies reach the backend unchanged.
- The website: files under `/assets/` (hashed names) may be cached for a long time. `index.html`, `config.js` and deep links like `/projects/5` must never be served stale, so a redeploy shows up right away. nginx already sends deep links to `index.html`.
- `/covers/*` comes from the S3 bucket and may be cached.
- The load balancer routes `/api/*` to the backend and everything else to the website. Its health checks are `/api/health` (backend) and `/health` (website).

### Containers (ECS on Fargate)

- One cluster with two services (backend and website), one task each, x86-64.
- An update is a rolling deploy: the old task keeps serving until the new one is healthy, and a failed deploy rolls back.
- There are two ECR repositories, one per image, and images are tagged with the git commit. Deleting the setup deletes the images too.
- Logs go to CloudWatch Logs, with short retention.
- We create our own task execution role and task role, and don't use the shared `ecsTaskExecutionRole`. The task role only allows putting objects under `covers/` in our bucket (for presigning).
- Backend settings: `AUTH_MODE=cognito`, `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `UPLOAD_MODE=s3`, `S3_BUCKET`, `S3_REGION`, `PUBLIC_FILE_BASE_URL=https://<cloudfront address>`, `SEED_DEMO_DATA=true`, plus the database connection (see below).
- Website settings, written into `config.js` at start: `API_BASE_URL=/api`, `USE_MOCK=false`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, and the sign-in mode pinned to Cognito.

### Database (RDS)

- PostgreSQL 17, `db.t4g.micro`, 20 GB gp3, one availability zone, not publicly accessible, in the private subnets.
- The master password is generated by AWS and stored in Secrets Manager. The backend gets it when its container starts. It must not change during the demo period: no automatic rotation, because ECS reads secrets only at start.
- The backend connects with SSL. The existing startup migrations create the tables, and `SEED_DEMO_DATA=true` loads the demo data the first time.
- Updates never replace the database. Deleting the setup deletes it without a final snapshot.

### Sign-in (Cognito)

- One user pool, with email as the username. Self sign-up is on, with verification and password reset by email code through Cognito's built-in email, which is limited to about 50 emails a day.
- Attributes: `email`, `name`, and the custom attributes `student_id` and `major`. The sign-up form sends these.
- The password rules match the sign-up form: at least 8 characters, upper- and lower-case letters, and a number. Symbols aren't required.
- One public app client with no secret, using SRP sign-in and refresh tokens. The smoke test may sign in through the admin password flow, which needs AWS credentials and can't be used from a browser.
- An `admin` group. In Cognito mode the backend takes the admin role from this group on every request, so John must be in it or he loses admin rights.
- The cheapest Cognito feature plan that covers this is enough.
- Demo accounts: a deploy step creates (or leaves alone, if they already exist) a Cognito user for each demo email. Each one has a verified email, gets no invitation email, and has the shared demo password set as permanent. On first sign-in the backend links each account to its seeded profile by email, which it already does.

### Cover images (S3)

- One private bucket with Block Public Access on, readable only through our CloudFront distribution.
- Browsers upload with the backend's existing 5-minute presigned PUT URLs, so the bucket allows cross-origin PUT for that purpose. The 5 MB limit stays a browser-side check, a known limitation.
- Deleting the setup empties and deletes the bucket.

### Commands (in `infra/`, run by Claude from Git Bash)

- **Deploy:** checks the AWS login and the region, creates or updates everything, builds and pushes both images, rolls out the services, creates the demo accounts, runs the smoke test, and prints the site address and a short console tour. Running it again is safe, also after a failure halfway, such as an expired login.
- **Reset demo data:** runs the backend's `python -m app.seed --reset` once as a one-off ECS task with the same settings. It deletes all app data and reloads the demo data. Cognito accounts stay, and the demo accounts relink on their next sign-in. Users who signed up for real get a fresh, empty profile.
- **Delete everything:** asks for confirmation, then removes everything the deployment created (stacks, images, uploaded files, the demo-password parameter) and nothing else.

### Testing (Test Deployed Application)

- **Automated smoke test against the live address:**
  - The website loads over HTTPS, and a deep link returns the app.
  - `config.js` has the user pool and client IDs, with Cognito mode.
  - `/api/health` is OK, and a request without a token gets 401.
  - Signed in as a demo user through Cognito: the profile, the project list and the dashboard load, and John's admin overview works.
  - A small image uploads through a presigned URL and loads back through CloudFront.
  - The load balancer refuses direct requests.
- **Manual checklist for the team:**
  - Sign up with a real email and check that the code arrives.
  - Sign in as each demo account and walk through the demo flows from `backend/README.md`.
  - Create a project with a cover image.
  - Open the admin page as John.
  - Check that Jack gets the suspended message.
- The results go in a short deployment test report.

### Cost (Claude's estimate)

About **$3 a day** while running: the load balancer, two small Fargate tasks, the micro database, four public IPv4 addresses and one secret. CloudFront, S3, Cognito and the logs are about free at this size. That comes to roughly $15–20 through the presentation.

## What the user sees in the AWS console

Switch the region (top right) to **Asia Pacific (Tokyo)**. Then:

- **CloudFormation → Stacks:** our stacks, each with a *Resources* tab that links to everything it created.
- **ECS → Clusters:** the services, their tasks and their logs.
- **RDS → Databases:** the database.
- **Cognito → User pools:** the users and the `admin` group.
- **CloudFront:** the address. CloudFront is global, so it appears in every region.
- **VPC:** our network.
- **S3:** the cover-image bucket.
- **Resource Groups & Tag Editor:** search `project=teamup` to see every tagged resource at once.

## Changes to existing code

- **Backend:** accept the database connection as separate values (host, port, name, user, password), since the password comes from Secrets Manager. Any generated password must work, including characters that would break a URL. Require SSL in AWS. `DATABASE_URL` keeps working locally.
- **Website** (teammate's `docker-entrypoint.sh`): `config.js` also sets the sign-in mode to `cognito`, so the deployed site can't fall into local login even if an image were ever built with local settings. `.env*` files are already left out of the image.
- **README:** a "Deployed on AWS" section with the diagram, the console tour, and how to deploy, reset and delete.
- Tests cover the code changes, and the existing test suites stay green.

## Done when

- The automated smoke test passes against the live address.
- The user and the team can sign in as the demo accounts and walk through the demo flows online.
- The README section and the test report are in the PR.
- Every created resource carries our name prefix or tag.
- The delete command has a dry run that lists exactly what it would remove, all of it ours, and that dry run has been checked. The real delete would break the site the team is testing on, so it runs only when the user asks.

## Priority order (if time runs short)

1. Website, API and database online, with Cognito sign-in and working demo accounts.
2. Cover image uploads through S3 and CloudFront.
3. The smoke test, the README section and the test report.
4. Polish for the reset and delete commands.

## Left to the builder

- The stack layout and template structure, CIDR ranges, which two availability zones, and names beyond the prefix. Updates must never replace the database, the user pool, the bucket or the CloudFront address.
- CloudFront cache and origin policies within the rules above, the price class, and how the load balancer rejects traffic that didn't come through our distribution.
- Health check timings, deployment settings, log retention and database backup retention.
- How the backend receives the database settings and SSL options.
- Script details, the smoke test's sign-in method, and the demo password format.
