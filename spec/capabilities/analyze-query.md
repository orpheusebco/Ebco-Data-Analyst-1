# Capability: Analyze Query (agentic loop)

## What It Does
For a natural-language question, the agent plans a strategy, writes pandas, runs it locally (no sandbox), inspects the result, and auto-retries a different approach on failure — streaming back a plain-language answer with key numbers.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question | str | UI `/ask` | yes |
| dataset_ids | list[str] | UI (loaded datasets) | yes |
| conversation history | messages | DB (per-dataset scope) | no |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| streamed answer + key numbers | SSE tokens | UI |
| clarifying question (if ambiguous) | SSE `clarify` | UI |
| Run row (question, code, result, status) | DB | SQLite |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | plan / write_code / inspect / narrate | retry w/ backoff, then set error → handle_error |
| Local Python exec | run generated pandas (NO sandbox) | not fatal — traceback feeds retry loop |

## Business Rules
- Only question + schema + ≤20-row samples are sent to Gemini; never full data.
- On code failure, inspect diagnoses and write_code retries a DIFFERENT approach, up to `MAX_ATTEMPTS` (assumed 4).
- Ask a clarifying question ONLY when the request is genuinely ambiguous (inspect sets `needs_clarification`).
- Answers stream; a spinner shows the current phase until the first token.

## Success Criteria
- [ ] An aggregation question on a ≥50k-row CSV returns the correct full-data number (not a sampled approximation) within ~30s.
- [ ] When first-generated code raises, the run shows >1 attempt and still returns a correct answer without user intervention.
- [ ] A genuinely ambiguous question yields a specific clarifying question, not a wrong guess.
- [ ] The generated code and result are persisted on the Run row.
