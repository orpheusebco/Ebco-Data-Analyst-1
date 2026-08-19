# Capabilities Index

> One file per capability. Each describes exactly one discrete thing the agent can do.

---

## Capabilities in This Project

| Capability | Phase | File |
|-----------|-------|------|
| Upload CSV | 1 | [csv-upload.md](csv-upload.md) |
| Analyze query (agentic loop) | 1 | [analyze-query.md](analyze-query.md) |
| Run history | 1 | [run-history.md](run-history.md) |
| Conversation memory | 1 | [conversation-memory.md](conversation-memory.md) |
| Dataset profiling + quality flags | 2 | [dataset-profiling.md](dataset-profiling.md) |
| Interactive charts | 2 | [interactive-charts.md](interactive-charts.md) |
| Follow-up suggestions | 2 | [followup-suggestions.md](followup-suggestions.md) |
| Multi-dataset compare | 3 | [multi-dataset-compare.md](multi-dataset-compare.md) |
| Pinnable dashboard | 3 | [pinnable-dashboard.md](pinnable-dashboard.md) |
| Exports (cleaned CSV / report) | 3 | [exports.md](exports.md) |
| Excel upload | 3 | [excel-upload.md](excel-upload.md) |

## How to Add a New Capability

Run `/zero-shot-build [description]`. The spec-writer creates a new `<name>.md`, updates this index, flags dependencies, and self-reviews fit against the architecture and data model.
