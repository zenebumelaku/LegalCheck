# LegalCheck Ethiopia

AI-assisted legal compliance auditing platform for Ethiopian businesses, HR professionals, and authorized legal reviewers, grounded in verified Ethiopian statutory sources focusing on **Labour Proclamation No. 1156/2019** and the **Civil Code of Ethiopia (1960)**.

---

## Key Features

1. **Document Compliance Auditing Wizard (`/audits/new`)**
   - 3-step structured wizard: Upload (PDF, DOCX, TXT), Document Information & Scope, and Confirmation.
   - Built-in sample contracts reflecting actual Ethiopian business scenarios (Tech Startup, Manufacturing Plant Operator, Commercial Account Executive).
   - Analysis covers statutory probation period limits (max 60 working days), working hours ceiling (48 hrs/wk), overtime compensation rates (Article 66), statutory maternity leave (120 consecutive days), annual leave (16 working days minimum), non-compete reasonableness (Civil Code Art. 2589), and mandatory PPE.

2. **Audit Findings & Reports (`/audits/:id`)**
   - Issue severity categorization: Critical, High, Medium, Low, Informational.
   - Distinct finding types: Potential Legal Conflict, Missing or Incomplete Clause, Outdated Legal Reference, Informational Observation.
   - Clause excerpts contrasted side-by-side with official Proclamation text and Negarit Gazeta citations.
   - Instant Client-side PDF Report Generation (`jspdf`).
   - "View Legal Source" modal providing full English and Amharic Gazette statutory wording.
   - "Report Inaccuracy" feedback workflow.

3. **Verified Ethiopian Legal Sources (`/legal-sources`)**
   - Full repository of Labour Proclamation No. 1156/2019, Civil Code Title XVI, and Commercial Registration No. 980/2016.
   - Annotated status badges: *In Force*, *Partially Amended*, *Repealed/Superseded* (Proclamation No. 377/2003).
   - Provenance tracking including legislative publisher, Federal Negarit Gazeta volume, and verification records.

4. **Dashboard & History (`/dashboard`, `/audits`)**
   - Verified audit metrics (total audits, completed, critical issues flagged, awaiting queue).
   - Search by document name and description, filters by audit status and type, sorting by date or finding count.

5. **Authentication & Governance (`/login`, `/register`, `/forgot-password`, `/settings`, `/profile`)**
   - Organization registration with company name and designated compliance role.
   - Configurable document data retention cycles (30 days, 90 days, 1 year, indefinite).
   - Secure session handling.

---

## Tech Stack

- **Framework**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS v4 + Plus Jakarta Sans typography
- **Icons**: Lucide React
- **PDF Generation**: jsPDF
- **API Architecture**: Centralized typed client with FastAPI integration and resilient offline/standalone fallback

---

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm

### Installation

```bash
# Clone the repository and install dependencies
npm install
```

### Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Configure your backend URL if connecting to an external FastAPI backend:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# or
VITE_API_BASE_URL=http://localhost:8000
```
*(If left blank, LegalCheck Ethiopia operates in resilient standalone mode with pre-seeded audits and client-side analysis).*

### Running Development Server

```bash
npm run dev
```

The app will be accessible at `http://localhost:3000`.

### Building for Production

```bash
npm run build
```

---

## Legal Notice

LegalCheck Ethiopia provides automated legal compliance intelligence based on Labour Proclamation No. 1156/2019. It does not constitute formal legal counsel, attorney-client privilege, or representation by licensed Ethiopian advocates.
