"""In-memory dataset registry + persistence of Dataset metadata.

The full DataFrame lives only in process memory; the DB stores metadata and
the uploaded file is saved under data/uploads/. Only column schema + a small
sample (<=20 rows) is ever exposed to the LLM.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from uuid import uuid4

import pandas as pd

from analysis.profiler import build_profile
from config.settings import get_settings
from db.models import DatasetProfile, DatasetRow
from db.session import create_db_session

SAMPLE_ROWS = 20

_frames: dict[str, pd.DataFrame] = {}
_lock = threading.Lock()


def _uploads_dir() -> Path:
    p = Path(get_settings().uploads_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def register_dataframe(dataset_id: str, df: pd.DataFrame) -> None:
    with _lock:
        _frames[dataset_id] = df


def get_dataframe(dataset_id: str) -> pd.DataFrame | None:
    with _lock:
        return _frames.get(dataset_id)


def has_dataframe(dataset_id: str) -> bool:
    with _lock:
        return dataset_id in _frames


def load_csv(file_bytes: bytes, name: str) -> dict:
    """Persist the upload, load it into the registry, and store a Dataset row.

    Returns a dict matching the POST /datasets response shape.
    """
    dataset_id = str(uuid4())
    safe_name = Path(name).name or "upload.csv"
    dest = _uploads_dir() / f"{dataset_id}__{safe_name}"
    dest.write_bytes(file_bytes)

    try:
        df = pd.read_csv(dest)
    except Exception as exc:  # noqa: BLE001 - surface a clean load error
        raise ValueError(f"Could not parse CSV: {exc}") from exc

    register_dataframe(dataset_id, df)

    row_count = int(df.shape[0])
    column_count = int(df.shape[1])

    profile = build_profile(df)

    with create_db_session() as session:
        session.add(
            DatasetRow(
                id=dataset_id,
                name=safe_name,
                source_path=str(dest),
                kind="csv",
                row_count=row_count,
                column_count=column_count,
            )
        )
        session.add(
            DatasetProfile(
                dataset_id=dataset_id,
                profile_json=json.dumps(profile),
            )
        )

    return {
        "dataset_id": dataset_id,
        "name": safe_name,
        "kind": "csv",
        "row_count": row_count,
        "column_count": column_count,
        "profile": profile,
    }


def get_profile(dataset_id: str) -> dict | None:
    """Load and parse the persisted data profile for a dataset (reads DB)."""
    with create_db_session() as session:
        row = (
            session.query(DatasetProfile)
            .filter(DatasetProfile.dataset_id == dataset_id)
            .order_by(DatasetProfile.created_at.desc())
            .first()
        )
        if row is None:
            return None
        return json.loads(row.profile_json)


def _reload_from_disk(dataset_id: str) -> pd.DataFrame | None:
    """DataFrames don't survive a restart; reload from the stored file if needed."""
    with create_db_session() as session:
        row = session.get(DatasetRow, dataset_id)
        if row is None:
            return None
        path = row.source_path
        kind = row.kind
    try:
        if kind == "csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
    except Exception:  # noqa: BLE001
        return None
    register_dataframe(dataset_id, df)
    return df


def resolve_dataframe(dataset_id: str) -> pd.DataFrame | None:
    df = get_dataframe(dataset_id)
    if df is None:
        df = _reload_from_disk(dataset_id)
    return df


def dataframe_var_name(index: int, dataset_ids: list[str]) -> str:
    """Stable exec namespace name for a dataset. Single dataset -> 'df'."""
    if len(dataset_ids) == 1:
        return "df"
    return f"df{index + 1}"


def build_namespace(dataset_ids: list[str]) -> dict[str, pd.DataFrame]:
    ns: dict[str, pd.DataFrame] = {}
    for i, ds_id in enumerate(dataset_ids):
        df = resolve_dataframe(ds_id)
        if df is None:
            raise KeyError(f"Unknown dataset_id: {ds_id}")
        ns[dataframe_var_name(i, dataset_ids)] = df
    return ns


def get_schema_and_samples(dataset_ids: list[str]) -> dict:
    """Return column schema (name+dtype) + <=20 sample rows per dataset.

    ONLY this is ever sent to the LLM — never the full data.
    """
    out: dict = {}
    for i, ds_id in enumerate(dataset_ids):
        df = resolve_dataframe(ds_id)
        if df is None:
            raise KeyError(f"Unknown dataset_id: {ds_id}")
        var = dataframe_var_name(i, dataset_ids)
        columns = [
            {"name": str(col), "dtype": str(df[col].dtype)} for col in df.columns
        ]
        sample = df.head(SAMPLE_ROWS)
        out[var] = {
            "dataset_id": ds_id,
            "dataframe_var": var,
            "row_count": int(df.shape[0]),
            "columns": columns,
            "sample_rows": json.loads(
                sample.to_json(orient="records", date_format="iso")
            ),
        }
    return out


def list_datasets() -> list[dict]:
    with create_db_session() as session:
        rows = (
            session.query(DatasetRow)
            .order_by(DatasetRow.created_at.desc())
            .all()
        )
        return [
            {
                "dataset_id": r.id,
                "name": r.name,
                "kind": r.kind,
                "row_count": r.row_count,
                "column_count": r.column_count,
            }
            for r in rows
        ]


def dataset_exists(dataset_id: str) -> bool:
    with create_db_session() as session:
        return session.get(DatasetRow, dataset_id) is not None
