"""Multi-dataset compare flow — REAL Gemini. Register two related DataFrames and
run the agent with a comparison question; assert code references both df1 and df2.
"""
import pytest

from datasets import store
from graph import runner
from db.models import RunRow
from db.session import create_db_session


@pytest.mark.usefixtures("_require_llm_key")
def test_multi_dataset_comparison_uses_both_frames(_isolated_db):
    import pandas as pd

    ds_a = store.load_csv(
        pd.DataFrame(
            {"region": ["north", "south", "east"], "sales": [100, 200, 300]}
        ).to_csv(index=False).encode("utf-8"),
        "region_sales_a.csv",
    )
    ds_b = store.load_csv(
        pd.DataFrame(
            {"region": ["north", "south", "east"], "sales": [90, 260, 250]}
        ).to_csv(index=False).encode("utf-8"),
        "region_sales_b.csv",
    )
    id_a = ds_a["dataset_id"]
    id_b = ds_b["dataset_id"]

    run_id = runner.run_agent(
        "For each region, compare sales in the first dataset against the second "
        "dataset and report the difference.",
        [id_a, id_b],
    )

    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        assert run is not None
        assert run.status == "completed"
        code = run.code or ""
        assert code, "expected non-empty generated code"
        assert "df1" in code and "df2" in code, f"code did not reference both frames:\n{code}"
