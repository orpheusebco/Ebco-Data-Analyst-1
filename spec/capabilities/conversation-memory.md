# Capability: Conversation Memory

## What It Does
Carries conversation history across turns so follow-up questions are answered in the context of prior answers.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| new question | str | UI `/ask` | yes |
| prior turns | messages | DB (per-dataset scope) | no |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| appended user + assistant turns | DB | SQLite |
| context-aware answer | SSE | UI |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | read/write Turn rows | 500 with clear message |

## Business Rules
- The last N turns (assumed 12) for the active dataset scope are included in the agent prompt.
- A follow-up referencing "that result" / "those rows" resolves against the prior turn.
- Memory is scoped per dataset scope, not global.

## Success Criteria
- [ ] A follow-up question with a pronoun ("break that down by month") is answered correctly using the prior turn's context.
- [ ] Turns persist and are replayed on the next ask within the session.
- [ ] Starting a question on a different dataset scope does not leak the other conversation.
