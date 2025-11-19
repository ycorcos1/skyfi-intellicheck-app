# Cognito Development User Setup

This guide walks through creating development users in the Cognito User Pool
provisioned for SkyFi IntelliCheck and retrieving JWTs for local testing.

---

## Prerequisites

- AWS CLI configured with the IntelliCheck IAM credentials
- Terraform infrastructure deployed (PR #5) to create the Cognito resources
- Access to the User Pool outputs:
  - `cognito_user_pool_id`
  - `cognito_app_client_id`
  - `cognito_issuer`

---

## Retrieve Terraform Outputs

```bash
cd infra
terraform output cognito_user_pool_id
terraform output cognito_app_client_id
terraform output cognito_issuer
```

Copy these values—they will be used for user creation and application
configuration.

---

## Create a Development User

### AWS Console

1. Open **Amazon Cognito** in the AWS Console (Region: `us-east-1`).
2. Select the `skyfi-intellicheck-user-pool-{environment}`.
3. Choose **Create user**.
4. Enter an email address (for example `dev@example.com`) and a temporary password.
5. Send credentials to the developer; the user will be prompted to change the
   password on first sign-in.

### AWS CLI

```bash
USER_POOL_ID="<cognito_user_pool_id output>"
EMAIL="dev@example.com"
TEMP_PASSWORD="TempPass123!"

aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$EMAIL" \
  --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
  --temporary-password "$TEMP_PASSWORD" \
  --region us-east-1

# Optional: immediately set a permanent password for the dev user.
aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "$EMAIL" \
  --password "DevPassword123!" \
  --permanent \
  --region us-east-1
```

---

## Authenticate and Retrieve Tokens

Use the Cognito App Client to initiate an auth flow and capture the tokens:

```bash
APP_CLIENT_ID="<cognito_app_client_id output>"
EMAIL="dev@example.com"
PASSWORD="DevPassword123!"

aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$APP_CLIENT_ID" \
  --auth-parameters USERNAME="$EMAIL",PASSWORD="$PASSWORD" \
  --region us-east-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

Store the returned token in an environment variable for local testing:

```bash
TOKEN="<paste token>"
```

---

## Test the FastAPI Authentication

```bash
# Public endpoint (should succeed without token)
curl http://localhost:8000/health

# Protected endpoint without token (should fail with 401)
curl http://localhost:8000/v1/protected

# Protected endpoint with valid token (should succeed)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/v1/protected
```

---

## Troubleshooting

- **Unable to find key / invalid credentials**  
  Ensure Terraform outputs are synced with the backend environment variables.
  Restart the backend to clear cached JWKS keys if you recently rotated keys.

- **Token expired**  
  Tokens expire after 60 minutes. Re-run the `initiate-auth` command to obtain a
  fresh token.

- **Password reset required**  
  When using temporary passwords, Cognito requires a password change on first
  sign-in. Use the AWS Console or CLI to set a permanent password.

- **Region mismatch**  
  Confirm that the backend `COGNITO_REGION` matches the deployed User Pool
  region (`us-east-1` by default).

