# Capability: Excel Upload

## What It Does
Loads an uploaded Excel (.xlsx) file (with sheet selection) into the in-memory registry, same as CSV.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| file | multipart XLSX | UI upload | yes |
| sheet | str | UI sheet picker | no (defaults to first sheet) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| dataset_id + name + row/column count + sheet | JSON | UI |
| Dataset row (kind=xlsx, sheet) | DB | SQLite |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| openpyxl / pandas | `read_excel` (list sheets, load selected) | 400 parse error, no persist |
| Filesystem | store upload | 400/500 |

## Business Rules
- If the workbook has multiple sheets, the UI offers a picker; default is the first sheet.
- Once loaded, an Excel-sourced dataset behaves identically to a CSV dataset for all downstream capabilities.
- Same size ceiling (~100 MB) and privacy rule as CSV upload.

## Success Criteria
- [ ] Uploading a fixture .xlsx loads with the correct schema and row/column count.
- [ ] A multi-sheet workbook lets the user pick a sheet; the chosen sheet's data loads.
- [ ] An Excel dataset can be queried by the analyze-query loop like any CSV.
