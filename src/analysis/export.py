"""Deterministic export builders — CSV (data) and Markdown (report).

NO LLM. Exports bundle already-stored run fields; the CSV path re-executes
the run's stored pandas code to regenerate the result table.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def coerce_to_frame(result: Any) -> pd.DataFrame | None:
    """Coerce an arbitrary execution result into a DataFrame, or None."""
    if result is None:
        return None
    if isinstance(result, pd.DataFrame):
        return result
    if isinstance(result, pd.Series):
        return result.to_frame()
    if isinstance(result, dict):
        # {key: value} -> two-column frame
        try:
            return pd.DataFrame(
                {"key": list(result.keys()), "value": list(result.values())}
            )
        except Exception:  # noqa: BLE001
            return pd.DataFrame([result])
    # scalar / other -> single-cell frame
    return pd.DataFrame({"result": [result]})


def clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Drop fully-empty columns and strip whitespace on object columns."""
    cleaned = df.dropna(axis=1, how="all").copy()
    for col in cleaned.columns:
        if cleaned[col].dtype == object:
            cleaned[col] = cleaned[col].map(
                lambda v: v.strip() if isinstance(v, str) else v
            )
    return cleaned


def build_csv(run: Any, exports_dir: Path) -> Path:
    """Regenerate the run's result table and write a cleaned CSV.

    Falls back to writing run.result_text if re-execution yields nothing.
    Imports the store lazily to avoid import coupling.
    """
    from analysis.executor import execute_code
    from datasets import store

    exports_dir.mkdir(parents=True, exist_ok=True)
    out_path = exports_dir / f"{run.id}.csv"

    frame: pd.DataFrame | None = None
    if run.code:
        try:
            dataset_ids = json.loads(run.dataset_ids) if run.dataset_ids else []
            namespace = store.build_namespace(dataset_ids)
            result, _stdout, error = execute_code(run.code, namespace)
            if error is None:
                frame = coerce_to_frame(result)
        except Exception:  # noqa: BLE001 - fall back to result_text
            frame = None

    if frame is not None and not frame.empty:
        clean_frame(frame).to_csv(out_path, index=False)
    else:
        # Fallback: dump the stored textual result as a single column.
        fallback = pd.DataFrame({"result_text": [run.result_text or ""]})
        fallback.to_csv(out_path, index=False)

    return out_path


def build_report(run: Any, exports_dir: Path) -> Path:
    """Assemble a Markdown report bundling stored run fields. NO LLM."""
    exports_dir.mkdir(parents=True, exist_ok=True)
    out_path = exports_dir / f"{run.id}.md"

    has_chart = bool(run.chart_spec)
    parts: list[str] = []
    parts.append(f"# Analysis Report\n")
    parts.append(f"**Run ID:** {run.id}\n")
    parts.append("## Question\n")
    parts.append(f"{run.question or '_(none)_'}\n")
    parts.append("## Plan\n")
    parts.append(f"{run.plan or '_(none)_'}\n")
    parts.append("## Answer\n")
    parts.append(f"{run.answer or '_(none)_'}\n")
    parts.append("## Generated Code\n")
    parts.append("```python\n" + (run.code or "") + "\n```\n")
    parts.append("## Result\n")
    parts.append("```\n" + (run.result_text or "") + "\n```\n")
    if has_chart:
        parts.append("## Chart\n")
        parts.append("_A chart was generated for this run (see the app)._\n")

    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path
