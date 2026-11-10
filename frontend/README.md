# LegalCheck Ethiopia

Frontend for the LegalCheck Ethiopia application. It connects to the existing
FastAPI backend for authentication, legal questions, legal-source records, and
source-grounded legal research actions. The repository does not include a
verified legal corpus; displayed legal results depend on source records that
have been independently verified and made eligible in the backend.

---

## Key Features

The frontend includes the legal Q&A page, legal-source views, and workspace
settings. Backend API responses are distinct from any demo or sample content.
Demo output is illustrative and must not be treated as verified legal
analysis. Actual source availability, authority, and applicability are
determined by backend source records and review status.

The backend combines semantic and keyword retrieval, then applies configured
reranking before answer generation. It validates citations against eligible
evidence and caches successful answers with their source references in Redis;
valid cache hits return the answer and references without repeating retrieval
or generation. Hybrid retrieval is the default. Cross-encoder reranking is
opt-in and requires `LEGAL_RERANKER_ENABLED=true` with a configured local model
at `LEGAL_RERANKER_MODEL_PATH`; when it is unavailable, retrieval keeps the
hybrid-fused ordering. Cache keys account for knowledge-base content and the
answer and retrieval settings, including reranker configuration.

The local development configuration has hybrid retrieval and Redis caching
enabled. Cross-encoder reranking is optional and is only applied when a local
reranker model is configured; otherwise candidates retain their hybrid fused
ranking. A competition deployment that requires cross-encoder reranking must
provide and configure that model before claiming reranking is active.

---

## Tech Stack

- **Framework**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS v4 + Plus Jakarta Sans typography
- **Icons**: Lucide React
- **PDF Generation**: jsPDF
- **API Architecture**: Centralized FastAPI client; local sample analysis is available only through explicit demo-mode opt-in

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

Configure your backend URL if connecting to the FastAPI backend:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# or
VITE_API_BASE_URL=http://localhost:8000
```

Enable the legacy demo-only local analysis path only when you intentionally want
offline sample data for UI testing:
```env
NEXT_PUBLIC_ENABLE_DEMO_FALLBACK=true
# or
VITE_ENABLE_DEMO_FALLBACK=true
```

*Without this flag, the frontend calls the real backend APIs and does not silently replace failed requests with mock data.*

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

LegalCheck is not legal advice, does not establish that a source is current or
applicable, and does not replace review by a qualified Ethiopian legal
professional. No legal accuracy or verified-corpus claim is made by this
frontend. Synthetic demo rules and sample contracts are not evidence of
Ethiopian law.
