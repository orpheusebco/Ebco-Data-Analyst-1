# API

---

## API Style

REST + Server-Sent Events (SSE) over FastAPI. Served at `:8001`; the static frontend is served at `:8001/app/`. No authentication (single-user local tool). All responses use the skeleton's `ok(...)` envelope except the SSE stream.

## Endpoints / Commands

### `POST /datasets`  (Phase 1: CSV; Phase 3: + Excel)

**Purpose:** Upload a file, load it into the in-memory registry, persist a `Dataset` row (Phase 2: also profile it).

**Request:** `multipart/form-data` — `file` (the CSV/XLSX), optional `sheet` (Excel, Phase 3).

**Response:**
```json
{ "dataset_id": "uuid", "name": "sales.csv", "kind": "csv",
  "row_count": 50000, "column_count": 12,
  "profile": null }
```
(`profile` populated in Phase 2.)

**Error cases:** 400 unreadable/oversize file or unsupported type; 413 over ~100 MB; 500 load failure.

### `GET /datasets`

**Purpose:** List loaded datasets (for the dataset switcher).
**Response:** `{ "datasets": [ { "dataset_id", "name", "kind", "row_count", "column_count" } ] }`

### `POST /datasets/excel/sheets`

**Purpose:** Inspect an uploaded Excel workbook and return its sheet names so the client can show the Excel sheet picker before committing to a `POST /datasets` upload.

**Request:** `multipart/form-data` — `file` (the .xlsx).
**Response:** `{ "sheets": ["Sheet1", "Sheet2", ...] }`

### `GET /datasets/{dataset_id}/profile`

**Purpose:** Return the persisted `DatasetProfile` for a dataset (columns + quality flags) for the profile panel.
**Response:** `{ "profile": { "row_count", "column_count", "columns": [...], "quality_flags": [...] } }`

### `POST /ask`  (SSE stream)

**Purpose:** Ask a natural-language question against one (Ph1) or several (Ph3) datasets; runs the agent and streams the answer.

**Request:**
```json
{ "dataset_ids": ["uuid"], "question": "average revenue by region?" }
```

**Response:** `text/event-stream`. Event types:
- `token` — `{ "text": "..." }` incremental answer text
- `status` — `{ "phase": "planning|writing_code|retrying|executing|inspecting|narrating|charting" }` drives the spinner. `write_code` emits `writing_code` on the first attempt and `retrying` on subsequent attempts; `chart` emits `charting`. (`clarify`/`followups` are their own event types, not `status` phases.)
- `clarify` — `{ "question": "..." }` when the agent needs clarification
- `chart` (Ph2) — `{ "spec": { plotly json } }`
- `followups` (Ph2) — `{ "items": ["...", "..."] }`
- `done` — `{ "run_id": "uuid", "status": "completed|failed|needs_clarification" }`
- `error` — `{ "message": "..." }`

**Error cases:** 400 unknown `dataset_id` or empty question; 500 fatal agent error (also emitted as an `error` SSE event).

### `GET /datasets/{dataset_id}/runs`

**Purpose:** Per-dataset run history (query + code + result).
**Response:** `{ "runs": [ { "run_id", "question", "code", "result_text", "answer", "status", "created_at" } ] }`

### `GET /runs/{run_id}`

**Purpose:** Full detail of one run (existing skeleton endpoint, extended with the new fields).

### `POST /runs/{run_id}/pin`  (Phase 3)
**Purpose:** Pin a run's answer/chart to the dashboard. **Request:** `{ "title": "..." }`. **Response:** the `PinnedItem`.

### `GET /dashboard`  (Phase 3)
**Purpose:** Ordered pinned items. **Response:** `{ "items": [ PinnedItem ... ] }`.
### `DELETE /dashboard/{item_id}` / `PATCH /dashboard/{item_id}` (Phase 3) — unpin / reorder.

### `POST /runs/{run_id}/export`  (Phase 3)
**Purpose:** Export the run's cleaned data / report. **Request:** `{ "format": "csv|report" }`. **Response:** file download (from `data/exports/`).

## Authentication

None. Single-user, local, no auth by design (see roadmap out-of-scope). The Gemini key is read from `.env`, never exposed to the client.
