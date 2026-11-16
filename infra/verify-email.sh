#!/usr/bin/env bash
# Let a real TeamUp user receive email. SES is in its sandbox in this account, and there Amazon only delivers
# to verified addresses. Each address added here gets an email from Amazon Web Services with a link to click
# within 24 hours. Until it's clicked, TeamUp's emails to that address are refused (the backend logs "Email
# address is not verified"). The addresses are tagged project=teamup, and bash infra/delete.sh removes them.
#   bash infra/verify-email.sh someone@example.com [more ...]   # add addresses, or send a new link
#   bash infra/verify-email.sh                                  # list them and whether they're verified
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$REPO_ROOT"
require_login

TAGS=(Key=project,Value=teamup Key=owner,Value=des424-126-g07)

# PENDING (link not clicked yet), SUCCESS, FAILED, ... or NONE when SES doesn't know the address
status_of() {
  awsr sesv2 get-email-identity --email-identity "$1" --query VerificationStatus --output text 2>/dev/null || echo NONE
}

for address in "$@"; do
  status="$(status_of "$address")"
  if [ "$status" = "NONE" ]; then
    awsr sesv2 create-email-identity --email-identity "$address" --tags "${TAGS[@]}" >/dev/null
    echo "$address: added. Amazon has emailed it a verification link."
  elif [ "$status" = "SUCCESS" ]; then
    echo "$address: already verified."
  elif grep -qxF "$address" <<< "$(ses_recipients)"; then
    # SES can't resend the link for an address, so delete the unverified address and add it again.
    awsr sesv2 delete-email-identity --email-identity "$address"
    awsr sesv2 create-email-identity --email-identity "$address" --tags "${TAGS[@]}" >/dev/null
    echo "$address: was $status. Amazon has emailed it a new verification link."
  else
    echo "$address: is in SES ($status) but wasn't added by this script, so it's left alone." >&2
  fi
done

echo
echo "Addresses that receive TeamUp email directly (added with this script, region $REGION):"
recipients="$(ses_recipients)"
[ -z "$recipients" ] && echo "  (none)"
for address in $recipients; do
  printf '  %-8s %s\n' "$(status_of "$address")" "$address"
done
echo "PENDING means the link hasn't been clicked yet. It works for 24 hours; add the address again for a new one."
