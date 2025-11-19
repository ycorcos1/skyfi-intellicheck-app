#!/usr/bin/env bash
# Script to add Cognito AdminUpdateUserAttributes permission to IAM user
# This must be run by an AWS administrator or user with iam:PutUserPolicy permissions

set -euo pipefail

IAM_USER_NAME="${1:-skyfi-intellicheck-app}"
POLICY_NAME="SkyFiIntelliCheck-CognitoUserUpdate"

echo "Adding Cognito user update permission for user: ${IAM_USER_NAME}"
echo ""

# Create the policy document
POLICY_DOC=$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CognitoUserUpdate",
      "Effect": "Allow",
      "Action": [
        "cognito-idp:AdminUpdateUserAttributes"
      ],
      "Resource": "*"
    }
  ]
}
EOF
)

echo "$POLICY_DOC" > /tmp/cognito-user-update-policy.json

echo "Policy document created. Attempting to add as inline policy..."
echo ""

# Try to add as inline policy
if aws iam put-user-policy \
  --user-name "${IAM_USER_NAME}" \
  --policy-name "${POLICY_NAME}" \
  --policy-document file:///tmp/cognito-user-update-policy.json \
  2>&1; then
  
  echo ""
  echo "✅ Permission added successfully!"
  echo ""
  echo "The IAM user now has permission to update Cognito user attributes."
  
else
  echo ""
  echo "❌ Failed to add permission (requires admin permissions)"
  echo ""
  echo "Alternative: Add manually via AWS Console:"
  echo "  1. Go to IAM → Users → ${IAM_USER_NAME}"
  echo "  2. Add permissions → Create inline policy"
  echo "  3. Paste the JSON from /tmp/cognito-user-update-policy.json"
fi

echo ""
echo "Policy document saved to: /tmp/cognito-user-update-policy.json"

