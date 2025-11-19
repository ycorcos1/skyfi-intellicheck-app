#!/bin/bash
# Script to update user first name and last name in Cognito User Pool
# Usage: ./update-user-name.sh <user_pool_id> <email> <first_name> <last_name>

set -e

if [ $# -lt 4 ]; then
  echo "Usage: $0 <user_pool_id> <email> <first_name> <last_name>"
  echo "Example: $0 us-east-1_XXXXXXXXX ycorcos26@gmail.com Yahav Corcos"
  exit 1
fi

USER_POOL_ID="$1"
EMAIL="$2"
FIRST_NAME="$3"
LAST_NAME="$4"
REGION="us-east-1"

echo "Updating user attributes for $EMAIL..."
echo "First Name: $FIRST_NAME"
echo "Last Name: $LAST_NAME"

aws cognito-idp admin-update-user-attributes \
  --user-pool-id "$USER_POOL_ID" \
  --username "$EMAIL" \
  --user-attributes \
    Name=given_name,Value="$FIRST_NAME" \
    Name=family_name,Value="$LAST_NAME" \
  --region "$REGION"

echo "User attributes updated successfully!"
echo ""
echo "Note: The user will need to log out and log back in to see the changes in the UI."

