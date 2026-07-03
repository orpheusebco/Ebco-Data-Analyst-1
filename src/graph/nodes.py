"""LangGraph nodes for the data-analysis agent.

Each node wraps its work in try/except; fatal errors set state["error"] and route
to handle_error. execute errors are NOT fatal — they drive the retry loop.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from analysis.executor import execute_code, render_result, strip_code_fences
from config.settings import get_settings
from datasets import store
from graph.state import AgentState
from llm.client import LLMClient

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

MODEL_PRO_DEFAULT = "gemini-2.5-pro"
MODEL_FLASH_DEFAULT = "gemini-2.5-flash"
# Default node model. Flash is ~2-4x faster than pro and handles pandas codegen,
# inspection, and narration well; the execute->inspect->retry loop self-corrects
# any codegen slips, so we favor flash for latency. Bump a specific node back to
# MODEL_PRO_DEFAULT if a harder-reasoning phase needs it.
MODEL_NODE_DEFAULT = MODEL_FLASH_DEFAULT


def _load_prompt(name: str) -> str:
    return (_PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def _model(default: str) -> str:
    # AGENT_LLM_MODEL overrides all node models when set.
    return get_settings().llm_model or default


def _emit(state: AgentState, event: dict) -> None:
    fn = state.get("_emit")
    if callable(fn):
        try:
            fn(event)
        except Exception:  # noqa: BLE001 - emitting must never break the graph
            pass


def _obs(state: AgentState):
    return state.get("_observer")


def _schema_text(schema: dict) -> str:
    return json.dumps(schema, indent=2, default=str)


def _messages_text(messages: list | None, limit: int = 12) -> str:
    if not messages:
        return "(no prior conversation)"
    recent = messages[-limit:]
    return "\n".join(f"{m.get('role')}: {m.get('content')}" for m in recent)


def _parse_json_object(text: str) -> dict:
    raw = strip_code_fences(text)
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #


def plan(state: AgentState) -> AgentState:
    _emit(state, {"type": "status", "phase": "planning"})
    obs = _obs(state)
    try:
        prompt = (
            f"Schema and samples:\n{_schema_text(state.get('schema', {}))}\n\n"
            f"Conversation so far:\n{_messages_text(state.get('messages'))}\n\n"
            f"Question: {state['question']}"
        )
        t0 = time.perf_counter()
        result = LLMClient().call_model(
            prompt, system=_load_prompt("plan.md"), model=_model(MODEL_NODE_DEFAULT)
        )
        if obs:
            obs.llm("plan", _model(MODEL_NODE_DEFAULT), len(prompt),
                    (time.perf_counter() - t0) * 1000)
            obs.node("plan")
        return {**state, "plan": result.strip(), "error": None}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"plan failed: {exc}"}


def write_code(state: AgentState) -> AgentState:
    attempts = state.get("attempts", 0)
    _emit(
        state,
        {"type": "status", "phase": "retrying" if attempts > 0 else "writing_code"},
    )
    obs = _obs(state)
    try:
        retry_ctx = ""
        if attempts > 0 and state.get("code"):
            err = state.get("exec_error") or ""
            insp = state.get("inspection") or {}
            retry_ctx = (
                "\n\nPRIOR ATTEMPT (failed) — try a DIFFERENT approach:\n"
                f"Prior code:\n{state.get('code')}\n\n"
                f"Prior error/traceback:\n{err}\n\n"
                f"Inspection reason: {insp.get('reason', '')}\n"
            )
        prompt = (
            f"Schema and samples:\n{_schema_text(state.get('schema', {}))}\n\n"
            f"Plan: {state.get('plan', '')}\n\n"
            f"Question: {state['question']}"
            f"{retry_ctx}"
        )
        t0 = time.perf_counter()
        raw = LLMClient().call_model(
            prompt,
            system=_load_prompt("write_code.md"),
            model=_model(MODEL_NODE_DEFAULT),
        )
        code = strip_code_fences(raw)
        if obs:
            obs.llm("write_code", _model(MODEL_NODE_DEFAULT), len(prompt),
                    (time.perf_counter() - t0) * 1000, attempt=attempts + 1)
            obs.node("write_code", attempt=attempts + 1)
        return {**state, "code": code, "attempts": attempts + 1, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"write_code failed: {exc}"}


def execute(state: AgentState) -> AgentState:
    _emit(state, {"type": "status", "phase": "executing"})
    obs = _obs(state)
    t0 = time.perf_counter()
    try:
        namespace = store.build_namespace(state["dataset_ids"])
    except Exception as exc:  # noqa: BLE001 - unknown dataset is fatal
        return {**state, "error": f"execute setup failed: {exc}"}

    result, stdout, exec_error = execute_code(state.get("code", ""), namespace)
    latency = (time.perf_counter() - t0) * 1000
    if obs:
        obs.exec(
            state.get("attempts", 0),
            ok=exec_error is None,
            latency_ms=latency,
            error=exec_error,
        )
    return {
        **state,
        "exec_result": result,
        "exec_stdout": stdout,
        "exec_error": exec_error,
        "error": None,
    }


def inspect(state: AgentState) -> AgentState:
    _emit(state, {"type": "status", "phase": "inspecting"})
    obs = _obs(state)
    try:
        exec_error = state.get("exec_error")
        if exec_error:
            result_block = f"EXECUTION ERROR / TRACEBACK:\n{exec_error}"
        else:
            result_block = (
                "RESULT:\n"
                f"{render_result(state.get('exec_result'))}\n\n"
                f"STDOUT:\n{state.get('exec_stdout') or ''}"
            )
        prompt = (
            f"Question: {state['question']}\n\n"
            f"Generated code:\n{state.get('code', '')}\n\n"
            f"{result_block}"
        )
        t0 = time.perf_counter()
        raw = LLMClient().call_model(
            prompt, system=_load_prompt("inspect.md"), model=_model(MODEL_NODE_DEFAULT)
        )
        parsed = _parse_json_object(raw)
        inspection = {
            "ok": bool(parsed.get("ok", False)) and not exec_error,
            "needs_clarification": bool(parsed.get("needs_clarification", False)),
            "reason": str(parsed.get("reason", "")),
        }
        if obs:
            obs.llm("inspect", _model(MODEL_NODE_DEFAULT), len(prompt),
                    (time.perf_counter() - t0) * 1000)
            obs.node("inspect", ok=inspection["ok"],
                     needs_clarification=inspection["needs_clarification"])
        return {**state, "inspection": inspection, "error": None}
    except Exception as exc:  # noqa: BLE001
        # If we can't parse the judgement, fall back to error-vs-ok heuristic.
        inspection = {
            "ok": not bool(state.get("exec_error")),
            "needs_clarification": False,
            "reason": f"inspect parse fallback: {exc}",
        }
        return {**state, "inspection": inspection, "error": None}


def clarify(state: AgentState) -> AgentState:
    obs = _obs(state)
    try:
        prompt = (
            f"Question: {state['question']}\n\n"
            f"Schema:\n{_schema_text(state.get('schema', {}))}\n\n"
            f"Inspection reason: {(state.get('inspection') or {}).get('reason', '')}"
        )
        question = LLMClient().call_model(
            prompt, system=_load_prompt("clarify.md"), model=_model(MODEL_FLASH_DEFAULT)
        ).strip()
        _emit(state, {"type": "clarify", "question": question})
        if obs:
            obs.node("clarify")
        return {
            **state,
            "clarifying_question": question,
            "status": "needs_clarification",
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"clarify failed: {exc}"}


def narrate(state: AgentState) -> AgentState:
    _emit(state, {"type": "status", "phase": "narrating"})
    obs = _obs(state)
    try:
        inspection = state.get("inspection") or {}
        best_effort = not inspection.get("ok", False)
        if state.get("exec_error"):
            outcome = (
                "The analysis could not be completed after retries. "
                f"Last error:\n{state.get('exec_error')}"
            )
        else:
            outcome = (
                "RESULT:\n"
                f"{render_result(state.get('exec_result'))}\n\n"
                f"STDOUT:\n{state.get('exec_stdout') or ''}"
            )
        note = (
            "\n\nNote: prior attempts did not fully satisfy the question; answer best-effort "
            "and be honest about limitations."
            if best_effort
            else ""
        )
        prompt = (
            f"Conversation so far:\n{_messages_text(state.get('messages'))}\n\n"
            f"Question: {state['question']}\n\n"
            f"{outcome}{note}"
        )
        t0 = time.perf_counter()
        model = _model(MODEL_NODE_DEFAULT)
        pieces: list[str] = []
        for token in LLMClient().stream_model(
            prompt, system=_load_prompt("narrate.md"), model=model
        ):
            pieces.append(token)
            _emit(state, {"type": "token", "text": token})
        answer = "".join(pieces).strip()
        if not answer:
            # Non-stream fallback
            answer = LLMClient().call_model(
                prompt, system=_load_prompt("narrate.md"), model=model
            ).strip()
            _emit(state, {"type": "token", "text": answer})
        if obs:
            obs.llm("narrate", model, len(prompt),
                    (time.perf_counter() - t0) * 1000, streamed=True)
            obs.node("narrate")
        messages = list(state.get("messages") or [])
        messages.append({"role": "assistant", "content": answer})
        return {**state, "answer": answer, "messages": messages, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {**state, "error": f"narrate failed: {exc}"}


def finalize(state: AgentState) -> AgentState:
    obs = _obs(state)
    if obs:
        obs.node("finalize")
    return {**state, "status": "completed"}


def handle_error(state: AgentState) -> AgentState:
    obs = _obs(state)
    _emit(state, {"type": "error", "message": state.get("error") or "Unknown error"})
    if obs:
        obs.node("handle_error", error=state.get("error"))
    return {**state, "status": "failed"}
