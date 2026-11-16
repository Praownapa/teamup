# TeamUp Deployment Test Report

Jira: **Test Deployed Application**. Tested on 2026-11-13 against **https://d2u84idlq1gpr5.cloudfront.net** (AWS, Tokyo), with images built from commit `3de0826`. How the deployment works is described in the README section "Deployed on AWS".

## Automated smoke test

`bash infra/smoke-test.sh` signs in two demo students through Cognito: John, the admin, and Jack, who is suspended. It then runs these checks against the live address. It also runs at the end of every `bash infra/deploy.sh`.

| # | Check | Result |
|---|---|---|
| 1 | The home page loads over HTTPS | PASS |
| 2 | A deep link (`/projects/1`) loads the app | PASS |
| 3 | `config.js` has the user pool and app client, with Cognito sign-in and no mock data | PASS |
| 4 | `/` and `config.js` aren't served from CloudFront's cache without checking, so a redeploy shows up at once | PASS |
| 5 | `/api/health` reports the database OK, and Swagger (`/api/docs`) loads | PASS |
| 6 | The API refuses a request without a token (401) | PASS |
| 7 | John's Cognito token works through CloudFront, and he has the admin role | PASS |
| 8 | A search with a query string (`?q=Food`) finds "Campus Food Waste Tracker" | PASS |
| 9 | John's dashboard loads | PASS |
| 10 | The admin overview loads for John | PASS |
| 11 | Jack is refused with "Your account has been suspended." | PASS |
| 12 | A cover image uploads through a presigned S3 link (regional address) and loads back through CloudFront | PASS |
| 13 | The load balancer can't be reached directly, only through CloudFront | PASS |

Result: **13 of 13 passed.** The test also fails when it should: with an invalid token for John, checks 7–10 and 12 fail.

## Other checks of the deployment

- **Re-running the deploy** with nothing changed: all three stacks report "No changes", the 18 demo accounts are kept (0 new), and it exits 0.
- **Resetting the demo data:** we accepted one of John's join requests, then ran `bash infra/reset-demo-data.sh --yes`. Both pending requests were back, and the smoke test passed again. Without `--yes`, the reset refuses to run.
- **Deleting (dry run only):** `bash infra/delete.sh` lists the 46 resources in the three TeamUp stacks, the two image repositories, the bucket and the demo-password parameter, and deletes nothing.
- **Offline tests:** 31 template and script tests pass, including cfn-lint (`infra/.venv/Scripts/python -m pytest infra -q`). The 84 backend tests and 46 frontend tests pass.

## Email notifications (SES), tested 2026-11-16

The backend sends an email for each of the five events in the requirements. The emails come from the team inbox, a Gmail address verified in SES. SES is in its sandbox in this account, so it only delivers to verified addresses. The demo students' addresses are made up, so their emails go to the team inbox, with the intended recipient at the start of the subject: `[for grace.hall@student.uni.ac.th] …`.

The test ran on Grace Hall's demo project, *City Air Quality Viz*, which has one open place.

| # | Event (requirement) | Live test | Email received |
|---|---|---|---|
| 1 | A student asks to join → the project owner | Noah asks to join | PASS |
| 2 | The owner accepts or declines → the student | Grace accepts Noah | PASS |
| 3 | The owner invites a student → that student | Grace invites Ava | PASS |
| 4 | The student accepts or declines → the owner | Ava declines | PASS |
| 5 | The owner removes a member → that member | Grace removes Noah | PASS |

- **Where they land:** all five emails arrived in the team inbox's **Spam** folder. Gmail distrusts them because Amazon sends them on behalf of a Gmail address. A Gmail filter with *Never send it to Spam* moves them to the inbox (see the README, **Email**).
- **Two emails at the same moment:** when accepting a request fills the team, the other waiting students are declined automatically, and two emails go out together. This is what happens when John accepts a request in the demo. In a second live test, Noah and Ava both asked to join and Grace accepted Noah. The backend logged no failed email for either of the two.
- **The project afterwards:** both tests left Grace's project as it was, with Grace and Ryan on the team and the Data Analyst place open.
- **Offline tests:** 18 new backend tests (102 in total) and 3 new template tests (34 in total). They cover each event, the email switches on the Account page, the demo inbox, and that a change that's rolled back emails nobody.

## Manual checklist for the team

Use https://d2u84idlq1gpr5.cloudfront.net. The demo password is in Parameter Store (see the README, "Deployed on AWS"). Before the presentation, run `bash infra/reset-demo-data.sh --yes` if testing used up the demo's join requests and invitations.

| # | Do this | Expected | Result | Tested by / date |
|---|---|---|---|---|
| 1 | Sign up with your own email | A 6-digit code arrives (check spam). After you enter it, you can sign in and finish the Welcome step | | |
| 2 | Use "Forgot password" with that email | A reset code arrives, and the new password works | | |
| 3 | Sign in as `john.carter@student.uni.ac.th` | The dashboard shows John's projects, and Admin appears in the menu | | |
| 4 | As John, accept one of the 2 pending join requests | The student joins the team | | |
| 5 | Sign in as `sophia.martinez@student.uni.ac.th` and accept John's invitation | Sophia joins the team | | |
| 6 | Sign in as `oliver.smith@student.uni.ac.th` and cancel his request to join John's project | The request disappears | | |
| 7 | Sign in as `emma.wilson@student.uni.ac.th` and leave John's team | Emma is no longer listed as a member | | |
| 8 | Create a project with a cover image (PNG, JPG or WebP, under 5 MB) | The image shows on the project page | | |
| 9 | As John, open the Admin page | The overview and the reports show | | |
| 10 | Sign in as `jack.scott@student.uni.ac.th` | "Your account has been suspended." | | |
| 11 | Open a deep link such as `/projects/1` directly, then refresh | The page loads (no 404) | | |
| 12 | After items 4 and 5, open the team inbox (check Spam too) | An email from TeamUp for each, with `[for …@student.uni.ac.th]` in the subject | | |
