# SkyFi IntelliCheck — Full UI Design Specification (With Visual Page Layouts)

Version: 2.0  
Owner: Yahav Corcos  
Brand Colors: Black #000000, White #FFFFFF, Yellow #FFCC00  
Goal: Premium, polished, enterprise-grade UI that is user-friendly, visually appealing, and professional.

---

# 1. Color & Typography

## Color Palette

- **Primary:** Black (#000000)
- **Secondary:** White (#FFFFFF)
- **Accent:** Yellow (#FFCC00)
- **Neutrals:**
  - Light Gray (#F5F5F5)
  - Medium Gray (#E0E0E0)
  - Dark Gray (#888888)
- **States:**
  - Success: Green (#28A745)
  - Error: Red (#DC3545)

## Typography

- **Display/Headers:** Bebas Neue or Bricolage Grotesque
- **Body/UI Text:** IBM Plex Sans or Source Sans 3
- **Monospace:** JetBrains Mono

---

# 2. Layout System

- 12-column grid
- 8px spacing increments
- Max content width: 1440px
- Page margins: 32px desktop, 16px mobile
- Header height: 64px

## Table Text Truncation

- Company Name: Max 30 chars, ellipsis
- Domain: Max 20 chars, ellipsis
- Tooltip on hover shows full text

## Table Sorting

- Default Sort: created_at DESC (newest first)
- Sortable Columns: Name, Domain, Status, Risk Score, Created, Last Analyzed
- Sort indicator: Arrow icon in column header

---

# 3. Component Design

## Buttons

- **Primary:** Yellow bg, black text
- **Secondary:** White bg, yellow border, black text
- **Disabled:** Light gray bg, dark gray text

## Inputs

- White background
- Border: #E0E0E0
- Focus border: Yellow
- Label text: Black
- Placeholder text: Dark gray

## Cards

- White background
- Shadow 0 2px 8px rgba(0,0,0,0.05)
- Rounded corners: 8px

## Status Badges

- Approved: Green border/text
- Pending: Yellow border/text
- Fraudulent: Red border/text
- Rejected: Gray border/text
- Revoked: Orange border/text
- Radius: 12px

## Analysis Status Indicators

- Pending: Gray
- In Progress: Blue with loading animation
- Completed: Green
- Failed: Red
- Incomplete: Yellow

---

# 4. Full Visual Wireframes

---

# PAGE 1 — LOGIN PAGE

```
┌─────────────────────────────────────────────────────────────┐
│ SkyFi IntelliCheck (Centered Logo)                          │
│                                                             │
│     ┌───────────────────────────────────────────────┐       │
│     │   LOGIN                                       │       │
│     │                                               │       │
│     │   Email [_______________________________]     │       │
│     │   Password [___________________________]      │       │
│     │                                               │       │
│     │   [  Sign In (yellow button)  ]               │       │
│     └───────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

# PAGE 2 — DASHBOARD

```
┌─────────────────────────────────────────────────────────────┐
│ BLACK TOP NAV (Logo left, User menu right)                  │
├─────────────────────────────────────────────────────────────┤

│  Page Title: Companies                                       │
│                                                              │
│  ┌───────────────────────Filters──────────────────────────┐  │
│  │ Search: [ Company Name ] (text input with autocomplete) │
│  │ Status: [ dropdown ]  (pending|approved|rejected|...)   │
│  │ Risk Score: [ Min: 0 -------|------- Max: 100 ]         │
│  │ [ Clear Filters ]                                       │
│  └─────────────────────────────────────────────────────────┘  │

│  ┌────────────────────Summary Cards (3)────────────────────┐ │
│  │  Pending: 14         Approved: 32         High Risk: 5   │
│  └──────────────────────────────────────────────────────────┘ │

│  Companies Table (sortable, paginated)                        │
│  ┌───────────────────────────────────────────────────────────┐│
│  │ Name ↓    | Domain    | Status   | Risk | Created | Last   ││
│  │-----------|-----------|----------|------|---------|--------││
│  │ NovaGeo   | novageo…  | Pending  | 68   | …       | …      ││
│  │ GeoStream | geost…    | Approved | 14   | …       | …      ││
│  └───────────────────────────────────────────────────────────┘│
│  [ Previous ] Page 1 of 10 [ Next ]                           │

└─────────────────────────────────────────────────────────────┘
```

---

# PAGE 3 — COMPANY DETAIL OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│ NAV (black)                                                 │
├─────────────────────────────────────────────────────────────┤

│ Breadcrumb:  Dashboard > Companies > NovaGeo Analytics       │

│ ┌──────────────── Company Header ────────────────┐          │
│ │ Company Name: NovaGeo Analytics                │          │
│ │ Domain: novageo.io                             │          │
│ │ Status Badge: [ Pending ]                      │          │
│ │ RISK SCORE: [ 68 – High Risk ] (big badge)     │          │
│ │ Analysis Status: [ In Progress... ] (polling)  │          │
│ └────────────────────────────────────────────────┘          │

│ ┌────────────────── Tabs ──────────────────────────────────┐ │
│ │ Overview | Analysis History | Documents | Notes           │ │
│ └──────────────────────────────────────────────────────────┘ │

│ ┌──────────────── Overview Two-Column Layout ──────────────┐│
│ │ Submitted Data                 | Discovered Data          ││
│ │ • Name: NovaGeo                | • Name: NovaGeo          ││
│ │ • Domain: novageo.io           | • Domain age: 6 months   ││
│ │ • Email: info@novageo.io       | • Email MX mismatch (!)  ││
│ │                                | • WHOIS: Privacy Enabled ││
│ └───────────────────────────────────────────────────────────┘│

│ ┌────────── Signals Table ────────────┐                     │
│ │ Field          | Value       | Status                     │
│ │ Domain Age     | 6 months    | [Suspicious - yellow]      │
│ │ Email Match    | Mismatch    | [Red - mismatch]           │
│ │ Website Lookup | OK          | [Green - match]            │
│ └────────────────────────────────────────────────────────────┘

│ ┌────────── LLM Narrative Summary (Gray Box) ───────────────┐│
│ │ "The company shows moderate risk due to domain age,       ││
│ │  email mismatch, and weak online presence…"               ││
│ └────────────────────────────────────────────────────────────┘│

│ Actions:                                                    │
│ [ Re-run Analysis ] [ Mark Suspicious ] [ Revoke Approval ] │
│ [ Mark Review Complete ] [ Export PDF ] [ Export JSON ]     │
│ [ Upload Document ] [ Restore ] (if deleted)                │

└─────────────────────────────────────────────────────────────┘
```

---

# PAGE 4 — ANALYSIS HISTORY

```
┌───────── Analysis History ─────────┐
│ Version | Date       | Score | View │
│---------------------------------------------------------------│
│   v3    | 2025-01-12 | 68    | [View Report]                 │
│   v2    | 2025-01-03 | 64    | [View Report]                 │
│   v1    | 2024-12-27 | 52    | [View Report]                 │
└──────────────────────────────────────────────────────────────┘
```

---

# PAGE 5 — NOTES TAB

```
┌────────────────────── Notes ────────────────────────────┐
│ [ Add Note ]                                             │
│                                                          │
│ Notes History:                                           │
│ ┌────────────────────────────────────────────────────┐   │
│ │ Jan 12, 2025 - John Doe                            │   │
│ │ "Company provided additional documentation..."     │   │
│ │ [Edit] [Delete]                                    │   │
│ ├────────────────────────────────────────────────────┤   │
│ │ Jan 10, 2025 - Jane Smith                          │   │
│ │ "Called company, verified contact information"     │   │
│ │ [Edit] [Delete]                                    │   │
│ └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

---

# PAGE 6 — DOCUMENTS TAB

```
┌────────────────────── Documents ────────────────────────────┐
│ [ Upload Document ]                                          │
│                                                              │
│ Uploaded Files:                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ filename.pdf (2.3 MB)     | Uploaded: Jan 12 by John    │││
│ │ Type: proof_of_address    | [Download] [Delete]          ││
│ ├──────────────────────────────────────────────────────────┤ │
│ │ business_license.jpg (1.1 MB) | Uploaded: Jan 2 by Jane │││
│ │ Type: business_license    | [Download] [Delete]          ││
│ └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

# PAGE 7 — PDF REPORT LAYOUT

```
┌───────────────────────────────┐
│ SkyFi IntelliCheck Report      │
│ Company: NovaGeo Analytics     │
│ Risk Score: 68 (High Risk)     │
├───────────────────────────────┤
│ Submitted vs Discovered        │
│ Signals Table                  │
│ LLM Narrative Summary          │
│ Full Details Appendix          │
└───────────────────────────────┘
```

---

# PAGE 8 — DOCUMENT UPLOAD MODAL

```
┌──────────────────────────────────────────────┐
│ Upload Supporting Document                   │
│----------------------------------------------│
│ [   Drag & Drop File Here   ]                │
│        OR                                      │
│ [ Choose File ]                                │
│                                                │
│ Document Type: [ dropdown: proof_of_address,  │
│                  business_license, other ]     │
│ Description: [_____________________________]   │
│                                                │
│ [ Upload Document (yellow button) ]            │
└──────────────────────────────────────────────┘
```

---

# PAGE 9 — EMPTY & ERROR STATES

**Empty:**

```
┌───────────────────────────────┐
│ No companies found.           │
│ Try adjusting your filters.   │
└───────────────────────────────┘
```

**Error:**

```
[!] Analysis Failed
Reason: WHOIS lookup timed out.
Failed Checks: WHOIS, MX Validation
Successful Checks: DNS, Website Lookup
[ Retry Analysis ] [ Retry Failed Only ]
```

**Partial Failure:**

```
[!] Analysis Incomplete
Some checks failed but others succeeded.
View partial results below.
[ Retry Failed Checks ] [ Accept Partial Results ]
```

---

# PAGE 10 — MOBILE VIEW SAMPLE

```
┌───── NAV (hamburger menu) ──────┐
│ SkyFi IntelliCheck              │
└──────────────────────────────────┘

SEARCH
[ Company Name ]

FILTERS
[ Status ▼ ]
[ Risk Min: __ Max: __ ]

——————————————
NovaGeo
Risk: 68 (High)
Status: Pending
Analysis: In Progress
——————————————
```

---

# End of Document
