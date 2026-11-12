#!/usr/bin/env bash
# Shared settings and helpers for the TeamUp deployment scripts: `source infra/lib.sh`.
#
# Every AWS call goes through `awsr`, which pins the TeamUp profile and the Tokyo region, so a script can
# never touch another region or another set of credentials by accident. The AWS account is shared with
# other student groups: only ever create, change or delete TeamUp's own resources (des424-126-g07-teamup-*).

set -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="des424-126-g07-teamup"
REGION="ap-northeast-1"
PROFILE="${PROFILE:-teamup}"
ACCOUNT_ID="528301714999"
USER_ARN="arn:aws:iam::528301714999:user/des424-126-g07"

export AWS_PAGER=""        # never open a pager
export MSYS_NO_PATHCONV=1  # Git Bash: don't rewrite arguments such as /des424-.../demo-password into Windows paths

if command -v aws >/dev/null 2>&1; then
  AWS_BIN="aws"
else
  AWS_BIN="/c/Program Files/Amazon/AWSCLIV2/aws.exe"  # the Windows installer's location
fi

if [ -x "$REPO_ROOT/infra/.venv/Scripts/python" ]; then
  PY="$REPO_ROOT/infra/.venv/Scripts/python"   # Windows venv
else
  PY="$REPO_ROOT/infra/.venv/bin/python"       # Mac / Linux venv
fi

# Windows programs end their lines with \r\n, and bash keeps the \r in $(...), which would quietly corrupt
# values such as stack outputs. Both wrappers strip it.
awsr() { "$AWS_BIN" --profile "$PROFILE" --region "$REGION" "$@" | tr -d '\r'; }
py() { "$PY" "$@" | tr -d '\r'; }

# A file path that aws.exe can open (it can't read /c/... paths when MSYS_NO_PATHCONV is set).
native_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}

# stack_output STACK KEY: the output's value, or nothing if the stack or the output doesn't exist.
stack_output() {
  local value
  value=$(awsr cloudformation describe-stacks --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue | [0]" --output text 2>/dev/null) || value=""
  [ "$value" = "None" ] && value=""
  printf '%s' "$value"
}

# Stop unless the CLI is signed in as our IAM user (the aws login session lasts a limited time).
require_login() {
  local arn
  arn=$(awsr sts get-caller-identity --query Arn --output text 2>/dev/null) || arn=""
  if [ "$arn" != "$USER_ARN" ]; then
    echo 'AWS sign-in expired or wrong account: run "aws login --profile teamup" in PowerShell, then re-run.' >&2
    exit 1
  fi
}

# ECR's login password is about 2.6 KB with aws login's temporary credentials: more than Windows Credential
# Manager can hold (2,560 bytes), so Docker Desktop's credential store fails with "The stub received bad
# data". On Windows the login therefore goes into a throwaway Docker config: with no credential helper on
# PATH, Docker keeps it in that folder's config.json (it warns that it's unencrypted), and the folder is
# deleted when the script exits. Elsewhere the normal docker login is used.
ecr_login() {  # ecr_login REGISTRY
  if command -v cygpath >/dev/null 2>&1; then
    ECR_DOCKER_CONFIG="$(mktemp -d)"
    trap 'rm -rf "$ECR_DOCKER_CONFIG"' EXIT
    echo '{}' > "$ECR_DOCKER_CONFIG/config.json"
    ECR_DOCKER_HOST="$(docker context inspect --format '{{.Endpoints.docker.Host}}')"  # the same Docker engine
    ECR_DOCKER_EXE="$(dirname "$(command -v docker)")/docker.exe"
    echo "(The ECR login is kept in a temporary folder that is deleted when this script ends.)"
  fi
  awsr ecr get-login-password | ecr_docker login --username AWS --password-stdin "$1"
}

ecr_docker() {  # docker, with the ECR login from ecr_login (use it for push)
  if [ -n "${ECR_DOCKER_CONFIG:-}" ]; then
    PATH="/usr/bin:/bin" DOCKER_CONFIG="$(cygpath -w "$ECR_DOCKER_CONFIG")" DOCKER_HOST="$ECR_DOCKER_HOST" \
      "$ECR_DOCKER_EXE" "$@"
  else
    docker "$@"
  fi
}

require_docker() {
  if ! docker info >/dev/null 2>&1; then
    echo "Docker isn't running: start Docker Desktop, then re-run." >&2
    exit 1
  fi
}

# deploy_stack STACK TEMPLATE [KEY=VALUE ...]: create or update a stack, tagged as TeamUp's.
# Re-running without changes is fine (--no-fail-on-empty-changeset).
deploy_stack() {
  local stack="$1" template="$2"
  shift 2
  local params=() status
  if [ $# -gt 0 ]; then params=(--parameter-overrides "$@"); fi
  # A stack whose very first create failed is left empty in ROLLBACK_COMPLETE and can't be updated:
  # delete it (it holds no resources any more) so this run can create it again.
  status=$(awsr cloudformation describe-stacks --stack-name "$stack" --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null) || status=""
  if [ "$status" = "ROLLBACK_COMPLETE" ]; then
    echo "$stack failed to create on an earlier run and is empty; deleting it so it can be created again."
    awsr cloudformation delete-stack --stack-name "$stack"
    awsr cloudformation wait stack-delete-complete --stack-name "$stack"
  fi
  awsr cloudformation deploy --stack-name "$stack" --template-file "$(native_path "$template")" \
    ${params[@]+"${params[@]}"} --capabilities CAPABILITY_NAMED_IAM --no-fail-on-empty-changeset \
    --tags project=teamup owner=des424-126-g07
}
