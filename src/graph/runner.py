"""Runs the agentic graph for one question and bridges it to an SSE stream.

- `run_agent(...)` runs the graph synchronously and returns the run_id (tests).
- `stream_ask(...)` runs the graph in a background thread and yields SSE events
  (status / token / clarify / done / error) as they are emitted by the nodes.
"""
from __future__ import annotations

import json
import queue
import threading
from datetime import datetime, timezone

from analysis.executor import render_result
from config.settings import get_settings
from datasets import store
from db.models import RunRow, TurnRow
from db.session import create_db_session, init_db
from graph.agent import agentic_ai
from graph.state import AgentState
from observability.events import RunObserver

_SENTINEL = {"__end__": True}


def scope_key_for(dataset_ids: list[str]) -> str:
    return ",".join(sorted(dataset_ids))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_history(scope_key: str) -> list[dict]:
    limit = get_settings().history_turns
    with create_db_session() as session:
        rows = (
            session.query(TurnRow)
            .filter(TurnRow.scope_key == scope_key)
            .order_by(TurnRow.created_at.desc())
            .limit(limit)
            .all()
        )
        # Dereference ORM attributes INSIDE the session so we never touch
        # detached instances after the context closes.
        return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def _create_run(question: str, dataset_ids: list[str]) -> str:
    with create_db_session() as session:
        run = RunRow(
            question=question,
            input_text=question,
            dataset_ids=json.dumps(dataset_ids),
            status="pending",
            attempts=0,
        )
        session.add(run)
        session.flush()
        return run.id


def _persist_final(run_id: str, scope_key: str, question: str, final: AgentState) -> None:
    status = final.get("status") or ("failed" if final.get("error") else "completed")
    result_text = render_result(final.get("exec_result")) if final.get("exec_result") is not None else ""
    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        if run is None:
            return
        run.status = status
        run.plan = final.get("plan")
        run.code = final.get("code")
        run.attempts = final.get("attempts", 0)
        run.result_text = result_text or None
        run.answer = final.get("answer")
        run.output_text = final.get("answer")
        chart_spec = final.get("chart_spec")
        run.chart_spec = json.dumps(chart_spec) if chart_spec is not None else None
        run.followups = json.dumps(final.get("followups") or [])
        run.clarifying_question = final.get("clarifying_question")
        run.error_message = final.get("error")
        run.completed_at = _now()

        # Persist conversation turns (user question + assistant answer)
        session.add(
            TurnRow(scope_key=scope_key, role="user", content=question, run_id=run_id)
        )
        assistant_text = final.get("answer") or final.get("clarifying_question")
        if assistant_text:
            session.add(
                TurnRow(
                    scope_key=scope_key,
                    role="assistant",
                    content=assistant_text,
                    run_id=run_id,
                )
            )


def _run_graph(question: str, dataset_ids: list[str], run_id: str, emit) -> AgentState:
    scope_key = scope_key_for(dataset_ids)
    observer = RunObserver(run_id, question)
    schema = store.get_schema_and_samples(dataset_ids)
    messages = _load_history(scope_key)

    initial: AgentState = {
        "run_id": run_id,
        "question": question,
        "dataset_ids": dataset_ids,
        "schema": schema,
        "messages": messages,
        "attempts": 0,
        "error": None,
        "_emit": emit,
        "_observer": observer,
    }
    try:
        final = agentic_ai.invoke(initial, config={"recursion_limit": 50})
    except Exception as exc:  # noqa: BLE001 - never crash the stream
        final = {**initial, "status": "failed", "error": f"graph failed: {exc}"}
        emit({"type": "error", "message": str(exc)})

    # strip runtime hooks before persistence
    final.pop("_emit", None)
    final.pop("_observer", None)
    _persist_final(run_id, scope_key, question, final)
    observer.finish(final.get("status", "completed"), final.get("error"))
    return final


def run_agent(question: str, dataset_ids: list[str], scope_key: str | None = None) -> str:
    """Synchronous run — returns the run_id. Collects events into a no-op sink."""
    init_db()
    run_id = _create_run(question, dataset_ids)
    _run_graph(question, dataset_ids, run_id, emit=lambda e: None)
    return run_id


def stream_ask(question: str, dataset_ids: list[str]):
    """Generator yielding SSE event dicts as the graph runs in a worker thread."""
    init_db()
    run_id = _create_run(question, dataset_ids)
    q: queue.Queue = queue.Queue()

    def emit(event: dict) -> None:
        q.put(event)

    result_holder: dict = {}

    def worker() -> None:
        try:
            final = _run_graph(question, dataset_ids, run_id, emit)
            result_holder["status"] = final.get("status", "completed")
        except Exception as exc:  # noqa: BLE001
            result_holder["status"] = "failed"
            q.put({"type": "error", "message": str(exc)})
        finally:
            q.put(_SENTINEL)

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    while True:
        event = q.get()
        if event is _SENTINEL:
            break
        yield event

    t.join(timeout=5)
    yield {
        "type": "done",
        "run_id": run_id,
        "status": result_holder.get("status", "completed"),
    }
