"""Unit tests for the pure-pandas data profiler. No LLM, no DB."""
import json

import numpy as np
import pandas as pd

from analysis.profiler import build_profile


def _make_df() -> pd.DataFrame:
    # 6 rows: one high-null column, one constant column, a duplicate row,
    # and a numeric outlier in `amount`.
    df = pd.DataFrame(
        {
            "amount": [10, 12, 11, 13, 1000, 12],  # 1000 is an outlier
            "region": ["east", "west", "east", "north", "south", "west"],
            "constant": [1, 1, 1, 1, 1, 1],  # constant column
            "notes": [None, None, None, None, "ok", "ok"],  # >30% null (4/6)
        }
    )
    # force a duplicate row (row 5 duplicates row 1: 12/west/1/ok? no) -> add explicit dup
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # duplicate first row
    return df


def _flag_types(profile: dict) -> set[str]:
    return {f["type"] for f in profile["quality_flags"]}


def test_row_and_column_counts():
    df = _make_df()
    profile = build_profile(df)
    assert profile["column_count"] == 4
    assert profile["row_count"] == 7


def test_dtypes_and_null_count():
    profile = build_profile(_make_df())
    cols = {c["name"]: c for c in profile["columns"]}
    assert cols["amount"]["dtype"].startswith("int") or cols["amount"]["dtype"].startswith("float")
    assert cols["region"]["dtype"] in ("object", "str")
    # notes: 4 nulls in original 6 rows + duplicated first row (None) = 5 nulls / 7
    assert cols["notes"]["null_count"] == 5
    assert cols["notes"]["null_pct"] > 30.0
    # numeric min/max present, non-numeric min/max are None
    assert cols["amount"]["min"] is not None
    assert cols["amount"]["max"] == 1000
    assert cols["region"]["min"] is None
    assert cols["region"]["max"] is None
    # sample values are strings, capped at 5
    assert all(isinstance(v, str) for v in cols["region"]["sample_values"])
    assert len(cols["region"]["sample_values"]) <= 5


def test_quality_flags_detect_each_kind():
    profile = build_profile(_make_df())
    types = _flag_types(profile)
    assert "high_null" in types
    assert "constant_column" in types
    assert "duplicate_rows" in types
    assert "numeric_outliers" in types
    # constant column reported by name
    constant_flag = next(f for f in profile["quality_flags"] if f["type"] == "constant_column")
    assert "constant" in constant_flag["columns"]
    outlier_flag = next(f for f in profile["quality_flags"] if f["type"] == "numeric_outliers")
    assert "amount" in outlier_flag["columns"]


def test_profile_is_json_serializable():
    # include numpy types and NaN to prove JSON-safety
    df = pd.DataFrame(
        {
            "x": np.array([1, 2, 3], dtype=np.int64),
            "y": np.array([1.5, np.nan, 2.5], dtype=np.float64),
            "d": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01"]),
        }
    )
    profile = build_profile(df)
    # must not raise
    dumped = json.dumps(profile)
    assert isinstance(dumped, str)


def test_empty_dataframe_is_safe():
    profile = build_profile(pd.DataFrame())
    assert profile["row_count"] == 0
    assert profile["column_count"] == 0
    assert profile["columns"] == []
    json.dumps(profile)  # must not raise
