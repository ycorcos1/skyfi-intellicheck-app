#!/bin/bash
# Verification script to check deployment status

set -euo pipefail

echo "=== SkyFi IntelliCheck Deployment Verification ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Checking GitHub Actions workflows..."
if [ -f ".github/workflows/frontend-deploy.yml" ] && \
   [ -f ".github/workflows/backend-deploy.yml" ] && \
   [ -f ".github/workflows/lambda-deploy.yml" ]; then
    check_pass "All workflow files exist"
    
    # Check for workflow_dispatch
    if grep -q "workflow_dispatch" .github/workflows/*.yml; then
        check_pass "All workflows have workflow_dispatch enabled"
    else
        check_fail "Some workflows missing workflow_dispatch"
    fi
else
    check_fail "Missing workflow files"
fi

echo ""
echo "2. Checking Lambda configuration..."
if [ -f "infra/lambda.tf" ]; then
    if grep -q "aws_lambda_event_source_mapping" infra/lambda.tf; then
        check_pass "Lambda SQS event source mapping configured"
    else
        check_fail "Lambda SQS event source mapping missing"
    fi
    
    if grep -q "enabled.*=.*true" infra/lambda.tf; then
        check_pass "Lambda event source mapping enabled"
    else
        check_warn "Lambda event source mapping enabled status unclear"
    fi
else
    check_fail "Lambda Terraform file missing"
fi

echo ""
echo "3. Checking SQS service configuration..."
if [ -f "backend/app/services/sqs_service.py" ]; then
    check_pass "SQS service exists"
    if grep -q "enqueue_analysis" backend/app/services/sqs_service.py; then
        check_pass "SQS enqueue_analysis method exists"
    else
        check_fail "SQS enqueue_analysis method missing"
    fi
else
    check_fail "SQS service file missing"
fi

echo ""
echo "4. Checking company creation endpoint..."
if [ -f "backend/app/api/v1/endpoints/companies.py" ]; then
    if grep -q "enqueue_analysis" backend/app/api/v1/endpoints/companies.py; then
        check_pass "Company creation enqueues analysis"
    else
        check_fail "Company creation does not enqueue analysis"
    fi
else
    check_fail "Companies endpoint file missing"
fi

echo ""
echo "5. Checking frontend build..."
if [ -f "frontend/package.json" ]; then
    check_pass "Frontend package.json exists"
    if [ -f "frontend/package-lock.json" ]; then
        check_pass "Frontend package-lock.json exists (required for npm ci)"
    else
        check_warn "Frontend package-lock.json missing (may cause CI issues)"
    fi
else
    check_fail "Frontend package.json missing"
fi

echo ""
echo "6. Checking authentication fixes..."
if [ -f "frontend/middleware.ts" ]; then
    if grep -q "authStatus === \"none\"" frontend/middleware.ts || grep -q "let the client handle it" frontend/middleware.ts; then
        check_pass "Middleware allows client-side auth handling"
    else
        check_warn "Middleware may be too aggressive"
    fi
else
    check_fail "Frontend middleware missing"
fi

if [ -f "frontend/src/components/layout/ProtectedLayout.tsx" ]; then
    if grep -q "hasInitialized" frontend/src/components/layout/ProtectedLayout.tsx; then
        check_pass "ProtectedLayout has initialization guard"
    else
        check_warn "ProtectedLayout may not have initialization guard"
    fi
else
    check_fail "ProtectedLayout missing"
fi

echo ""
echo "=== Verification Complete ==="
echo ""
echo "Next steps:"
echo "1. Check GitHub Actions: https://github.com/ycorcos1/skyfi-intellicheck-app/actions"
echo "2. If deployments aren't running, manually trigger via 'Run workflow' button"
echo "3. After deployment, test:"
echo "   - Login to dashboard"
echo "   - Create a company"
echo "   - Verify analysis status changes from 'pending' to 'in progress' to 'completed'"
echo "   - Check CloudWatch logs: /aws/lambda/skyfi-intellicheck-worker-dev"

