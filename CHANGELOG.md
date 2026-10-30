# Review changelog - 2026-10-30

## Verified fixes

- Removed hardcoded local runtime values that overrode Vite env. Added a testable config resolver with explicit precedence, false handling, validation and base-URL slash normalization.
- Kept all existing endpoint methods, paths, payloads and Cognito attribute names. Documented `/admin/overview`, both custom attributes, project-based team retrieval, full member mutation responses, filters and partial profile PUT behavior.
- HTTP errors accept `message`, string `detail` and FastAPI validation arrays; non-JSON errors retain readable fallback. Preserved 401 redirect and 204 behavior.
- Password validation now enforces every stated requirement independently of the strength meter. Signup respects confirmation state; unsupported auth challenges and resend failures are visible.
- Added failure handling to profile/onboarding, save/report, invitation/cancel/leave, notification and admin actions. Async loads ignore stale responses/unmounts. Profile-load failures offer retry rather than leaving team pages spinning indefinitely.
- Team email preference now saves account-wide `notify.requests` using the existing profile endpoint. Presigned responses must contain both URLs in real mode; publishing waits for uploads.
- Project saved state is keyed by project ID. Admin chart handles zero/empty data. Mobile navigation and filters remain available.
- Expanded `.gitignore`, added LF shell rules, made Docker use `npm ci`, rejected unsafe runtime JS config characters, and stopped Nginx returning SPA HTML for `/api/` requests sent to the wrong service.
- Updated toolchain to Vite 7.3.7 / React plugin 5.2.0, Router 7.18.5 and Vitest 5.0.5; refreshed lockfile and Node requirement (22.12+), Docker Node 22. API contract unchanged. Migration references: https://v7.vite.dev/guide/migration and https://reactrouter.com/7.9.6/upgrading/v6 .
- Added regression tests, API response examples, precise README and revised handoff. Removed unsupported claims of full testing and prior Git publication.

## Still separate from this delivery

Real Cognito/backend/S3/SES integration, server authorization/data validation/concurrency, MFA UX, production session policy, legal links, AWS provisioning, Docker image testing and final cross-browser/accessibility review. See HANDOFF and TEST-REPORT. No GitHub push, cloud deployment or real email sent.
