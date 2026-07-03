# Agent

---

## Agent Architecture Pattern

**Chosen:** **Graph (LangGraph)** — a single agentic loop with conditional edges. Each question runs a plan → write-code → execute → inspect cycle that loops back to write-code on failure (retry with a different approach), branches to a clarify node when the request is genuinely ambiguous, and proceeds to narration/charting/finalize on success. The conditional retry/clarify/branch topology is exactly what a graph (not a linear loop) is for.

---

## LLM Provider & Model

| Agent / Node | Provider | Model ID | Rationale |
|-------------|----------|----------|-----------|
| `plan` | Gemini | `gemini-2.5-flash` | Strategy for the ask; flash is fast and sufficient |
| `write_code` | Gemini | `gemini-2.5-flash` | Pandas generation; execute→inspect→retry loop self-corrects any slips |
| `inspect` | Gemini | `gemini-2.5-flash` | Judges whether the result answers the question / diagnoses errors |
| `narrate` | Gemini | `gemini-2.5-flash` | Plain-language answer with key numbers; streamed |
| `chart` (Ph2) | Gemini | `gemini-2.5-flash` | Structured chart-type + spec selection; latency-sensitive |
| `suggest_followups` (Ph2) | Gemini | `gemini-2.5-flash` | Cheap, short generation |
| `clarify` | Gemini | `gemini-2.5-flash` | Short clarifying question |

**Flash-only invariant:** every node defaults to `gemini-2.5-flash` (`MODEL_NODE_DEFAULT = MODEL_FLASH_DEFAULT` in `src/graph/nodes.py`). `gemini-2.5-pro` is intentionally **not** used — flash cuts end-to-end latency ~2.25x and the execute→inspect→retry loop self-corrects any codegen slips, so the extra pro reasoning is not needed. `MODEL_PRO_DEFAULT` remains defined only as an escape hatch if a future node needs it.

Model is env-configurable via `AGENT_LLM_MODEL` (overrides all nodes when set); provider auto-detected from `AGENT_GEMINI_API_KEY`.

**Fallback behaviour:** Each LLM call retries up to 2 times with exponential backoff on transient errors (rate limit / 5xx). On exhaustion the node sets `state["error"]` and routes to `handle_error`, which streams a clear error and marks the run `failed`. No offline/stub path — tests use the real Gemini key from `.env`.

**Prompt strategy:** System/user split. `write_code` uses a strict system prompt instructing the model to return ONLY a Python code block that defines a function operating on named DataFrames and assigning to `result`, given the schema + samples + (on retry) the prior code and its error/inspection. `inspect` and `chart` use JSON-structured output. Only schema + ≤20-row samples are ever included — never full data.

---

## Tools & Tool Calling

This is a code-generation agent, not an LLM-tool-calling agent — "tools" are internal functions the graph nodes invoke deterministically, not model-selected tool calls.

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `execute_code` | Runs generated pandas against in-memory DataFrames, NO sandbox | code str, dataset DataFrames | `result` value + captured stdout, or exception + traceback | None (reads DataFrames; may create export files in Phase 3) |
| `get_schema_and_samples` | Builds column schema + ≤20-row sample for the LLM | dataset_id(s) | schema dict + sample rows | None |
| `build_profile` (Ph2) | Computes columns/types/ranges/nulls + quality flags | DataFrame | profile dict | Persists `DatasetProfile` |
| `build_chart_spec` (Ph2) | Turns a result + chart choice into Plotly JSON | result, chart type | Plotly JSON | None |
| `export_clean` (Ph3) | Writes cleaned CSV / report to `data/exports/` | DataFrame/result | file path | Writes file |

**Tool selection strategy:** Rule-based — the graph decides which internal function runs at each node. The LLM chooses *code content* and *chart type*, not which tool executes.

**Tool failure handling:** `execute_code` failures are expected and drive the retry loop (traceback fed back to `write_code`). Other tool errors set `state["error"]` → `handle_error`.

---

## Agent State

```python
class AgentState(TypedDict, total=False):
    # Identity
    run_id: str                          # set by runner at init

    # Input
    question: str                        # the user's natural-language question
    dataset_ids: list[str]               # loaded datasets in scope (1 in Ph1, N in Ph3)
    schema: dict                         # column schema + samples per dataset (get_schema_and_samples)
    messages: list                       # [{role, content}] conversation history across turns

    # Pipeline data (populated progressively)
    plan: str | None                     # plan node: strategy for the question
    code: str | None                     # write_code node: latest generated pandas
    exec_result: object | None           # execute node: value assigned to `result`
    exec_stdout: str | None              # execute node: captured stdout
    exec_error: str | None               # execute node: traceback if code raised
    inspection: dict | None              # inspect node: {ok: bool, reason: str, needs_clarification: bool}
    attempts: int                        # write_code/execute attempts so far (retry cap)
    clarifying_question: str | None      # clarify node: question posed back to the user

    # Output
    answer: str | None                   # narrate node: streamed plain-language answer
    chart_spec: dict | None              # chart node (Ph2): Plotly JSON
    followups: list[str]                 # suggest_followups node (Ph2)

    # Control
    error: str | None                    # any node on fatal failure
    status: str | None                   # completed | failed | needs_clarification
```

---

## Nodes / Steps

### `plan`
**Reads:** `question`, `schema`, `messages`. **Writes:** `plan`.
**LLM call:** yes — `gemini-2.5-pro`; produces a short strategy (skipped-through for trivial asks). **External:** Gemini (retry→error).
**Behaviour:** Produces a brief analysis strategy so `write_code` has a target. For simple questions the plan is one line.

### `write_code`
**Reads:** `question`, `schema`, `plan`, `code`, `exec_error`, `inspection`, `attempts`. **Writes:** `code`, increments `attempts`.
**LLM call:** yes — `gemini-2.5-pro`; returns ONLY a pandas code block assigning to `result`. **External:** Gemini (retry→error).
**Behaviour:** On first pass, generates code from plan + schema. On retry, is given the prior code + traceback/inspection and must try a *different* approach.

### `execute`
**Reads:** `code`, `dataset_ids`. **Writes:** `exec_result`, `exec_stdout`, `exec_error`.
**LLM call:** no. **External:** local Python exec, NO sandbox (`execute_code`) — failures captured, not fatal.
**Behaviour:** Runs the generated pandas against the in-memory DataFrames; captures the `result` value or the traceback.

### `inspect`
**Reads:** `question`, `code`, `exec_result`, `exec_stdout`, `exec_error`. **Writes:** `inspection`.
**LLM call:** yes — `gemini-2.5-pro`, JSON output `{ok, reason, needs_clarification}`. **External:** Gemini (retry→error).
**Behaviour:** Judges whether the result correctly answers the question. If code errored → `ok:false`. If the question is genuinely ambiguous → `needs_clarification:true`.

### `clarify`
**Reads:** `question`, `inspection`, `schema`. **Writes:** `clarifying_question`, `status="needs_clarification"`.
**LLM call:** yes — `gemini-2.5-flash`. **Behaviour:** Composes one specific clarifying question, streams it, and ends the run awaiting the user's next turn (which arrives as a new `/ask` with prior `messages`).

### `narrate`
**Reads:** `question`, `exec_result`, `exec_stdout`, `messages`. **Writes:** `answer`, appends to `messages`.
**LLM call:** yes — `gemini-2.5-pro`, streamed. **Behaviour:** Produces the plain-language answer with the key numbers; tokens stream to the client.

### `chart` (Phase 2)
**Reads:** `question`, `exec_result`. **Writes:** `chart_spec`.
**LLM call:** yes — `gemini-2.5-flash`, JSON. **Behaviour:** Decides whether a chart helps and, if so, picks the type and emits Plotly JSON. Skips (null) when a chart adds nothing.

### `suggest_followups` (Phase 2)
**Reads:** `question`, `answer`, `schema`. **Writes:** `followups` (2-3). **LLM call:** yes — `gemini-2.5-flash`.

### `finalize`
**Reads:** all output fields. **Writes:** `status="completed"`. Persists code/result/answer/chart/followups to the `Run` row.

### `handle_error`
**Reads:** `error`, `run_id`. **Writes:** `status="failed"`. Streams the error, marks the run failed.

---

## Graph / Flow Topology

```
START
  │
  ▼
plan ──(error)──► handle_error ──► END
  │
  ▼
write_code ──(error)──► handle_error
  │
  ▼
execute
  │
  ▼
inspect ──(error)──► handle_error
  │
  ├─(ok:true)──────────────► narrate
  ├─(needs_clarification)──► clarify ──► END
  └─(ok:false & attempts<MAX)─► write_code   (retry, different approach)
      └─(ok:false & attempts>=MAX)─► narrate  (narrate best-effort / report failure to answer)
                                        │
narrate ──► chart(Ph2) ──► suggest_followups(Ph2) ──► finalize ──► END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `plan` / `write_code` / `inspect` | `state["error"]` is not None | `handle_error` |
| `inspect` | `inspection["ok"]` is True | `narrate` |
| `inspect` | `inspection["needs_clarification"]` is True | `clarify` |
| `inspect` | `ok` False and `attempts` < `MAX_ATTEMPTS` | `write_code` |
| `inspect` | `ok` False and `attempts` >= `MAX_ATTEMPTS` | `narrate` |

> **Assumed:** `MAX_ATTEMPTS = 4` (not specified). Env-configurable via `AGENT_MAX_ATTEMPTS`.

---

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| **Within a run** | LangGraph state | plan, code, exec result, inspection, attempts |
| **Across runs** | SQLite | `Run` history (query + code + result) per dataset; profiles; pins |
| **Conversation** | `messages` in state, persisted per dataset and replayed | user/assistant turns so follow-ups keep context |

**Context window management:** Only schema + ≤20-row samples per dataset are sent (never full data). Conversation history is included as recent turns; if it grows large, older turns are truncated to the last N (assumed N=12) with the running dataset context preserved.

> **Assumed:** conversation history window N=12 turns; overridable via `AGENT_HISTORY_TURNS`.

---

## Human-in-the-Loop Checkpoints

| Checkpoint | Shown to user | Expected action | Timeout / default |
|------------|---------------|-----------------|-------------------|
| `clarify` | A specific clarifying question when the ask is genuinely ambiguous | User replies via the next `/ask` turn | None — run ends `needs_clarification`; user may ignore and rephrase |

---

## Error Handling & Recovery

**Node-level:** every node wraps its work in try/except; fatal errors set `state["error"]` and route to `handle_error`. `execute` errors are NOT fatal — they feed the retry loop.

**Graph-level (`handle_error`):** reads `state.error`, `state.run_id`; updates the `Run` row → status `failed`, `error_message`, `completed_at`; logs with `run_id`; streams a clear error; terminates.

**Resume / retry strategy:** the write-code/execute/inspect retry loop is the core recovery mechanism (auto-retry a different approach, up to `MAX_ATTEMPTS`). A failed run is not auto-resumed; the user re-asks.

**Partial failure:** if `chart` or `suggest_followups` (non-critical) fail, the agent logs and continues — the answer still returns (graceful degrade).

---

## Observability

| Signal | What | Where |
|--------|------|-------|
| **Trace** | One structured log context per run, one entry per node (via `src/observability/events.py`) | stdout structured logs |
| **LLM calls** | Node, model, prompt (schema+samples only), latency, token/char counts | Structured log |
| **Code execution** | Generated code, attempt number, success/error, traceback, latency | Structured log + persisted on `Run` |
| **Run outcome** | Status, total duration, error if any | SQLite `Run` + structured log |

> LangSmith optional: if `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` are set, LangGraph traces export automatically. Structured stdout logging is the always-on default and is wired in Phase 1 — never deferred.

---

## Concurrency Model

- **Run isolation:** single user, one analysis at a time per browser session. `/ask` runs are keyed by `run_id`; a second concurrent `/ask` is allowed but the DataFrame registry is read-only during analysis so runs don't corrupt each other.
- **Parallel nodes within a run:** none — the loop is inherently sequential.
- **Checkpointing:** none required (no long-running pause; `clarify` ends the run rather than pausing it).

---

## Graph Assembly (`src/graph/agent.py`)

```python
graph = StateGraph(AgentState)

graph.add_node("plan", plan)
graph.add_node("write_code", write_code)
graph.add_node("execute", execute)
graph.add_node("inspect", inspect)
graph.add_node("clarify", clarify)
graph.add_node("narrate", narrate)
# Phase 2: graph.add_node("chart", chart); graph.add_node("suggest_followups", suggest_followups)
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)

graph.set_entry_point("plan")

graph.add_conditional_edges("plan",
    lambda s: "handle_error" if s.get("error") else "write_code")
graph.add_conditional_edges("write_code",
    lambda s: "handle_error" if s.get("error") else "execute")
graph.add_edge("execute", "inspect")
graph.add_conditional_edges("inspect", route_after_inspect,
    {"handle_error": "handle_error", "narrate": "narrate",
     "clarify": "clarify", "write_code": "write_code"})

graph.add_edge("clarify", END)
# Phase 1: graph.add_edge("narrate", "finalize")
# Phase 2: narrate -> chart -> suggest_followups -> finalize
graph.add_edge("narrate", "finalize")
graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)

compiled_graph = graph.compile()
```
