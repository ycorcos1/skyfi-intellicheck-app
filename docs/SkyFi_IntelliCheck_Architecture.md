# SkyFi IntelliCheck — Architecture Diagram & System Design Document

Version: 1.0  
Status: Final  
Owner: Yahav Corcos  
Scope: Backend architecture + frontend–backend interactions only  
Frontend visuals: Excluded  
Future hooks: Excluded

---

## 1. Purpose & Scope

This document describes the architecture, system components, data flows, and execution pipeline of SkyFi IntelliCheck. It does not include UI/UX layouts, detailed design specs, or future enhancements. It serves as the runtime blueprint for both Cursor and developers to understand how backend services communicate.

---

## 2. High-Level Architecture Overview

### 2.1 Text Overview

SkyFi IntelliCheck is an AWS-native distributed backend consisting of:

- Frontend: Next.js (S3 + CloudFront)
- API Layer: FastAPI on ECS Fargate
- Authentication: AWS Cognito
- Database: RDS PostgreSQL
- Storage: S3
- Async Workers: SQS → Lambda
- Optional orchestration: Step Functions
- External integrations: WHOIS, DNS, HTTP scraping, OpenAI

---

### 2.2 High-Level Architecture Diagram (ASCII)

```
                    ┌────────────────────────────┐
                    │        Frontend            │
                    │        (Next.js)           │
                    └──────────────┬─────────────┘
                                   │
                    ┌──────────────▼─────────────┐
                    │    CloudFront + S3 (UI)    │
                    └──────────────┬─────────────┘
                                   │
                    ┌──────────────▼─────────────┐
                    │        API Gateway         │
                    └──────────────┬─────────────┘
                                   │   JWT Auth
                                   ▼
                    ┌────────────────────────────┐
                    │   FastAPI on ECS Fargate   │
                    │ (REST API + Business Logic)│
                    └──────────────┬─────────────┘
                      Writes        │     Reads
                      to DB         │
                                   ▼
                 ┌──────────────────────────────────┐
                 │        PostgreSQL (RDS)          │
                 │ companies / analyses / docs meta │
                 └──────────────────┬───────────────┘
                                    │
                ┌───────────────────┴──────────────────┐
                │             S3 Storage               │
                │ (supporting documents, static data) │
                └───────────────────┬──────────────────┘
                                    │
                                    ▼
                    ┌────────────────────────────┐
                    │   SQS Verification Queue   │
                    └──────────────┬─────────────┘
                                   │ triggers
                                   ▼
                    ┌────────────────────────────┐
                    │   Lambda Worker (Analysis) │
                    │ WHOIS / DNS / Scrape / LLM │
                    └──────────────┬─────────────┘
                                   │ writes results
                                   ▼
                         ┌─────────────────────┐
                         │RDS (analysis table) │
                         └─────────────────────┘
```

---

## 3. Component Breakdown

### 3.1 Frontend (Next.js)

Responsible for:

- Company creation
- Dashboard filtering + search
- Viewing analysis results
- Triggering re-analysis
- Uploading documents via signed URLs
- Exporting PDF/JSON
- Handling Cognito auth

---

### 3.2 AWS Cognito (Authentication)

Responsible for:

- Login
- Token issuance
- JWT validation via API Gateway

---

### 3.3 FastAPI on ECS Fargate (API)

Responsible for:

- CRUD for companies
- Soft delete
- Triggering analysis via SQS
- Returning analysis results
- Generating exports
- Issuing S3 signed URLs for uploads

Endpoints include:

- POST /companies
- GET /companies (with query params: ?page=X&limit=Y&search=&status=&risk_min=&risk_max=)
- GET /companies/{id}
- PATCH /companies/{id} (editable only before first analysis)
- DELETE /companies/{id} (soft delete)
- POST /companies/{id}/reanalyze
- PATCH /companies/{id}/status (mark review complete, approve, mark suspicious, revoke approval)
- POST /companies/{id}/revoke-approval
- POST /companies/{id}/notes
- GET /companies/{id}/notes
- PATCH /companies/{id}/notes/{note_id}
- DELETE /companies/{id}/notes/{note_id}
- GET /companies/{id}/analysis/status (for real-time polling)
- POST /companies/{id}/documents/upload-url
- GET /companies/{id}/documents
- GET /companies/{id}/documents/{doc_id}/download-url
- GET /companies/{id}/export/pdf
- GET /companies/{id}/export/json

---

### 3.4 PostgreSQL (RDS)

Stores:

- Companies
- Company analyses (versioned)
- Document metadata
- Internal notes
- Soft deletion flags

Design:

- Append-only `company_analyses`
- Latest risk score cached in `companies`
- Analysis status tracking fields for async processing (analysis_status, current_step)

---

### 3.5 S3 Storage

Used for:

- Supporting documents
- PDF exports
- Static frontend assets

Secure via:

- Private bucket
- IAM role restrictions
- Presigned uploads

---

### 3.6 SQS Queue

Decouples:

- API requests
- Analysis pipeline

Message contains:

- company_id
- analysis_version
- timestamp

---

### 3.7 Lambda Worker (Verification Pipeline)

Tasks:

- WHOIS lookup
- DNS checks
- Homepage scraping
- MX validation
- Phone parsing
- Rule engine → signals
- OpenAI → narrative & score adjustment
- Write to RDS

Includes retries and DLQ.

---

### 3.8 Step Functions (Optional)

Used when analysis complexity exceeds Lambda's capabilities:

- Triggered if analysis takes > 10 minutes
- Triggered if company has > 10 documents to process
- Ensures <2 hour SLA via multi-step orchestration
- Otherwise: Direct Lambda invocation is sufficient

---

### 3.9 External Integrations

- WHOIS
- DNS
- HTTP scraping
- OpenAI

---

## 4. Core Workflows / Sequence Diagrams

### 4.1 Company Creation → Automatic Analysis

```
Frontend → API: POST /companies
API → RDS: create row
API → SQS: enqueue analysis job

Worker:
  WHOIS, DNS, Scrape
  Rule engine
  OpenAI
  Compute final score
Worker → RDS: insert analysis + update company
```

---

### 4.2 Re-analysis

```
Frontend → API: POST /companies/{id}/reanalyze
  Request body: { "retry_failed_only": true } (optional, default: false)
API → SQS: new message
  If retry_failed_only=true:
    Message includes: { "company_id", "retry_mode": "failed_only", "failed_checks": [...] }
  If retry_failed_only=false or omitted:
    Message includes: { "company_id", "retry_mode": "full" }
Worker → RDS: new analysis version
  If retry_mode="failed_only": only executes checks in failed_checks array, reuses other results
  If retry_mode="full": executes all checks
```

---

### 4.3 Document Upload

```
Frontend → API: upload-url
API → S3: generate signed URL
Frontend → S3: PUT document
Frontend → API: save metadata (filename, size, type, uploaded_by)
```

---

### 4.4 Real-Time Status Polling

```
Frontend → API: GET /companies/{id}/analysis/status (every 5 seconds)
API → RDS: fetch current status
API → Frontend: {
  "analysis_status": "pending|in_progress|complete",
  "progress_percentage": 0-100,
  "current_step": "whois|dns|mx_validation|website_scrape|llm_processing|complete",
  "failed_checks": [...]
}
Frontend: Update UI progress indicator

Progress Calculation:
- progress_percentage = (completed_checks / total_checks) * 100
- total_checks = 5 (whois, dns, mx_validation, website_scrape, llm_processing)
- Worker updates companies.analysis_status and companies.current_step after each check
- Polling stops when analysis_status === "complete"
```

---

### 4.5 Export PDF/JSON

JSON:

```
Frontend → API → RDS → Frontend.json
```

PDF:

```
Frontend → API → RDS → PDF generator → binary return
(Generated on-demand, no caching, streamed directly to client)
```

---

## 5. Data Flow & Storage Responsibilities

### Company creation:

- Insert row into `companies`
- Initial analysis queued

### Analysis completion:

- Insert into `company_analyses`
- Update `companies.risk_score`

### Document upload:

- Stored in S3
- Metadata mapped in DB

### Soft delete:

- `is_deleted = true`
- Hidden from default views
- Viewable with `?include_deleted=true` query parameter
- Restorable by operators
- Hard delete after 90 days (compliance requirement)

---

## 6. Error Handling & Retry Strategy

### Worker:

- Automatic retries
- DLQ
- Marks failed jobs with "analysis_failed"
- Partial failure handling:
  - Save partial results with "incomplete" flag
  - Track which checks succeeded/failed
  - Allow operator to manually input missing data
  - Provide "retry failed checks only" option

### API:

- Consistent errors
- Clear operator messaging
- Standard error response format:
  ```json
  {
    "error": {
      "code": "ERROR_CODE",
      "message": "Human-readable message",
      "details": {},
      "request_id": "unique-id"
    }
  }
  ```

### Document uploads:

- Handle signed URL expiration gracefully

### Rate Limiting:

- OpenAI: 3 requests/second, use exponential backoff
- WHOIS: 1 request/second per provider
- Implement circuit breaker pattern
- Queue analysis if rate limited

---

## 7. Security Architecture

- JWT auth via Cognito
- ECS + RDS in private subnet
- ALB public-facing
- HTTPS only
- Secrets in Secrets Manager
- Private S3 bucket with strict IAM

---

## 8. Scalability & Performance

- Lambda scales automatically
- ECS scales via CPU/memory
- SQS absorbs traffic spikes
- Step Functions for long-running tasks
- Meets 2-hour SLA

---

## 9. Observability

### Logs:

- Structured JSON logs

### Metrics:

- Queue depth
- Latency
- Worker failures
- Analysis durations

### Dashboards:

- CloudWatch system dashboards

---

## 10. Environment Configuration

### dev:

- Lower concurrency
- Verbose logs
- Optional mocks

### prod:

- Full integrations
- Auto-scaling
- Backups enabled

### Shared Environment Variables:

- OPENAI_API_KEY
- SKYFI_API_KEY
- DB_URL
- S3_BUCKET_NAME
- COGNITO_POOL_ID
- COGNITO_CLIENT_ID
- JWT_ISSUER

### API Versioning:

- All endpoints use `/v1/` prefix
- Analysis algorithm version stored in `company_analyses.algorithm_version`
- Historical reports can be regenerated with their original algorithm version

---

# End of Architecture Document
