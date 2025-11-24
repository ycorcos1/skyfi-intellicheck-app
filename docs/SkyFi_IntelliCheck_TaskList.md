# SkyFi IntelliCheck — Full Project Task List

Version: 1.0  
Owner: Yahav Corcos  
Deployment Region: us-east-1  
Dedicated VPC: **skyfi-intellicheck-vpc**

---

# PR #0 – Repo & Docs Bootstrap

Set up a clean monorepo with folders for backend, frontend, infra, and docs. Add the three markdown docs you already have (PRD, Architecture, Design Spec) under `/docs`. Add a top-level `README.md` explaining the project, stacks used, and how the docs are meant to guide development. Add a `.gitignore` covering Python, Node, Docker, and Terraform/CDK.

**Acceptance:** Repo checked in with `/backend`, `/frontend`, `/infra`, `/docs`, `.gitignore`, and a `README.md` that references SkyFi IntelliCheck and the three docs.

---

# PR #1 – IAM User & AWS CLI Setup (Cursor-Ready)

Define exactly how Cursor will interact with AWS. Have Cursor generate an IAM policy (JSON) describing the minimum permissions needed for this project. You manually create an **IAM user** dedicated to IntelliCheck, attach a policy or role with those permissions, create access keys, and configure the local AWS CLI. Test using `aws sts get-caller-identity`.

**Acceptance:** IAM user exists, CLI configured, and a committed `docs/aws-permissions.md` describes permissions Cursor can assume.

---

# PR #2 – Core Infra: `skyfi-intellicheck-vpc`

Create Terraform/CDK infra defining a VPC named **`skyfi-intellicheck-vpc`** in `us-east-1` with CIDR like `10.20.0.0/16`, three public subnets, three private subnets, NAT gateways, Internet Gateway, and route tables with clear tagging.

**Acceptance:** Infra deploys successfully and VPC is visible with all subnets and routing set up.

---

# PR #3 – Infra: RDS, S3, SQS, Lambda, ECS Skeleton

Extend infra to include:

- RDS PostgreSQL instance in private subnets
- S3 bucket for documents
- SQS queue + DLQ
- Lambda worker stub
- ECS Cluster and empty Fargate service definition

**Acceptance:** Infra deploy produces RDS, S3, SQS, Lambda stub, and ECS skeleton within the new VPC.

---

# PR #4 – Backend Service Bootstrap (FastAPI + DB)

Scaffold FastAPI in `/backend`. Include structure for routes, models, migrations, config, etc. Implement DB connection using RDS URL. Add `/health` and `/version` endpoints. Add Dockerfile.

**Acceptance:** Local FastAPI starts and connects to dev DB; Docker image builds and runs.

---

# PR #5 – Cognito Authentication Integration

Provision Cognito User Pool and App Client via infra. Integrate JWT validation in FastAPI. Protect all endpoints except `/health` and `/version`. Document how to create dev users.

**Acceptance:** Protected endpoints require valid Cognito JWT.

---

# PR #6 – Database Schema (companies, company_analyses, documents, notes)

Implement ORM models and migrations for:

- `companies` (with analysis_status, current_step, last_analyzed_at fields)
- `company_analyses` (with algorithm_version, is_complete, failed_checks fields)
- `documents` (with file_size, mime_type, uploaded_by, document_type, description)
- `notes` (new table for internal operator notes)

Ensure versioned analysis storage and soft delete support.

**Acceptance:** Migrations run successfully on dev RDS.

---

# PR #7 – Worker: External Integrations + Rule Engine Skeleton

In the Lambda worker:

- WHOIS lookup
- DNS queries
- HTTP homepage fetch & parse
- MX record lookup
- Phone normalization
- Rule engine that outputs `signals` + `rule_score`
- Track successful/failed checks separately
- Support partial failure handling

**Acceptance:** Worker produces structured output with `rule_score` and `failed_checks` for a test company.

---

# PR #8 – Worker: OpenAI Integration + Hybrid Scoring

Add OpenAI integration:

- Generate `llm_summary`, `llm_details`, `llm_score_adjustment`
- Compute final score: `clamp(rule_score + llm_score_adjustment, 0, 100)`
- Store algorithm_version with each analysis
- Write analysis to DB with completeness flag

**Acceptance:** Worker writes complete analysis records with algorithm version into DB.

---

# PR #9 – End-to-End SQS → Lambda Flow

Wire SQS to Lambda with retries + DLQ. Add status tracking in DB (`analysis_pending`, `in_progress`, `completed`, `failed`, `incomplete`). Add structured logs and correlation IDs. Implement rate limiting for external APIs.

**Acceptance:** Sending a message triggers full pipeline and updates DB correctly with appropriate status.

---

# PR #10 – Lambda Worker Deployment

Deploy the Lambda worker code to AWS:

- Create deployment package (zip file) containing worker code and dependencies
- Set up build script or process to package Lambda function
- Update Lambda function code (replace stub with actual worker implementation)
- Configure Lambda environment variables (DB_SECRET_ARN, S3_BUCKET_NAME, OPENAI_API_KEY, etc.)
- Test Lambda function invocation directly
- Verify SQS → Lambda trigger works end-to-end
- Add Terraform configuration for Lambda deployment (or use AWS CLI/SDK)
- Set up Lambda versioning and aliases for safe deployments
- Configure Lambda dead letter queue (DLQ) if not already set
- Test full worker pipeline with sample company data

**Acceptance:** Lambda worker code is deployed and functional; SQS messages trigger worker execution; worker successfully processes companies and writes to DB; DLQ captures failed invocations.

---

# PR #11 – Company API: CRUD, Soft Delete, Auto-Analysis

FastAPI endpoints (all under `/v1/` prefix):

- `POST /companies` (creates + enqueues analysis)
- `GET /companies` (filters, search, risk range, pagination: ?page=X&limit=Y&search=&status=&risk_min=&risk_max=&include_deleted=)
- `GET /companies/{id}` (details + latest analysis)
- `PATCH /companies/{id}` (editable only before first analysis)
- `DELETE /companies/{id}` (soft delete with restoration capability)
- `POST /companies/{id}/restore` (restore soft-deleted company)

**Business Rule:** Companies editable before first analysis only; after analysis, must use re-analyze.

**Acceptance:** API fully functional with Cognito auth enforced and proper status state machine.

---

# PR #12 – API: Reanalysis, Status Management, Real-Time Status

Add endpoints:

- `POST /companies/{id}/reanalyze` (request body: { "retry_failed_only": true } for selective retry)
- `PATCH /companies/{id}/status` (mark review complete, approve, mark suspicious)
- `POST /companies/{id}/revoke-approval`
- `GET /companies/{id}/analysis/status` (for real-time polling: returns status, progress_percentage, current_step)

**Acceptance:** Status updates follow state machine rules, new analysis versions work, and real-time status endpoint supports 5-second polling.

---

# PR #13 – Documents API & S3 Integration

Implement:

- `POST /companies/{id}/documents/upload-url` (presigned URL generation)
- `POST /companies/{id}/documents` (metadata persistence: filename, size, mime_type, uploaded_by, document_type, description)
- `GET /companies/{id}/documents` (list documents)
- `GET /companies/{id}/documents/{doc_id}/download-url` (presigned download URL)
- `DELETE /companies/{id}/documents/{doc_id}` (delete document)

**Acceptance:** Upload and download flow works fully with metadata tracking.

---

# PR #14 – Notes API & Internal Operator Notes

Implement:

- `POST /companies/{id}/notes` (create note with user_id from Cognito)
- `GET /companies/{id}/notes` (list all notes)
- `PATCH /companies/{id}/notes/{note_id}` (edit note)
- `DELETE /companies/{id}/notes/{note_id}` (delete note)

**Acceptance:** Notes functionality works with proper user tracking.

---

# PR #15 – Export JSON & PDF Reports

Implement:

- `GET /companies/{id}/export/json`
- `GET /companies/{id}/export/pdf`

Follow PRD's report structure and design spec's PDF layout. PDFs generated on-demand and streamed directly (no caching).

**Acceptance:** JSON schema valid; PDF renders correctly with all sections.

---

# PR #16 – Observability & Metrics

Add:

- Structured logs
- CloudWatch metrics (queue depth, analysis failures/success, latency)
- Basic CloudWatch Dashboard

**Acceptance:** Logs and metrics visible in CloudWatch.

---

# PR #17 – ECR Repository Setup

Create Elastic Container Registry (ECR) for storing Docker images:

- Create ECR repository for backend API Docker images
- Configure ECR lifecycle policies (retain last N images, delete old untagged images)
- Set up ECR repository policies and permissions
- Configure image scanning (optional, for security)
- Add Terraform outputs for ECR repository URL
- Document process for building and pushing Docker images to ECR
- Test Docker image push/pull workflow
- Set up authentication for ECR (IAM roles, docker login process)

**Acceptance:** ECR repository exists and is accessible; Docker images can be pushed and pulled; lifecycle policies are configured; ECS task execution role has permissions to pull from ECR.

---

# PR #18 – Backend Infrastructure Deployment (API Gateway, ALB, ECS Service)

Deploy the backend API to production infrastructure:

- Create Application Load Balancer (ALB) in public subnets with security groups
- Configure API Gateway (REST API) with Cognito authorizer for JWT validation
- Set up VPC Link between API Gateway and ALB (or use ALB directly with public access)
- Update ECS service to run actual tasks (set `desired_count > 0`)
- Configure ALB target group pointing to ECS service
- Set up health checks for ECS tasks
- Configure auto-scaling policies for ECS service (min/max tasks based on CPU/memory)
- Update ECS task definition with actual Docker image from ECR (created in PR #17)
- Configure security groups to allow ALB → ECS communication
- Add Terraform outputs for API Gateway URL and ALB DNS name
- Test API endpoints through API Gateway/ALB

**Acceptance:** Backend API is accessible via API Gateway/ALB URL; ECS tasks are running and healthy; Cognito JWT auth works through API Gateway; health checks pass.

---

# PR #19 – Frontend Bootstrap (Next.js + Global Theme + Design Tokens)

Goal: Initialize frontend and establish global theme foundation.

- Set up Next.js app in `/frontend` using TypeScript.
- Implement global theme tokens (colors, typography, spacing, border-radii, shadows).
- Add global CSS reset and base layout wrapper.
- Configure environment variables for Cognito (no full auth flow yet).
- Set up initial folder structure for components, pages, hooks, and styles.
  Acceptance: Next.js app runs with global theme applied, basic layout wrapper visible, and no route errors.

---

# PR #20 – App Shell, Navigation & Full Authentication Flow

Goal: Implement authenticated layout and functional login using Cognito.

- Build top navigation bar (black background, product name/logo, user menu).
- Add protected layout wrapper that hides all pages behind authentication.
- Implement full Cognito auth flow: login, logout, token storage, session handling.
- Create Login page UI exactly matching the Design Spec.
- Add redirect logic for unauthenticated → login, and authenticated → dashboard.
  Acceptance: Login page works fully; protected routes require valid Cognito session; app shell appears only after login.

---

# PR #21 – Core UI Components (Buttons, Inputs, Dropdowns, Badges, Cards, Table Shell)

Goal: Build reusable UI primitives to support all pages.

- Implement Button variants (primary, secondary, disabled) with theme-driven styles.
- Implement Input + Select components with label, error states, and placeholder behavior.
- Add Status Badges (Pending, Approved, High Risk, Fraudulent).
- Add Card component with padding + shadow.
- Implement a Table shell component (header, row styling, pagination placeholders).
- Create a UI Sandbox page to preview all components.
  Acceptance: Sandbox page displays working versions of each UI component; all styling follows Design Spec.

---

# PR #22 – Companies Dashboard (Static UI Only)

Goal: Build full dashboard layout with mock data only.

- Create page header “Companies”.
- Implement filter panel with search input, domain dropdown, status dropdown, risk range inputs.
- Add summary cards (Pending, Approved, High Risk).
- Render companies table with mock rows.
- Add “Create Company” button + placeholder modal.
- Ensure entire layout matches spacing/visuals from Design Spec.
  Acceptance: Dashboard renders with static content exactly matching Design Spec wireframes.

---

# PR #23 – Companies Dashboard Integration (API, Filters, Search, Pagination)

Goal: Replace static content with real backend integration.

- Use `GET /companies` for data loading with query params.
- Implement debounced search by name.
- Wire up domain/status/risk score filters.
- Implement pagination and sorting.
- Replace mock rows with live API data.
- Implement loading skeletons, empty states, and error messages.
- Connect “Create Company” form to `POST /companies`; refresh data on success.
  Acceptance: Dashboard fully reflects backend data, filters update results, create flow works, and UI handles loading/empty/error states.

---

# PR #24 – Company Detail Page (Static Layout for Overview + Tabs + Header)

Goal: Build detail page layout using mock data.

- Add breadcrumb (Dashboard → Companies → {Company}).
- Create header with company name, domain, status badge, big risk score badge.
- Add action buttons row (static).
- Implement tabs: Overview, Analysis History, Documents, Notes.
- Build Overview tab: Submitted vs. Discovered columns, signals table skeleton, LLM summary box.
  Acceptance: Detail page loads with full static UI matching Design Spec.

---

# PR #25 – Company Detail Integration (Overview, Actions, Polling)

Goal: Wire detail page to backend + enable all Overview actions.

- Fetch company + latest analysis via `GET /companies/{id}`.
- Populate Overview tab with real data (submitted/discovered/signals/risk/summary).
- Implement Re-run Analysis, Flag Fraudulent, Revoke Approval.
- Implement Export JSON and Export PDF.
- Add Upload Document modal (UI only here).
- Implement polling for pending/in-progress analyses.
  Acceptance: Overview tab shows real data; actions work; polling updates UI correctly.

---

# PR #26 – Analysis History Tab (Full UI + Backend Integration)

Goal: Implement complete version history tab.

- Fetch all analyses (versions).
- Display table with Version, Date, Risk Score, and View Report.
- Implement modal or inline viewer for historic version details.
- Ensure latest-view logic remains consistent.
  Acceptance: History tab loads all versions; viewing historic reports works.

---

# PR #27 – Documents & Notes Tabs (Upload, List, Download, Notes CRUD)

Goal: Fully implement Documents + Notes.

- Connect Documents tab to `GET /companies/{id}/documents`.
- Implement upload modal with presigned URL support.
- List documents with download button.
- Implement Notes tab with add, edit, delete operations.
- Add loading/error states for both.
  Acceptance: Document upload/download works; Notes create/edit/delete works end-to-end.

---

# PR #28 – Export Experience (JSON + PDF + Optional Preview)

Goal: Polish export UX.

- Implement clean JSON export download flow.
- Implement PDF export with loading state.
- Add optional modal/page preview styled like final report.
- Add error handling for export failures.
  Acceptance: JSON/PDF export flows work reliably; preview (if enabled) matches expected layout.

---

# PR #29 – Accessibility, Responsiveness & Final Visual Polish

Goal: Finalize UI quality + accessibility.

- Add keyboard accessible focus states.
- Verify and fix color contrast issues.
- Ensure responsiveness for all pages.
- Add missing empty/error states.
- Refine spacing, hover states, transitions.
- Run Lighthouse/aXe checks and fix major issues.
  Acceptance: UI is fully responsive, accessible, polished, and consistent.

---

# PR #30 – Frontend Infrastructure Deployment (CloudFront, S3, DNS)

Deploy the frontend application to production infrastructure:

- Create S3 bucket for static frontend assets (Next.js export)
- Configure S3 bucket with static website hosting or CloudFront origin
- Create ACM certificate for HTTPS (in us-east-1 for CloudFront)
- Create CloudFront distribution pointing to S3 bucket
- Configure CloudFront with:
  - Custom error pages (SPA routing support)
  - HTTPS/SSL certificate (ACM)
  - Caching policies for static assets
  - Origin access control (OAC) for S3
- Set up CloudFront behaviors for API routes (proxy to API Gateway)
- Configure environment variables in frontend build (API Gateway URL, Cognito settings)
- Set up manual deployment process for frontend builds (build → upload to S3 → invalidate CloudFront)
- Add Terraform outputs for CloudFront distribution URL
- (Optional) Configure Route53 DNS record pointing to CloudFront distribution
- Test frontend accessibility and API integration through CloudFront

**Acceptance:** Frontend is accessible via CloudFront URL; static assets load correctly; API calls route to backend; Cognito authentication works; SPA routing functions properly; HTTPS works with valid certificate.

---

# PR #31 – CI/CD Pipeline Setup

Set up automated deployment pipelines for backend and frontend:

- Choose CI/CD platform (GitHub Actions, AWS CodePipeline, GitLab CI, etc.)
- Create backend deployment pipeline:
  - Build Docker image from Dockerfile
  - Push image to ECR
  - Update ECS service with new image
  - Run health checks after deployment
- Create frontend deployment pipeline:
  - Build Next.js application
  - Export static files
  - Upload to S3 bucket
  - Invalidate CloudFront cache
- Create Lambda deployment pipeline:
  - Package Lambda function code
  - Update Lambda function
  - Run smoke tests
- Set up environment-specific deployments (dev, prod)
- Configure secrets management for CI/CD (API keys, credentials)
- Add deployment notifications (Slack, email, etc.)
- Document deployment process and rollback procedures
- Set up branch protection and deployment approvals for production

**Acceptance:** CI/CD pipelines are functional; code changes trigger automated deployments; deployments succeed to dev environment; production deployments require approval; rollback procedures work.
