#!/usr/bin/env bash
set -euo pipefail

INFO_COLOR="\033[1;34m"
SUCCESS_COLOR="\033[1;32m"
WARN_COLOR="\033[1;33m"
ERROR_COLOR="\033[1;31m"
RESET_COLOR="\033[0m"

log_info() {
  echo -e "${INFO_COLOR}[INFO]${RESET_COLOR} $*"
}

log_success() {
  echo -e "${SUCCESS_COLOR}[SUCCESS]${RESET_COLOR} $*"
}

log_warn() {
  echo -e "${WARN_COLOR}[WARN]${RESET_COLOR} $*"
}

log_error() {
  echo -e "${ERROR_COLOR}[ERROR]${RESET_COLOR} $*" >&2
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log_error "Required command '$1' is not installed."
    exit 1
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${REPO_ROOT}/infra"
FRONTEND_DIR="${REPO_ROOT}/frontend"

ENVIRONMENT="${1:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

require_command terraform
require_command npm
require_command aws
require_command curl

tf_output() {
  local output_name="$1"
  if ! terraform -chdir="${INFRA_DIR}" output -raw "${output_name}" 2>/dev/null; then
    log_error "Unable to read Terraform output '${output_name}'. Make sure infrastructure is applied."
    exit 1
  fi
}

log_info "SkyFi IntelliCheck Frontend Deployment"
log_info "Environment: ${ENVIRONMENT}"
log_info "AWS Region: ${AWS_REGION}"

log_info "Fetching Terraform outputs..."
FRONTEND_BUCKET="$(tf_output frontend_bucket_name)"
CLOUDFRONT_DIST_ID="$(tf_output cloudfront_distribution_id)"
CLOUDFRONT_DOMAIN="$(tf_output cloudfront_distribution_domain_name)"
API_URL="$(tf_output api_url)"
COGNITO_POOL_ID="$(tf_output cognito_user_pool_id)"
COGNITO_CLIENT_ID="$(tf_output cognito_app_client_id)"

# Derive Cognito region from issuer URL if possible
COGNITO_ISSUER="$(tf_output cognito_issuer)"
COGNITO_REGION="$(echo "${COGNITO_ISSUER}" | awk -F'[./]' '{for(i=1;i<=NF;i++){if($i=="cognito-idp"){print $(i-1);exit}}}' || echo "${AWS_REGION}")"

log_info "Frontend bucket: ${FRONTEND_BUCKET}"
log_info "CloudFront distribution: ${CLOUDFRONT_DIST_ID}"
log_info "CloudFront domain: ${CLOUDFRONT_DOMAIN}"

ENV_FILE="${FRONTEND_DIR}/.env.production"

log_info "Writing production environment file to ${ENV_FILE}"
cat > "${ENV_FILE}" <<EOF
NEXT_PUBLIC_API_URL=${API_URL}
NEXT_PUBLIC_COGNITO_USER_POOL_ID=${COGNITO_POOL_ID}
NEXT_PUBLIC_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
NEXT_PUBLIC_COGNITO_REGION=${COGNITO_REGION}
NEXT_PUBLIC_ENV=${ENVIRONMENT}
EOF

log_info "Installing frontend dependencies..."
cd "${FRONTEND_DIR}"
npm install

log_info "Building static frontend assets..."
npm run build:production

if [ ! -d "${FRONTEND_DIR}/out" ]; then
  log_error "Expected build output directory 'out' not found."
  exit 1
fi

log_info "Syncing static assets to S3..."
aws s3 sync "${FRONTEND_DIR}/out/" "s3://${FRONTEND_BUCKET}/" \
  --region "${AWS_REGION}" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "*.json" \
  --exclude "*.txt"

aws s3 sync "${FRONTEND_DIR}/out/" "s3://${FRONTEND_BUCKET}/" \
  --region "${AWS_REGION}" \
  --cache-control "public, max-age=0, must-revalidate" \
  --content-type "text/html" \
  --exclude "*" \
  --include "*.html"

aws s3 sync "${FRONTEND_DIR}/out/" "s3://${FRONTEND_BUCKET}/" \
  --region "${AWS_REGION}" \
  --cache-control "public, max-age=0, must-revalidate" \
  --content-type "application/json" \
  --exclude "*" \
  --include "*.json"

aws s3 sync "${FRONTEND_DIR}/out/" "s3://${FRONTEND_BUCKET}/" \
  --region "${AWS_REGION}" \
  --cache-control "public, max-age=300, must-revalidate" \
  --content-type "text/plain" \
  --exclude "*" \
  --include "*.txt"

log_info "Creating CloudFront cache invalidation..."
INVALIDATION_ID="$(aws cloudfront create-invalidation \
  --distribution-id "${CLOUDFRONT_DIST_ID}" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)"

log_info "Waiting for invalidation ${INVALIDATION_ID} to complete..."
aws cloudfront wait invalidation-completed \
  --distribution-id "${CLOUDFRONT_DIST_ID}" \
  --id "${INVALIDATION_ID}"

log_info "Performing health check against deployed site..."
HTTP_STATUS="$(curl -o /dev/null -s -w "%{http_code}" "https://${CLOUDFRONT_DOMAIN}")"

if [ "${HTTP_STATUS}" != "200" ]; then
  log_warn "Health check returned status ${HTTP_STATUS}. Verify the site manually."
else
  log_success "Frontend is reachable at https://${CLOUDFRONT_DOMAIN}"
fi

log_success "Deployment complete."
echo ""
echo "Next steps:"
echo "  - Test authentication flow end-to-end."
echo "  - Verify API integrations, document uploads, and exports."
echo "  - Review CloudFront logs and metrics for anomalies."

