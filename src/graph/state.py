from typing import Any, Callable, TypedDict


class AgentState(TypedDict, total=False):
    # Identity
    run_id: str

    # Input
    question: str
    dataset_ids: list[str]
    schema: dict
    messages: list  # [{role, content}] conversation history across turns

    # Pipeline data (populated progressively)
    plan: str | None
    code: str | None
    exec_result: Any
    exec_stdout: str | None
    exec_error: str | None
    inspection: dict | None
    attempts: int
    clarifying_question: str | None

    # Output
    answer: str | None

    # Control
    error: str | None
    status: str | None

    # Runtime hooks (in-process only — not persisted)
    _emit: Callable[[dict], None]
    _observer: Any
