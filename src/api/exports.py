"""Export a run's data (CSV) or a Markdown report as a file download.

Deterministic — NO LLM. See analysis/export.py for the builders.
"""
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from analysis.export import build_csv, build_report
from api._common import api_error
from config.settings import get_settings
from db.models import RunRow
from db.session import get_session

router = APIRouter()


class ExportRequest(BaseModel):
    format: str = "csv"


def _download_name(run: RunRow, ext: str) -> str:
    base = (run.question or run.id or "export").strip()
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in base)
    safe = safe.strip().replace(" ", "_")[:60] or run.id
    return f"{safe}.{ext}"


@router.post("/runs/{run_id}/export")
def export_run(
    run_id: str,
    body: ExportRequest,
    session: Session = Depends(get_session),
) -> FileResponse:
    run = session.get(RunRow, run_id)
    if run is None:
        raise api_error("NOT_FOUND", f"Run {run_id} not found", 404)

    fmt = (body.format or "csv").lower()
    if fmt not in {"csv", "report"}:
        raise api_error("BAD_REQUEST", f"Unsupported export format: {fmt}", 400)

    exports_dir = Path(get_settings().exports_dir)

    if fmt == "csv":
        path = build_csv(run, exports_dir)
        return FileResponse(
            path=str(path),
            media_type="text/csv",
            filename=_download_name(run, "csv"),
        )

    path = build_report(run, exports_dir)
    return FileResponse(
        path=str(path),
        media_type="text/markdown",
        filename=_download_name(run, "md"),
    )
