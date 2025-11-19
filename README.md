# SkyFi IntelliCheck

**Version:** 1.0  
**Owner:** Yahav Corcos  
**Status:** Active Development  
**Deployment Region:** us-east-1  
**VPC:** skyfi-intellicheck-vpc

---

## Overview

SkyFi IntelliCheck is an internal enterprise verification and risk-assessment platform used by SkyFi teams to validate companies registering for enterprise access. The system automatically performs multi-source data verification, risk scoring, and report generation, while providing a polished operator dashboard to review, confirm, override, and archive verification results.

## Key Features

- **Automated Verification Pipeline**: Multi-source data validation using WHOIS, DNS, web scraping, and AI reasoning
- **Hybrid Risk Scoring**: Combines rule-based checks with OpenAI GPT-powered analysis
- **Operator Dashboard**: Clean, professional UI for reviewing and managing company verifications
- **Document Management**: Upload and manage supporting documents per company
- **PDF & JSON Export**: Generate detailed verification reports
- **Audit Trail**: Complete history of all analyses and operator actions

## Technology Stack

### Backend

- **API Framework**: FastAPI (Python)
- **Database**: PostgreSQL (AWS RDS)
- **Async Processing**: AWS Lambda + SQS
- **Storage**: AWS S3
- **Authentication**: AWS Cognito

### Frontend

- **Framework**: Next.js (React)
- **Hosting**: CloudFront + S3
- **Design**: Black/White/Yellow brand palette

### Infrastructure

- **Cloud Provider**: AWS (us-east-1)
- **IaC**: Terraform/CDK
- **Compute**: ECS Fargate (API), Lambda (Workers)
- **Orchestration**: AWS Step Functions (optional)
- **Monitoring**: CloudWatch

### External Integrations

- OpenAI GPT (AI reasoning)
- WHOIS/DNS services
- HTTP scraping

## Project Structure

```
skyfi-intellicheck-app/
├── backend/          # FastAPI application, models, workers
├── frontend/         # Next.js application
├── infra/           # Terraform/CDK infrastructure definitions
└── docs/            # Project documentation
```

## Documentation

This project follows a documentation-driven development approach. All core specifications are maintained in the `/docs` folder:

- **[Product Requirements Document (PRD)](docs/SkyFi_IntelliCheck_PRD.md)**: Complete product specification, user stories, API schemas, and functional requirements
- **[Architecture Document](docs/SkyFi_IntelliCheck_Architecture.md)**: System design, component breakdown, data flows, and security architecture
- **[Design Specification](docs/SkyFi_IntelliCheck_Design_Spec.md)**: UI/UX layouts, color palette, component design, and visual wireframes
- **[Task List](docs/SkyFi_IntelliCheck_TaskList.md)**: Sequential PR-based development plan with acceptance criteria
- **[Cognito Dev Setup](docs/cognito-dev-setup.md)**: Creating development users and fetching JWTs for local testing
- **[CI/CD Deployment Guide](docs/ci-cd-deployment-guide.md)**: Automated pipeline configuration, required secrets, and rollback procedures

## Development Workflow

Development follows a PR-based approach with 20+ sequential pull requests, each building on the previous. See [Task List](docs/SkyFi_IntelliCheck_TaskList.md) for the complete development roadmap.

### Key Principles

1. AWS-native architecture
2. Asynchronous verification pipeline
3. Single-role operator system (MVP)
4. Versioned analysis storage
5. Soft delete with restoration capability

## Getting Started

### Prerequisites

- AWS CLI configured
- Python 3.11+
- Node.js 18+
- Docker
- Terraform/CDK

### Backend (FastAPI)

```bash
# 1. Navigate to backend
cd backend

# 2. Create and activate virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# edit .env with your database connection string (DB_URL, etc.)
# provide Cognito configuration (COGNITO_USER_POOL_ID, COGNITO_APP_CLIENT_ID, COGNITO_REGION)
# you can retrieve values from `terraform output`

# 5. Start the API
uvicorn main:app --reload

# 6. Run tests
pytest

# API is available at:
#   http://localhost:8000/health
#   http://localhost:8000/version
#   http://localhost:8000/docs
```

#### Docker Workflow

```bash
# Build image
docker build -t skyfi-intellicheck-backend ./backend

# Run container
docker run -p 8000:8000 \
  -e DB_URL="postgresql://user:password@host:5432/dbname" \
  skyfi-intellicheck-backend
```

### Frontend (Next.js)

Coming in PR #16.

## Infrastructure Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5.0 installed
- Access to AWS account with permissions to create VPC resources

### Deploy Infrastructure

1. Navigate to the infrastructure directory:

   ```bash
   cd infra
   ```

2. Copy the example variables file:

   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

3. Edit `terraform.tfvars` with your specific configuration (if needed).

4. Initialize Terraform:

   ```bash
   terraform init
   ```

5. Review the planned changes:

   ```bash
   terraform plan
   ```

6. Apply the infrastructure:

   ```bash
   terraform apply
   ```

7. View outputs:
   ```bash
   terraform output
   ```

### Destroy Infrastructure

To tear down all resources:

```bash
cd infra
terraform destroy
```

### Infrastructure Outputs

After deployment, Terraform outputs the following values:

- `vpc_id`: VPC identifier
- `public_subnet_ids`: List of public subnet IDs
- `private_subnet_ids`: List of private subnet IDs
- `nat_gateway_ids`: NAT Gateway IDs
- Use these values in subsequent infrastructure PRs (RDS, ECS, etc.)

## Environment Variables

Core environment variables (managed via AWS Secrets Manager in production):

- `OPENAI_API_KEY`
- `DB_URL`
- `S3_BUCKET_NAME`
- `COGNITO_REGION`
- `COGNITO_USER_POOL_ID`
- `COGNITO_APP_CLIENT_ID`
- `COGNITO_ISSUER` (optional; derived from region + user pool if omitted)

## CI/CD

Automated GitHub Actions workflows manage deployments:

- `Pull Request Checks`: Runs backend tests, frontend lint/build, and Lambda packaging validation.
- `Backend Deployment`: Builds and deploys the FastAPI container to ECS + ECR (`main` → dev, `production` → prod with approval).
- `Frontend Deployment`: Builds the Next.js app and syncs assets to the appropriate S3 bucket and CloudFront distribution.
- `Lambda Deployment`: Packages and updates the analysis worker Lambda function.

See the [CI/CD Deployment Guide](docs/ci-cd-deployment-guide.md) for required secrets, IAM permissions, and rollback instructions.

## Deployment Environments

All infrastructure is deployed to **us-east-1** within the dedicated VPC **skyfi-intellicheck-vpc**.

- **dev**: Continuous deployments from `main` with verbose logging enabled.
- **prod**: Manual approvals required from the `production` branch with auto-scaling, backups, and restricted access.

## Contributing

This is an internal SkyFi project. Follow the PR workflow defined in the Task List.

## License

Internal Use Only - SkyFi Technologies

---

**Current Phase**: PR #2 - Core VPC Infrastructure
