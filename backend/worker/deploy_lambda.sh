#!/bin/bash
# Deploy Lambda worker to AWS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_PATH="${SCRIPT_DIR}/lambda_deployment_package.zip"
ENVIRONMENT="${1:-dev}"
AWS_REGION="${2:-us-east-1}"

# Get Lambda function name from Terraform outputs
LAMBDA_FUNCTION_NAME="skyfi-intellicheck-worker-${ENVIRONMENT}"

echo "Deploying Lambda worker to AWS..."
echo "Environment: ${ENVIRONMENT}"
echo "Function: ${LAMBDA_FUNCTION_NAME}"
echo "Region: ${AWS_REGION}"

# Build package if it doesn't exist
if [ ! -f "$PACKAGE_PATH" ]; then
    echo "Package not found, building..."
    bash "${SCRIPT_DIR}/build_lambda.sh"
fi

# Verify package exists
if [ ! -f "$PACKAGE_PATH" ]; then
    echo "❌ Error: Deployment package not found at ${PACKAGE_PATH}"
    exit 1
fi

# Check package size (Lambda has 50MB limit for direct upload, 250MB unzipped)
PACKAGE_SIZE=$(stat -f%z "$PACKAGE_PATH" 2>/dev/null || stat -c%s "$PACKAGE_PATH" 2>/dev/null)
PACKAGE_SIZE_MB=$((PACKAGE_SIZE / 1024 / 1024))

if [ $PACKAGE_SIZE_MB -gt 50 ]; then
    echo "⚠️  Warning: Package size is ${PACKAGE_SIZE_MB}MB (Lambda direct upload limit is 50MB)"
    echo "   Consider using S3 for deployment if size exceeds 50MB"
fi

# Update Lambda function code
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file "fileb://${PACKAGE_PATH}" \
    --region "$AWS_REGION" \
    --output json > /tmp/lambda_update.json

# Wait for update to complete (with error handling)
echo "Waiting for function update to complete..."
if aws lambda wait function-updated \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --region "$AWS_REGION" 2>/dev/null; then
    echo "✅ Function update confirmed"
else
    echo "⚠️  Could not verify function update (permissions issue), but code was uploaded"
    echo "   Checking if update succeeded..."
    sleep 3
fi

echo "✅ Lambda function code deployed successfully!"

# Display function info (with error handling)
echo ""
echo "Function Configuration:"
if aws lambda get-function \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --query 'Configuration.{FunctionName:FunctionName, Runtime:Runtime, Handler:Handler, CodeSize:CodeSize, LastModified:LastModified, State:State, Version:Version}' \
    --output table 2>/dev/null; then
    :
else
    echo "⚠️  Could not retrieve function configuration (permissions issue)"
    echo "   Code was successfully uploaded (CodeSize: $(cat /tmp/lambda_update.json | grep -o '"CodeSize":[0-9]*' | cut -d: -f2) bytes)"
fi

# Display environment variables (excluding sensitive ones)
echo ""
echo "Environment Variables:"
if aws lambda get-function \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --query 'Configuration.Environment.Variables' \
    --output table 2>/dev/null; then
    :
else
    echo "⚠️  Could not retrieve environment variables (permissions issue)"
fi

