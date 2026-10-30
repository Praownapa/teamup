# TeamUp Frontend Handoff Notes

Revised 2026-10-30 (Asia/Bangkok). Supersedes the uploaded 2026-10-29 notes.

## Handoff status

Source reviewed and amended locally; automated regression/build checks and mock browser checks are recorded in TEST-REPORT. This is a frontend integration handoff, not a claim that the application is fully tested or already in GitHub. No backend, AWS account configuration, Figma source or Git history was supplied.

## What changed before handoff

Runtime config no longer masks `.env.local`. Error display supports message/detail/validation arrays. Both Cognito custom attributes are documented. API tables now follow actual calls. Password checks, several failed-action states, profile retry, stale-load handling, notification preference persistence, upload validation and mobile navigation were repaired. Dependency versions and lockfile were updated after audit. See CHANGELOG for exact scope.

## Configuration to share between teams

Local defaults: mock true, API `/api`; `public/config.js` empty. Explicit runtime overrides win over Vite build env, which wins over defaults. Docker generates `/config.js` on startup and defaults mock false. Provide API base URL, region, Cognito Pool ID and no-secret App Client ID. S3 bucket policy/CORS and SES settings are backend/AWS configuration, not browser credentials. Rebuild for Vite env changes; restart for container runtime changes.

## Backend team

Use API-CONTRACT.md, endpoints.js and RESPONSE-EXAMPLES.json together. All routes and payloads remain compatible with the original frontend calls. The default full admin URL is `/api/admin/overview`, not `/api/admin/stats`. Team data comes from GET `/projects/{id}`, not a members-list URL. Joining uses POST `/projects/{id}/requests`, not POST `/requests`. Member removal still returns a full project object.

Validate access tokens and derive identity from verified sub. Access tokens are not a guaranteed source of email/custom attributes; implement trusted profile bootstrap and decide backend/Cognito synchronization. Return readable errors, arrays rather than list envelopes, and all fields the views consume. Guard admin/owner/member operations and enforce capacity, duplicate prevention, request/invitation transitions and atomic acceptance on the server. Mock behavior is illustrative, not an authorization implementation.

## AWS / DevOps team

Create an email-login Cognito pool with email verification and a public App Client (no secret). Create String attributes student_id and major (sent as custom:student_id and custom:major), allow appropriate App Client reads/writes, and create admin group. Match the password policy (8+, upper/lower/digit); implement additional UI before requiring MFA or custom challenges. Test delivery/confirmation/resend/reset and token refresh.

Provision backend database and profile bootstrap, S3 signed PUT uploads with separate bucket CORS, and SES delivery/preferences. Route `/api/*` to backend through ALB; default route to frontend; `/health` frontend health check. Configure HTTPS/ACM, security groups, task roles, CloudWatch and deployment rollback. Existing deploy.sh assumes an already-created ECS service using the intended latest image; it is not infrastructure setup. Use an immutable task image revision for production releases where practical. Docker and AWS execution remain unverified here.

## Remaining integration checklist (after backend/AWS are connected)

1. Switch mock off and confirm Network requests hit the intended API, with a real Cognito access token.
2. Register a new email, confirm/resend code, log in/out, reset password, refresh expired tokens and test remember-me across tabs/restored sessions. Verify leading-zero student ID and major are stored; verify first profile creation and subsequent edits.
3. Test dashboard, filters/sorting, project creation, details, saves/reports, recommendations, invitations, requests, role changes, removal/leave, recruitment toggles, profile fields and notifications with persisted server data.
4. Test accepted/rejected/cancelled transitions, full teams, simultaneous acceptance, duplicate requests, empty lists, loading/failed requests and retry. Verify 401, 403, 404, validation errors and non-JSON proxy failures.
5. Test admin as admin and ordinary user; directly call restricted endpoints to confirm server enforcement. Check suspension and protection of personal data.
6. Upload PNG/JPEG/WebP up to 5 MB; test invalid MIME, oversize, expired presign, failed PUT, bucket CORS and persistence/readability of file_url after reload.
7. Verify SES email delivery/preferences; Team Management switch is account-wide notify.requests, not a per-project setting. No frontend code sends SES email itself.
8. Test Docker health, generated config/no-cache, deep-link refresh, ALB routes/TLS and rollback. Check browser console, responsive layout and keyboard/accessibility in target browsers.
9. Replace Terms/Privacy hash placeholders with approved pages, agree university-email restrictions (currently only email syntax is checked), and update Figma if required. Review illustration provenance/license before publication.

## Known limitations to retain in team planning

Mock mode is a single synthetic admin persona with memory-only data and preview-only image URLs. Mock does not enforce all business rules or model separate users. Extra Cognito challenges are reported but not implemented. Remember-me does not instantly revoke browser-stored tokens on window close. Backend email, authorization, storage and concurrency remain server tasks. Mobile fixes received limited smoke coverage, not exhaustive device/accessibility acceptance. There is no supplied lint setup or exhaustive end-to-end suite.

## Delivery and GitHub

ZIP contains source, lockfile, tests, README, changelog, contract/examples and these notes. It excludes node_modules, dist, local env, Git history and review scratch files. Re-run npm ci/test/build after extracting. Inspect the staged files and credentials before committing. The reviewer did not create a remote, push to GitHub or deploy AWS.
