# Test report - 2026-10-30 (Asia/Bangkok)

## Executed checks

| Check | Result |
|---|---|
| npm install | Passed after retry outside restricted network; lockfile retained/updated |
| npm test | 35/35 passed across 5 files using Vitest 5.0.5 |
| npm run build | Passed with Vite 7.3.7; 697 modules transformed |
| Dependency audit | 0 vulnerabilities in final installed set; see audit-summary.json |
| Browser smoke | Headless Microsoft Edge, 1440x1000: mock login and 14 routes rendered; zero pageerror events |
| Profile mutation | Edited/saved display name and checked returned UI value in mock mode |
| Email preference | Team switch saved account-wide notify.requests and reflected updated state |
| Mobile | Explore at 390x844: navigation/filters visible; document width 390, no horizontal overflow |
| Shell syntax | bash -n accepted docker-entrypoint.sh and deploy/deploy.sh; scripts not executed/deployed |
| API preservation | src/api/endpoints.js byte-equivalent to original after newline normalization |
| Ignore rules | Git check-ignore verified env variants, node_modules, dist, private.pem, key.key, .aws/credentials excluded; .env.example, source and lockfile allowed |
| Secret scan | No matches for private-key blocks, AWS access-key patterns, GitHub tokens, JWTs or explicit secret assignments in candidate text files |

Test environment: Windows; Node 24.22.1; npm 11.19.1. Final dependencies: React 18, Vite 7.3.7, @vitejs/plugin-react 5.2.0, react-router-dom 7.18.5, Vitest 5.0.5. Supported Node engines follow Vitest: ^22.12.0 or ^24.0.0 or >=26.0.0. Docker uses Node 22.

## Regression scope

Config default/env/runtime precedence, explicit false, invalid flag and URL normalization; error message/detail/FastAPI validation handling; password policy; Authorization/JSON request body; 401 redirect, 204, 403/non-JSON/network errors; real/mock function parity; admin overview route; member DELETE response; both Cognito custom attributes; mock project creation/recruitment and full-team request transition; S3 MIME/size, missing URLs, PUT headers and failures.

Browser routes: /, /projects, /projects/1, /projects/3, /projects/new, /teammates, /requests, /teams, /teams/1, /profile, /students/2, /notifications, /admin, /welcome. The browser smoke used the development server and mock data, not a real backend or production container. Screenshots of Admin and mobile Explore were visually inspected. Raw browser results are included in browser-results.json.

## Not verified / remaining work

- Real backend/API contract acceptance, Cognito network calls, actual token validation/refresh, S3/SES, database persistence or AWS permissions/infrastructure.
- Docker image build/start, Nginx runtime and ECS/ALB deployment: Docker unavailable. Shell syntax success is not container validation.
- Exhaustive browser/device/accessibility/performance testing, all mutation/error branches, MFA and browser session restore semantics.
- No original Git history was supplied. Pattern-based scanning is not a guarantee that arbitrary secrets or personal data cannot exist. Cognito/account IDs in templates remain placeholders; mock identities are sample data.
- Initial network/browser isolation failures were resolved for npm and mock browser checks. The older test runner briefly introduced audited issues; it was replaced, and the final installed dependency set reports zero.
- No lint script existed; no claim of lint or complete production/end-to-end acceptance is made.

## Reproduce

Extract the ZIP; use a supported Node release; run npm ci, npm test, npm run build and npm run dev. The browser evidence records this review's smoke run; follow HANDOFF.md for the manual integration acceptance matrix. Audit databases change over time, so rerun npm audit before release.
