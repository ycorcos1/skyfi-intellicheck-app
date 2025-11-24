# SkyFi IntelliCheck

**Version:** 1.0  
**Owner:** Yahav Corcos  
**Status:** Active Development  
**Deployment Region:** us-east-1

---

## Table of Contents

- [Project Overview](#project-overview)
  - [What This Project Is](#what-this-project-is)
  - [What This Project Does](#what-this-project-does)
  - [Why This Was Built](#why-this-was-built)
  - [What Problem It Solves](#what-problem-it-solves)
- [How It Was Built](#how-it-was-built)
  - [Architecture Overview](#architecture-overview)
  - [Key Design Decisions](#key-design-decisions)
  - [Technology Stack](#technology-stack)
- [Features](#features)
- [Setup Instructions](#setup-instructions)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [AWS Infrastructure Setup](#aws-infrastructure-setup)
  - [Cognito Development User Setup](#cognito-development-user-setup)
- [API Documentation](#api-documentation)
  - [Authentication](#authentication)
  - [Company Endpoints](#company-endpoints)
  - [Document Endpoints](#document-endpoints)
  - [Note Endpoints](#note-endpoints)
  - [Health Endpoints](#health-endpoints)
- [Database Schema](#database-schema)
  - [Tables Overview](#tables-overview)
  - [Table Details](#table-details)
  - [Relationships](#relationships)
- [Analysis Pipeline Details](#analysis-pipeline-details)
  - [Overview](#overview)
  - [Step-by-Step Process](#step-by-step-process)
  - [Risk Scoring Algorithm](#risk-scoring-algorithm)
  - [Signal Generation](#signal-generation)
  - [LLM Analysis](#llm-analysis)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Debugging Tips](#debugging-tips)
- [Security Considerations](#security-considerations)
  - [Authentication & Authorization](#authentication--authorization)
  - [Data Protection](#data-protection)
  - [Infrastructure Security](#infrastructure-security)
- [Performance and Scaling](#performance-and-scaling)
  - [Current Capacity](#current-capacity)
  - [Scaling Behavior](#scaling-behavior)
  - [Optimization Tips](#optimization-tips)
- [Known Limitations](#known-limitations)
- [Rate Limiting](#rate-limiting)
  - [API Rate Limits](#api-rate-limits)
  - [External Service Rate Limits](#external-service-rate-limits)
  - [Rate Limiter Implementation](#rate-limiter-implementation)
- [Error Handling](#error-handling)
  - [Error Response Format](#error-response-format)
  - [HTTP Status Codes](#http-status-codes)
  - [Retry Logic](#retry-logic)
  - [Error Recovery](#error-recovery)
- [Environment Variables](#environment-variables)
- [CI/CD Configuration](#cicd-configuration)
- [Deployment Guides](#deployment-guides)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## Project Overview

### What This Project Is

SkyFi IntelliCheck is an **internal enterprise verification platform** built for **SkyFi teams** to validate companies registering for enterprise access. It's an AWS-native, serverless application that automates company verification and risk assessment using multiple data sources and AI-powered analysis.

### What This Project Does

SkyFi IntelliCheck automates the verification and risk assessment of companies during enterprise registration. The system:

- **Automatically verifies** company information using multiple data sources (WHOIS, DNS, web scraping, AI reasoning)
- **Calculates risk scores** using a hybrid approach combining rule-based checks with OpenAI GPT-powered analysis
- **Provides a dashboard** for operators to review, approve, reject, or flag companies
- **Manages documents** uploaded as supporting evidence
- **Generates reports** in both PDF and JSON formats
- **Maintains audit trails** of all analyses and operator actions

### Why This Was Built

SkyFi's self-service registration for Enterprise accounts was vulnerable to risks including:

- **Account hijacking**: Fraudulent actors creating accounts with stolen credentials
- **Company misrepresentation**: Companies providing false information to bypass compliance
- **Non-existent companies**: Registration of fake companies to gain access

The previous manual review process was:

- **Slow**: Time-consuming for operators, creating bottlenecks
- **Error-prone**: Dependent on operator expertise and attention to detail
- **Inconsistent**: Different operators might assess the same company differently

### What Problem It Solves

SkyFi IntelliCheck was built to:

- **Automate verification** using AI and public data sources, reducing manual workload by 70%
- **Increase accuracy** by 80% through consistent, automated checks
- **Improve compliance** to 95% with business standards
- **Provide reliable risk scoring** for informed decision-making
- **Scale efficiently** to handle growing registration volumes
- **Maintain audit trails** for compliance and accountability

---

## How It Was Built

### Architecture Overview

SkyFi IntelliCheck follows an **AWS-native, serverless architecture** designed for scalability and reliability:

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
│              React 19 + TypeScript + Tailwind                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              CloudFront + S3 (Static Hosting)                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              API Gateway / Application Load Balancer         │
│                    (HTTPS, JWT Auth)                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         FastAPI on ECS Fargate (Containerized API)           │
│              Python 3.11 + SQLAlchemy + Pydantic            │
└───────────┬───────────────────────────────┬─────────────────┘
            │                               │
            ▼                               ▼
┌───────────────────────┐    ┌──────────────────────────────┐
│  PostgreSQL (RDS)     │    │   S3 (Document Storage)      │
│  - Companies          │    │   - Supporting documents    │
│  - Analyses           │    │   - PDF exports              │
│  - Documents metadata │    │   - Static assets            │
│  - Notes              │    └──────────────────────────────┘
└───────────┬───────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│              SQS Queue (Verification Jobs)                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         Lambda Worker (Analysis Pipeline)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  WHOIS   │  │   DNS    │  │    MX    │  │   Web    │   │
│  │  Lookup  │  │ Resolve  │  │ Validate │  │ Scrape  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Signal Generator + Rule Engine               │  │
│  └───────────────────────┬──────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────▼──────────────────────────────┐ │
│  │              OpenAI GPT-4 (LLM Analysis)               │ │
│  └───────────────────────┬──────────────────────────────┘ │
│                          │                                   │
│  ┌───────────────────────▼──────────────────────────────┐ │
│  │         Hybrid Risk Score Calculation                 │ │
│  └──────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  RDS (Write)  │
                    │  - Analysis   │
                    │  - Risk Score │
                    └───────────────┘
```

### Key Design Decisions

1. **Asynchronous Processing**: Company analysis runs in the background via SQS → Lambda to meet the 2-hour SLA requirement
2. **Hybrid Risk Scoring**: Combines deterministic rule-based checks with AI reasoning for balanced accuracy
3. **Versioned Analysis Storage**: All analyses are stored with version numbers, allowing historical review
4. **Soft Delete**: Companies can be soft-deleted and restored, with hard delete after 90 days for compliance
5. **Infrastructure as Code**: All infrastructure defined in Terraform for reproducibility
6. **CI/CD Automation**: GitHub Actions workflows for automated deployments
7. **Containerized API**: FastAPI runs on ECS Fargate for scalability and ease of deployment
8. **Serverless Workers**: Lambda functions for analysis pipeline, auto-scaling based on queue depth

### Technology Stack

#### Backend

- **API Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15+ (AWS RDS)
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **Async Processing**: AWS Lambda + SQS
- **Storage**: AWS S3
- **Authentication**: AWS Cognito (JWT)

#### Frontend

- **Framework**: Next.js 16 (React 19)
- **Language**: TypeScript
- **Styling**: CSS Modules + CSS Variables
- **Hosting**: CloudFront + S3
- **Design**: Black/White/Yellow brand palette

#### Infrastructure

- **Cloud Provider**: AWS (us-east-1)
- **IaC**: Terraform >= 1.5.0
- **Compute**: ECS Fargate (API), Lambda (Workers)
- **Orchestration**: AWS Step Functions (optional, for complex workflows)
- **Monitoring**: CloudWatch Logs, Metrics, Alarms
- **Networking**: VPC, ALB, NAT Gateway, Security Groups

#### External Integrations

- **OpenAI GPT-4**: AI reasoning and risk assessment
- **WHOIS Services**: Domain registration data
- **DNS Services**: Domain resolution and record validation
- **HTTP Scraping**: Website content analysis

---

## Features

### Core Features

- **Automated Company Verification**

  - Multi-source data validation (WHOIS, DNS, MX, Web scraping)
  - Real-time analysis status tracking
  - Background processing via SQS/Lambda

- **Hybrid Risk Scoring**

  - Rule-based scoring from verification signals
  - AI-powered analysis using OpenAI GPT-4
  - Final score combines both approaches (0-100 scale)

- **Operator Dashboard**

  - Company listing with filtering and search
  - Real-time analysis progress tracking
  - Status management (approve, reject, flag, revoke)
  - Bulk upload for testing/demo purposes

- **Document Management**

  - Secure document upload via presigned S3 URLs
  - Document metadata tracking
  - Download with presigned URLs
  - Document deletion

- **Internal Notes**

  - Operator notes per company
  - Note creation, editing, and deletion
  - User tracking for audit purposes

- **Export Capabilities**

  - PDF report generation (on-demand)
  - JSON export with full analysis data
  - Preview before export

- **Analysis History**

  - Versioned analysis storage
  - View all analysis versions per company
  - Compare analysis results over time

- **Reanalysis**

  - Full reanalysis (all checks)
  - Selective retry (failed checks only)
  - Automatic versioning

- **Soft Delete & Restoration**
  - Soft delete with `is_deleted` flag
  - Restore deleted companies
  - Hard delete after 90 days (compliance)

### Advanced Features

- **Real-time Status Polling**: Frontend polls analysis status every 5 seconds
- **Auto-approval**: Companies with low risk scores (≤30) can be auto-approved
- **Bulk Operations**: Bulk upload JSON for testing/demo
- **Audit Trail**: Complete history of all operator actions
- **Correlation IDs**: Request tracking across services
- **Structured Logging**: JSON-formatted logs for CloudWatch

---

## Setup Instructions

### Prerequisites

Before setting up the project locally, ensure you have:

- **AWS CLI** configured with appropriate credentials
- **Python 3.11+** installed
- **Node.js 18+** and npm installed
- **Docker** installed (for containerized backend)
- **Terraform >= 1.5.0** installed
- **Git** for version control

#### AWS Account Setup

You'll need an AWS account with permissions to create:

- VPC, subnets, NAT gateways
- RDS PostgreSQL instances
- S3 buckets
- Lambda functions
- ECS clusters and services
- Cognito User Pools
- CloudFront distributions
- Secrets Manager secrets
- IAM roles and policies

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

### AWS Infrastructure Setup

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

### Cognito Development User Setup

To test authentication locally, you'll need to create a development user in Cognito.

#### Prerequisites

- Terraform infrastructure deployed (Cognito resources created)
- AWS CLI configured with appropriate credentials

#### Retrieve Cognito Configuration

```bash
cd infra
terraform output cognito_user_pool_id
terraform output cognito_app_client_id
terraform output cognito_issuer
```

#### Create a Development User

**Using AWS Console:**

1. Open **Amazon Cognito** in AWS Console (Region: `us-east-1`)
2. Select your User Pool (`skyfi-intellicheck-user-pool-{environment}`)
3. Click **Create user**
4. Enter email address and temporary password
5. User will be prompted to change password on first sign-in

**Using AWS CLI:**

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

#### Authenticate and Get Token

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

#### Test API Authentication

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

## API Documentation

### Authentication

All protected endpoints require a valid JWT token from AWS Cognito in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

The API validates:

- Token signature (RS256)
- Token expiration
- Token issuer (Cognito User Pool)
- Token audience (App Client ID)

### Company Endpoints

#### Create Company

**POST** `/v1/companies`

Creates a new company and automatically enqueues it for analysis.

**Request Body:**

```json
{
  "name": "Example Corp",
  "domain": "example.com",
  "website_url": "https://example.com",
  "email": "contact@example.com",
  "phone": "+1-555-123-4567"
}
```

**Response:** `201 Created`

```json
{
  "company": {
    "id": "uuid",
    "name": "Example Corp",
    "domain": "example.com",
    "status": "pending",
    "risk_score": 0,
    "analysis_status": "pending",
    "created_at": "2025-01-15T10:00:00Z"
  },
  "correlation_id": "correlation-uuid"
}
```

#### List Companies

**GET** `/v1/companies`

List companies with filtering, search, and pagination.

**Query Parameters:**

- `page` (int, default: 1): Page number (1-indexed)
- `limit` (int, default: 20, max: 100): Items per page
- `search` (string, optional): Case-insensitive search by company name
- `status` (string, optional): Filter by status (`pending`, `approved`, `suspicious`, `fraudulent`)
- `risk_min` (int, optional): Minimum risk score (0-100)
- `risk_max` (int, optional): Maximum risk score (0-100)
- `include_deleted` (bool, default: false): Include soft-deleted companies

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Example Corp",
      "domain": "example.com",
      "status": "approved",
      "risk_score": 25,
      "analysis_status": "complete",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 20,
  "pages": 5
}
```

#### Get Company Detail

**GET** `/v1/companies/{company_id}`

Retrieve a single company with latest analysis.

**Response:** `200 OK`

```json
{
  "id": "uuid",
  "name": "Example Corp",
  "domain": "example.com",
  "status": "approved",
  "risk_score": 25,
  "analysis_status": "complete",
  "latest_analysis": {
    "id": "uuid",
    "version": 1,
    "risk_score": 25,
    "is_complete": true,
    "failed_checks": [],
    "llm_summary": "Company appears legitimate...",
    "created_at": "2025-01-15T10:05:00Z"
  },
  "created_at": "2025-01-15T10:00:00Z"
}
```

#### Update Company

**PATCH** `/v1/companies/{company_id}`

Update company details (only allowed before first analysis).

**Request Body:**

```json
{
  "name": "Updated Name",
  "website_url": "https://newurl.com",
  "email": "newemail@example.com",
  "phone": "+1-555-999-9999"
}
```

**Response:** `200 OK` (Company object)

#### Delete Company

**DELETE** `/v1/companies/{company_id}`

Permanently delete a company (hard delete). Use soft delete via status update for reversible deletion.

**Response:** `204 No Content`

#### Restore Company

**POST** `/v1/companies/{company_id}/restore`

Restore a soft-deleted company.

**Response:** `200 OK` (Company object)

#### Reanalyze Company

**POST** `/v1/companies/{company_id}/reanalyze`

Trigger a new analysis for a company.

**Request Body:**

```json
{
  "retry_failed_only": false
}
```

**Response:** `200 OK`

```json
{
  "message": "Reanalysis queued",
  "correlation_id": "correlation-uuid"
}
```

#### Update Company Status

**PATCH** `/v1/companies/{company_id}/status`

Update company status via state machine action.

**Request Body:**

```json
{
  "action": "mark_review_complete"
}
```

**Valid Actions:**

- `mark_review_complete`: `pending`/`suspicious` → `approved`
- `approve`: `pending`/`suspicious` → `approved`
- `mark_suspicious`: `pending`/`approved` → `suspicious`
- `revoke_approval`: `approved` → `suspicious`

> Note: Status `fraudulent` is assigned automatically by the analysis worker when a completed analysis produces a risk score of 70 or higher.

**Response:** `200 OK`

```json
{
  "company": {
    /* Company object */
  },
  "previous_status": "pending",
  "new_status": "approved"
}
```

#### Revoke Approval

**POST** `/v1/companies/{company_id}/revoke-approval`

Shortcut endpoint to revoke company approval.

**Response:** `200 OK` (StatusUpdateResponse)

#### Get Analysis Status

**GET** `/v1/companies/{company_id}/analysis/status`

Get real-time analysis status for polling.

**Response:** `200 OK`

```json
{
  "analysis_status": "in_progress",
  "progress_percentage": 60,
  "current_step": "website_scrape",
  "failed_checks": [],
  "last_updated": "2025-01-15T10:07:30Z"
}
```

#### List Analysis History

**GET** `/v1/companies/{company_id}/analyses`

Get all analysis versions for a company.

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "version": 2,
    "risk_score": 30,
    "is_complete": true,
    "created_at": "2025-01-16T10:00:00Z"
  },
  {
    "id": "uuid",
    "version": 1,
    "risk_score": 25,
    "is_complete": true,
    "created_at": "2025-01-15T10:05:00Z"
  }
]
```

#### Export JSON

**GET** `/v1/companies/{company_id}/export/json`

Export company verification report as JSON.

**Response:** `200 OK`

```json
{
  "company": {
    /* Company data */
  },
  "latest_analysis": {
    /* Analysis data */
  },
  "exported_at": "2025-01-15T10:00:00Z"
}
```

#### Export PDF

**GET** `/v1/companies/{company_id}/export/pdf`

Export company verification report as PDF.

**Response:** `200 OK` (application/pdf binary)

**Headers:**

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="company-report.pdf"
```

#### Bulk Upload

**POST** `/v1/companies/bulk-upload`

Bulk upload companies from JSON array (for testing/demo).

**Request Body:**

```json
[
  {
    "name": "Company 1",
    "domain": "company1.com",
    "email": "contact@company1.com",
    "status": "approved",
    "risk_score": 25
  },
  {
    "name": "Company 2",
    "domain": "company2.com",
    "email": "contact@company2.com",
    "status": "rejected",
    "risk_score": 75
  }
]
```

**Response:** `201 Created`

```json
{
  "created": [{ "id": "uuid", "name": "Company 1", "domain": "company1.com" }],
  "errors": [{ "index": 1, "error": "Domain already exists" }],
  "total_processed": 2,
  "success_count": 1,
  "error_count": 1
}
```

### Document Endpoints

#### Generate Upload URL

**POST** `/v1/companies/{company_id}/documents/upload-url`

Generate a presigned S3 URL for document upload.

**Request Body:**

```json
{
  "filename": "business-license.pdf",
  "mime_type": "application/pdf",
  "file_size": 1024000
}
```

**Response:** `200 OK`

```json
{
  "upload_url": "https://s3.amazonaws.com/bucket/path?signature=...",
  "s3_key": "companies/{company_id}/documents/{document_id}/business-license.pdf",
  "expires_in": 3600
}
```

#### Save Document Metadata

**POST** `/v1/companies/{company_id}/documents`

Save document metadata after upload.

**Request Body:**

```json
{
  "s3_key": "companies/{company_id}/documents/{document_id}/business-license.pdf",
  "filename": "business-license.pdf",
  "mime_type": "application/pdf",
  "file_size": 1024000,
  "document_type": "business_license",
  "description": "State business license"
}
```

**Response:** `201 Created` (Document object)

#### List Documents

**GET** `/v1/companies/{company_id}/documents`

List all documents for a company.

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "uuid",
      "filename": "business-license.pdf",
      "file_size": 1024000,
      "mime_type": "application/pdf",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### Generate Download URL

**GET** `/v1/companies/{company_id}/documents/{document_id}/download-url`

Generate a presigned S3 URL for document download.

**Response:** `200 OK`

```json
{
  "download_url": "https://s3.amazonaws.com/bucket/path?signature=...",
  "expires_in": 900
}
```

#### Delete Document

**DELETE** `/v1/companies/{company_id}/documents/{document_id}`

Delete a document (removes from S3 and database).

**Response:** `204 No Content`

### Note Endpoints

#### Create Note

**POST** `/v1/companies/{company_id}/notes`

Create an internal note for a company.

**Request Body:**

```json
{
  "content": "Follow up with company regarding additional documentation."
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "content": "Follow up with company regarding additional documentation.",
  "user_id": "cognito-user-id",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

#### List Notes

**GET** `/v1/companies/{company_id}/notes`

List all notes for a company.

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "uuid",
      "content": "Note content",
      "user_id": "cognito-user-id",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### Update Note

**PATCH** `/v1/companies/{company_id}/notes/{note_id}`

Update an existing note.

**Request Body:**

```json
{
  "content": "Updated note content"
}
```

**Response:** `200 OK` (Note object)

#### Delete Note

**DELETE** `/v1/companies/{company_id}/notes/{note_id}`

Delete a note.

**Response:** `204 No Content`

### Health Endpoints

#### Health Check

**GET** `/health`

Health check endpoint that validates application and database connectivity.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-01-15T10:00:00Z"
}
```

#### Version Info

**GET** `/version`

Return API version and optional build metadata.

**Response:** `200 OK`

```json
{
  "version": "1.0.0",
  "environment": "development",
  "git_sha": "abc123",
  "build_timestamp": "2025-01-15T10:00:00Z"
}
```

---

## Database Schema

### Tables Overview

The database consists of four main tables:

1. **`companies`**: Core company information and status
2. **`company_analyses`**: Versioned analysis results
3. **`documents`**: Document metadata (files stored in S3)
4. **`notes`**: Internal operator notes

### Table Details

#### `companies` Table

| Column             | Type         | Constraints       | Description                                                                     |
| ------------------ | ------------ | ----------------- | ------------------------------------------------------------------------------- |
| `id`               | UUID         | PRIMARY KEY       | Unique company identifier                                                       |
| `name`             | VARCHAR(255) | NOT NULL          | Company name                                                                    |
| `domain`           | VARCHAR(255) | NOT NULL, INDEXED | Company domain                                                                  |
| `website_url`      | VARCHAR(500) | NULLABLE          | Company website URL                                                             |
| `email`            | VARCHAR(255) | NULLABLE          | Contact email                                                                   |
| `phone`            | VARCHAR(50)  | NULLABLE          | Contact phone                                                                   |
| `status`           | ENUM         | NOT NULL, INDEXED | Company status (`pending`, `approved`, `suspicious`, `fraudulent`)             |
| `risk_score`       | INTEGER      | NOT NULL, INDEXED | Current risk score (0-100)                                                      |
| `analysis_status`  | ENUM         | NOT NULL, INDEXED | Analysis status (`pending`, `in_progress`, `complete`)                          |
| `current_step`     | VARCHAR(50)  | NULLABLE          | Current analysis step                                                           |
| `last_analyzed_at` | TIMESTAMP    | NULLABLE          | Last analysis timestamp                                                         |
| `is_deleted`       | BOOLEAN      | NOT NULL, INDEXED | Soft delete flag                                                                |
| `created_at`       | TIMESTAMP    | NOT NULL, INDEXED | Creation timestamp                                                              |
| `updated_at`       | TIMESTAMP    | NOT NULL          | Last update timestamp                                                           |

**Indexes:**

- Primary key on `id`
- Index on `domain`
- Index on `status`
- Index on `risk_score`
- Index on `analysis_status`
- Index on `is_deleted`
- Index on `created_at`

#### `company_analyses` Table

| Column              | Type          | Constraints          | Description                                       |
| ------------------- | ------------- | -------------------- | ------------------------------------------------- |
| `id`                | UUID          | PRIMARY KEY          | Unique analysis identifier                        |
| `company_id`        | UUID          | FOREIGN KEY, INDEXED | Reference to `companies.id`                       |
| `version`           | INTEGER       | NOT NULL             | Analysis version number (incremental per company) |
| `algorithm_version` | VARCHAR(50)   | NOT NULL             | Algorithm version used                            |
| `submitted_data`    | JSONB         | NOT NULL             | Original company data submitted                   |
| `discovered_data`   | JSONB         | NOT NULL             | Data discovered from external checks              |
| `signals`           | JSONB         | NOT NULL             | Array of verification signals                     |
| `risk_score`        | INTEGER       | NOT NULL             | Calculated risk score (0-100)                     |
| `llm_summary`       | VARCHAR(2000) | NULLABLE             | LLM-generated summary                             |
| `llm_details`       | VARCHAR(5000) | NULLABLE             | LLM-generated detailed analysis                   |
| `is_complete`       | BOOLEAN       | NOT NULL             | Whether analysis completed successfully           |
| `failed_checks`     | JSONB         | NOT NULL             | Array of failed check names                       |
| `created_at`        | TIMESTAMP     | NOT NULL, INDEXED    | Analysis timestamp                                |

**Indexes:**

- Primary key on `id`
- Foreign key index on `company_id`
- Index on `created_at`

**Unique Constraint:**

- (`company_id`, `version`) - Ensures unique version numbers per company

#### `documents` Table

| Column          | Type         | Constraints          | Description                              |
| --------------- | ------------ | -------------------- | ---------------------------------------- |
| `id`            | UUID         | PRIMARY KEY          | Unique document identifier               |
| `company_id`    | UUID         | FOREIGN KEY, INDEXED | Reference to `companies.id`              |
| `filename`      | VARCHAR(255) | NOT NULL             | Original filename                        |
| `s3_key`        | VARCHAR(500) | NOT NULL, UNIQUE     | S3 object key                            |
| `file_size`     | INTEGER      | NOT NULL             | File size in bytes                       |
| `mime_type`     | VARCHAR(100) | NOT NULL             | MIME type                                |
| `uploaded_by`   | VARCHAR(255) | NOT NULL             | Cognito user ID                          |
| `document_type` | VARCHAR(100) | NULLABLE             | Document type (e.g., `business_license`) |
| `description`   | VARCHAR(500) | NULLABLE             | Document description                     |
| `created_at`    | TIMESTAMP    | NOT NULL, INDEXED    | Upload timestamp                         |

**Indexes:**

- Primary key on `id`
- Foreign key index on `company_id`
- Unique index on `s3_key`
- Index on `created_at`

#### `notes` Table

| Column       | Type         | Constraints          | Description                      |
| ------------ | ------------ | -------------------- | -------------------------------- |
| `id`         | UUID         | PRIMARY KEY          | Unique note identifier           |
| `company_id` | UUID         | FOREIGN KEY, INDEXED | Reference to `companies.id`      |
| `user_id`    | VARCHAR(255) | NOT NULL             | Cognito user ID who created note |
| `content`    | TEXT         | NOT NULL             | Note content                     |
| `created_at` | TIMESTAMP    | NOT NULL, INDEXED    | Creation timestamp               |
| `updated_at` | TIMESTAMP    | NOT NULL             | Last update timestamp            |

**Indexes:**

- Primary key on `id`
- Foreign key index on `company_id`
- Index on `created_at`

### Relationships

```
companies (1) ──< (many) company_analyses
companies (1) ──< (many) documents
companies (1) ──< (many) notes
```

- **One-to-Many**: Each company can have multiple analyses (versioned)
- **One-to-Many**: Each company can have multiple documents
- **One-to-Many**: Each company can have multiple notes
- **Cascade Delete**: Deleting a company (hard delete) cascades to analyses, documents, and notes

---

## Analysis Pipeline Details

### Overview

The analysis pipeline is an asynchronous, multi-step verification process that:

1. Collects data from multiple external sources
2. Generates verification signals by comparing submitted vs discovered data
3. Calculates a rule-based risk score
4. Uses AI (OpenAI GPT-4) to provide qualitative analysis and score adjustment
5. Computes a final hybrid risk score (0-100)

The entire process runs in a Lambda worker triggered by SQS messages, ensuring it doesn't block API requests and can scale independently.

### Step-by-Step Process

#### 1. Company Creation & Enqueueing

When a company is created via `POST /v1/companies`:

1. Company record is inserted into `companies` table with:

   - `status = "pending"`
   - `analysis_status = "pending"`
   - `risk_score = 0`

2. A message is enqueued to SQS with:

   ```json
   {
     "company_id": "uuid",
     "retry_mode": "full",
     "correlation_id": "uuid"
   }
   ```

3. API returns immediately with `correlation_id` for tracking

#### 2. Lambda Worker Trigger

SQS triggers the Lambda worker, which:

1. Fetches the company record from database
2. Updates `analysis_status = "in_progress"` and `current_step = "whois"`
3. Begins executing verification checks sequentially

#### 3. WHOIS Lookup

**Purpose**: Verify domain registration information

**Process:**

- Queries WHOIS service for domain registration data
- Extracts: domain age, registrar, creation date, privacy status
- Rate limited: 1 request/second

**Output:**

```json
{
  "domain_age_days": 365,
  "registrar": "Example Registrar",
  "privacy_enabled": false,
  "creation_date": "2024-01-15T00:00:00Z"
}
```

**Updates**: `current_step = "dns"`

#### 4. DNS Resolution

**Purpose**: Verify domain resolves and get IP addresses

**Process:**

- Resolves domain to IP addresses (A records)
- Retrieves nameservers
- Rate limited: 5 requests/second

**Output:**

```json
{
  "resolves": true,
  "nameservers": ["ns1.example.com", "ns2.example.com"],
  "a_records": ["192.0.2.1", "192.0.2.2"]
}
```

**Updates**: `current_step = "mx_validation"`

#### 5. MX Validation

**Purpose**: Verify email domain has mail exchange records

**Process:**

- Extracts email domain from company email (or uses company domain)
- Queries MX records for email domain
- Rate limited: No specific limit (DNS-based)

**Output:**

```json
{
  "has_mx_records": true,
  "mx_records": [{ "priority": 10, "exchange": "mail.example.com" }],
  "email_configured": true
}
```

**Updates**: `current_step = "website_scrape"`

#### 6. Website Scraping

**Purpose**: Verify website is reachable and extract metadata

**Process:**

- Fetches company website URL via HTTP
- Extracts: HTTP status code, page title, meta description, content length
- Rate limited: 10 requests/second
- Timeout: 30 seconds

**Output:**

```json
{
  "reachable": true,
  "status_code": 200,
  "title": "Example Corp - Home",
  "description": "Leading provider of...",
  "content_length": 50000
}
```

**Updates**: `current_step = "phone"` (then `"llm_processing"`)

#### 7. Phone Normalization

**Purpose**: Validate and normalize phone number format

**Process:**

- Parses phone number format
- Validates against international formats
- Extracts region/country code

**Output:**

```json
{
  "normalized": "+15551234567",
  "valid": true,
  "region": "US"
}
```

**Updates**: `current_step = "llm_processing"`

#### 8. Signal Generation

**Purpose**: Generate verification signals by comparing submitted vs discovered data

**Process:**

- Compares each data point (domain age, email match, website reachability, etc.)
- Generates signals with status (`ok`, `suspicious`, `mismatch`, `warning`, `failed`)
- Assigns weights to signals based on severity

**Example Signals:**

```json
[
  {
    "field": "domain_age",
    "status": "suspicious",
    "value": "180 days",
    "weight": 20,
    "severity": "high"
  },
  {
    "field": "email_match",
    "status": "ok",
    "value": "Domain matches",
    "weight": 0,
    "severity": "low"
  },
  {
    "field": "website_lookup",
    "status": "suspicious",
    "value": "Unreachable (HTTP 404)",
    "weight": 25,
    "severity": "high"
  }
]
```

#### 9. Rule-Based Scoring

**Purpose**: Calculate initial risk score from signals

**Process:**

- Sums weights of all signals with `status != "ok"` and `weight > 0`
- Clamps result between 0 and 100

**Rule Weights:**

- `domain_age_lt_1_year`: 20 points
- `whois_privacy_enabled`: 10 points
- `address_mismatch`: 15 points
- `email_mismatch`: 10 points
- `phone_region_mismatch`: 10 points
- `website_unreachable`: 25 points
- `no_mx_records`: 15 points

**Example:**

- Domain age < 1 year: +20
- Website unreachable: +25
- **Rule Score: 45**

#### 10. LLM Analysis

**Purpose**: Provide qualitative analysis and score adjustment

**Process:**

1. Builds structured prompt with:

   - Submitted data
   - Discovered data
   - Generated signals
   - Current rule score

2. Calls OpenAI GPT-4 API with:

   - Model: `gpt-4`
   - Temperature: 0.3 (for consistency)
   - Max tokens: 1000
   - Response format: JSON

3. Rate limited: 3 requests/second with exponential backoff

4. Parses JSON response:

   ```json
   {
     "llm_summary": "Company appears legitimate with minor concerns...",
     "llm_details": "The domain is relatively new but shows active website...",
     "llm_score_adjustment": -5
   }
   ```

5. Validates and clamps `llm_score_adjustment` between -20 and +20

**Updates**: `current_step = "complete"`

#### 11. Hybrid Score Calculation

**Purpose**: Combine rule-based score with LLM adjustment

**Formula:**

```
final_score = clamp(rule_score + llm_score_adjustment, 0, 100)
```

**Example:**

- Rule Score: 45
- LLM Adjustment: -5
- **Final Score: 40**

#### 12. Save Analysis

**Process:**

1. Determines next version number (increments from latest analysis)
2. Inserts new record into `company_analyses` table with:

   - All discovered data
   - All signals
   - Final risk score
   - LLM summary and details
   - Failed checks list (if any)

3. Updates `companies` table:
   - `risk_score = final_score`
   - `analysis_status = "complete"`
   - `last_analyzed_at = now()`
   - `current_step = "complete"`
   - `status` auto-updates based on outcome:
     - `fraudulent` if `risk_score >= 70`
     - `suspicious` if analysis is incomplete or `risk_score` in 31-69
     - `approved` if analysis is complete and `risk_score <= 30`

#### 13. Error Handling

If any check fails:

- Error is logged with correlation ID
- Check is marked as failed in `failed_checks` array
- Analysis continues with other checks
- If critical checks fail, `is_complete = false` and the company status is set to `suspicious` (analysis status remains `complete`)

### Risk Scoring Algorithm

The risk score is calculated using a **hybrid approach**:

1. **Rule-Based Score** (0-100):

   - Sum of signal weights
   - Deterministic, reproducible
   - Fast calculation

2. **LLM Adjustment** (-20 to +20):

   - Qualitative analysis from GPT-4
   - Considers context and patterns
   - Can adjust score up or down

3. **Final Score** (0-100):
   - `final_score = clamp(rule_score + llm_adjustment, 0, 100)`
   - Combines both approaches

**Risk Levels:**

- **0-30**: Low Risk (Green) - Auto-approval eligible
- **31-69**: Moderate Risk (Yellow) - Requires review
- **70-100**: High Risk (Red) - Requires investigation

### Signal Generation

Signals are generated by comparing submitted data with discovered data:

**Signal Statuses:**

- `ok`: No issues detected
- `suspicious`: Potential concern
- `mismatch`: Data doesn't match
- `warning`: Minor issue
- `failed`: Check failed

**Signal Severities:**

- `low`: Informational
- `medium`: Moderate concern
- `high`: Significant concern

**Signal Fields:**

- `domain_age`: Domain registration age
- `whois_privacy`: WHOIS privacy protection
- `dns_resolution`: DNS resolution status
- `website_lookup`: Website reachability
- `email_match`: Email domain match
- `mx_records`: MX record configuration
- `phone_validation`: Phone number validity

### LLM Analysis

The LLM analysis provides:

1. **Summary** (2-3 sentences):

   - Executive summary of risk assessment
   - Key concerns or positive indicators

2. **Details** (paragraph):

   - Detailed reasoning
   - Notable patterns
   - Contextual factors

3. **Score Adjustment** (-20 to +20):
   - Negative: Lower risk indicators
   - Positive: Higher risk indicators
   - Zero: No adjustment needed

---

## Troubleshooting

### Common Issues

#### Backend API Not Starting

**Symptoms:**

- `uvicorn` fails to start
- Database connection errors
- Port already in use

**Solutions:**

1. Check database connection string in `.env`
2. Verify PostgreSQL is running: `pg_isready`
3. Check port 8000 is available: `lsof -i :8000`
4. Verify all environment variables are set

#### Authentication Failures

**Symptoms:**

- 401 Unauthorized errors
- Token validation failures
- Cognito errors

**Solutions:**

1. Verify Cognito configuration in `.env`:

   - `COGNITO_USER_POOL_ID`
   - `COGNITO_APP_CLIENT_ID`
   - `COGNITO_ISSUER`

2. Check token is not expired:

   ```bash
   # Decode JWT (without verification)
   echo $TOKEN | cut -d. -f2 | base64 -d | jq
   ```

3. Verify user exists in Cognito:
   ```bash
   aws cognito-idp list-users --user-pool-id $POOL_ID
   ```

#### Analysis Not Running

**Symptoms:**

- Companies stuck in `pending` status
- No Lambda invocations
- SQS messages not processing

**Solutions:**

1. Check SQS queue URL in `.env`
2. Verify Lambda function is deployed and has correct IAM permissions
3. Check CloudWatch logs for Lambda errors
4. Verify SQS queue has messages:
   ```bash
   aws sqs get-queue-attributes --queue-url $QUEUE_URL --attribute-names ApproximateNumberOfMessages
   ```

#### Database Connection Issues

**Symptoms:**

- Connection timeout errors
- "Connection refused" errors
- RDS endpoint not reachable

**Solutions:**

1. Verify RDS endpoint is correct
2. Check security group allows connections from your IP
3. Verify database credentials in Secrets Manager
4. Test connection:
   ```bash
   psql -h $RDS_ENDPOINT -U $DB_USER -d $DB_NAME
   ```

#### Frontend Build Failures

**Symptoms:**

- TypeScript errors
- Build timeouts
- Missing environment variables

**Solutions:**

1. Check all `NEXT_PUBLIC_*` variables are set in `.env.local`
2. Clear Next.js cache: `rm -rf .next`
3. Verify Node.js version: `node --version` (should be 18+)
4. Reinstall dependencies: `rm -rf node_modules && npm install`

### Debugging Tips

#### Enable Debug Logging

**Backend:**

```python
# In backend/.env
LOG_LEVEL=DEBUG
```

**Frontend:**

```typescript
// In browser console
localStorage.setItem("debug", "true");
```

#### Check CloudWatch Logs

```bash
# API logs
aws logs tail /aws/ecs/skyfi-intellicheck-api-dev --follow

# Lambda logs
aws logs tail /aws/lambda/skyfi-intellicheck-worker-dev --follow
```

#### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# With authentication
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/v1/companies
```

#### Verify Infrastructure

```bash
cd infra
terraform output  # View all outputs
terraform state list  # List all resources
```

---

## Security Considerations

### Authentication & Authorization

#### JWT Token Validation

- **Algorithm**: RS256 (RSA with SHA-256)
- **Issuer Validation**: Must match Cognito User Pool
- **Audience Validation**: Must match App Client ID
- **Expiration Check**: Tokens expire after 1 hour (configurable in Cognito)
- **Signature Verification**: Uses JWKS from Cognito

#### Token Structure

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/pool-id",
  "aud": "app-client-id",
  "exp": 1234567890,
  "iat": 1234564290
}
```

#### API Security

- **HTTPS Only**: All API traffic encrypted in transit
- **CORS**: Configured for frontend domain only
- **Rate Limiting**: Applied at ALB level (future enhancement)
- **Input Validation**: All inputs validated via Pydantic schemas
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

### Data Protection

#### Encryption at Rest

- **RDS**: Encrypted with AWS KMS (default encryption)
- **S3**: Server-side encryption (SSE-S3 or SSE-KMS)
- **Secrets Manager**: Encrypted with AWS KMS

#### Encryption in Transit

- **API**: TLS 1.2+ via ALB/CloudFront
- **Database**: SSL/TLS connections required
- **S3**: HTTPS for all operations

#### Data Access Control

- **Database**: IAM authentication for Lambda, password for API
- **S3**: IAM roles with least privilege
- **Presigned URLs**: Time-limited (1 hour upload, 15 min download)

#### PII Handling

- **Email**: Stored in database, used for verification only
- **Phone**: Stored in database, normalized format
- **Documents**: Stored in private S3 bucket, access via presigned URLs
- **Notes**: Internal only, not exposed externally

### Infrastructure Security

#### Network Security

- **VPC**: Isolated network with private subnets
- **Security Groups**: Restrictive rules, allow only necessary traffic
- **NAT Gateway**: Outbound internet access for private subnets
- **No Public IPs**: ECS tasks and RDS in private subnets

#### IAM Roles

- **Least Privilege**: Each service has minimal required permissions
- **No Hardcoded Credentials**: All credentials via IAM roles or Secrets Manager
- **Role-Based Access**: Different roles for API, Lambda, ECS tasks

#### Secrets Management

- **AWS Secrets Manager**: Database credentials, API keys
- **Environment Variables**: Non-sensitive configuration only
- **Rotation**: Secrets can be rotated without code changes

#### Monitoring & Auditing

- **CloudWatch Logs**: All API and Lambda logs
- **CloudTrail**: API calls and infrastructure changes
- **Correlation IDs**: Request tracking across services
- **Audit Trail**: All operator actions logged

---

## Performance and Scaling

### Current Capacity

#### API (ECS Fargate)

- **Instance Type**: Fargate (CPU/Memory configurable)
- **Default**: 0.5 vCPU, 1 GB RAM per task
- **Scaling**: Auto-scaling based on CPU/Memory utilization
- **Concurrent Requests**: ~100-200 per task (depends on workload)

#### Lambda Worker

- **Memory**: 512 MB - 3 GB (configurable)
- **Timeout**: 15 minutes (max)
- **Concurrency**: 1000 concurrent executions (default)
- **Scaling**: Automatic based on SQS queue depth

#### Database (RDS)

- **Instance Type**: db.t3.medium (default, configurable)
- **Storage**: 20 GB GP3 (auto-scaling enabled)
- **Connections**: ~100-200 concurrent (depends on instance size)
- **Backup**: Automated daily backups, 7-day retention

#### SQS Queue

- **Message Retention**: 14 days
- **Visibility Timeout**: 5 minutes (configurable)
- **Dead Letter Queue**: Configured for failed messages
- **Throughput**: Unlimited (SQS standard)

### Scaling Behavior

#### Horizontal Scaling

**API:**

- ECS Service auto-scaling based on:
  - CPU utilization > 70%
  - Memory utilization > 80%
  - Target tracking scaling policy
- Scales from 1 to 10 tasks (configurable)

**Lambda:**

- Automatically scales based on SQS queue depth
- Processes up to 5 messages per invocation (batch)
- Can handle thousands of concurrent analyses

**Database:**

- Vertical scaling: Increase instance size
- Read replicas: Can add for read-heavy workloads
- Connection pooling: SQLAlchemy connection pool (default: 5-10)

#### Vertical Scaling

- **ECS Tasks**: Increase CPU/Memory allocation
- **Lambda**: Increase memory (also increases CPU proportionally)
- **RDS**: Upgrade instance type (requires downtime for single-AZ)

### Optimization Tips

#### API Performance

1. **Connection Pooling**: Tune SQLAlchemy pool size
2. **Caching**: Consider Redis for frequently accessed data
3. **Pagination**: Always use pagination for list endpoints
4. **Indexes**: Ensure database indexes are optimized

#### Lambda Performance

1. **Memory Allocation**: More memory = more CPU (faster execution)
2. **Batch Processing**: Process multiple messages per invocation
3. **Warm Starts**: Keep Lambda warm with scheduled events (optional)
4. **Timeout Tuning**: Set appropriate timeout (not too high)

#### Database Performance

1. **Indexes**: Ensure all query patterns are indexed
2. **Query Optimization**: Use `EXPLAIN ANALYZE` for slow queries
3. **Connection Pooling**: Tune pool size based on load
4. **Read Replicas**: Use for read-heavy workloads

#### SQS Optimization

1. **Batch Size**: Process multiple messages per Lambda invocation
2. **Visibility Timeout**: Set based on average processing time
3. **Dead Letter Queue**: Monitor and handle failed messages
4. **Long Polling**: Enable for cost reduction

---

## Known Limitations

### Current Limitations

1. **Single Operator Role**

   - All operators have the same permissions
   - No role-based access control (RBAC)
   - Future: Admin, Reviewer, Viewer roles

2. **No Real-time Updates**

   - Frontend polls analysis status every 5 seconds
   - No WebSocket/SSE for real-time updates
   - Future: WebSocket support for live updates

3. **Limited Analysis Customization**

   - Analysis algorithm is fixed (version 1.0.0)
   - Cannot customize rule weights per company type
   - Future: Configurable analysis profiles

4. **No Bulk Operations**

   - Cannot bulk update company statuses
   - Cannot bulk export reports
   - Future: Bulk operations API

5. **Document Size Limits**

   - S3 presigned URL uploads limited by S3 (5 GB max)
   - No client-side chunking for large files
   - Future: Multipart upload support

6. **Analysis Timeout**

   - Lambda timeout: 15 minutes max
   - Very complex analyses may timeout
   - Future: Step Functions for long-running analyses

7. **No Analysis Scheduling**

   - Cannot schedule periodic reanalysis
   - Manual reanalysis only
   - Future: Scheduled analysis jobs

8. **Limited Export Formats**

   - Only PDF and JSON exports
   - No CSV, Excel, or other formats
   - Future: Additional export formats

9. **No Email Notifications**

   - No email alerts for analysis completion
   - No email notifications for status changes
   - Future: Email notification system

10. **Single Region Deployment**
    - Deployed only in `us-east-1`
    - No multi-region support
    - Future: Multi-region deployment for DR

### Technical Debt

1. **Test Coverage**

   - Backend: ~60% coverage
   - Frontend: Limited unit tests
   - Future: Increase to 80%+ coverage

2. **Documentation**

   - API documentation in code (OpenAPI/Swagger)
   - No separate API documentation site
   - Future: Dedicated API docs site

3. **Monitoring**

   - Basic CloudWatch metrics
   - No custom dashboards
   - Future: Comprehensive monitoring dashboard

4. **Error Handling**
   - Basic error responses
   - No error categorization/tracking
   - Future: Enhanced error tracking (Sentry, etc.)

---

## Rate Limiting

### API Rate Limits

Currently, the API does not implement explicit rate limiting. However, the following limits apply:

#### ALB Limits

- **Connection Rate**: ~1000 connections/second (default ALB limit)
- **Request Rate**: Limited by ECS task capacity
- **Future**: API Gateway rate limiting (1000 requests/second per API key)

#### Database Limits

- **Connection Pool**: 5-10 connections per ECS task (configurable)
- **Query Rate**: Limited by RDS instance capacity
- **Concurrent Queries**: ~100-200 (depends on instance size)

### External Service Rate Limits

#### OpenAI API

- **Rate Limit**: 3 requests/second (configurable)
- **Implementation**: Token bucket rate limiter
- **Burst**: 3 requests (matches rate)
- **Retry**: Exponential backoff on rate limit errors

**Configuration:**

```python
OPENAI_RATE_LIMIT=3  # requests per second
```

#### WHOIS Services

- **Rate Limit**: 1 request/second (configurable)
- **Implementation**: Token bucket rate limiter
- **Burst**: 1 request
- **Retry**: Exponential backoff

**Configuration:**

```python
WHOIS_RATE_LIMIT=1  # requests per second
```

#### DNS Resolution

- **Rate Limit**: 5 requests/second (configurable)
- **Implementation**: Token bucket rate limiter
- **Burst**: 5 requests
- **No Retry**: DNS failures are logged but not retried

**Configuration:**

```python
DNS_RATE_LIMIT=5  # requests per second
```

#### HTTP Scraping

- **Rate Limit**: 10 requests/second (configurable)
- **Implementation**: Token bucket rate limiter
- **Burst**: 10 requests
- **Retry**: 3 attempts with exponential backoff

**Configuration:**

```python
HTTP_RATE_LIMIT=10  # requests per second
```

### Rate Limiter Implementation

The rate limiter uses a **token bucket algorithm**:

```python
class TokenBucketRateLimiter:
    def __init__(self, rate: float, burst: float = None):
        self.rate = rate  # Tokens per second
        self.burst = burst or rate  # Max tokens
        self.tokens = self.burst  # Current tokens
        self.last_update = time.time()

    def acquire(self, tokens: int = 1, block: bool = True):
        # Add tokens based on elapsed time
        # Remove tokens if available
        # Block until tokens available if block=True
```

**Features:**

- Thread-safe (uses locks)
- Configurable rate and burst
- Blocking and non-blocking modes
- Timeout support

**Usage:**

```python
limiter = get_rate_limiter('openai', rate=3)
limiter.wait()  # Block until token available
# Make API call
```

---

## Error Handling

### Error Response Format

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "additional context"
    },
    "request_id": "correlation-uuid"
  }
}
```

### HTTP Status Codes

| Code | Meaning               | Usage                                      |
| ---- | --------------------- | ------------------------------------------ |
| 200  | OK                    | Successful GET, PATCH, POST                |
| 201  | Created               | Successful POST (resource created)         |
| 204  | No Content            | Successful DELETE                          |
| 400  | Bad Request           | Invalid request body, validation errors    |
| 401  | Unauthorized          | Missing or invalid authentication token    |
| 403  | Forbidden             | Valid token but insufficient permissions   |
| 404  | Not Found             | Resource doesn't exist                     |
| 409  | Conflict              | Resource conflict (e.g., duplicate domain) |
| 422  | Unprocessable Entity  | Validation errors in request body          |
| 500  | Internal Server Error | Unexpected server error                    |
| 503  | Service Unavailable   | Service temporarily unavailable            |

### Common Error Codes

#### Authentication Errors

- `AUTH_REQUIRED`: Missing Authorization header
- `AUTH_INVALID`: Invalid or expired token
- `AUTH_MALFORMED`: Malformed token format

#### Validation Errors

- `VALIDATION_ERROR`: Request body validation failed
- `INVALID_STATUS_TRANSITION`: Invalid company status change
- `INVALID_UUID`: Invalid UUID format

#### Resource Errors

- `COMPANY_NOT_FOUND`: Company doesn't exist
- `COMPANY_ALREADY_EXISTS`: Domain already registered
- `ANALYSIS_NOT_FOUND`: Analysis doesn't exist
- `DOCUMENT_NOT_FOUND`: Document doesn't exist

#### Business Logic Errors

- `COMPANY_ALREADY_ANALYZED`: Cannot update company after analysis
- `ANALYSIS_IN_PROGRESS`: Analysis already running
- `INVALID_RETRY_MODE`: Invalid retry mode for reanalysis

### Retry Logic

#### API Retries

The API does not automatically retry failed requests. Clients should implement retry logic with exponential backoff:

```python
import time
import requests

def api_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code < 500:
                return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) * 1.0
            time.sleep(wait_time)
```

#### Lambda Worker Retries

**SQS Retries:**

- **Visibility Timeout**: 5 minutes (configurable)
- **Max Receives**: 3 attempts
- **Dead Letter Queue**: Failed messages after 3 attempts

**External API Retries:**

- **Max Retries**: 3 attempts (configurable)
- **Backoff**: Exponential (1s, 2s, 4s)
- **Rate Limit Handling**: Special handling for 429 errors

**Example:**

```python
for attempt in range(max_retries):
    try:
        result = await api_call()
        return result
    except RateLimitError:
        wait_time = (2 ** attempt) * 1.0
        await asyncio.sleep(wait_time)
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        wait_time = (2 ** attempt) * 1.0
        await asyncio.sleep(wait_time)
```

### Error Recovery

#### Partial Analysis Failures

If some checks fail during analysis:

1. **Failed checks** are recorded in `failed_checks` array
2. **Successful checks** are saved in `discovered_data`
3. **Analysis status** is set to `"incomplete"` if critical checks fail
4. **Operator can retry** failed checks only via `retry_failed_only=true`

#### Database Connection Failures

- **Connection Pool**: Automatically retries connections
- **SQLAlchemy**: Built-in retry logic for transient errors
- **Timeout**: 30 seconds (configurable)

#### S3 Upload Failures

- **Presigned URL Expiration**: URLs expire after 1 hour
- **Client Retry**: Frontend should retry on 403/404 errors
- **New URL**: Generate new presigned URL if expired

#### Lambda Timeout

- **Timeout**: 15 minutes (max)
- **Checkpointing**: Analysis progress saved after each check
- **Resume**: Can resume from last successful check (future enhancement)

---

## Environment Variables

### Backend Environment Variables

| Variable                | Description                     | Required | Source                              |
| ----------------------- | ------------------------------- | -------- | ----------------------------------- |
| `DB_URL`                | PostgreSQL connection string    | Yes      | Terraform output or local DB        |
| `COGNITO_USER_POOL_ID`  | Cognito User Pool ID            | Yes      | Terraform output                    |
| `COGNITO_APP_CLIENT_ID` | Cognito App Client ID           | Yes      | Terraform output                    |
| `COGNITO_REGION`        | AWS region for Cognito          | Yes      | `us-east-1`                         |
| `COGNITO_ISSUER`        | Cognito issuer URL              | Optional | Derived from region + pool ID       |
| `SQS_QUEUE_URL`         | SQS queue URL for analysis jobs | Yes      | Terraform output                    |
| `S3_BUCKET_NAME`        | S3 bucket for documents         | Yes      | Terraform output                    |
| `OPENAI_API_KEY`        | OpenAI API key for LLM analysis | Optional | Secrets Manager or env var          |
| `AWS_REGION`            | AWS region                      | Yes      | `us-east-1`                         |
| `ENVIRONMENT`           | Environment name                | Yes      | `development`, `dev`, or `prod`     |
| `API_VERSION`           | API version                     | Yes      | `1.0.0`                             |
| `LOG_LEVEL`             | Logging level                   | Optional | `INFO`, `DEBUG`, `WARNING`, `ERROR` |

### Frontend Environment Variables

| Variable                           | Description            | Required |
| ---------------------------------- | ---------------------- | -------- |
| `NEXT_PUBLIC_API_URL`              | Backend API URL        | Yes      |
| `NEXT_PUBLIC_COGNITO_USER_POOL_ID` | Cognito User Pool ID   | Yes      |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID`    | Cognito App Client ID  | Yes      |
| `NEXT_PUBLIC_COGNITO_REGION`       | AWS region for Cognito | Yes      |

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

| Secret                            | Description                                   |
| --------------------------------- | --------------------------------------------- |
| `AWS_ACCESS_KEY_ID`               | AWS access key for CI/CD IAM user             |
| `AWS_SECRET_ACCESS_KEY`           | AWS secret key for CI/CD IAM user             |
| `API_URL_DEV`                     | Dev API URL (from `terraform output api_url`) |
| `API_URL_PROD`                    | Prod API URL                                  |
| `COGNITO_POOL_ID_DEV`             | Dev Cognito User Pool ID                      |
| `COGNITO_POOL_ID_PROD`            | Prod Cognito User Pool ID                     |
| `COGNITO_CLIENT_ID_DEV`           | Dev Cognito App Client ID                     |
| `COGNITO_CLIENT_ID_PROD`          | Prod Cognito App Client ID                    |
| `COGNITO_REGION_DEV`              | Cognito region (usually `us-east-1`)          |
| `COGNITO_REGION_PROD`             | Cognito region for prod                       |
| `CLOUDFRONT_DISTRIBUTION_ID_DEV`  | Dev CloudFront distribution ID                |
| `CLOUDFRONT_DISTRIBUTION_ID_PROD` | Prod CloudFront distribution ID               |
| `FRONTEND_URL_PROD`               | Prod frontend URL (for workflow metadata)     |

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

**Current Phase**: Production Ready - All Core Features Implemented
