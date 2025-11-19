#!/usr/bin/env bash
# Basic smoke tests for SkyFi IntelliCheck deployments.

set -euo pipefail

API_URL="${API_URL:-${1:-}}"

if [[ -z "${API_URL}" ]]; then
  echo "ERROR: API_URL environment variable (or argument) must be provided." >&2
  exit 1
fi

echo "🚬 Running smoke tests against ${API_URL}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -x "${SCRIPT_DIR}/health-check.sh" ]]; then
  echo "ERROR: health-check.sh not found or not executable at ${SCRIPT_DIR}/health-check.sh" >&2
  exit 1
fi

"${SCRIPT_DIR}/health-check.sh" "${API_URL}"

echo "🔎 Fetching OpenAPI schema..."
OPENAPI_STATUS="$(curl -s -o /dev/null -w '%{http_code}' "${API_URL}/openapi.json" || true)"
if [[ "${OPENAPI_STATUS}" == "200" ]]; then
  echo "✅ OpenAPI schema reachable."
else
  echo "⚠️  OpenAPI schema returned HTTP ${OPENAPI_STATUS}. This may require authentication; verify manually."
fi

echo "✅ Smoke tests completed."

