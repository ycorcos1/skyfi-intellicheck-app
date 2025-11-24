# SkyFi IntelliCheck — Product Requirements Document (PRD)

Version: 1.0  
Status: Final  
Owner: Yahav Corcos  
Project Type: Internal SkyFi Enterprise Verification System  
Deployment: AWS-Native  
LLM: OpenAI GPT Models  
Verification Runtime: Asynchronous (SQS → Lambda)

---

## 1. Executive Summary

SkyFi IntelliCheck is an internal enterprise verification and risk-assessment platform used by SkyFi teams to validate companies registering for enterprise access. The system automatically performs multi-source data verification, risk scoring, and report generation, while providing a polished operator dashboard to review, confirm, override, and archive verification results.

The goal is to protect SkyFi from fraudulent enterprise accounts, improve compliance, and streamline internal onboarding workflows.

---

## 2. Goals & Objectives

### Primary Goals

- Automatically verify company registration data using public sources and AI reasoning.
- Provide operators with a clean, unified dashboard to review verification results.
- Generate detailed verification reports, including risk scores, signals, and supporting data.
- Ensure analysis runs in the background with reliable asynchronous processing.
- Export verification reports as polished PDF and machine-readable JSON.
- Maintain all historical analyses for compliance and auditing.

### Secondary Goals

- Allow operators to upload supporting documents per company.
- Provide high-quality UX/UI without unnecessary animations.
- Offer real-time status feedback during asynchronous analysis.

### Future Goals (Not Part of MVP)

- Scheduled re-analysis (e.g., every 30 days).

---

## 3. Scope

### In Scope

- Single-role operator system.
- Company creation, display, filtering, editing before review, and soft deletion.
- Automated verification pipeline (WHOIS/DNS/scraping/rule-based checks + LLM reasoning).
- Hybrid risk-scoring engine.
- Verification history storage.
- Operator dashboard.
- Re-run analysis, mark suspicious, revoke approval.
- Supporting document uploads.
- PDF and JSON export.
- Full AWS-native infrastructure.

### Out of Scope

- Global company registry.
- Real-time fraud detection.
- Proprietary system integration.
- Role-based permission tiers.
- External customer-facing UI.

---

## 4. Target Users & Personas

| Persona             | Needs                                    | Satisfied By                              |
| ------------------- | ---------------------------------------- | ----------------------------------------- |
| Compliance Officers | Accurate verification & fraud prevention | Automated verification + detailed reports |
| IT Security Teams   | Identify high-risk companies             | Risk scores, filtering, fraudulent tags   |
| Business Analysts   | Trustworthy company profile data         | Full reports + data exports               |

---

## 5. User Stories

1. Auto-verify company information during registration.
2. View alerts for high-risk companies.
3. Access detailed verification reports.
4. Re-run analyses after editing company data.
5. Upload supporting documents.
6. Export reports as PDF or JSON.

---

## 6. Functional Requirements

### 6.1 Company Management

- Create, edit (pre-review only - editable before first analysis, not after), soft delete
- Upload documents
- View full company list
- Editing after analysis requires re-analysis

### 6.2 Automated Analysis Pipeline

- Triggered on creation
- WHOIS, DNS, scraping, MX validation, phone validation
- Hybrid rule-based + LLM reasoning
- Complete within 2 hours
- Real-time status updates via polling endpoint (every 5 seconds)
- Partial failure handling with retry options

### 6.3 Verification Report

- Submitted vs discovered data.
- Signal breakdown.
- Risk score.
- Summary + detailed reasoning.
- Version history.

### 6.4 Operator Actions

- Re-run analysis
- Mark review complete
- Revoke approval
- Mark company as suspicious
- Internal notes (add, view, edit)
- Export PDF/JSON
- Restore soft-deleted companies

> Fraudulent status is assigned automatically when the analysis completes with a risk score ≥ 70.

### 6.5 Dashboard

- Filters: status (dropdown), risk range (min/max sliders)
- Search: company name (text input with autocomplete)
- Pagination and sorting
- Summary cards showing key metrics

---

## 7. Non-Functional Requirements

### Performance

- Analysis ≤ 2 hours.
- Dashboard loads < 500ms.

### Security

- Cognito auth, HTTPS, encryption (KMS), Secrets Manager.

### Scalability

- SQS → Lambda → ECS horizontally scalable.

### Compliance

- GDPR-aligned practices
- No unnecessary PII
- Soft delete with restoration capability
- Hard delete after 90 days
- Audit logs

---

## 8. User Experience & Design Considerations

- Premium UI
- WCAG accessible
- Real-time status feedback via polling (every 5 seconds)
- Color-coded badges
- Clear partial failure states with retry options

---

## 9. System Architecture

```
Frontend (React/Next.js)
      |
CloudFront + S3
      |
API Gateway
      |
ECS Fargate (FastAPI Backend)
      |
PostgreSQL (RDS)
      |
S3 (Document Storage)
      |
SQS Queue --> Lambda Worker --> Step Functions (optional)
```

---

## 10. API Schema (High-Level)

### Company

```json
{
  "id": "uuid",
  "name": "string",
  "domain": "string",
  "website_url": "string",
  "email": "string",
  "phone": "string",
  "status": "pending|approved|suspicious|fraudulent",
  "risk_score": 0,
  "analysis_status": "pending|in_progress|complete",
  "current_step": "whois|dns|mx_validation|website_scrape|llm_processing|complete",
  "last_analyzed_at": "timestamp",
  "created_at": "...",
  "updated_at": "...",
  "is_deleted": false
}
```

**Status State Machine (manual actions):**

- `pending` → `approved` (via `mark_review_complete` or `approve`)
- `pending` → `suspicious` (via `mark_suspicious`)
- `suspicious` → `approved` (via `mark_review_complete` or `approve`)
- `approved` → `suspicious` (via `mark_suspicious` or `revoke_approval`)

Fraudulent status is assigned automatically by the worker when `risk_score >= 70`.

### Analysis Record

```json
{
  "id": "uuid",
  "company_id": "uuid",
  "version": 3,
  "algorithm_version": "1.0.0",
  "submitted_data": {},
  "discovered_data": {},
  "signals": [],
  "risk_score": 72,
  "llm_summary": "string",
  "llm_details": "string",
  "is_complete": true,
  "failed_checks": [],
  "created_at": "..."
}
```

---

## 11. Database Schema

### companies

- id (UUID)
- name
- domain
- website_url
- email
- phone
- status (enum: 'pending', 'approved', 'suspicious', 'fraudulent')
- risk_score
- analysis_status (enum: 'pending', 'in_progress', 'complete')
- current_step (VARCHAR(50), tracks current analysis step: 'whois', 'dns', 'mx_validation', 'website_scrape', 'llm_processing', 'complete')
- last_analyzed_at
- is_deleted
- created_at
- updated_at

### company_analyses

- id
- company_id
- version
- algorithm_version
- submitted_data
- discovered_data
- signals
- risk_score
- llm_summary
- llm_details
- is_complete
- failed_checks
- created_at

### documents

- id
- company_id
- filename
- s3_key
- file_size
- mime_type
- uploaded_by (Cognito user ID)
- document_type (nullable, e.g., "proof_of_address")
- description (nullable)
- created_at

### notes

- id (UUID)
- company_id (UUID, FK)
- user_id (from Cognito)
- content (TEXT)
- created_at
- updated_at

---

## 12. Verification Flow (Sequence Diagram)

```
Frontend → API: POST /v1/companies
API → DB: create record
API → SQS: enqueue analysis

Lambda Worker:
  → WHOIS/DNS/Web Scraper
  → Rule Engine
  → OpenAI Reasoning
  → DB save analysis

Frontend → API: GET /v1/companies/{id}/analysis/status (polling every 5s)
API → DB: fetch current status
API → Frontend: {
  analysis_status: "pending|in_progress|complete",
  progress_percentage: 0-100,
  current_step: "whois|dns|mx_validation|website_scrape|llm_processing|complete",
  failed_checks: [...]
}

Frontend → API: GET /v1/companies/{id}
API → DB: fetch data
Frontend: render report
```

---

## 13. Hybrid Risk Scoring Model

### Rule-Based Weights (Examples)

- Domain age < 1 year: +20
- WHOIS privacy: +10
- Address mismatch: +15
- Email mismatch: +10
- Phone region mismatch: +10
- Unreachable website: +25

### LLM Contribution

- Textual reasoning.
- ±20 score adjustment.
- Highlights subjective signals.

### Final Score

```
final_score = clamp(rule_score + llm_score_adjustment, 0, 100)
```

---

## 14. Example JSON Report

```json
{
  "company": {
    "name": "NovaGeo Analytics",
    "domain": "novageo.io",
    "status": "pending"
  },
  "analysis": {
    "risk_score": 68,
    "signals": [
      { "field": "domain_age", "status": "suspicious" },
      { "field": "email_domain_match", "status": "mismatch" },
      { "field": "website_lookup", "status": "ok" }
    ],
    "llm_summary": "The company appears moderately risky...",
    "version": 1
  }
}
```

---

## 15. PDF Report Structure

1. Cover Page
2. Company Overview
3. Submitted vs Discovered
4. Risk Score Badge
5. Signals Table
6. LLM Summary
7. Detailed Appendix

---

## 16. Deployment Requirements

- RDS Postgres
- SQS Queue
- Lambda Worker
- ECS Fargate API
- Cognito
- S3
- CloudFront
- Secrets Manager
- CloudWatch
- Environments: dev, prod

---

## 17. Acceptance Criteria

- All analyses run asynchronously.
- PDF + JSON reports export correctly.
- Document uploads function via S3.
- Dashboard filtering/search works.
- Soft delete hides companies.
- Risk scores remain deterministic + LLM-enhanced.
- All actions logged.

---

## 18. Future Enhancements

- Scheduled re-analysis
- Notifications
- Multi-tenancy
- Dark mode
- Paid enrichment APIs

---

# End of PRD
