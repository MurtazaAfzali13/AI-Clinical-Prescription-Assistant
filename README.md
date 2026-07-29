# Doctor Copilot System — Watan Hospital

An AI-assisted prescription platform: a doctor writes a free-text encounter
note in English, a LangGraph multi-agent pipeline turns it into structured
prescription data, checks it against a Pinecone drug-interaction knowledge
base, and — once safe — prints a prescription formatted to match the Watan
Hospital letterhead.

## Architecture

```
doctor-copilot-system/
├── backend/                  FastAPI + LangGraph + Pinecone + Supabase
│   ├── app/
│   │   ├── agents/           LangGraph state, nodes, graph wiring
│   │   │   ├── state.py          GraphState (TypedDict) + factory
│   │   │   ├── extractor.py      Extractor agent (raw text -> structured data)
│   │   │   ├── safety_checker.py Safety/RAG agent (drug interaction checks)
│   │   │   └── graph.py          StateGraph: Extractor -> Safety Checker
│   │   ├── api/routes/       FastAPI routers (prescriptions incl. stream + override, health)
│   │   ├── core/             Settings, exception hierarchy, structured logging, Supabase-JWT auth
│   │   ├── models/           Pydantic schemas shared across the API + agents
│   │   └── services/         Pinecone client wrapper, Supabase persistence wrapper
│   ├── scripts/               ingest_drug_interactions.py (Pinecone seed data)
│   └── tests/                 pytest suite (LLM + Pinecone + Supabase are mocked)
│
├── supabase/
│   └── schema.sql             doctors / patients / prescriptions / prescription_overrides + RLS
│
└── frontend/                 Next.js 14 (App Router) + TypeScript + Tailwind
    ├── middleware.ts          Supabase session refresh + /dashboard route protection
    ├── app/                   Routes: /, /login (real Supabase auth), /dashboard
    ├── components/
    │   ├── ui/                 shadcn/ui-style primitives (Button, Card, Input...)
    │   └── prescription/       DashboardClient, PrescriptionForm (SSE streaming), PrescriptionPreview (HITL override)
    └── lib/
        ├── api/                Typed fetch client for the FastAPI backend
        ├── supabase/           Browser + server Supabase clients
        ├── types/              TypeScript types mirroring the backend schemas
        └── pdf/                PrescriptionPDF.tsx (@react-pdf/renderer print template)
```

## Agent pipeline

1. **Extractor agent** — an LLM with structured output turns the doctor's
   free-text note into a `PrescriptionExtraction` (patient, diagnosis,
   medications, advice). All prompts, inputs, and outputs are English-only
   by design.
2. **Safety Checker agent (RAG)** — looks up each extracted medication in a
   Pinecone vector index of known drug interactions and produces
   `InteractionWarning`s. `high`/`critical` severities block printing until
   resolved.

The graph is a small `StateGraph` (`app/agents/graph.py`) so more agents
(WebResearcher, MCPToolAgent, Reflection/FactChecker) can be added as
additional nodes without touching the existing ones.

Progress streams live to the UI via `GET /prescriptions/stream` (Server-Sent
Events), and a **human-in-the-loop override** (`POST /prescriptions/override`)
lets the attending physician force-approve a flagged prescription after
recording a mandatory clinical justification — logged to
`prescription_overrides` for audit.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY, PINECONE_API_KEY, SUPABASE_*, etc.
uvicorn app.main:app --reload --port 8000
```

Run the test suite (no real API keys required — the LLM, Pinecone, and
Supabase clients are all mocked):

```bash
pytest -v
```

Seed the Pinecone drug-interaction index (requires real `PINECONE_API_KEY`
and `OPENAI_API_KEY`):

```bash
python -m scripts.ingest_drug_interactions
```

### Database (Supabase)

Create a Supabase project, then run `supabase/schema.sql` in the SQL editor
(or `supabase db push` if using the CLI). Copy the project URL, anon key,
service-role key, and JWT secret into `backend/.env` and
`frontend/.env.local`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Visit `http://localhost:3000` → Sign in → write an encounter note → watch
the Extractor and Safety agents run live → review warnings (override if
clinically justified) → print.

> Without `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` set,
> both the backend and frontend fall back to a demo doctor so the pipeline
> stays fully usable without a database.

## Matching the letterhead exactly

`lib/pdf/PrescriptionPDF.tsx` reproduces the Watan Hospital prescription
layout: a curved teal header band (SVG wave), patient info row, diagnosis,
medications table, advice, signature line, curved footer, and a caduceus-
style watermark. The hospital's actual logo and public-health seal are
photographic graphics that can't be hand-recreated as vector code without
losing fidelity — swap in the real files and update the header/footer
markup to use `<Image>` once you have them.

## What's complete vs. still open

**Complete and tested:**
- Sprint 1 — foundation (FastAPI skeleton, Next.js/Tailwind/shadcn skeleton)
- Sprint 2 — Extractor agent (LangGraph, structured output)
- Sprint 3 — Safety/RAG agent + Pinecone query path + ingestion script
- Sprint 4 — Supabase schema/RLS, real auth, live agent-status streaming,
  human-in-the-loop override
- Sprint 5 — print engine matching the letterhead layout

**Still open:**
- Real hospital logo / public-health seal / watermark image assets (the
  current ones are vector approximations, not the photographic originals)
- End-to-end verification against a live Supabase + Pinecone + OpenAI
  project (everything here is unit-tested with mocks, not integration-
  tested against real cloud services)
- Doctor self-registration / profile management UI (schema supports it;
  no UI yet)

