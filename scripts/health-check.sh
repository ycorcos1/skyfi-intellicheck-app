#!/usr/bin/env bash
# Health check helper for SkyFi IntelliCheck API deployments.

set -euo pipefail

API_URL="${API_URL:-${1:-}}"
MAX_RETRIES="${MAX_RETRIES:-10}"
RETRY_DELAY="${RETRY_DELAY:-10}"

if [[ -z "${API_URL}" ]]; then
  echo "ERROR: API_URL environment variable (or argument) must be provided." >&2
  exit 1
fi

echo "🔍 Checking API health at ${API_URL}"
echo "   Retries: ${MAX_RETRIES}, Delay: ${RETRY_DELAY}s"

attempt=1
while [[ "${attempt}" -le "${MAX_RETRIES}" ]]; do
  response="$(curl -s -w '\n%{http_code}' "${API_URL}/health" || true)"
  status="${response##*$'\n'}"

  if [[ "${status}" == "200" ]]; then
    echo "✅ Health endpoint returned 200 on attempt ${attempt}"

    version_json="$(curl -s "${API_URL}/version" || true)"
    if [[ -n "${version_json}" ]]; then
      version="$(printf '%s' "${version_json}" | python3 - <<'PY' || echo 'unknown'
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get("api_version", data.get("version", "unknown")))
except Exception:
    print("unknown")
PY
)"
      echo "ℹ️  API version: ${version}"
    else
      echo "⚠️  Version endpoint returned empty response."
    fi

    exit 0
  fi

  echo "❌ Attempt ${attempt}/${MAX_RETRIES} failed with status ${status}. Retrying in ${RETRY_DELAY}s..."
  attempt=$((attempt + 1))
  sleep "${RETRY_DELAY}"
done

echo "❌ API health check failed after ${MAX_RETRIES} attempts."
exit 1

