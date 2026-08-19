# Capability: Follow-up Suggestions

## What It Does
After each answer, suggests 2-3 relevant follow-up questions the user can click to ask.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question | str | agent state | yes |
| answer | str | narrate node | yes |
| schema | dict | agent state | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| followups (2-3 strings) | JSON array | SSE `followups` + Run row |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini (flash) | generate follow-ups | non-fatal — omit, answer still returns |

## Business Rules
- Exactly 2-3 suggestions, grounded in the dataset schema and the just-answered question.
- Clicking a suggestion submits it as a new `/ask` turn (uses conversation memory).

## Success Criteria
- [ ] Each completed answer includes 2-3 non-empty follow-up strings.
- [ ] Clicking a follow-up asks that exact question and returns a contextual answer.
- [ ] A failure of this node does not block the primary answer.
