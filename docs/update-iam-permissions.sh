#!/usr/bin/env bash
# Script to update IAM user permissions for SkyFi IntelliCheck
# This script requires admin permissions or must be run by an AWS administrator

set -euo pipefail

IAM_USER_NAME="${1:-skyfi-intellicheck-app}"
POLICY_NAME="${2:-SkyFiIntelliCheckPolicy}"

echo "Updating IAM permissions for user: ${IAM_USER_NAME}"
echo "Policy name: ${POLICY_NAME}"

# Extract the JSON policy from the markdown file
# This assumes the policy JSON is between ```json and ``` markers
POLICY_JSON=$(sed -n '/^```json$/,/^```$/p' aws-permissions.md | sed '1d;$d')

# Create a temporary file with the policy
TEMP_POLICY=$(mktemp)
echo "${POLICY_JSON}" > "${TEMP_POLICY}"

echo ""
echo "Policy document prepared. Applying to IAM user..."
echo ""

# Apply the policy as an inline policy
aws iam put-user-policy \
  --user-name "${IAM_USER_NAME}" \
  --policy-name "${POLICY_NAME}" \
  --policy-document "file://${TEMP_POLICY}"

echo ""
echo "✅ IAM policy updated successfully!"
echo ""
echo "To verify, run:"
echo "  aws iam get-user-policy --user-name ${IAM_USER_NAME} --policy-name ${POLICY_NAME}"

# Cleanup
rm -f "${TEMP_POLICY}"

