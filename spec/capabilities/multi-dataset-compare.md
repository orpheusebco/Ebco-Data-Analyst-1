# Capability: Multi-dataset Compare

## What It Does
Loads several datasets and answers questions that compare across them (the agent generates pandas spanning multiple DataFrames).

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question | str | UI `/ask` | yes |
| dataset_ids | list[str] (≥2) | UI multi-select | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| cross-dataset answer + key numbers | SSE | UI |
| Run row with dataset_ids array | DB | SQLite |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | plan/write_code across multiple schemas | retry loop, then error |
| Local exec | run pandas over multiple named DataFrames | traceback feeds retry |

## Business Rules
- Schema + samples for EACH selected dataset are provided to the agent, named distinctly.
- Generated code references each DataFrame by a stable name (e.g. `df_<dataset_id>` or user-facing alias).
- Same privacy rule: only schemas + samples leave the machine.

## Success Criteria
- [ ] A comparison question over two fixture datasets returns the correct cross-dataset number.
- [ ] The Run row records all participating dataset_ids.
- [ ] Column-name collisions across datasets do not corrupt the result.
