#!/bin/sh
# สร้าง config.js จาก environment variable ของ ECS task ทุกครั้งที่ container เริ่ม
# ทำให้ใช้ image เดียวกันได้ทั้ง dev / staging / prod โดยไม่ต้อง build ใหม่
set -eu
for value in "${API_BASE_URL:-/api}" "${USE_MOCK:-false}" "${COGNITO_USER_POOL_ID:-}" "${COGNITO_CLIENT_ID:-}"; do
  case "$value" in *[!a-zA-Z0-9_./:?-]*) echo "Invalid runtime config characters" >&2; exit 1 ;; esac
done
case "${USE_MOCK:-false}" in true|false) ;; *) echo "USE_MOCK must be true or false" >&2; exit 1 ;; esac
# AUTH_MODE is fixed, not read from the environment: the deployed site always signs in with Cognito.
# Local login (VITE_AUTH_MODE=local) is for development only and can't be switched on here.
cat > /usr/share/nginx/html/config.js <<EOF
window.__CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL:-/api}",
  USE_MOCK: "${USE_MOCK:-false}",
  COGNITO_USER_POOL_ID: "${COGNITO_USER_POOL_ID:-}",
  COGNITO_CLIENT_ID: "${COGNITO_CLIENT_ID:-}",
  AUTH_MODE: "cognito"
};
EOF
echo "TeamUp config.js written (USE_MOCK=${USE_MOCK:-false})"
