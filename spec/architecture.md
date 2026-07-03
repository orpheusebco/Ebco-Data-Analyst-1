# Architecture

---

## System Overview

A single-process local web application. A Next.js browser UI talks to a FastAPI backend over REST + Server-Sent Events. The backend loads uploaded CSV/Excel files fully into an in-process pandas registry, and for each natural-language question runs a LangGraph agent that plans, generates pandas code with Gemini, executes it locally (no sandbox) against the in-memory DataFrames, inspects the result, and retries on failure. Answers stream token-by-token to the UI. All runs (query + generated code + result), dataset metadata, profiles, and pinned dashboard items are persisted in SQLite. Only the question, column schema, and small samples are ever sent to the LLM.

## Component Map

```
[Next.js UI (browser)]
        │  REST + SSE
        ▼
[FastAPI app] ──────────► [Gemini API]   (schema + samples only)
        │
        ├─► [Dataset Registry]  (in-memory pandas DataFrames, keyed by dataset_id)
        │
        ├─► [LangGraph Agent]  ──► [Local Python Executor]  (runs pandas, NO sandbox)
        │
        └─► [SQLite via SQLAlchemy]  (datasets, runs, profiles, pinned items)
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API (`src/api/`) | REST endpoints + SSE streaming; request validation; router registration |
| Agent (`src/graph/`) | LangGraph state, nodes, edges, runner — the plan/write/execute/inspect/retry loop |
| Analysis (`src/analysis/`) | Local code executor, profiler, chart-spec builder, exporters |
| Datasets (`src/datasets/`) | In-memory registry: load CSV/Excel, hold DataFrames, expose schema + samples |
| LLM (`src/llm/`) | Gemini client (already wired) |
| Storage (`src/db/`) | SQLAlchemy models + session; Alembic migrations |
| Observability (`src/observability/`) | Structured logging of prompts, generated code, execution results, latency |

## Data Flow

1. Trigger: user uploads a file (`POST /datasets`) → registry loads it into a pandas DataFrame; a `Dataset` row is persisted. (Phase 2+: profiling node runs on upload.)
2. User asks a question (`POST /ask`, SSE) with `dataset_id`(s) + question text.
3. Runner creates a `Run` row, builds `AgentState` (question, schema, samples, conversation history), invokes the graph.
4. Graph: `plan` → `write_code` → `execute` → `inspect` → (retry `write_code` on failure, up to N) → (`clarify` if ambiguous) → `narrate` (streams answer) → (Phase 2+: `chart`, `suggest_followups`) → `finalize`.
5. Output: streamed plain-language answer + key numbers (+ chart JSON + follow-ups in later phases); the `Run` row is updated with generated code, result, status.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Gemini API | Plan, generate pandas, narrate answer, pick chart, suggest follow-ups | Retry with backoff; after N failures set `state.error`, surface a clear error in the stream, mark run failed |
| SQLite (local file) | Persist datasets, runs, profiles, pinned items | Fatal — surface 500; app cannot run without it |
| Local filesystem | Uploaded files + exported files under `data/` | Surface 400/500 with clear message |

## Stack

- **Language:** Python 3.12 (backend), TypeScript (frontend)
- **Agent framework:** LangGraph (multi-node loop with conditional retry/clarify edges)
- **LLM provider + model:** Google Gemini via `AGENT_GEMINI_API_KEY`; **flash-only** — every agent node defaults to `gemini-2.5-flash` (`MODEL_NODE_DEFAULT = MODEL_FLASH_DEFAULT` in `src/graph/nodes.py`). `gemini-2.5-pro` is intentionally not used (flash cuts latency ~2.25x; the execute→inspect→retry loop self-corrects codegen slips). Env-configurable via `AGENT_LLM_MODEL` (overrides all nodes); provider auto-detected
- **Backend:** FastAPI (with SSE streaming via `StreamingResponse`)
- **Database + ORM:** SQLite + SQLAlchemy 2.0 + Alembic
- **Frontend:** Next.js 15 + React 19 + Tailwind (static-exported, served at `:8001/app/`)
- **Dependency management:** uv + pyproject.toml (backend); pnpm (frontend)

| Key library | Version | Purpose |
|-------------|---------|---------|
| pandas | ^2.2 | Local data loading + analysis |
| openpyxl | ^3.1 | Excel (.xlsx) ingestion (Phase 3) |
| numpy | (pandas dep) | Numeric ops available to generated code |
| plotly | ^5.24 | Chart-spec JSON generation (Phase 2) |
| google-genai | (already present) | Gemini client |
| langgraph | (already present) | Agent graph |
| fastapi / sqlalchemy / alembic | (already present) | API + storage |
| Playwright | ^1.48 | Frontend E2E smoke tests |

> **Assumed:** Gemini model ID `gemini-2.5-flash` (not specified in the brief) is used for all nodes; overridable via `AGENT_LLM_MODEL`. `gemini-2.5-pro` is deliberately unused (see flash-only invariant above).

**Avoid:** any code-sandbox library (explicitly out of scope — trusted local machine); any cloud object storage; SQLAlchemy async engine (keep the sync session the skeleton already uses); sending full DataFrames or full columns to the LLM.

## Deployment Model

Long-running local single-process service started with `uv run python -m src` (serves API + static frontend on `:8001`). Single user, no auth, no container required. Datasets live in memory for the process lifetime; metadata/runs/pins persist in SQLite across restarts (DataFrames must be re-uploaded after a restart — an accepted limitation).

> **Assumed:** in-memory DataFrame registry is not rehydrated on restart; the user re-uploads files after restarting the process. This keeps Phase 1 simple and matches the single-session workflow in the brief.
