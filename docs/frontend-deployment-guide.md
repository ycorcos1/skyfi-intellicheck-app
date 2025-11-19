# SkyFi IntelliCheck Frontend Deployment Guide

This guide explains how to deploy the SkyFi IntelliCheck frontend to AWS using the infrastructure delivered in PR #30.

---

## 1. Prerequisites

- Terraform infrastructure applied (PR #30 resources provisioned)
- Backend API deployed and reachable (PR #18)
- AWS CLI configured with credentials that can manage S3, CloudFront, ACM, and Route53
- Node.js 18+ with npm
- Terraform >= 1.5.0
- `curl` installed (used by the deployment script for health checks)
- Network access to download npm packages and reach AWS services

---

## 2. Infrastructure Deployment

If you have not yet applied the Terraform configuration:

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Key Terraform Resources

- S3 bucket for static assets
- CloudFront distribution with security headers and SPA routing
- Optional ACM certificate (us-east-1) and Route53 records for custom domains
- Outputs for frontend bucket, CloudFront details, API URL, and Cognito configuration

---

## 3. Required Terraform Outputs

The deployment script consumes the following outputs:

- `frontend_bucket_name`
- `cloudfront_distribution_id`
- `cloudfront_distribution_domain_name`
- `api_url`
- `cognito_user_pool_id`
- `cognito_app_client_id`
- `cognito_issuer`

You can inspect them manually with:

```bash
terraform -chdir=infra output
```

---

## 4. Deployment Script

The repository includes `scripts/deploy-frontend.sh` which automates the build and upload process.

### Usage

```bash
./scripts/deploy-frontend.sh [environment]
```

- `environment` defaults to `dev`
- Export `AWS_REGION` if you need a different region (default: `us-east-1`)

### What the Script Does

1. Validates required CLI tools.
2. Reads Terraform outputs for bucket, CloudFront, and Cognito configuration.
3. Writes `frontend/.env.production` with the correct environment variables.
4. Installs npm dependencies (if needed).
5. Builds static assets (`next build` with `output: 'export'`).
6. Syncs assets to S3 with optimized cache headers.
7. Creates a CloudFront cache invalidation and waits for completion.
8. Performs a basic health check against the CloudFront URL.

> **Note:** `.env.production` is ignored by git. The script overwrites it on each run, so capture any manual changes elsewhere if required.

---

## 5. Manual Deployment Steps (Optional)

If you prefer manual steps:

1. Copy `terraform.tfvars.example` to `terraform.tfvars` (if needed) and apply Terraform.
2. Create `frontend/.env.production` with values from Terraform outputs:
   ```ini
   NEXT_PUBLIC_API_URL=https://<alb-or-api-gateway-url>
   NEXT_PUBLIC_COGNITO_USER_POOL_ID=<user-pool-id>
   NEXT_PUBLIC_COGNITO_CLIENT_ID=<app-client-id>
   NEXT_PUBLIC_COGNITO_REGION=us-east-1
   NEXT_PUBLIC_ENV=production
   ```
3. Build static assets:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
4. Upload to S3:
   ```bash
   aws s3 sync out/ s3://<frontend-bucket>/ --delete
   ```
5. Create a CloudFront invalidation:
   ```bash
   aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
   ```

---

## 6. Post-Deployment Verification

1. Navigate to the CloudFront URL (from `frontend_url` output or terminal script summary).
2. Verify HTTPS lock icon (valid certificate).
3. Log in via Cognito and confirm redirect to dashboard.
4. Exercise key workflows:
   - Company search/filtering
   - Company creation
   - Document upload/download
   - Notes CRUD operations
   - PDF/JSON exports
5. Refresh dashboard and detail routes (SPA routing 403/404 overrides should succeed).
6. Check browser console for CSP or CORS errors.

---

## 7. Rollback Procedure

**If the new deployment introduces issues:**

1. Restore specific files using S3 object versioning:
   ```bash
   aws s3api list-object-versions --bucket <frontend-bucket>
   aws s3api copy-object \
     --copy-source "<frontend-bucket>/<key>?versionId=<version>" \
     --bucket <frontend-bucket> \
     --key <key>
   ```
2. Re-run the deployment script with the previous Git commit (checkout prior commit, run script).
3. Invalidate CloudFront cache to propagate the rollback.

---

## 8. Troubleshooting

| Symptom | Possible Cause | Resolution |
| --- | --- | --- |
| CloudFront returns 403 | OAC not attached or bucket policy missing | Re-apply Terraform, ensure `aws_s3_bucket_policy.frontend` exists |
| SPA routes 404 on refresh | Custom error responses not configured | Confirm Terraform `custom_error_response` blocks, re-deploy |
| API calls blocked by CSP | `api_url` variable not set | Update `terraform.tfvars` with `api_url`, re-apply and redeploy |
| Cognito redirect loop | Callback URLs not updated | Update Cognito app client with CloudFront URL, re-run deployment |
| Static assets stale | Cache invalidation skipped | Re-run script or create manual invalidation |

---

## 9. Environment Variables Reference

| Variable | Description | Source |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Backend API base URL | Terraform output `api_url` (ALB or API Gateway) |
| `NEXT_PUBLIC_COGNITO_USER_POOL_ID` | Cognito user pool | Terraform output `cognito_user_pool_id` |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | Cognito app client | Terraform output `cognito_app_client_id` |
| `NEXT_PUBLIC_COGNITO_REGION` | Cognito region | Derived from output `cognito_issuer` |
| `NEXT_PUBLIC_ENV` | Deployment environment label | Script argument |

---

## 10. Monitoring & Observability

- CloudFront metrics (cache hit rate, 4xx/5xx errors)
- S3 access logs (enable via Terraform if needed)
- Browser performance (Lighthouse audits)
- Cognito sign-in metrics
- Backend API logs for CORS/auth failures

---

## 11. Security Checklist

- [x] S3 bucket private; only CloudFront OAC access
- [x] HTTPS enforced (CloudFront redirects HTTP)
- [x] Security headers (HSTS, CSP, X-Frame-Options, etc.) applied
- [x] CloudFront minimum TLS version 1.2
- [x] Environment variables managed outside of version control
- [x] Cache invalidation performed after each deployment

---

## 12. Additional Notes

- When enabling a custom domain, ensure ACM certificate validation completes before creating CloudFront distribution (Terraform handles Route53 validation automatically when `route53_zone_id` is supplied).
- `cloudfront_price_class` defaults to `PriceClass_100` (US, Canada, Europe). Adjust in `terraform.tfvars` for global traffic.
- Update Cognito app client callback and sign-out URLs to include the CloudFront (or custom) domain.
- Update backend CORS configuration (`frontend_urls` variable) to include the CloudFront/custom domain before deploying.

---

Deployment complete! Refer back to this document during future releases or custom domain cutovers.

