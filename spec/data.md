# Data Model

---

## Storage Technology

SQLite (local file, `AGENT_DATABASE_URL`, default `sqlite:///./data/agent.db`) via SQLAlchemy 2.0 + Alembic. Chosen because this is an explicitly single-user, single-machine tool. The full DataFrames live in an in-memory registry (not the DB); SQLite stores only metadata, run history, profiles, and pins. Uploaded raw files and exports live on the local filesystem under `data/`.

## Entities

### Entity: Dataset
A single uploaded file loaded into the in-memory registry.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (uuid) | yes | Primary key; the `dataset_id` used everywhere |
| name | str | yes | Original filename |
| source_path | str | yes | Local path of the stored upload under `data/uploads/` |
| kind | str | yes | `csv` or `xlsx` |
| sheet | str \| null | no | Excel sheet name (Phase 3) |
| row_count | int | yes | Number of rows loaded |
| column_count | int | yes | Number of columns |
| created_at | datetime | yes | Upload time |

### Entity: Run
One natural-language question and its full agentic execution trail. Organized per dataset.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (uuid) | yes | Primary key |
| dataset_ids | str (JSON array) | yes | Datasets in scope (1 in Ph1, N in Ph3) |
| question | str | yes | The user's natural-language question |
| plan | str \| null | no | Strategy from the plan node |
| code | str \| null | no | Final generated pandas code |
| attempts | int | yes | Number of write-code/execute attempts |
| result_text | str \| null | no | String/JSON rendering of the execution result |
| answer | str \| null | no | Streamed plain-language answer |
| chart_spec | str \| null (JSON) | no | Plotly JSON (Phase 2) |
| followups | str \| null (JSON array) | no | Suggested follow-ups (Phase 2) |
| clarifying_question | str \| null | no | Set when status is needs_clarification |
| status | str | yes | `pending` \| `completed` \| `failed` \| `needs_clarification` |
| error_message | str \| null | no | Set on failure |
| created_at | datetime | yes | Run start |
| completed_at | datetime \| null | no | Run end |

### Entity: Turn (conversation memory)
A single message in the per-dataset conversation. (May be stored as rows or as a JSON `messages` column on a `Conversation` keyed by dataset scope — implementation choice; the spec requires cross-turn context to persist.)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (uuid) | yes | Primary key |
| scope_key | str | yes | Identifies the dataset scope this conversation belongs to |
| role | str | yes | `user` \| `assistant` |
| content | str | yes | Message text |
| run_id | str \| null | no | The run this turn is associated with |
| created_at | datetime | yes | Turn time |

### Entity: DatasetProfile (Phase 2)
Auto-generated profile + data-quality flags for a dataset.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (uuid) | yes | Primary key |
| dataset_id | str | yes | FK → Dataset (indexed) |
| profile_json | str (Text, JSON) | yes | Single column holding the full profile dict (see below) |
| created_at | datetime | yes | Profiling time |

`profile_json` deserializes to a dict with top-level keys `row_count`, `column_count`, `columns`, and `quality_flags` (produced by `src/analysis/profiler.py:build_profile`):
- `columns` — array of per-column objects: `name`, `dtype`, `null_count`, `null_pct`, `distinct_count`, `min`, `max`, `sample_values` (note: `distinct_count`, not `unique_count`; `min`/`max` are non-null only for numeric/datetime columns; all values are JSON-safe with NaN→null).
- `quality_flags` — array of `{ type, severity, message, columns }` objects; `type` is one of `high_null`, `constant_column`, `duplicate_rows`, `numeric_outliers`.

### Entity: PinnedItem (Phase 3)
An answer/chart pinned to the persistent dashboard.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str (uuid) | yes | Primary key |
| run_id | str | yes | FK → Run (source of the pinned answer/chart) |
| title | str | yes | User/agent title for the tile |
| chart_spec | str \| null (JSON) | no | Snapshot of the chart |
| answer | str \| null | no | Snapshot of the answer text |
| position | int | yes | Order on the dashboard |
| created_at | datetime | yes | Pin time |

### Relationships

- `Dataset` 1 ─ N `Run` (via `dataset_ids`; many-to-many in Phase 3 multi-dataset runs).
- `Dataset` 1 ─ 1 `DatasetProfile`.
- `Run` 1 ─ N `Turn` (a run may append a user + assistant turn).
- `Run` 1 ─ N `PinnedItem`.

## Data Lifecycle

- **Created:** Dataset on upload; Run on each `/ask`; Turn per message; DatasetProfile on upload (Ph2); PinnedItem on pin (Ph3).
- **Updated:** Run progressively during execution (code, result, status, completed_at).
- **Deleted:** user may delete a Dataset (cascades its Runs/Profile/Turns; in-memory DataFrame dropped). No automatic archival/TTL — this is a personal tool; the user prunes manually.
- **Restart:** DB rows persist; in-memory DataFrames do not (files must be re-uploaded — see architecture Assumed note).

## Sensitive Data

The datasets may contain the user's own private/PII data, but this is a single-user local machine with no auth and no external transmission of bulk data — only schema + ≤20-row samples reach Gemini. No secrets are stored in the DB; the Gemini key lives only in `.env`. Uploaded files and exports sit under `data/` on the local disk.
