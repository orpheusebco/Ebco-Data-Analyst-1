# Capability: Run History

## What It Does
Stores and lists every query, the exact code the agent ran, and the result — organized per dataset.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id | str | UI | yes (for listing) |
| run data | Run fields | agent runner | yes (for writing) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| list of runs (question, code, result_text, answer, status, created_at) | JSON | UI history panel |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | insert/update/select Run | 500 with clear message |

## Business Rules
- Every `/ask` creates exactly one Run row, updated progressively through the loop.
- History is filterable by dataset_id and ordered newest-first.
- Failed and needs_clarification runs are retained (full audit trail), not discarded.

## Success Criteria
- [ ] After an ask, `GET /datasets/{id}/runs` returns the run with non-empty question, code, and result_text.
- [ ] Expanding a run in the UI shows the generated code and result.
- [ ] History persists across process restarts.
