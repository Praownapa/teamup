#!/usr/bin/env bash
# Create or update TeamUp on AWS (Tokyo) from start to finish. Safe to re-run, also after a failure halfway
# (for example an expired sign-in): stacks without changes are skipped and existing demo accounts are kept.
#   bash infra/deploy.sh
# Needs: "aws login --profile teamup" done in PowerShell, Docker Desktop running, and everything committed
# (the images are tagged with the commit).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$REPO_ROOT"

step() { printf '\n== %s ==\n' "$*"; }
net_out() { stack_output "$PREFIX-network" "$1"; }
data_out() { stack_output "$PREFIX-data" "$1"; }

step "1/8 Checking the AWS sign-in, Docker and git"
require_login
require_docker
if [ -n "$(git status --porcelain)" ]; then
  echo "Commit your changes first: the image tag is the commit." >&2
  exit 1
fi
TAG="$(git rev-parse --short HEAD)"
echo "Account $ACCOUNT_ID, region $REGION, commit $TAG"

step "2/8 Looking up CloudFront's address list (for the load balancer's firewall)"
PREFIX_LIST="$(awsr ec2 describe-managed-prefix-lists \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --query 'PrefixLists[0].PrefixListId' --output text)"
echo "$PREFIX_LIST"

step "3/8 Network and data stacks (the first run takes about 15 minutes: the database is slow to create)"
deploy_stack "$PREFIX-network" infra/templates/network.yaml "CloudFrontPrefixListId=$PREFIX_LIST"
deploy_stack "$PREFIX-data" infra/templates/data.yaml \
  "PrivateSubnetIds=$(net_out PrivateSubnetIds)" "DatabaseSecurityGroupId=$(net_out DatabaseSecurityGroupId)"

step "4/8 Building and pushing the backend and website images ($TAG)"
ecr_login "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
BACKEND_IMAGE="$(data_out BackendRepositoryUri):$TAG"
FRONTEND_IMAGE="$(data_out FrontendRepositoryUri):$TAG"
docker build --platform linux/amd64 -t "$BACKEND_IMAGE" backend
docker build --platform linux/amd64 -t "$FRONTEND_IMAGE" .
ecr_docker push "$BACKEND_IMAGE"
ecr_docker push "$FRONTEND_IMAGE"

step "5/8 App stack (the first run takes about 10 minutes: CloudFront is slow to create)"
deploy_stack "$PREFIX-app" infra/templates/app.yaml \
  "VpcId=$(net_out VpcId)" \
  "PublicSubnetIds=$(net_out PublicSubnetIds)" \
  "AlbSecurityGroupId=$(net_out AlbSecurityGroupId)" \
  "BackendSecurityGroupId=$(net_out BackendSecurityGroupId)" \
  "FrontendSecurityGroupId=$(net_out FrontendSecurityGroupId)" \
  "DatabaseEndpoint=$(data_out DatabaseEndpoint)" \
  "DatabasePort=$(data_out DatabasePort)" \
  "DatabaseName=$(data_out DatabaseName)" \
  "DatabaseSecretArn=$(data_out DatabaseSecretArn)" \
  "CoversBucketName=$(data_out CoversBucketName)" \
  "CoversBucketArn=$(data_out CoversBucketArn)" \
  "CoversBucketRegionalDomainName=$(data_out CoversBucketRegionalDomainName)" \
  "UserPoolId=$(data_out UserPoolId)" \
  "UserPoolClientId=$(data_out UserPoolClientId)" \
  "BackendImage=$BACKEND_IMAGE" \
  "FrontendImage=$FRONTEND_IMAGE"

step "6/8 Stack policies (an update may never replace the database, the accounts, the bucket or the address)"
awsr cloudformation set-stack-policy --stack-name "$PREFIX-data" \
  --stack-policy-body "file://$(native_path infra/stack-policies/data.json)"
awsr cloudformation set-stack-policy --stack-name "$PREFIX-app" \
  --stack-policy-body "file://$(native_path infra/stack-policies/app.json)"

step "7/8 Demo accounts, then the smoke test"
bash infra/demo-accounts.sh
if [ -f infra/smoke-test.sh ]; then
  bash infra/smoke-test.sh
fi

step "8/8 Done"
SITE="$(stack_output "$PREFIX-app" SiteUrl)"
DEMO_PASSWORD="$(awsr ssm get-parameter --name "/$PREFIX/demo-password" --with-decryption \
  --query Parameter.Value --output text)"
cat <<EOF
TeamUp is online: $SITE

Demo logins (all with the same password): john.carter@student.uni.ac.th (admin), sophia.martinez@,
oliver.smith@, henry.moore@, emma.wilson@ ... (@student.uni.ac.th). jack.scott@ is suspended.
Demo password: $DEMO_PASSWORD   (kept in SSM Parameter Store: /$PREFIX/demo-password)

In the AWS console: switch the region (top right) to Asia Pacific (Tokyo), then open
CloudFormation -> Stacks -> $PREFIX-network / $PREFIX-data / $PREFIX-app -> Resources.
EOF
