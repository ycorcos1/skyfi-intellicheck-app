#!/usr/bin/env bash
set -euo pipefail

# SkyFi IntelliCheck - Backend Docker image build and ECR push script
# Usage: ./scripts/build-and-push.sh [environment] [tag]
# Example: ./scripts/build-and-push.sh dev v1.0.0

ENVIRONMENT="${1:-dev}"
TAG="${2:-latest}"
AWS_REGION="${AWS_REGION:-us-east-1}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT_DIR}/../infra"

echo "SkyFi IntelliCheck - Building and pushing backend image"
echo "Environment : ${ENVIRONMENT}"
echo "Tag         : ${TAG}"
echo "AWS Region  : ${AWS_REGION}"

if ! command -v aws >/dev/null 2>&1; then
  echo "❌ AWS CLI is required but not found in PATH."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker is required but not found in PATH."
  exit 1
fi

if [ ! -d "${INFRA_DIR}" ]; then
  echo "❌ Unable to locate infra directory at ${INFRA_DIR}"
  exit 1
fi

pushd "${INFRA_DIR}" >/dev/null
if ! terraform output -raw ecr_repository_url >/dev/null 2>&1; then
  echo "❌ Terraform output ecr_repository_url not found. Ensure terraform apply has been run."
  popd >/dev/null
  exit 1
fi
ECR_REPO_URL="$(terraform output -raw ecr_repository_url)"
popd >/dev/null

IMAGE_LOCAL_NAME="skyfi-intellicheck-backend:${TAG}"
IMAGE_ECR_TAGGED="${ECR_REPO_URL}:${TAG}"
IMAGE_ECR_LATEST="${ECR_REPO_URL}:latest"

echo "📦 ECR repository URL: ${ECR_REPO_URL}"

echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_REPO_URL}"

echo "🏗️  Building Docker image (${IMAGE_LOCAL_NAME})..."
docker build -t "${IMAGE_LOCAL_NAME}" -f "${ROOT_DIR}/Dockerfile" "${ROOT_DIR}"

echo "🏷️  Tagging image for ECR..."
docker tag "${IMAGE_LOCAL_NAME}" "${IMAGE_ECR_TAGGED}"
docker tag "${IMAGE_LOCAL_NAME}" "${IMAGE_ECR_LATEST}"

echo "⬆️  Pushing tags to ECR..."
docker push "${IMAGE_ECR_TAGGED}"
docker push "${IMAGE_ECR_LATEST}"

echo "✅ Image push complete."
echo "    Pushed: ${IMAGE_ECR_TAGGED}"
echo "    Pushed: ${IMAGE_ECR_LATEST}"