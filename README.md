# Data-Analysis Agent

A personal, single-user data-analysis agent. Upload a CSV and explore it through
natural-language questions. For each question the agent plans a strategy, writes
pandas, runs it locally against the full dataset (no sandbox), inspects the
result, and retries a different approach on failure — streaming back a
plain-language answer with the key numbers. Every question, the exact generated
code, and the result are stored as per-dataset run history. Conversation history
carries across turns.

Only the question + column schema + a small (<=20-row) sample ever reach the LLM
(Google Gemini). The full data is analysed locally and never uploaded in bulk.

- **Stack:** FastAPI + LangGraph + SQLAlchemy/SQLite + Google Gemini (`google-genai`) + pandas.
- **Served at:** `http://localhost:8001` (API) and `http://localhost:8001/app/` (UI).

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for Python dependency management.
- A Google Gemini API key.
- Node + [pnpm](https://pnpm.io/) to build the frontend (served statically by FastAPI).

## Setup

All commands run from the repository root.

```bash
# 1. Configure secrets — set the Gemini key (never commit .env).
cp .env.example .env
#   edit .env and set: AGENT_GEMINI_API_KEY=<your key>

# 2. Install Python dependencies (incl. dev extras for tests).
uv sync --extra dev

# 3. Create / migrate the database.
uv run alembic upgrade head
uv run alembic current          # should print the head revision id

# 4. Build the frontend once (static export served at /app/).
cd frontend && pnpm install && pnpm build && cd ..
```

## Run

```bash
uv run python -m src            # serves FastAPI + the built UI on :8001
```

Then open `http://localhost:8001/app/`, upload a CSV, and ask a question.

| URL | What |
|-----|------|
| `http://localhost:8001/app/` | UI — upload + chat + history |
| `http://localhost:8001/health` | Health check |
| `http://localhost:8001/docs` | Swagger API docs |

## Configuration (`.env`, prefix `AGENT_`)

| Var | Default | Purpose |
|-----|---------|---------|
| `AGENT_GEMINI_API_KEY` | — | Gemini API key (required) |
| `AGENT_LLM_MODEL` | `gemini-2.5-pro` | Overrides the model for all nodes |
| `AGENT_DATABASE_URL` | `sqlite:///./data/agent.db` | Metadata / run history store |
| `AGENT_MAX_ATTEMPTS` | `4` | Write-code/execute retry cap |
| `AGENT_HISTORY_TURNS` | `12` | Conversation-history window replayed to the LLM |

## API (Phase 1)

- `POST /datasets` — multipart CSV upload → `{dataset_id, name, kind, row_count, column_count, profile: null}`.
- `GET /datasets` — list loaded datasets.
- `POST /ask` — SSE stream (`text/event-stream`); events: `status {phase}`, `token {text}`, `clarify {question}`, `done {run_id, status}`, `error {message}`. Request: `{dataset_ids: [id], question}`.
- `GET /datasets/{dataset_id}/runs` — per-dataset run history.
- `GET /runs/{run_id}` — full run detail.

All non-SSE responses use the `{ "data": ..., "error": ... }` envelope.

## Tests

Tests run against the **real** Gemini API using the key in `.env` and the SQLite
production driver — there is no stubbed LLM path.

```bash
uv run pytest -q                       # full suite (real Gemini; needs AGENT_GEMINI_API_KEY)
uv run pytest tests/unit -q            # fast, no API key required
```

The suite includes a real end-to-end test that uploads a >=50,000-row CSV and
asserts the streamed answer contains the correct FULL-data aggregate (which
differs from any head-sample answer), plus a persisted `Run` row with non-empty
generated code and result.

## Project layout

```
src/
  api/            FastAPI routers: health, datasets, ask (SSE), history, runs
  analysis/       executor.py — runs generated pandas, captures errors (no sandbox)
  datasets/       store.py — in-memory DataFrame registry + schema/sampling
  graph/          LangGraph: state, nodes, edges, agent, runner
  prompts/        plan / write_code / inspect / narrate / clarify (.md)
  db/             SQLAlchemy models + session
  llm/            provider-agnostic client + gemini/anthropic providers (streaming)
  observability/  structured stdout logging (one context per run)
alembic/          migrations
tests/            unit / integration / e2e
frontend/         Next.js static export, served at /app/
```
