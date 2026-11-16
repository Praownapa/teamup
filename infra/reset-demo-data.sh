#!/usr/bin/env bash
# Put the online demo data back to how it starts, for example right before the presentation (testing uses
# up the demo's pending join requests and invitations).
#   bash infra/reset-demo-data.sh --yes
# This DELETES ALL APP DATA in the online database (projects, requests, profiles, including real sign-ups),
# then loads the demo data again. Cognito logins stay: the demo students relink to their profiles on their
# next sign-in, and people who signed up for real get a fresh, empty profile.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$REPO_ROOT"

if [ "${1:-}" != "--yes" ]; then
  cat >&2 <<'EOF'
This deletes ALL app data in the online TeamUp database and loads the demo data again.
Cognito logins stay. To go ahead, run: bash infra/reset-demo-data.sh --yes
EOF
  exit 1
fi
require_login

CLUSTER="$(stack_output "$PREFIX-app" ClusterName)"
FAMILY="$(stack_output "$PREFIX-app" BackendTaskFamily)"
SUBNETS="$(stack_output "$PREFIX-network" PublicSubnetIds)"
GROUP="$(stack_output "$PREFIX-network" BackendSecurityGroupId)"
if [ -z "$CLUSTER" ] || [ -z "$FAMILY" ] || [ -z "$SUBNETS" ]; then
  echo "TeamUp isn't deployed: run bash infra/deploy.sh" >&2
  exit 1
fi

# A one-off copy of the backend task (same image, settings and database password) that runs the seed
# command instead of the API, then stops.
echo "Running python -m app.seed --reset as a one-off backend task..."
TASK_ARN="$(awsr ecs run-task --cluster "$CLUSTER" --task-definition "$FAMILY" --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$GROUP],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"backend","command":["python","-m","app.seed","--reset"]}]}' \
  --started-by reset-demo-data --query 'tasks[0].taskArn' --output text)"
TASK_ID="${TASK_ARN##*/}"
echo "Task $TASK_ID started; waiting for it to finish (about a minute)..."
awsr ecs wait tasks-stopped --cluster "$CLUSTER" --tasks "$TASK_ARN"

EXIT_CODE="$(awsr ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[0].exitCode' --output text)"
echo "--- the task's log ---"
awsr logs get-log-events --log-group-name "/ecs/$PREFIX/backend" --log-stream-name "backend/backend/$TASK_ID" \
  --query 'events[].[message]' --output text || true

if [ "$EXIT_CODE" != "0" ]; then
  REASON="$(awsr ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" --query 'tasks[0].stoppedReason' --output text)"
  echo "The reset failed (exit code $EXIT_CODE): $REASON" >&2
  exit 1
fi
echo "Done: the demo data is back to how it starts."
