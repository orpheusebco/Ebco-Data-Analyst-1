"""Real end-to-end: a plot-style question yields a persisted Plotly chart_spec
and 2-3 follow-up suggestions. REAL Gemini via .env, sqlite production driver.

Asserts the persisted Run carries:
- chart_spec that parses to a dict containing a "data" key (valid Plotly figure),
- followups that parses to a list of 2-3 non-empty strings,
- status == "completed".
"""
import json

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from datasets import store
from db import session as session_module
from db.models import RunRow
from graph.runner import run_agent


def _require_gemini():
    from config.settings import get_settings

    s = get_settings()
    if not s.gemini_api_key and not s.anthropic_api_key:
        pytest.skip("No LLM key set in .env (AGENT_GEMINI_API_KEY / AGENT_ANTHROPIC_API_KEY)")


def _load_fixture() -> str:
    # Category comparison data — a natural bar/line chart.
    df = pd.DataFrame(
        {
            "region": ["north", "south", "east", "west", "central"],
            "sales": [1200, 950, 1500, 800, 1100],
        }
    )
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    result = store.load_csv(csv_bytes, "region_sales.csv")
    return result["dataset_id"]


def test_chart_and_followups_persisted(_isolated_db):
    _require_gemini()
    dataset_id = _load_fixture()

    run_id = run_agent(
        "Plot the total sales for each region so I can compare them.",
        [dataset_id],
    )

    with Session(session_module._engine) as s:
        run = s.get(RunRow, run_id)

    assert run is not None
    assert run.status == "completed", f"status={run.status} err={run.error_message}"

    # Chart spec: valid Plotly figure with a "data" key.
    assert run.chart_spec, "chart_spec must be persisted for a plot-style question"
    spec = json.loads(run.chart_spec)
    assert isinstance(spec, dict), f"chart_spec must be a dict, got {type(spec)}"
    assert "data" in spec, f"chart_spec must contain a 'data' key: {spec}"
    assert isinstance(spec["data"], list) and spec["data"], "chart data must be non-empty"

    # Follow-ups: list of 2-3 non-empty strings.
    assert run.followups, "followups must be persisted"
    items = json.loads(run.followups)
    assert isinstance(items, list), f"followups must be a list, got {type(items)}"
    assert 2 <= len(items) <= 3, f"expected 2-3 follow-ups, got {len(items)}: {items}"
    assert all(isinstance(x, str) and x.strip() for x in items), items


def test_scalar_result_has_no_chart_but_still_completes(_isolated_db):
    """A single-scalar answer should not force a chart, and must never fail the run."""
    _require_gemini()
    dataset_id = _load_fixture()

    run_id = run_agent(
        "What is the total sales across all regions? Give just the number.",
        [dataset_id],
    )

    with Session(session_module._engine) as s:
        run = s.get(RunRow, run_id)

    assert run is not None
    assert run.status == "completed", f"status={run.status} err={run.error_message}"
    # chart_spec may be None (scalar isn't plottable); followups still persist as a list.
    assert run.followups is not None
    assert isinstance(json.loads(run.followups), list)
