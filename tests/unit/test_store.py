"""Dataset store unit tests — schema/sampling, persistence, var naming. No LLM."""
import pandas as pd

from datasets import store


def _make_csv_bytes(rows: int = 30) -> bytes:
    df = pd.DataFrame({"amount": range(rows), "region": ["x", "y"] * (rows // 2)})
    return df.to_csv(index=False).encode("utf-8")


def test_load_csv_persists_and_registers(_isolated_db):
    result = store.load_csv(_make_csv_bytes(30), "sales.csv")
    assert result["kind"] == "csv"
    assert result["row_count"] == 30
    assert result["column_count"] == 2
    assert result["profile"] is None
    ds_id = result["dataset_id"]
    assert store.dataset_exists(ds_id)
    assert store.get_dataframe(ds_id) is not None


def test_schema_and_samples_caps_rows(_isolated_db):
    result = store.load_csv(_make_csv_bytes(100), "big.csv")
    ds_id = result["dataset_id"]
    schema = store.get_schema_and_samples([ds_id])
    assert "df" in schema  # single dataset -> variable name 'df'
    entry = schema["df"]
    assert entry["row_count"] == 100
    # Only a sample (<=20 rows) is exposed — never the full data
    assert len(entry["sample_rows"]) <= store.SAMPLE_ROWS
    col_names = {c["name"] for c in entry["columns"]}
    assert col_names == {"amount", "region"}


def test_single_dataset_var_name_is_df():
    assert store.dataframe_var_name(0, ["only"]) == "df"


def test_build_namespace_unknown_dataset_raises(_isolated_db):
    try:
        store.build_namespace(["does-not-exist"])
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_list_datasets_empty(_isolated_db):
    assert store.list_datasets() == []
