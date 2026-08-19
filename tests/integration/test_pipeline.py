"""Real end-to-end integration — REAL Gemini via .env, sqlite production driver.

Builds a >=50,000-row CSV whose head-sample answer differs observably from the
full-data answer, then runs a real aggregation question through the graph and
asserts the streamed answer contains the correct FULL-data number and that a Run
row was persisted with non-empty generated code + result.
"""
import json

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from datasets import store
from db import session as session_module
from db.models import RunRow
from graph.runner import run_agent

ROWS = 50_000


def _load_fixture() -> tuple[str, float]:
    # amount cycles 0..99 over 50k rows -> full mean 49.5; head(20) mean is 9.5.
    amount = [i % 100 for i in range(ROWS)]
    df = pd.DataFrame({"amount": amount, "region": ["north", "south"] * (ROWS // 2)})
    expected_mean = float(df["amount"].mean())  # 49.5
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    result = store.load_csv(csv_bytes, "big_sales.csv")
    return result["dataset_id"], expected_mean


@pytest.mark.usefixtures("_require_llm_key")
def test_full_data_aggregation_end_to_end(_isolated_db):
    dataset_id, expected_mean = _load_fixture()
    assert expected_mean == 49.5

    run_id = run_agent(
        "What is the mean of the amount column across all rows? "
        "Give the exact number.",
        [dataset_id],
    )

    with Session(session_module._engine) as s:
        run = s.get(RunRow, run_id)

    assert run is not None
    assert run.status == "completed", f"status={run.status} err={run.error_message}"
    assert run.code and "amount" in run.code, "generated code must be persisted"
    assert run.result_text, "result_text must be persisted"
    assert run.answer, "streamed answer must be persisted"
    assert json.loads(run.dataset_ids) == [dataset_id]

    answer = run.answer.replace(",", "")
    # Full-data mean is 49.5; the head-sample mean (9.5) must NOT be what surfaces.
    assert "49.5" in answer or "49.50" in answer, f"answer missing full mean: {run.answer}"


@pytest.mark.usefixtures("_require_llm_key")
def test_multi_turn_history_carries_across_turns(_isolated_db):
    """Second turn must load prior turns (real _load_history over existing rows)
    and reach status=completed with a non-empty contextual answer. Guards the
    detached-ORM-instance regression that crashed the second turn."""
    dataset_id, _ = _load_fixture()

    first_id = run_agent(
        "What is the mean of the amount column across all rows? "
        "Give the exact number.",
        [dataset_id],
    )
    with Session(session_module._engine) as s:
        first = s.get(RunRow, first_id)
    assert first is not None and first.status == "completed", (
        f"first turn failed: status={first.status} err={first.error_message}"
    )

    # Follow-up references the prior answer WITHOUT restating the column — this
    # only works if conversation history carried across turns.
    second_id = run_agent(
        "Now multiply that mean you just gave me by 2. Give the exact number.",
        [dataset_id],
    )
    with Session(session_module._engine) as s:
        second = s.get(RunRow, second_id)

    assert second is not None
    assert second.status == "completed", (
        f"second turn failed: status={second.status} err={second.error_message}"
    )
    assert second.answer and second.answer.strip(), "second turn answer must be non-empty"


@pytest.mark.usefixtures("_require_llm_key")
def test_conversation_history_persisted(_isolated_db):
    dataset_id, _ = _load_fixture()
    run_agent("How many rows are in the dataset?", [dataset_id])

    from db.models import TurnRow

    with Session(session_module._engine) as s:
        turns = s.query(TurnRow).all()
    roles = {t.role for t in turns}
    assert "user" in roles and "assistant" in roles
