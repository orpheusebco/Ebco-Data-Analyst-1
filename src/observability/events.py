"""Structured stdout observability — one context per run, one line per node.

Always-on (independent of LangSmith). Proves that only schema + samples are
sent to the LLM by logging the payload char-size.
"""
from __future__ import annotations

import contextvars
import time
from contextlib import contextmanager
from typing import Any, Callable

import structlog

# --- Live SSE event emitter (per-run, thread/context-scoped) -----------------
# Graph nodes call emit(...) to push events to the active /ask SSE stream.
# The runner sets an emitter before invoking the graph; when none is set
# (e.g. plain unit tests) emit() is a no-op.
_emitter: contextvars.ContextVar[Callable[[str, dict], None] | None] = (
    contextvars.ContextVar("sse_emitter", default=None)
)


def set_emitter(fn: Callable[[str, dict], None] | None) -> None:
    _emitter.set(fn)


def emit(event_type: str, data: dict) -> None:
    fn = _emitter.get()
    if fn is not None:
        fn(event_type, data)


def emit_status(phase: str) -> None:
    emit("status", {"phase": phase})


def log_node(
    node: str,
    run_id: str | None = None,
    *,
    model: str | None = None,
    attempt: int | None = None,
    latency_ms: float | None = None,
    llm_payload_chars: int | None = None,
    exec_ok: bool | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """One structured stdout line per node execution."""
    log = get_logger("agent.node")
    fields = {
        "node": node,
        "run_id": run_id,
        "model": model,
        "attempt": attempt,
        "latency_ms": round(latency_ms, 1) if latency_ms is not None else None,
        "llm_payload_chars": llm_payload_chars,
        "exec_ok": exec_ok,
        "error": error,
    }
    fields = {k: v for k, v in fields.items() if v is not None}
    fields.update(extra)
    log.info("node", **fields)


class node_timer:
    """Context manager measuring node latency in ms."""

    def __enter__(self) -> "node_timer":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.latency_ms = (time.perf_counter() - self._t0) * 1000.0


def configure_logging(log_level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), log_level, 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str = "agent") -> structlog.BoundLogger:
    return structlog.get_logger(name)


class RunObserver:
    """One structured logging context bound to a run_id."""

    def __init__(self, run_id: str, question: str = "") -> None:
        self.run_id = run_id
        self._log = get_logger("agent.run").bind(run_id=run_id)
        self._log.info(
            "run.start",
            question_summary=(question or "")[:120],
        )
        self._t0 = time.perf_counter()

    def node(self, name: str, **fields) -> None:
        self._log.info(f"node.{name}", node=name, **fields)

    def llm(
        self,
        node: str,
        model: str,
        prompt_chars: int,
        latency_ms: float,
        **fields,
    ) -> None:
        self._log.info(
            "llm.call",
            node=node,
            model=model,
            prompt_chars=prompt_chars,
            latency_ms=round(latency_ms, 1),
            **fields,
        )

    def exec(
        self, attempt: int, ok: bool, latency_ms: float, error: str | None = None
    ) -> None:
        self._log.info(
            "code.exec",
            attempt=attempt,
            ok=ok,
            latency_ms=round(latency_ms, 1),
            error=(error or "")[:400] if error else None,
        )

    def finish(self, status: str, error: str | None = None) -> None:
        self._log.info(
            "run.finish",
            status=status,
            total_ms=round((time.perf_counter() - self._t0) * 1000, 1),
            error=(error or "")[:400] if error else None,
        )


@contextmanager
def timed():
    t0 = time.perf_counter()
    holder = {"ms": 0.0}
    try:
        yield holder
    finally:
        holder["ms"] = (time.perf_counter() - t0) * 1000
