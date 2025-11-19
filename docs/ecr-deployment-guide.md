# SkyFi IntelliCheck – Backend ECR Deployment Guide

This guide explains how to build the backend Docker image and push it to the Elastic Container Registry (ECR) provisioned for SkyFi IntelliCheck.

## Prerequisites

- AWS CLI configured with the IntelliCheck IAM user/role
- Docker installed locally
- Terraform infrastructure applied so the ECR repository exists
- Logged in to this repository root (`/Users/yahavcorcos/Desktop/gauntlet-workspace/skyfi-intellicheck-app`)

## Quick Start (Recommended)

```bash
cd backend
./scripts/build-and-push.sh dev v1.0.0
```

The script performs the following:

1. Fetches the ECR repository URL from Terraform outputs.
2. Authenticates the Docker CLI with ECR.
3. Builds the backend Docker image.
4. Tags the image with the provided version and `latest`.
5. Pushes both tags to ECR.

Environment defaults:

- Environment argument defaults to `dev`.
- Tag argument defaults to `latest`.
- AWS region defaults to `us-east-1` (override by exporting `AWS_REGION`).

## Manual Workflow

```bash
# 1. Retrieve ECR repository URL (requires terraform apply already run)
cd infra
ECR_REPO_URL=$(terraform output -raw ecr_repository_url)

# 2. Authenticate to ECR
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin "${ECR_REPO_URL}"

# 3. Build backend image
cd ../backend
docker build -t skyfi-intellicheck-backend:v1.0.0 .

# 4. Tag for ECR
docker tag skyfi-intellicheck-backend:v1.0.0 "${ECR_REPO_URL}:v1.0.0"
docker tag skyfi-intellicheck-backend:v1.0.0 "${ECR_REPO_URL}:latest"

# 5. Push tags
docker push "${ECR_REPO_URL}:v1.0.0"
docker push "${ECR_REPO_URL}:latest"
```

## Image Tagging Strategy

- `latest` — always points to the most recent build.
- `vX.Y.Z` — semantic version for release builds (e.g., `v1.0.0`).
- `release-*` — pre-release or candidate builds.
- `sha-<commit>` — optional commit-specific tags for traceability.

## Lifecycle Policies

The Terraform configuration applies two lifecycle policies:

1. Retain the 10 most recent images whose tags start with `v` or `release`.
2. Expire untagged images after 7 days.

## Verifying the Repository

```bash
# List repositories
aws ecr describe-repositories \
  --repository-names "skyfi-intellicheck-backend-dev"

# Check pushed images
aws ecr describe-images \
  --repository-name "skyfi-intellicheck-backend-dev"
```

## Troubleshooting

- **Authentication errors**: Confirm AWS credentials with `aws sts get-caller-identity`.
- **Terraform output missing**: Run `terraform apply` in `infra/` to create/update the ECR repository.
- **Permission denied pushing images**: Ensure the IAM user/role includes the required `ecr:*` permissions from `docs/aws-permissions.md`.
- **Docker build failures**: Run `docker build --no-cache .` to surface build-time issues.

## Next Steps

After pushing an image, update the ECS task definition (PR #18) to point at the new ECR image URI: `$(terraform output -raw ecr_repository_url):<tag>`.


