# Capability: Exports (cleaned CSV / report)

## What It Does
Exports a run's cleaned data as CSV or a report artifact for download.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| run_id | str | UI export action | yes |
| format | str (`csv`\|`report`) | UI | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| exported file | file | `data/exports/` → browser download |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| pandas | write cleaned CSV | 500 with clear message |
| Filesystem | write export file | 500 |

## Business Rules
- Export re-derives the cleaned result from the run's stored code/result locally (no LLM, no data leaves the machine).
- CSV export reflects the exact result the run produced.
- Files are written under `data/exports/` and streamed as a download.

## Success Criteria
- [ ] Exporting a run as CSV downloads a file whose content matches the run's result.
- [ ] The report export produces a readable artifact containing the question, answer, and key numbers.
- [ ] An export for a failed run returns a clear error, not a corrupt file.
