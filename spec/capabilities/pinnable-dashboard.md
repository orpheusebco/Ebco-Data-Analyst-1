# Capability: Pinnable Dashboard

## What It Does
Lets the user pin answers/charts to a persistent, curated dashboard — the primary curated view.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| run_id | str | UI pin action | yes |
| title | str | UI | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| PinnedItem (title, chart_spec/answer snapshot, position) | DB | SQLite |
| ordered dashboard tiles | JSON | UI dashboard view |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | insert/select/update/delete PinnedItem | 500 with clear message |

## Business Rules
- Pinning snapshots the answer/chart at pin time (later dataset changes don't mutate a pin).
- Dashboard tiles are ordered by `position`; user can reorder and remove.
- The dashboard persists across restarts.

## Success Criteria
- [ ] Pinning a run creates a PinnedItem returned by `GET /dashboard`.
- [ ] Pinned tiles survive a page reload and a process restart.
- [ ] Reorder and unpin update the dashboard correctly.
