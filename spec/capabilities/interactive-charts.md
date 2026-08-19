# Capability: Interactive Charts

## What It Does
When a chart aids the answer, the agent picks the chart type and returns interactive Plotly JSON (zoom/filter/hover, exportable as image).

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question | str | agent state | yes |
| exec_result | value/DataFrame | execute node | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| chart_spec (Plotly JSON) or null | JSON | SSE `chart` + Run row |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini (flash) | pick chart type + emit spec | non-fatal — skip chart, answer still returns |
| plotly | build/validate figure JSON | log + skip chart |

## Business Rules
- The chart node decides whether a chart helps; if not, returns null (no chart forced).
- Chart data is built locally from the result; only compact result data goes into the spec.
- The user can export the rendered chart as an image (client-side).

## Success Criteria
- [ ] A trend/distribution question returns valid Plotly JSON of an appropriate type.
- [ ] A purely scalar answer (e.g. "what is the total?") returns no chart (null).
- [ ] The rendered chart supports hover/zoom and export-as-image in the UI.
