"""Pure-pandas data profiling — no LLM, fast, JSON-safe output.

`build_profile(df)` computes a data profile plus data-quality flags for an
uploaded dataset. Every value in the returned dict is JSON-serializable:
numpy scalars are cast to native Python types and NaN/NaT become None.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd
from pandas.api import types as ptypes

HIGH_NULL_PCT = 30.0  # columns with more than this % nulls are flagged
MAX_SAMPLE_VALUES = 5


def _json_safe(value: Any) -> Any:
    """Coerce a scalar to a JSON-serializable native Python value (NaN -> None)."""
    if value is None:
        return None
    # pandas missing sentinels
    try:
        if value is pd.NaT or (ptypes.is_scalar(value) and pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    # numpy / pandas scalar unwrapping
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (int, bool, str)):
        return value
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    # dates / times / anything else -> string
    return str(value)


def _min_max(series: pd.Series) -> tuple[Any, Any]:
    """min/max for numeric or datetime columns only; else (None, None)."""
    if ptypes.is_numeric_dtype(series) or ptypes.is_datetime64_any_dtype(series):
        non_null = series.dropna()
        if non_null.empty:
            return None, None
        return _json_safe(non_null.min()), _json_safe(non_null.max())
    return None, None


def _sample_values(series: pd.Series) -> list[str]:
    values: list[str] = []
    for v in series.dropna().unique()[:MAX_SAMPLE_VALUES]:
        safe = _json_safe(v)
        values.append(safe if isinstance(safe, str) else str(safe))
    return values


def _outlier_columns(df: pd.DataFrame) -> list[str]:
    """Numeric columns containing values beyond 1.5*IQR of Q1/Q3."""
    affected: list[str] = []
    for col in df.columns:
        series = df[col]
        if not ptypes.is_numeric_dtype(series) or ptypes.is_bool_dtype(series):
            continue
        non_null = series.dropna()
        if non_null.empty:
            continue
        q1 = non_null.quantile(0.25)
        q3 = non_null.quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        if ((non_null < lower) | (non_null > upper)).any():
            affected.append(str(col))
    return affected


def build_profile(df: pd.DataFrame) -> dict:
    """Compute a JSON-safe data profile + quality flags for a DataFrame."""
    if df is None:
        df = pd.DataFrame()

    row_count = int(df.shape[0])
    column_count = int(df.shape[1])

    columns: list[dict] = []
    high_null_cols: list[str] = []
    constant_cols: list[str] = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        null_pct = round((null_count / row_count) * 100, 2) if row_count else 0.0
        distinct_count = int(series.dropna().nunique())
        col_min, col_max = _min_max(series)
        columns.append(
            {
                "name": str(col),
                "dtype": str(series.dtype),
                "null_count": null_count,
                "null_pct": null_pct,
                "distinct_count": distinct_count,
                "min": col_min,
                "max": col_max,
                "sample_values": _sample_values(series),
            }
        )
        if null_pct > HIGH_NULL_PCT:
            high_null_cols.append(str(col))
        if distinct_count <= 1:
            constant_cols.append(str(col))

    quality_flags: list[dict] = []

    if high_null_cols:
        quality_flags.append(
            {
                "type": "high_null",
                "severity": "warning",
                "message": (
                    f"{len(high_null_cols)} column(s) have more than "
                    f"{int(HIGH_NULL_PCT)}% missing values."
                ),
                "columns": high_null_cols,
            }
        )

    if constant_cols:
        quality_flags.append(
            {
                "type": "constant_column",
                "severity": "info",
                "message": (
                    f"{len(constant_cols)} column(s) contain a single "
                    "constant value (or all nulls)."
                ),
                "columns": constant_cols,
            }
        )

    duplicate_count = int(df.duplicated().sum()) if column_count else 0
    if duplicate_count > 0:
        quality_flags.append(
            {
                "type": "duplicate_rows",
                "severity": "warning",
                "message": f"{duplicate_count} duplicate row(s) detected.",
                "columns": [],
            }
        )

    outlier_cols = _outlier_columns(df) if column_count else []
    if outlier_cols:
        quality_flags.append(
            {
                "type": "numeric_outliers",
                "severity": "info",
                "message": (
                    f"{len(outlier_cols)} numeric column(s) contain outliers "
                    "beyond 1.5x the interquartile range."
                ),
                "columns": outlier_cols,
            }
        )

    return {
        "row_count": row_count,
        "column_count": column_count,
        "columns": columns,
        "quality_flags": quality_flags,
    }
