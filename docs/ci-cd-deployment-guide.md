# SkyFi IntelliCheck CI/CD Deployment Guide

## Overview

This guide explains how automated deployments for SkyFi IntelliCheck work and how to manage the pipelines for each environment.

Three GitHub Actions workflows handle deployments:

- `backend-deploy.yml` builds the FastAPI container, pushes it to Amazon ECR, and refreshes the ECS service.
- `frontend-deploy.yml` builds the Next.js application, publishes the static assets to the S3 bucket, and invalidates the CloudFront cache.
- `lambda-deploy.yml` packages the Lambda worker and updates the deployed function.

The `pr-checks.yml` workflow runs unit tests, linting, and packaging checks on every pull request targeting `main` or `production`.

## Branch Strategy

- `main`: Deploys automatically to the **dev** environment.
- `production`: Deploys to the **prod** environment after manual approval. Configure the `production` environment in GitHub with required reviewers to enforce approvals.

## Required GitHub Secrets

Store the following secrets at the repository level. Keep values distinct for each environment.

| Secret | Description |
| ------ | ----------- |
| `AWS_ACCESS_KEY_ID` | Access key for the CI/CD IAM user (least-privilege). |
| `AWS_SECRET_ACCESS_KEY` | Secret key for the CI/CD IAM user. |
| `API_URL_DEV` | Base URL for the dev API (e.g., `https://api-dev.example.com`). |
| `API_URL_PROD` | Base URL for the prod API. |
| `COGNITO_POOL_ID_DEV` | Cognito User Pool ID (dev). |
| `COGNITO_POOL_ID_PROD` | Cognito User Pool ID (prod). |
| `COGNITO_CLIENT_ID_DEV` | Cognito App Client ID (dev). |
| `COGNITO_CLIENT_ID_PROD` | Cognito App Client ID (prod). |
| `COGNITO_REGION_DEV` | Cognito region for dev (usually `us-east-1`). |
| `COGNITO_REGION_PROD` | Cognito region for prod. |
| `CLOUDFRONT_DISTRIBUTION_ID_DEV` | CloudFront distribution ID for dev. |
| `CLOUDFRONT_DISTRIBUTION_ID_PROD` | CloudFront distribution ID for prod. |
| `FRONTEND_URL_PROD` | Public URL for the production frontend (used for workflow metadata). |

> **Tip:** If the Terraform naming conventions are unchanged, S3 buckets and ECS/ECR resource names do not require secrets because they are deterministic (`skyfi-intellicheck-<component>-{env}`).

## IAM Permissions

The CI/CD IAM user must have permissions to:

- Authenticate to Amazon ECR (`ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `ecr:PutImage`).
- Manage ECS services (`ecs:UpdateService`, `ecs:DescribeServices`, `ecs:DescribeTaskDefinition`, `ecs:RegisterTaskDefinition`).
- Write CloudWatch logs and perform CloudFront invalidations.
- Sync to S3 buckets used for the frontend.
- Update Lambda function code and wait for deployment completion.

Refer to `docs/aws-permissions.md` and `docs/additional-permissions-needed.json` for a baseline policy; add ECS, Lambda, S3, and CloudFront permissions for CI/CD automation.

## Workflow Summary

### backend-deploy.yml

1. Builds and tags the Docker image with the commit SHA and `latest`.
2. Pushes the image to the environment-specific ECR repository.
3. Forces a new deployment on the ECS service and waits for stability.
4. Runs `scripts/health-check.sh` against the environment API URL.

### frontend-deploy.yml

1. Builds the Next.js app with environment-specific variables.
2. Syncs the `out/` directory to the S3 bucket (`skyfi-intellicheck-frontend-{env}`).
3. Invalidates the CloudFront distribution cache.

### lambda-deploy.yml

1. Generates `lambda_deployment_package.zip` via `backend/worker/build_lambda.sh`.
2. Updates the Lambda function code (`skyfi-intellicheck-worker-{env}`).
3. Waits for deployment completion.
4. Runs `python backend/worker/test_deployment.py {env}` (skips invocation tests when no company ID is supplied).

### pr-checks.yml

1. Installs backend dependencies and runs `pytest`.
2. Runs `npm run lint` and `npm run build` for the frontend.
3. Builds the Lambda deployment package to ensure packaging scripts remain valid.

## Manual Deployment & Rollback

### Backend (ECS)

1. Identify the previous stable Task Definition revision.
2. Run:
   ```bash
   aws ecs update-service \
     --cluster skyfi-intellicheck-cluster-{env} \
     --service skyfi-intellicheck-api-service-{env} \
     --task-definition <previous-task-definition-arn>
   ```
3. Monitor the service in the ECS console until it returns to a steady state.

### Frontend (S3/CloudFront)

1. Use S3 versioning to restore the previous deployment (`skyfi-intellicheck-frontend-{env}`).
2. Re-run the workflow or manually invalidate CloudFront:
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id <distribution-id> \
     --paths "/*"
   ```

### Lambda Worker

1. List previous versions:
   ```bash
   aws lambda list-versions-by-function --function-name skyfi-intellicheck-worker-{env}
   ```
2. Update the alias (or function) to a known good version:
   ```bash
   aws lambda update-function-code \
     --function-name skyfi-intellicheck-worker-{env} \
     --qualifier <version> \
     --zip-file fileb://backend/worker/lambda_deployment_package.zip
   ```

## Monitoring & Alerts

- **CloudWatch Logs**: Check `/aws/ecs/skyfi-intellicheck-api-service-{env}` and `/aws/lambda/skyfi-intellicheck-worker-{env}`.
- **CloudWatch Metrics**: Review queue depth, Lambda errors, ECS CPU/memory, and ALB target health.
- **Notifications**: Configure a Slack webhook (e.g., with `8398a7/action-slack`) if real-time alerts are required.

## Local Testing Tips

- Run `scripts/health-check.sh https://api-dev.example.com` before and after deployments.
- Use `scripts/smoke-test.sh https://api-dev.example.com` to validate the OpenAPI schema.
- For Lambda, `python backend/worker/test_deployment.py dev <company_id>` runs end-to-end smoke tests for a specific company.

## Troubleshooting

- **Workflow fails during `aws ecs wait services-stable`**: Check ECS service events; roll back to the previous task definition.
- **Frontend deploy succeeds but site is stale**: Ensure CloudFront invalidation step completed successfully.
- **Lambda smoke test fails**: Review CloudWatch logs and confirm the deployment package contains the latest code.
- **Permission errors**: Verify the IAM policy attached to the CI/CD user includes the required ECS, Lambda, S3, and CloudFront actions.

---

For further questions about deployment operations, contact the SkyFi IntelliCheck platform team.

