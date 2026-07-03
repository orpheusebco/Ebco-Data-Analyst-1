# Capability: Upload CSV

## What It Does
Loads an uploaded CSV file (up to ~100 MB) into the in-memory pandas registry and persists its metadata as a Dataset.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| file | multipart CSV | UI upload | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| dataset_id + name + row/column count | JSON | UI (confirmation) |
| stored file | file | `data/uploads/` |
| Dataset row | DB | SQLite |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Filesystem | Save upload | 400/500 with clear message |
| pandas | `read_csv` into registry | 400 parse error, do not persist |

## Business Rules
- Only schema + samples ever leave the machine; the full DataFrame stays in memory.
- Reject files over ~100 MB (413) and non-CSV types (400).
- Each upload creates a distinct dataset_id; re-uploading the same name is a new dataset.

## Success Criteria
- [ ] Uploading a valid CSV returns a dataset_id with correct row_count and column_count.
- [ ] The DataFrame is retrievable from the registry by dataset_id.
- [ ] An unreadable or oversize file returns a 4xx and persists no Dataset row.
