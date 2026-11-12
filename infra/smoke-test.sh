#!/usr/bin/env bash
# Live smoke test of the deployed TeamUp (Jira: Test Deployed Application). It signs in two demo students
# through Cognito (John the admin, Jack who is suspended) and checks the website, the API through
# CloudFront, a cover upload, and that the load balancer can't be reached directly.
#   bash infra/smoke-test.sh
# Exit code 0 means all 13 checks passed.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$REPO_ROOT"
require_login

SITE="$(stack_output "$PREFIX-app" SiteUrl)"
ALB="$(stack_output "$PREFIX-app" LoadBalancerDnsName)"
POOL="$(stack_output "$PREFIX-data" UserPoolId)"
CLIENT="$(stack_output "$PREFIX-data" UserPoolClientId)"
BUCKET="$(stack_output "$PREFIX-data" CoversBucketName)"
if [ -z "$SITE" ] || [ -z "$POOL" ]; then
  echo "TeamUp isn't deployed yet: run bash infra/deploy.sh" >&2
  exit 1
fi
PASSWORD="$(awsr ssm get-parameter --name "/$PREFIX/demo-password" --with-decryption \
  --query Parameter.Value --output text)"

# An access token for a demo student, from Cognito's admin sign-in (it needs AWS credentials, so only
# scripts like this one can use it; the website signs in with SRP).
token_for() {
  awsr cognito-idp admin-initiate-auth --user-pool-id "$POOL" --client-id "$CLIENT" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH --auth-parameters "USERNAME=$1,PASSWORD=$PASSWORD" \
    --query AuthenticationResult.AccessToken --output text
}

JOHN_TOKEN="$(token_for john.carter@student.uni.ac.th)"
JACK_TOKEN="$(token_for jack.scott@student.uni.ac.th)"
export JOHN_TOKEN JACK_TOKEN

echo "Smoke test of $SITE"
py infra/smoke_test.py --site "$SITE" --alb "$ALB" --pool "$POOL" --client "$CLIENT" --bucket "$BUCKET"
