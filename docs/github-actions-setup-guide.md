# GitHub Actions Setup Guide - Step by Step

This guide will walk you through setting up GitHub Actions to automatically build and deploy your backend Docker image to ECR.

## Prerequisites

- ✅ Git repository initialized (done)
- ✅ Initial commit created (done)
- GitHub account
- GitHub Desktop installed
- AWS CLI configured with appropriate permissions

## Step 1: Create GitHub Repository

1. Open **GitHub Desktop**
2. Click **File** → **Add Local Repository**
3. Navigate to: `/Users/yahavcorcos/Desktop/gauntlet-workspace/skyfi-intellicheck-app`
4. Click **Add Repository**
5. Click **Publish repository** (top right)
6. Choose:
   - **Name**: `skyfi-intellicheck-app` (or your preferred name)
   - **Description**: (optional)
   - **Keep this code private** or **Make this code public** (your choice)
7. Click **Publish Repository**

## Step 2: Get Required Values from Terraform

Before setting up secrets, we need to get some values from your Terraform outputs. Run these commands:

```bash
cd /Users/yahavcorcos/Desktop/gauntlet-workspace/skyfi-intellicheck-app/infra

# Get API URL (CloudFront domain)
terraform output -raw api_url

# Get CloudFront Distribution ID for frontend
terraform output -raw frontend_cloudfront_distribution_id

# Get Cognito values
terraform output cognito_user_pool_id
terraform output cognito_user_pool_client_id
```

**Save these values** - you'll need them in the next step.

## Step 3: Configure GitHub Secrets

1. Go to your GitHub repository in a web browser
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **New repository secret** for each secret below:

### Required Secrets for Backend Deployment:

| Secret Name | Value | How to Get |
|------------|-------|------------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key | From your AWS IAM user |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key | From your AWS IAM user |
| `API_URL_DEV` | Your API URL | From `terraform output -raw api_url` |
| `COGNITO_POOL_ID_DEV` | Cognito User Pool ID | From `terraform output cognito_user_pool_id` |
| `COGNITO_CLIENT_ID_DEV` | Cognito Client ID | From `terraform output cognito_user_pool_client_id` |
| `COGNITO_REGION_DEV` | `us-east-1` | Usually `us-east-1` |
| `CLOUDFRONT_DISTRIBUTION_ID_DEV` | CloudFront Distribution ID | From `terraform output -raw frontend_cloudfront_distribution_id` |

### Optional Secrets (for production later):

- `API_URL_PROD`
- `COGNITO_POOL_ID_PROD`
- `COGNITO_CLIENT_ID_PROD`
- `COGNITO_REGION_PROD`
- `CLOUDFRONT_DISTRIBUTION_ID_PROD`
- `FRONTEND_URL_PROD`

## Step 4: Verify IAM Permissions

The IAM user/role used for GitHub Actions needs these permissions:

- `ecr:GetAuthorizationToken`
- `ecr:BatchGetImage`
- `ecr:PutImage`
- `ecr:BatchCheckLayerAvailability`
- `ecr:GetDownloadUrlForLayer`
- `ecs:UpdateService`
- `ecs:DescribeServices`
- `ecs:DescribeTaskDefinition`
- `ecs:RegisterTaskDefinition`
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`
- `cloudfront:CreateInvalidation`
- `s3:PutObject`
- `s3:GetObject`
- `s3:ListBucket`

If you're using the same IAM user that deployed Terraform, you likely already have these permissions.

## Step 5: Push Your Code

1. In **GitHub Desktop**, you should see your commit ready to push
2. Click **Push origin** (or **Publish branch** if it's the first push)
3. Wait for the push to complete

## Step 6: Trigger the Workflow

The workflow will automatically trigger when you push to the `main` branch. However, since we just did the initial commit, you can:

1. **Option A**: Make a small change and push again
   ```bash
   # Make a small change to trigger the workflow
   echo "# GitHub Actions Setup Complete" >> README.md
   git add README.md
   git commit -m "Trigger GitHub Actions workflow"
   ```
   Then push from GitHub Desktop.

2. **Option B**: Manually trigger the workflow
   - Go to your GitHub repository
   - Click **Actions** tab
   - Click **Backend Deployment** workflow
   - Click **Run workflow** → **Run workflow**

## Step 7: Monitor the Workflow

1. Go to your GitHub repository
2. Click **Actions** tab
3. You should see "Backend Deployment" workflow running
4. Click on it to see the progress
5. The workflow will:
   - ✅ Checkout code
   - ✅ Configure AWS credentials
   - ✅ Login to ECR
   - ✅ Build Docker image
   - ✅ Push to ECR
   - ✅ Force new ECS deployment
   - ✅ Wait for ECS service stability
   - ✅ Run health checks

## Step 8: Verify Deployment

Once the workflow completes successfully:

1. Check ECS service:
   ```bash
   aws ecs describe-services \
     --cluster skyfi-intellicheck-cluster-dev \
     --services skyfi-intellicheck-api-service-dev \
     --query "services[0].{Status:status,DesiredCount:desiredCount,RunningCount:runningCount}"
   ```

2. Check target group health:
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn $(aws elbv2 describe-target-groups --names skyfi-intcheck-tg-dev --query "TargetGroups[0].TargetGroupArn" --output text) \
     --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"
   ```

3. Test the API:
   ```bash
   curl $(terraform output -raw api_url)/health
   ```

## Troubleshooting

### Workflow Fails with "Access Denied"
- Check IAM permissions for the AWS credentials
- Verify the IAM user has ECR and ECS permissions

### Workflow Fails with "Image not found"
- This is expected on first run - the workflow will build and push the image

### ECS Service Doesn't Update
- Check ECS service events in AWS Console
- Verify the task definition was updated
- Check CloudWatch logs for errors

### Health Checks Fail
- Check ECS task logs in CloudWatch
- Verify the `/health` endpoint is accessible
- Check security group rules allow ALB to reach ECS tasks

## Next Steps

Once the backend is deployed successfully:

1. The frontend can be deployed using `frontend-deploy.yml` workflow
2. The Lambda worker can be deployed using `lambda-deploy.yml` workflow
3. Set up branch protection rules for `main` and `production` branches
4. Configure environment-specific secrets for production

## Need Help?

- Check the [CI/CD Deployment Guide](./ci-cd-deployment-guide.md) for more details
- Review workflow logs in the GitHub Actions tab
- Check AWS CloudWatch logs for application errors

