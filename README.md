# Doctor Copilot System — Watan Hospital

An AI-assisted clinical platform for Watan Hospital doctors: a doctor writes
(or dictates) a free-text encounter note, a LangGraph multi-agent pipeline
turns it into structured prescription data, checks it against a Pinecone
drug-interaction knowledge base, and — once safe — prints a prescription
formatted to match the hospital's letterhead. A second chat agent lets
doctors look up a patient's full history and refer patients to colleagues,
gated by a treatment-relationship access-control model. An analytics
dashboard summarizes the doctor's daily volume and safety interventions.

## Architecture

```
doctor-copilot-system/
├── backend/                  FastAPI + LangGraph + Pinecone + Supabase
│   ├── app/
│   │   ├── agents/           LangGraph state, nodes, graph wiring
│   │   │   ├── state.py            GraphState (TypedDict) + factory
│   │   │   ├── extractor.py        Extractor agent (raw text -> structured data)
│   │   │   ├── safety_checker.py   Safety/RAG agent (drug interaction checks)
│   │   │   ├── graph.py            StateGraph: Extractor -> Safety Checker
│   │   │   └── patient_chat_agent.py  Tool-calling ReAct loop for patient lookup/referral
│   │   ├── tools/
│   │   │   └── patient_tools.py    lookup_patient_by_id, lookup_patient_by_name, refer_patient
│   │   ├── api/routes/        FastAPI routers:
│   │   │   ├── prescription.py     create, /stream (SSE), /override (HITL)
│   │   │   ├── chat.py              patient-records chatbot endpoint
│   │   │   ├── analytics.py         doctor dashboard stats
│   │   │   ├── transcription.py     voice-to-text (Whisper via OpenRouter)
│   │   │   └── health.py
│   │   ├── core/              Settings, exception hierarchy, structured logging, Supabase-JWT auth
│   │   ├── models/            Pydantic schemas shared across the API + agents
│   │   └── services/
│   │       ├── pinecone_service.py       drug-interaction vector store
│   │       ├── supabase_service.py       persistence, treatment relationships, dashboard stats
│   │       └── transcription_service.py  Whisper transcription via OpenRouter
│   ├── scripts/                ingest_drug_interactions.py (Pinecone seed data)
│   └── tests/                  pytest suite, 46 tests (LLM + Pinecone + Supabase are all mocked)
│
├── supabase/
│   └── schema.sql              doctors / patients / prescriptions / prescription_overrides /
│                                treatment_relationships / patient_lookup_audit_log + RLS
│
└── frontend/                   Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui
    ├── middleware.ts            Supabase session refresh + route protection
    ├── app/                     Routes: /, /login, /dashboard, /patients, /analytics
    ├── components/
    │   ├── ui/                   shadcn/ui-style primitives (Button, Card, Input...)
    │   ├── prescription/         DashboardClient, PrescriptionForm (SSE + voice dictation),
    │   │                         PrescriptionPreview (HITL override), VoiceRecorderButton
    │   ├── chat/                 PatientChatWidget (patient lookup + referral chatbot)
    │   ├── analytics/             PulseStat, VolumeTraceChart, DiagnosesDonut, RecentActivityLog
    │   ├── theme-provider.tsx    next-themes wrapper
    │   └── theme-toggle.tsx      light/dark mode toggle button
    └── lib/
        ├── api/                  Typed fetch client for the FastAPI backend
        ├── supabase/             Browser + server Supabase clients
        ├── types/                TypeScript types mirroring the backend schemas
        └── pdf/                  PrescriptionPDF.tsx (@react-pdf/renderer print template)
```

## Agent pipeline

1. **Extractor agent** — an LLM with structured output turns the doctor's
   free-text (or dictated) note into a `PrescriptionExtraction` (patient,
   diagnosis, medications, current medications, advice). All prompts,
   inputs, and outputs are English-only by design.
2. **Safety Checker agent (RAG)** — looks up each newly-prescribed
   medication in a Pinecone vector index of known drug interactions and
   checks it against both the other newly-prescribed drugs *and* the
   patient's existing medications. Produces `InteractionWarning`s;
   `high`/`critical` severities block printing until resolved.
3. **Patient Records Chat Agent** — a separate tool-calling ReAct loop
   (`app/agents/patient_chat_agent.py`, via `langgraph.prebuilt.ToolNode` +
   `tools_condition`) that lets a doctor ask natural-language questions
   about a patient ("show me Ahmad Karimi's file") or refer a patient to a
   colleague by email. It never fabricates patient data -- every answer is
   grounded in a real Supabase lookup.

The Extractor/Safety graph is a small `StateGraph` (`app/agents/graph.py`)
so more agents (WebResearcher, MCPToolAgent, Reflection/FactChecker) can be
added as additional nodes without touching the existing ones.

Progress streams live to the UI via `GET /prescriptions/stream` (Server-Sent
Events), and a **human-in-the-loop override** (`POST /prescriptions/override`)
lets the attending physician force-approve a flagged prescription after
recording a mandatory clinical justification — logged to
`prescription_overrides` for audit.

## Treatment relationship access model

Access to a patient's record is **not** granted just by being an
authenticated doctor. A doctor can only view or discuss a patient (via the
chatbot or otherwise) if an active `treatment_relationships` row exists
for that (doctor, patient) pair:

- **Created automatically** the first time a doctor writes a prescription
  for a patient (that visit *is* what establishes the relationship).
- **Shared via referral** — a treating doctor can refer a patient to
  another doctor by email (`refer_patient` tool), creating a `referred`
  relationship for the receiving doctor.
- **Enforced twice**: once by Postgres Row Level Security on `patients`,
  and again in application code in `SupabaseService.get_patient_full_record`
  (since the backend uses the Supabase service-role key, which bypasses
  RLS). Even a "multiple patients matched" disambiguation response only
  ever lists patients within the doctor's own relationships — it never
  reveals the existence of a patient the doctor doesn't treat.
- Every lookup attempt, successful or not, is recorded in
  `patient_lookup_audit_log`.

## Analytics dashboard

`/analytics` shows the doctor's day at a glance: patients seen today,
prescriptions written today, active patients under treatment, safety
warnings today, a 14-day volume trend chart, a diagnoses breakdown, and a
recent-activity log — all computed live from Supabase
(`SupabaseService.get_dashboard_stats`), not mock data. Styled as a dark
"vitals monitor" theme, independent of the app's light/dark toggle.

## Voice-to-text (dictation)

The "Dictate note" button on the prescription form records audio via the
browser's `MediaRecorder` API and sends it to `POST /api/v1/transcribe`,
which forwards it to Whisper through **OpenRouter's audio endpoint**
(`stt_model_name`, default `openai/whisper-1`) — no separate OpenAI account
needed, same `OPENROUTER_API_KEY` as the rest of the app.

> **Known gotcha:** OpenRouter's audio endpoint requires a minimum account
> balance (currently $0.50) before it will accept any request, independent
> of actual per-minute usage cost. If transcription fails with an HTTP 402
> error, add credit at https://openrouter.ai/settings/credits.

## Light/dark mode

A theme toggle (sun/moon button, top-right of every page) switches the
whole app between light and dark via `next-themes` + Tailwind's `class`
strategy + CSS variables (`--background`, `--foreground`, `--card`,
`--border` in `globals.css`). The `/analytics` page is intentionally
excluded — it always renders in its fixed dark "vitals monitor" theme.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in OPENROUTER_API_KEY, PINECONE_API_KEY, SUPABASE_*, etc.
uvicorn app.main:app --reload --port 8000
```

Run the test suite (no real API keys required — the LLM, Pinecone, and
Supabase clients are all mocked):

```bash
pytest -v   # 46 tests
```

Seed the Pinecone drug-interaction index (requires a real `PINECONE_API_KEY`
and `OPENROUTER_API_KEY`, and the index must already exist — create it in
the Pinecone console first with a dimension matching `EMBEDDING_MODEL`,
e.g. 1536 for `openai/text-embedding-3-small`):

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

Visit `http://localhost:3000` → Sign in → write (or dictate) an encounter
note → watch the Extractor and Safety agents run live → review warnings
(override if clinically justified) → print. Visit `/patients` to ask the
records chatbot about a patient or refer them to a colleague, and
`/analytics` for the daily dashboard.

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

**Complete and tested (46/46 backend tests, full frontend build):**
- Sprint 1 — foundation (FastAPI skeleton, Next.js/Tailwind/shadcn skeleton)
- Sprint 2 — Extractor agent (LangGraph, structured output)
- Sprint 3 — Safety/RAG agent + Pinecone query path + ingestion script
- Sprint 4 — Supabase schema/RLS, real auth, live agent-status streaming,
  human-in-the-loop override
- Sprint 5 — print engine matching the letterhead layout
- Sprint 6 — treatment-relationship access model, patient-records chatbot,
  patient referral
- Sprint 7 — analytics dashboard, light/dark theme toggle, voice dictation

**Still open:**
- Real hospital logo / public-health seal / watermark image assets (the
  current ones are vector approximations, not the photographic originals)
- End-to-end verification against a live Supabase + Pinecone + OpenRouter
  project (everything here is unit-tested with mocks, not integration-
  tested against real cloud services)
- Doctor self-registration / profile management UI (schema supports it;
  no UI yet)
- Audit-log viewer UI for `patient_lookup_audit_log` (data is captured;
  no doctor/admin-facing screen yet)
- Real microphone test in a browser (voice dictation is unit-tested on the
  backend only; the OpenRouter audio endpoint also requires a minimum
  account balance — see the gotcha above)
