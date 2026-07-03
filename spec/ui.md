# UI

---

## UI Type

Web app in the browser (Next.js 15 + React 19 + Tailwind), statically exported and served at `:8001/app/`. Single-user, no login. A two-region layout: a left/main **chat + analysis** column and a right/secondary **dashboard + history + profile** column. Phase 1 renders the full layout with clearly-labelled NON-FUNCTIONAL stubs for everything not yet built, so the user sees the whole vision.

## Views / Screens

### Screen: Workspace (single page)

**Purpose:** Upload data, ask questions, read streamed answers, review history.

**Key elements (Phase 1 — REAL):**
- **Upload control** — CSV file picker → shows dataset name + row/column count once loaded.
- **Chat panel** — message list (user questions + streamed assistant answers with key numbers), an input box, a **spinner** while the agent works (driven by `status` SSE events).
- **Answer rendering** — plain prose + a simple table when the result is tabular.
- **History panel** — per-dataset list of past runs; expanding one shows the question, the generated code, and the result.
- **Clarify prompt** — when the agent asks a clarifying question, it appears inline and the user answers in the same input.

**Key elements (Phase 1 — labelled NON-FUNCTIONAL stubs, greyed with a "Coming soon" tag):**
- Excel upload, Multi-file select / Compare, Chart area, Dashboard tiles, Profile panel, Data-quality flags, Follow-up suggestion chips, Export buttons.

**Phase 2 (wires stubs to real):** Profile panel (columns/types/ranges/missing values) + data-quality flags appear on upload; interactive Plotly **chart** renders in-answer (hover/zoom/filter, export-as-image); 2-3 **follow-up chips** appear after each answer and are clickable.

**Phase 3 (wires stubs to real):** dataset switcher / multi-select for cross-dataset compare; **Dashboard** view of pinned tiles (reorder/remove) as the primary curated view; **pin** buttons on answers/charts; **export** buttons (cleaned CSV / report); Excel upload with sheet picker.

**Actions available:** upload file; ask question; answer a clarification; expand a history run; (Ph2) click a follow-up, export a chart image; (Ph3) switch/select datasets, pin/unpin/reorder tiles, export CSV/report.

## Error States

- **Upload error** — inline banner (unsupported type, too large, parse failure) with the message from the API.
- **Agent error** — the `error` SSE event renders as a red inline message in the chat; the run is marked failed in history.
- **Loading/streaming** — a spinner with the current phase label (planning / writing code / executing / retrying) until the first token, then tokens stream in.
- **Empty states** — "Upload a CSV to begin" before any dataset; "No history yet" in the history panel.
- **Stub click** — labelled stubs are visibly disabled (not clickable) so they cannot be mistaken for broken features.

## Tech Stack

Next.js 15 + React 19 + Tailwind CSS. SSE consumed via the browser `EventSource`/fetch-stream in `frontend/src/lib/api.ts`. Plotly.js for interactive charts (Phase 2). E2E smoke tests in `frontend/tests/e2e/` with Playwright (required — the Phase gate runs `pnpm exec playwright test` against the real running app covering the primary journey).
