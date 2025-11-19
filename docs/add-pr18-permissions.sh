#!/usr/bin/env bash
# Script to add PR #18 required permissions to IAM user
# This must be run by an AWS administrator or user with iam:CreatePolicy and iam:AttachUserPolicy permissions

set -euo pipefail

IAM_USER_NAME="${1:-skyfi-intellicheck-app}"
POLICY_NAME="SkyFiIntelliCheck-PR18-Permissions"

echo "Adding PR #18 permissions for user: ${IAM_USER_NAME}"
echo ""

# Create the policy document
POLICY_DOC=$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3AccelerateConfig",
      "Effect": "Allow",
      "Action": ["s3:GetBucketAccelerateConfiguration"],
      "Resource": ["arn:aws:s3:::skyfi-intellicheck-*", "arn:aws:s3:::skyfi-intellicheck-*/*"]
    },
    {
      "Sid": "ELBTargetGroupAndListeners",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:ModifyTargetGroupAttributes",
        "elasticloadbalancing:DescribeTargetGroupAttributes",
        "elasticloadbalancing:CreateListener",
        "elasticloadbalancing:DeleteListener",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:ModifyListener"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CognitoTags",
      "Effect": "Allow",
      "Action": ["cognito-idp:TagResource", "cognito-idp:UntagResource"],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogsTags",
      "Effect": "Allow",
      "Action": ["logs:TagResource", "logs:UntagResource"],
      "Resource": "*"
    }
  ]
}
EOF
)

echo "$POLICY_DOC" > /tmp/pr18-policy.json

echo "Policy document created. Attempting to create managed policy..."
echo ""

# Try to create managed policy (requires admin permissions)
if aws iam create-policy \
  --policy-name "${POLICY_NAME}" \
  --policy-document file:///tmp/pr18-policy.json \
  --description "Additional permissions for PR #18: ALB, Cognito, CloudWatch Logs tagging" \
  2>&1; then
  
  echo ""
  echo "✅ Managed policy created successfully!"
  echo ""
  
  # Get account ID
  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"
  
  echo "Attaching policy to user..."
  aws iam attach-user-policy \
    --user-name "${IAM_USER_NAME}" \
    --policy-arn "${POLICY_ARN}"
  
  echo ""
  echo "✅ Policy attached successfully!"
  echo ""
  echo "Permissions added:"
  echo "  - s3:GetBucketAccelerateConfiguration"
  echo "  - elasticloadbalancing:ModifyTargetGroupAttributes"
  echo "  - elasticloadbalancing:DescribeTargetGroupAttributes"
  echo "  - elasticloadbalancing:CreateListener/DeleteListener/DescribeListeners/ModifyListener"
  echo "  - cognito-idp:TagResource/UntagResource"
  echo "  - logs:TagResource/UntagResource"
  
else
  echo ""
  echo "❌ Failed to create managed policy (requires admin permissions)"
  echo ""
  echo "Alternative: Add as inline policy (if user has space):"
  echo "  aws iam put-user-policy \\"
  echo "    --user-name ${IAM_USER_NAME} \\"
  echo "    --policy-name ${POLICY_NAME} \\"
  echo "    --policy-document file:///tmp/pr18-policy.json"
  echo ""
  echo "Or manually add via AWS Console:"
  echo "  1. Go to IAM → Users → ${IAM_USER_NAME}"
  echo "  2. Add permissions → Create inline policy"
  echo "  3. Paste the JSON from /tmp/pr18-policy.json"
fi

echo ""
echo "Policy document saved to: /tmp/pr18-policy.json"

