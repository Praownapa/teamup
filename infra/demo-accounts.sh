#!/usr/bin/env bash
# Give every demo student a Cognito login with the shared demo password, and put John Carter in the admin
# group. Safe to re-run: existing accounts are kept (their password is set to the stored one again).
#   bash infra/demo-accounts.sh
# The password lives only in SSM Parameter Store, as a SecureString: /des424-126-g07-teamup/demo-password
# (Tokyo). It is created the first time and never written to git or to a file.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$REPO_ROOT"
require_login

POOL="$(stack_output "$PREFIX-data" UserPoolId)"
if [ -z "$POOL" ]; then
  echo "The data stack isn't deployed yet: run bash infra/deploy.sh" >&2
  exit 1
fi
PARAM="/$PREFIX/demo-password"

NEW_PASSWORD=""
if ! PASSWORD="$(awsr ssm get-parameter --name "$PARAM" --with-decryption --query Parameter.Value --output text 2>/dev/null)"; then
  PASSWORD="$(py infra/demo_accounts.py password)"
  # No --overwrite: if it appeared in the meantime, this fails instead of replacing it.
  awsr ssm put-parameter --name "$PARAM" --type SecureString --value "$PASSWORD" \
    --description "TeamUp demo students' shared password" \
    --tags Key=project,Value=teamup Key=owner,Value=des424-126-g07 >/dev/null
  NEW_PASSWORD=1
fi

mapfile -t USERS < <(py infra/demo_accounts.py users backend/seed/demo.sql)
created=0
for line in "${USERS[@]}"; do
  email="${line%%$'\t'*}"
  name="${line#*$'\t'}"
  if ! awsr cognito-idp admin-get-user --user-pool-id "$POOL" --username "$email" >/dev/null 2>&1; then
    # A verified email and no invitation email: these addresses are made up and can't receive mail.
    attributes=$(printf '[{"Name":"email","Value":"%s"},{"Name":"email_verified","Value":"true"},{"Name":"name","Value":"%s"}]' \
      "$email" "$name")
    awsr cognito-idp admin-create-user --user-pool-id "$POOL" --username "$email" --message-action SUPPRESS \
      --user-attributes "$attributes" >/dev/null
    created=$((created + 1))
  fi
  awsr cognito-idp admin-set-user-password --user-pool-id "$POOL" --username "$email" --password "$PASSWORD" --permanent
done

# In Cognito mode the backend takes the admin role from this group, so John needs it to stay admin.
awsr cognito-idp admin-add-user-to-group --user-pool-id "$POOL" --username john.carter@student.uni.ac.th --group-name admin

echo "Demo accounts: ${#USERS[@]} ready (${created} new). John Carter is in the admin group."
if [ -n "$NEW_PASSWORD" ]; then
  echo "New demo password (kept in SSM Parameter Store $PARAM): $PASSWORD"
fi
