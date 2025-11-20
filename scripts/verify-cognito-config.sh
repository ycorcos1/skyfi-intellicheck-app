#!/bin/bash
# Script to verify Cognito configuration matches between frontend and backend

set -euo pipefail

echo "=== Cognito Configuration Verification ==="
echo ""

# Check if terraform is available
if ! command -v terraform &> /dev/null; then
    echo "⚠️  Terraform not found. Skipping Terraform output check."
    echo ""
else
    echo "📋 Terraform Outputs (what backend expects):"
    cd infra
    terraform output -json 2>/dev/null | jq -r '
        "COGNITO_USER_POOL_ID: " + (.cognito_user_pool_id.value // "NOT SET"),
        "COGNITO_CLIENT_ID: " + (.cognito_app_client_id.value // "NOT SET"),
        "COGNITO_REGION: us-east-1",
        "COGNITO_ISSUER: " + (.cognito_issuer.value // "NOT SET")
    ' || echo "⚠️  Could not read Terraform outputs. Make sure Terraform is initialized."
    cd ..
    echo ""
fi

echo "📋 GitHub Secrets (what frontend uses):"
echo "   These should be set in GitHub repository secrets:"
echo "   - COGNITO_POOL_ID_DEV"
echo "   - COGNITO_CLIENT_ID_DEV"
echo "   - COGNITO_REGION_DEV"
echo "   - API_URL_DEV"
echo ""

echo "🔍 To verify:"
echo "   1. Check GitHub Secrets match Terraform outputs above"
echo "   2. Check backend ECS task environment variables match Terraform outputs"
echo "   3. Check frontend build uses the GitHub secrets"
echo ""

echo "💡 Common issues:"
echo "   - Frontend Cognito Pool ID doesn't match backend"
echo "   - Frontend Cognito Client ID doesn't match backend"
echo "   - Token issuer/audience validation fails"
echo ""

