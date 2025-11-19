# SkyFi IntelliCheck

**Version:** 1.0  
**Owner:** Yahav Corcos  
**Status:** Active Development  
**Deployment Region:** us-east-1

---

## Table of Contents

- [Who This Project Is For](#who-this-project-is-for)
- [What This Project Does](#what-this-project-does)
- [Why This Was Built](#why-this-was-built)
- [How It Was Built](#how-it-was-built)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Infrastructure Setup](#infrastructure-setup)
- [Cognito Development User Setup](#cognito-development-user-setup)
- [Environment Variables](#environment-variables)
- [CI/CD Configuration](#cicd-configuration)
- [Deployment Guides](#deployment-guides)
  - [Backend Deployment (ECR)](#backend-deployment-ecr)
  - [Frontend Deployment](#frontend-deployment)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## Who This Project Is For

SkyFi IntelliCheck is an **internal enterprise verification platform** built for **SkyFi teams** to validate companies registering for enterprise access. It's designed for:

- **Compliance Officers**: Who need accurate verification and fraud prevention tools
- **IT Security Teams**: Who must identify high-risk companies and prevent fraudulent access
- **Business Analysts**: Who require trustworthy company profile data for decision-making

This is an internal SkyFi project, not intended for external use.

---

## What This Project Does

SkyFi IntelliCheck automates the verification and risk assessment of companies during enterprise registration. The system:

- **Automatically verifies** company information using multiple data sources (WHOIS, DNS, web scraping, AI reasoning)
- **Calculates risk scores** using a hybrid approach combining rule-based checks with OpenAI GPT-powered analysis
- **Provides a dashboard** for operators to review, approve, reject, or flag companies
- **Manages documents** uploaded as supporting evidence
- **Generates reports** in both PDF and JSON formats
- **Maintains audit trails** of all analyses and operator actions

### Key Features

- **Automated Verification Pipeline**: Multi-source data validation using WHOIS, DNS, web scraping, and AI reasoning
- **Hybrid Risk Scoring**: Combines rule-based checks with OpenAI GPT-powered analysis
- **Operator Dashboard**: Clean, professional UI for reviewing and managing company verifications
- **Document Management**: Upload and manage supporting documents per company
- **PDF & JSON Export**: Generate detailed verification reports
- **Audit Trail**: Complete history of all analyses and operator actions
- **Asynchronous Processing**: Background analysis pipeline using SQS → Lambda
- **Real-time Status Updates**: Polling endpoint for analysis progress

---

## Why This Was Built

SkyFi's self-service registration for Enterprise accounts was vulnerable to risks including:

- Account hijacking
- Company misrepresentation
- Registration of non-existent companies to bypass compliance checks

The previous manual review process was:
- **Slow**: Time-consuming for operators
- **Error-prone**: Dependent on operator expertise
- **Inconsistent**: Different operators might assess the same company differently

SkyFi IntelliCheck was built to:
- **Automate verification** using AI and public data sources
- **Increase accuracy** by 80% through consistent, automated checks
- **Reduce manual review time** by 70%
- **Improve compliance** to 95% with business standards
- **Provide reliable risk scoring** for informed decision-making

---

## How It Was Built

SkyFi IntelliCheck follows an **AWS-native, serverless architecture** designed for scalability and reliability:

### Architecture Overview

```
Frontend (Next.js)
      ↓
CloudFront + S3
      ↓
API Gateway / ALB
      ↓
FastAPI on ECS Fargate
      ↓
PostgreSQL (RDS)
      ↓
S3 (Document Storage)
      ↓
SQS Queue → Lambda Worker → External APIs (WHOIS, DNS, OpenAI)
```

### Key Design Decisions

1. **Asynchronous Processing**: Company analysis runs in the background via SQS → Lambda to meet the 2-hour SLA requirement
2. **Hybrid Risk Scoring**: Combines deterministic rule-based checks with AI reasoning for balanced accuracy
3. **Versioned Analysis Storage**: All analyses are stored with version numbers, allowing historical review
4. **Soft Delete**: Companies can be soft-deleted and restored, with hard delete after 90 days for compliance
5. **Infrastructure as Code**: All infrastructure defined in Terraform for reproducibility
6. **CI/CD Automation**: GitHub Actions workflows for automated deployments

---

## Technology Stack

### Backend
- **API Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL (AWS RDS)
- **Async Processing**: AWS Lambda + SQS
- **Storage**: AWS S3
- **Authentication**: AWS Cognito

### Frontend
- **Framework**: Next.js 16 (React 19)
- **Language**: TypeScript
- **Hosting**: CloudFront + S3
- **Design**: Black/White/Yellow brand palette

### Infrastructure
- **Cloud Provider**: AWS (us-east-1)
- **IaC**: Terraform
- **Compute**: ECS Fargate (API), Lambda (Workers)
- **Orchestration**: AWS Step Functions (optional)
- **Monitoring**: CloudWatch

### External Integrations
- OpenAI GPT (AI reasoning)
- WHOIS/DNS services
- HTTP scraping

---

## Project Structure

```
skyfi-intellicheck-app/
├── backend/          # FastAPI application, models, workers
│   ├── app/          # Application code (API, models, services)
│   ├── worker/       # Lambda worker for analysis pipeline
│   ├── scripts/      # Deployment and utility scripts
│   ├── tests/        # Test suite
│   ├── Dockerfile    # Container definition
│   └── requirements.txt
├── frontend/         # Next.js application
│   ├── src/
│   │   ├── app/      # Next.js app router pages
│   │   ├── components/ # React components
│   │   ├── lib/      # API clients and utilities
│   │   └── styles/   # Global styles and tokens
│   └── package.json
├── infra/           # Terraform infrastructure definitions
│   ├── *.tf         # Infrastructure modules
│   └── terraform.tfvars.example
├── docs/            # Project documentation
│   ├── SkyFi_IntelliCheck_PRD.md
│   ├── SkyFi_IntelliCheck_Architecture.md
│   ├── SkyFi_IntelliCheck_Design_Spec.md
│   └── SkyFi_IntelliCheck_TaskList.md
└── scripts/         # Root-level utility scripts
```

---

## Prerequisites

Before setting up the project locally, ensure you have:

- **AWS CLI** configured with appropriate credentials
- **Python 3.11+** installed
- **Node.js 18+** and npm installed
- **Docker** installed (for containerized backend)
- **Terraform >= 1.5.0** installed
- **Git** for version control

### AWS Account Setup

You'll need an AWS account with permissions to create:
- VPC, subnets, NAT gateways
- RDS PostgreSQL instances
- S3 buckets
- Lambda functions
- ECS clusters and services
- Cognito User Pools
- CloudFront distributions
- Secrets Manager secrets

---

## Local Development Setup

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the `backend/` directory:
   ```bash
   # Database
   DB_URL=postgresql://user:password@localhost:5432/intellicheck
   
   # Cognito (get from Terraform outputs after infrastructure deployment)
   COGNITO_REGION=us-east-1
   COGNITO_USER_POOL_ID=your-pool-id
   COGNITO_APP_CLIENT_ID=your-client-id
   COGNITO_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/your-pool-id
   
   # AWS Services
   AWS_REGION=us-east-1
   SQS_QUEUE_URL=your-queue-url
   S3_BUCKET_NAME=your-bucket-name
   
   # OpenAI (optional for local dev)
   OPENAI_API_KEY=your-openai-key
   
   # Application
   API_VERSION=1.0.0
   ENVIRONMENT=development
   ```

5. **Start the API server:**
   ```bash
   uvicorn main:app --reload
   ```

6. **Verify the API is running:**
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs
   - Version: http://localhost:8000/version

7. **Run tests:**
   ```bash
   pytest
   ```

#### Docker Workflow (Alternative)

```bash
# Build image
docker build -t skyfi-intellicheck-backend ./backend

# Run container
docker run -p 8000:8000 \
  -e DB_URL="postgresql://user:password@host:5432/dbname" \
  -e COGNITO_USER_POOL_ID="your-pool-id" \
  -e COGNITO_APP_CLIENT_ID="your-client-id" \
  skyfi-intellicheck-backend
```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure environment variables:**
   
   Create a `.env.local` file in the `frontend/` directory:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_COGNITO_USER_POOL_ID=your-pool-id
   NEXT_PUBLIC_COGNITO_CLIENT_ID=your-client-id
   NEXT_PUBLIC_COGNITO_REGION=us-east-1
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

5. **Access the application:**
   - Frontend: http://localhost:3000
   - Login page: http://localhost:3000/login

6. **Run linting:**
   ```bash
   npm run lint
   ```

7. **Build for production:**
   ```bash
   npm run build
   ```

### Infrastructure Setup

1. **Navigate to infrastructure directory:**
   ```bash
   cd infra
   ```

2. **Copy the example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. **Edit `terraform.tfvars` with your configuration:**
   ```hcl
   aws_region           = "us-east-1"
   environment          = "dev"
   vpc_name             = "skyfi-intellicheck-vpc"
   vpc_cidr             = "10.20.0.0/16"
   availability_zones   = ["us-east-1a", "us-east-1b", "us-east-1c"]
   # ... other variables
   ```

4. **Initialize Terraform:**
   ```bash
   terraform init
   ```

5. **Review planned changes:**
   ```bash
   terraform plan
   ```

6. **Apply infrastructure:**
   ```bash
   terraform apply
   ```

7. **View outputs (needed for local development):**
   ```bash
   terraform output
   ```

   Key outputs you'll need:
   - `cognito_user_pool_id`
   - `cognito_app_client_id`
   - `api_url`
   - `rds_endpoint`
   - `s3_bucket_name`
   - `sqs_queue_url`

8. **Destroy infrastructure (when done):**
   ```bash
   terraform destroy
   ```

---

## Cognito Development User Setup

To test authentication locally, you'll need to create a development user in Cognito.

### Prerequisites

- Terraform infrastructure deployed (Cognito resources created)
- AWS CLI configured with appropriate credentials

### Retrieve Cognito Configuration

```bash
cd infra
terraform output cognito_user_pool_id
terraform output cognito_app_client_id
terraform output cognito_issuer
```

### Create a Development User

#### Using AWS Console

1. Open **Amazon Cognito** in AWS Console (Region: `us-east-1`)
2. Select your User Pool (`skyfi-intellicheck-user-pool-{environment}`)
3. Click **Create user**
4. Enter email address and temporary password
5. User will be prompted to change password on first sign-in

#### Using AWS CLI

```bash
USER_POOL_ID="<cognito_user_pool_id from terraform output>"
EMAIL="dev@example.com"
TEMP_PASSWORD="YourTempPassword123!"

# Create user
aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$EMAIL" \
  --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
  --temporary-password "$TEMP_PASSWORD" \
  --region us-east-1

# Set permanent password (optional)
aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "$EMAIL" \
  --password "YourPermanentPassword123!" \
  --permanent \
  --region us-east-1
```

### Authenticate and Get Token

```bash
APP_CLIENT_ID="<cognito_app_client_id from terraform output>"
EMAIL="dev@example.com"
PASSWORD="YourPermanentPassword123!"

# Get authentication token
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$APP_CLIENT_ID" \
  --auth-parameters USERNAME="$EMAIL",PASSWORD="$PASSWORD" \
  --region us-east-1 \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

### Test API Authentication

```bash
# Set token from previous step
TOKEN="<paste token here>"

# Test public endpoint (should work without token)
curl http://localhost:8000/health

# Test protected endpoint without token (should fail with 401)
curl http://localhost:8000/v1/companies

# Test protected endpoint with token (should succeed)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/v1/companies
```

---

## Environment Variables

### Backend Environment Variables

| Variable | Description | Required | Source |
|----------|-------------|----------|--------|
| `DB_URL` | PostgreSQL connection string | Yes | Terraform output or local DB |
| `COGNITO_USER_POOL_ID` | Cognito User Pool ID | Yes | Terraform output |
| `COGNITO_APP_CLIENT_ID` | Cognito App Client ID | Yes | Terraform output |
| `COGNITO_REGION` | AWS region for Cognito | Yes | `us-east-1` |
| `COGNITO_ISSUER` | Cognito issuer URL | Optional | Derived from region + pool ID |
| `SQS_QUEUE_URL` | SQS queue URL for analysis jobs | Yes | Terraform output |
| `S3_BUCKET_NAME` | S3 bucket for documents | Yes | Terraform output |
| `OPENAI_API_KEY` | OpenAI API key for LLM analysis | Optional | Secrets Manager or env var |
| `AWS_REGION` | AWS region | Yes | `us-east-1` |
| `ENVIRONMENT` | Environment name | Yes | `development`, `dev`, or `prod` |

### Frontend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | Yes |
| `NEXT_PUBLIC_COGNITO_USER_POOL_ID` | Cognito User Pool ID | Yes |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | Cognito App Client ID | Yes |
| `NEXT_PUBLIC_COGNITO_REGION` | AWS region for Cognito | Yes |

**Note:** In production, sensitive values are managed via AWS Secrets Manager.

---

## CI/CD Configuration

The project uses GitHub Actions for automated deployments. Workflows are located in `.github/workflows/`.

### Workflows

- **`pr-checks.yml`**: Runs tests, linting, and build validation on pull requests
- **`backend-deploy.yml`**: Builds and deploys backend to ECS/ECR
- **`frontend-deploy.yml`**: Builds and deploys frontend to S3/CloudFront
- **`lambda-deploy.yml`**: Packages and deploys Lambda worker

### Branch Strategy

- **`main`**: Auto-deploys to **dev** environment
- **`production`**: Requires manual approval, deploys to **prod** environment

### Required GitHub Secrets

Configure these in your GitHub repository settings (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key for CI/CD IAM user |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for CI/CD IAM user |
| `API_URL_DEV` | Dev API URL (from `terraform output api_url`) |
| `API_URL_PROD` | Prod API URL |
| `COGNITO_POOL_ID_DEV` | Dev Cognito User Pool ID |
| `COGNITO_POOL_ID_PROD` | Prod Cognito User Pool ID |
| `COGNITO_CLIENT_ID_DEV` | Dev Cognito App Client ID |
| `COGNITO_CLIENT_ID_PROD` | Prod Cognito App Client ID |
| `COGNITO_REGION_DEV` | Cognito region (usually `us-east-1`) |
| `COGNITO_REGION_PROD` | Cognito region for prod |
| `CLOUDFRONT_DISTRIBUTION_ID_DEV` | Dev CloudFront distribution ID |
| `CLOUDFRONT_DISTRIBUTION_ID_PROD` | Prod CloudFront distribution ID |
| `FRONTEND_URL_PROD` | Prod frontend URL (for workflow metadata) |

### IAM Permissions for CI/CD

The CI/CD IAM user needs permissions for:
- ECR: `GetAuthorizationToken`, `BatchGetImage`, `PutImage`
- ECS: `UpdateService`, `DescribeServices`, `DescribeTaskDefinition`
- Lambda: `UpdateFunctionCode`, `GetFunction`
- S3: `PutObject`, `GetObject`, `ListBucket`
- CloudFront: `CreateInvalidation`
- CloudWatch: `PutLogEvents`

---

## Deployment Guides

### Backend Deployment (ECR)

#### Quick Start

```bash
cd backend
./scripts/build-and-push.sh dev v1.0.0
```

This script:
1. Fetches ECR repository URL from Terraform outputs
2. Authenticates Docker with ECR
3. Builds the Docker image
4. Tags with version and `latest`
5. Pushes to ECR

#### Manual Deployment

```bash
# 1. Get ECR repository URL
cd infra
ECR_REPO_URL=$(terraform output -raw ecr_repository_url)

# 2. Authenticate to ECR
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin "${ECR_REPO_URL}"

# 3. Build and tag image
cd ../backend
docker build -t skyfi-intellicheck-backend:v1.0.0 .
docker tag skyfi-intellicheck-backend:v1.0.0 "${ECR_REPO_URL}:v1.0.0"
docker tag skyfi-intellicheck-backend:v1.0.0 "${ECR_REPO_URL}:latest"

# 4. Push to ECR
docker push "${ECR_REPO_URL}:v1.0.0"
docker push "${ECR_REPO_URL}:latest"

# 5. Update ECS service (forces new deployment)
aws ecs update-service \
  --cluster skyfi-intellicheck-cluster-dev \
  --service skyfi-intellicheck-api-service-dev \
  --force-new-deployment \
  --region us-east-1
```

### Frontend Deployment

#### Prerequisites

- Terraform infrastructure deployed
- Backend API deployed and accessible
- Node.js 18+ installed

#### Deployment Steps

1. **Get Terraform outputs:**
   ```bash
   cd infra
   terraform output frontend_bucket_name
   terraform output cloudfront_distribution_id
   terraform output api_url
   terraform output cognito_user_pool_id
   terraform output cognito_app_client_id
   ```

2. **Build frontend:**
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

3. **Sync to S3:**
   ```bash
   aws s3 sync out/ s3://<bucket-name>/ --delete
   ```

4. **Invalidate CloudFront cache:**
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id <distribution-id> \
     --paths "/*"
   ```

#### Using Deployment Script

```bash
./scripts/deploy-frontend.sh dev
```

This script handles:
- Building with correct environment variables
- Syncing to S3 with proper cache headers
- CloudFront cache invalidation
- Health checks

---

## Documentation

This project follows a documentation-driven development approach. Core specifications are in the `/docs` folder:

- **[Product Requirements Document (PRD)](docs/SkyFi_IntelliCheck_PRD.md)**: Complete product specification, user stories, API schemas, and functional requirements
- **[Architecture Document](docs/SkyFi_IntelliCheck_Architecture.md)**: System design, component breakdown, data flows, and security architecture
- **[Design Specification](docs/SkyFi_IntelliCheck_Design_Spec.md)**: UI/UX layouts, color palette, component design, and visual wireframes
- **[Task List](docs/SkyFi_IntelliCheck_TaskList.md)**: Sequential PR-based development plan with acceptance criteria

### Development Workflow

Development follows a PR-based approach with 30+ sequential pull requests, each building on the previous. See the [Task List](docs/SkyFi_IntelliCheck_TaskList.md) for the complete development roadmap.

### Key Principles

1. AWS-native architecture
2. Asynchronous verification pipeline
3. Single-role operator system (MVP)
4. Versioned analysis storage
5. Soft delete with restoration capability

---

## Contributing

This is an internal SkyFi project. Development follows the PR workflow defined in the [Task List](docs/SkyFi_IntelliCheck_TaskList.md).

### Development Process

1. Review the Task List to understand the current phase
2. Create a feature branch from `main`
3. Implement changes following the architecture and design specs
4. Write tests for new functionality
5. Submit a pull request with clear description
6. Ensure all CI/CD checks pass
7. Get code review approval
8. Merge to `main` (auto-deploys to dev)

---

## License

Internal Use Only - SkyFi Technologies

---

**Current Phase**: PR #31 - CI/CD Pipeline Setup (Complete)
