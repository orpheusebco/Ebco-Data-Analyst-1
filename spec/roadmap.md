# Roadmap

---

## What This Agent Does

A personal, single-user data-analysis agent. One power user uploads CSV/Excel files (up to ~100 MB) and explores them through natural-language questions. A session is: upload one or several files, then ask many questions — including comparisons across multiple loaded datasets. The agent is genuinely agentic: for each question it plans a strategy, writes Python/pandas, runs it locally, inspects the result, and retries with a different approach on failure — asking a clarifying question only when the request is genuinely ambiguous. Datasets and conversation history persist across turns. Answers stream back in plain language with key numbers, and every query + the code it ran + the result is stored as full run history in the database, organized per dataset.

## Who Uses It

A single technical power user (data analyst / engineer) running the tool locally on their own trusted machine. No authentication, no multi-tenancy. They already know their data and want fast, conversational exploration without writing pandas by hand.

## Core Problem Being Solved

Ad-hoc data exploration today means repeatedly writing, running, and debugging pandas snippets in a notebook. This agent replaces that loop with natural-language questions answered by an autonomous write-code / run / inspect / retry cycle, keeping a curated dashboard and a full audit trail of every analysis.

## Success Criteria

- [ ] A user can upload one CSV and get a correct, streamed plain-language answer (with key numbers) to a natural-language question within ~30s, on the first try.
- [ ] The agent iterates automatically: when generated pandas raises an error, it inspects the error and retries a different approach without user intervention (observable in run history — >1 code attempt on a failing first try).
- [ ] Every query, the exact generated code, and the result are persisted to the DB and viewable per dataset.
- [ ] Conversation history carries across turns — a follow-up question that references "that result" or "those rows" is answered in context.
- [ ] Only the question + column schema + small samples are sent to the LLM; the full dataset is analyzed locally and never uploaded in bulk (verifiable in logged LLM payloads).

## What This Agent Does NOT Do (Out of Scope)

- No sandboxing of generated Python — it runs directly on the trusted local machine (explicit design choice).
- No authentication, user accounts, or multi-user isolation.
- No cloud deployment or horizontal scaling — local single-process only.
- No datasets that do not fit in local memory (hard ceiling ~100 MB CSV / a few GB RAM).
- No scheduled / automated pipelines — every analysis is user-triggered.
- No write-back to source systems or external databases; outputs are answers, charts, and exported files only.
- No fine-tuning or training; the LLM is used only for code generation and narration.

## Key Constraints

- **LLM:** Google Gemini via `AGENT_GEMINI_API_KEY` (already in `.env`). Provider auto-detected by the skeleton.
- **Data privacy:** only question + schema + small samples (≤ ~20 rows) leave the machine; full data analyzed locally.
- **Latency:** answers within ~30s acceptable.
- **Scale:** CSV/Excel up to ~100 MB, loaded fully into memory.
- **Execution:** generated Python runs with NO sandbox — trusted local machine, keep it simple.
- **Trust bar:** production-grade correctness, error handling, and observability from day one.

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** Real end-to-end on ONE path. Everything else ships as a clearly-labelled NON-FUNCTIONAL stub in the Phase 1 UI so the user sees the vision without mistaking a stub for a bug.

### Phase 1 — Ask One CSV

- **Goal:** Upload one CSV → ask one natural-language question → the LangGraph agent runs its full plan → write-pandas → execute → inspect → retry loop (real Gemini, real local pandas, NO sandbox) → streams back a plain-language answer with key numbers → the run (query + generated code + result) is saved to per-dataset history in the DB. Conversation history carries across turns for the loaded dataset.
- **Independent slices (parallel build units):**
  - `backend-core` (backend) — dataset load/registry, LangGraph agentic loop (plan/write-code/execute/inspect/retry/clarify), run persistence, conversation memory. deps: none.
  - `backend-api` (backend) — upload endpoint, streaming ask endpoint (SSE), history + datasets read endpoints. deps: none (codes against the state/runner interfaces defined in `agent.md`/`api.md`; both slices owned by the same generator if seams overlap, else split on file paths below).
  - `frontend` (frontend) — chat panel with streaming answer + spinner, upload control (CSV), history panel; labelled NON-FUNCTIONAL stubs for: Excel upload, multi-file compare, charts, dashboard, auto-profiling, data-quality flags, follow-up suggestions, exports. deps: none (mocks the API shape from `api.md`).
- **Key surfaces / files:**
  - `backend-core`: `src/graph/state.py`, `src/graph/nodes.py`, `src/graph/agent.py`, `src/graph/edges.py`, `src/graph/runner.py`, `src/prompts/*.md`, `src/datasets/store.py`, `src/analysis/executor.py`, `src/db/models.py`, `alembic/versions/*`.
  - `backend-api`: `src/api/datasets.py`, `src/api/ask.py`, `src/api/history.py`, `src/__main__.py` (router registration), `src/domain/*.py`.
  - `frontend`: `frontend/src/app/page.tsx`, `frontend/src/components/*`, `frontend/src/lib/api.ts`, `frontend/tests/e2e/*`.
- **Gate command:** `uv run alembic upgrade head; uv run pytest -q; cd frontend && pnpm build && pnpm exec playwright test`
  - The pytest suite MUST include a real end-to-end test: upload a fixture CSV (≥ 50k rows so a sampled answer differs observably from a full-data answer) → POST an aggregation question → assert the streamed answer contains the correct full-data number → assert a `Run` row persisted with non-empty generated code and result. Runs against real Gemini via `.env` and the sqlite production driver.
- **How the user tests it (handoff seed):** Run `uv run alembic upgrade head` then `uv run python -m src`; build the frontend once with `cd frontend && pnpm build`. Open `http://localhost:8001/app/`. Upload a CSV. Type a question (e.g. "What is the average of column X grouped by column Y?"). Watch the spinner then the streamed answer with numbers appear. Ask a follow-up referencing the prior answer — it stays in context. Open the History panel to see the query, generated code, and result. Everything greyed/labelled "Coming soon" (Excel, Compare, Charts, Dashboard, Profiling, Data-quality, Follow-ups, Export) is a NON-FUNCTIONAL stub, not a bug.

### Phase 2 — Understand & Visualize

- **Goal:** On upload the agent auto-profiles the dataset and flags data-quality issues; answers can return interactive charts (agent picks the type); after each answer the agent suggests 2-3 follow-up questions.
- **Capabilities:** `dataset_profiling`, `interactive_charts`, `followup_suggestions`.
- **Independent slices (parallel build units):**
  - `backend-profiling` (backend) — profiling + data-quality node run on upload; persists a `DatasetProfile`. deps: none.
  - `backend-charts` (backend) — chart-spec node produces Plotly JSON; follow-up-suggestions node. deps: none (new nodes/edges added to the graph; disjoint from profiling files).
  - `frontend` (frontend) — profile/quality panel, interactive Plotly chart render (zoom/filter/hover, export-as-image), follow-up suggestion chips. deps: none (API shapes from `api.md`).
- **Key surfaces / files:**
  - `backend-profiling`: `src/analysis/profiler.py`, `src/graph/nodes.py` (profile node), `src/db/models.py` (+`DatasetProfile`), `alembic/versions/*`, `src/api/datasets.py` (profile in response).
  - `backend-charts`: `src/analysis/charts.py`, `src/graph/nodes.py` (chart + followup nodes), `src/prompts/chart.md`, `src/prompts/followups.md`, `src/api/ask.py` (chart + followups in stream).
  - `frontend`: `frontend/src/components/ProfilePanel.tsx`, `frontend/src/components/ChartView.tsx`, `frontend/src/components/FollowUps.tsx`, `frontend/tests/e2e/*`.
- **Gate command:** `uv run alembic upgrade head; uv run pytest -q; cd frontend && pnpm build && pnpm exec playwright test`
  - pytest MUST: assert upload of the fixture CSV returns a profile with correct column count/types/null counts and ≥1 data-quality flag; assert a "plot / trend" question returns valid Plotly JSON with the expected chart type; assert an answer response includes 2-3 follow-up strings. Real Gemini, sqlite driver.
- **How the user tests it (handoff seed):** Upload a CSV — a profile panel (columns, types, ranges, missing values) and data-quality flags appear immediately. Ask a question that implies a trend/distribution — an interactive chart renders (hover/zoom/filter, export-as-image button works). After each answer, 2-3 clickable follow-up chips appear; clicking one asks it. Dashboard, Compare, Export, Excel remain labelled stubs.

### Phase 3 — Compare, Curate & Export

- **Goal:** Load multiple datasets and ask cross-dataset comparison questions; pin charts/answers to a persistent curated dashboard (the primary view); export cleaned CSVs and reports; upload Excel files.
- **Capabilities:** `multi_dataset_compare`, `pinnable_dashboard`, `exports`, `excel_upload`.
- **Independent slices (parallel build units):**
  - `backend-multi-excel` (backend) — multi-dataset registry + comparison context in the graph; Excel ingestion (openpyxl, sheet selection). deps: none.
  - `backend-dashboard-export` (backend) — pin/unpin persistence, dashboard read; cleaned-CSV + report export generation. deps: none (disjoint files from multi-excel).
  - `frontend` (frontend) — dataset switcher / multi-select for compare, dashboard view (pinned tiles, reorder/remove), pin buttons, export buttons, Excel upload + sheet picker. deps: none.
- **Key surfaces / files:**
  - `backend-multi-excel`: `src/datasets/store.py` (multi + Excel loader), `src/graph/nodes.py` (multi-dataset context), `src/api/datasets.py` (Excel + sheet params).
  - `backend-dashboard-export`: `src/api/dashboard.py`, `src/api/exports.py`, `src/db/models.py` (+`PinnedItem`), `src/analysis/export.py`, `alembic/versions/*`.
  - `frontend`: `frontend/src/components/DatasetSwitcher.tsx`, `frontend/src/components/Dashboard.tsx`, `frontend/src/components/ExportBar.tsx`, `frontend/src/components/ExcelUpload.tsx`, `frontend/tests/e2e/*`.
- **Gate command:** `uv run alembic upgrade head; uv run pytest -q; cd frontend && pnpm build && pnpm exec playwright test`
  - pytest MUST: load two fixture datasets and assert a comparison question returns a correct cross-dataset number; upload a fixture `.xlsx` and assert it loads with correct schema; pin an item and assert it persists and is returned by the dashboard endpoint; export a cleaned CSV and assert the file content is correct. Real Gemini, sqlite driver.
- **How the user tests it (handoff seed):** Upload two CSVs (and an `.xlsx`), select both, ask "compare average X between dataset A and dataset B" — get a cross-dataset answer. Pin an answer/chart; it appears on the Dashboard view and survives a page reload. Click Export to download a cleaned CSV / report. No labelled stubs remain — every surface is functional.
