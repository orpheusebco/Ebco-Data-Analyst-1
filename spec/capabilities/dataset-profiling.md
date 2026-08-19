# Capability: Dataset Profiling + Quality Flags

## What It Does
On upload, auto-profiles the dataset (columns, types, ranges, missing values) and flags data-quality issues.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset DataFrame | pandas | registry (on upload) | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| per-column profile (name, dtype, min/max/range, null_count, unique_count) | JSON | UI + DB |
| quality_flags (high-null, duplicate rows, constant column, mixed types) | JSON array | UI + DB |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| pandas | compute describe/dtypes/isnull | log + partial profile, non-fatal |
| SQLite | persist DatasetProfile | 500 |

## Business Rules
- Profiling is computed locally on the full DataFrame (no LLM, no data leaves the machine).
- Runs automatically on every upload; result cached as a DatasetProfile row.
- At least the standard flags are evaluated: >X% nulls, exact-duplicate rows, constant/single-value columns, mixed-type columns.

## Success Criteria
- [ ] Uploading the fixture CSV returns a profile with correct column count, dtypes, and null counts.
- [ ] At least one quality flag is produced for a fixture that contains a high-null or duplicate-row issue.
- [ ] The profile is persisted and returned on the dataset detail response.
