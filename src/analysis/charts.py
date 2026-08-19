"""Deterministic Plotly-spec assembly from an LLM chart-type choice + exec result.

The LLM only picks the chart_type and which columns map to x / y (see
prompts/chart.md). This module coerces the execution result (a DataFrame,
Series, scalar, or dict) into plottable arrays and assembles a JSON-serializable
Plotly figure spec: {"data": [...], "layout": {...}}.

Everything returned is plain-Python / JSON-safe — no numpy scalars, no NaN.
Returns None whenever the result cannot be turned into a meaningful chart.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

_SUPPORTED = {"bar", "line", "scatter", "histogram", "pie"}
_MAX_POINTS = 500


def _clean_scalar(v: Any) -> Any:
    """Coerce a single value into a JSON-safe scalar (no numpy, no NaN)."""
    if v is None:
        return None
    if isinstance(v, float):
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(v, (int, str, bool)):
        return v
    # numpy / pandas scalar types
    try:
        item = v.item()  # numpy scalar -> python scalar
    except Exception:  # noqa: BLE001
        return str(v)
    if isinstance(item, float) and (math.isnan(item) or math.isinf(item)):
        return None
    return item


def _clean_list(values: Any) -> list:
    return [_clean_scalar(v) for v in values]


def _as_frame(result: Any) -> pd.DataFrame | None:
    """Coerce common result shapes into a tidy DataFrame we can plot."""
    if isinstance(result, pd.DataFrame):
        df = result.reset_index()
        return df
    if isinstance(result, pd.Series):
        s = result
        name = s.name if s.name is not None else "value"
        df = s.reset_index()
        # After reset_index the value column is the last one; name it stably.
        df.columns = [*[str(c) for c in df.columns[:-1]], str(name)]
        return df
    if isinstance(result, dict):
        # dict of scalars -> two-column (key, value); dict of lists -> columns.
        if result and all(not isinstance(v, (list, tuple, pd.Series)) for v in result.values()):
            return pd.DataFrame(
                {"key": list(result.keys()), "value": list(result.values())}
            )
        try:
            return pd.DataFrame(result).reset_index()
        except Exception:  # noqa: BLE001
            return None
    return None


def _pick_column(df: pd.DataFrame, name: Any, fallback_idx: int) -> str | None:
    cols = [str(c) for c in df.columns]
    if isinstance(name, str) and name in cols:
        return name
    if 0 <= fallback_idx < len(cols):
        return cols[fallback_idx]
    return None


def build_chart_spec(chart_type: str, result: Any, question: str) -> dict | None:
    """Build a Plotly figure spec from a chart-type choice and an exec result.

    `chart_type` is the LLM's choice; extra hints (x/y/title) may be passed by
    the caller inside a dict form via build_chart_spec_from_choice, but the core
    contract here is (chart_type, result, question). Returns None if not
    plottable.
    """
    return build_chart_spec_from_choice(
        {"chart_type": chart_type, "title": question}, result, question
    )


def build_chart_spec_from_choice(
    choice: dict, result: Any, question: str
) -> dict | None:
    """Assemble a Plotly spec from a full LLM choice dict + the exec result.

    choice = {"chart_type", "x"?, "y"?, "title"?}
    """
    chart_type = str(choice.get("chart_type") or "").strip().lower()
    if chart_type not in _SUPPORTED:
        return None

    df = _as_frame(result)
    if df is None or df.empty or df.shape[1] == 0:
        return None

    # Cap the number of points so specs stay small and JSON-friendly.
    if len(df) > _MAX_POINTS:
        df = df.head(_MAX_POINTS)

    cols = [str(c) for c in df.columns]
    df.columns = cols

    title = str(choice.get("title") or question or "").strip() or "Chart"
    x_hint = choice.get("x")
    y_hint = choice.get("y")

    try:
        if chart_type == "histogram":
            col = _pick_column(df, x_hint, len(cols) - 1)
            if col is None:
                return None
            trace = {"type": "histogram", "x": _clean_list(df[col])}
            layout = {"title": title, "xaxis": {"title": col}, "yaxis": {"title": "count"}}
            return {"data": [trace], "layout": layout}

        if chart_type == "pie":
            label_col = _pick_column(df, x_hint, 0)
            value_col = _pick_column(df, y_hint, len(cols) - 1)
            if label_col is None or value_col is None:
                return None
            trace = {
                "type": "pie",
                "labels": _clean_list(df[label_col]),
                "values": _clean_list(df[value_col]),
            }
            return {"data": [trace], "layout": {"title": title}}

        # bar / line / scatter share the x + one-or-more-y shape.
        x_col = _pick_column(df, x_hint, 0)
        if x_col is None:
            return None
        x_values = _clean_list(df[x_col])

        y_cols: list[str] = []
        if isinstance(y_hint, list):
            for name in y_hint:
                c = _pick_column(df, name, -1)
                if c and c not in y_cols and c != x_col:
                    y_cols.append(c)
        elif isinstance(y_hint, str):
            c = _pick_column(df, y_hint, -1)
            if c and c != x_col:
                y_cols.append(c)
        if not y_cols:
            # default: every remaining column that isn't x.
            y_cols = [c for c in cols if c != x_col]
        if not y_cols:
            return None

        # For a single-series bar chart of categories, sort by magnitude so the
        # comparison reads largest-to-smallest instead of in arbitrary row order.
        if chart_type == "bar" and len(y_cols) == 1:
            try:
                df = df.sort_values(by=y_cols[0], ascending=False)
                x_values = _clean_list(df[x_col])
            except Exception:  # noqa: BLE001 - never let sorting break the chart
                pass

        mode_map = {"scatter": "markers", "line": "lines"}
        plotly_type = "bar" if chart_type == "bar" else "scatter"

        traces = []
        for c in y_cols:
            trace: dict[str, Any] = {
                "type": plotly_type,
                "name": c,
                "x": x_values,
                "y": _clean_list(df[c]),
            }
            if chart_type in mode_map:
                trace["mode"] = mode_map[chart_type]
            traces.append(trace)

        layout = {
            "title": title,
            "xaxis": {"title": x_col},
            "yaxis": {"title": y_cols[0] if len(y_cols) == 1 else "value"},
        }
        return {"data": traces, "layout": layout}
    except Exception:  # noqa: BLE001 - never let chart assembly raise
        return None
