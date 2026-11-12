#!/usr/bin/env bash
# Delete TeamUp's AWS setup. By default this is only a DRY RUN: it lists what would be deleted and deletes
# nothing.
#   bash infra/delete.sh                  # dry run
#   bash infra/delete.sh --really-delete  # delete everything listed, the database too (no copy is kept)
# It only ever touches TeamUp's own stacks (des424-126-g07-teamup-*), their images and uploaded files, and
# the demo-password parameter: nothing else in the shared account.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$REPO_ROOT"
require_login

STACKS=("$PREFIX-app" "$PREFIX-data" "$PREFIX-network")  # the order they must be deleted in
PARAM="/$PREFIX/demo-password"

stack_exists() { awsr cloudformation describe-stacks --stack-name "$1" >/dev/null 2>&1; }

echo "TeamUp's AWS resources (account $ACCOUNT_ID, region $REGION):"
for stack in "${STACKS[@]}"; do
  echo
  if stack_exists "$stack"; then
    echo "Stack $stack:"
    awsr cloudformation describe-stack-resources --stack-name "$stack" \
      --query 'StackResources[].[ResourceType,PhysicalResourceId]' --output text | sed 's/^/  /'
  else
    echo "Stack $stack: (not deployed)"
  fi
done
echo
for repo in "$PREFIX-backend" "$PREFIX-frontend"; do
  images="$(awsr ecr describe-images --repository-name "$repo" --query 'length(imageDetails)' --output text 2>/dev/null)" \
    || images="(no repository)"
  echo "Images in ECR repository $repo: $images"
done
BUCKET="$(stack_output "$PREFIX-data" CoversBucketName)"
if [ -n "$BUCKET" ]; then
  # Count the listed files (the CLI pages through results and drops the KeyCount summary).
  echo "Files in bucket $BUCKET: $(awsr s3api list-objects-v2 --bucket "$BUCKET" --query 'length(Contents || `[]`)' --output text)"
fi
if awsr ssm get-parameter --name "$PARAM" >/dev/null 2>&1; then
  echo "SSM parameter $PARAM: exists"
else
  echo "SSM parameter $PARAM: (none)"
fi

if [ "${1:-}" != "--really-delete" ]; then
  echo
  echo "Dry run: nothing was deleted. Run with --really-delete to delete everything above."
  exit 0
fi

echo
echo "Deleting..."
if [ -n "$BUCKET" ]; then
  awsr s3 rm "s3://$BUCKET" --recursive --only-show-errors  # a bucket must be empty to be deleted
fi
for stack in "${STACKS[@]}"; do
  if stack_exists "$stack"; then
    echo "Deleting stack $stack (CloudFront and the database take several minutes)..."
    awsr cloudformation delete-stack --stack-name "$stack"
    awsr cloudformation wait stack-delete-complete --stack-name "$stack"
  fi
done
awsr ssm delete-parameter --name "$PARAM" 2>/dev/null || true
echo "Done: TeamUp's AWS setup is deleted."
