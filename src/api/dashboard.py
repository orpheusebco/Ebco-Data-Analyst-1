"""Dashboard: pin runs to a dashboard, list, reorder, and unpin them.

Pinning snapshots a run's answer + chart_spec into a PinnedItem so the
dashboard is stable even if the underlying run changes. NO LLM — deterministic.
"""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.models import PinnedItem, RunRow
from db.session import get_session

router = APIRouter()


class PinRequest(BaseModel):
    title: str | None = None


class ReorderRequest(BaseModel):
    position: int


def serialize_item(item: PinnedItem) -> dict:
    chart_spec = None
    if item.chart_spec:
        try:
            chart_spec = json.loads(item.chart_spec)
        except Exception:  # noqa: BLE001
            chart_spec = None
    return {
        "id": item.id,
        "run_id": item.run_id,
        "title": item.title,
        "chart_spec": chart_spec,
        "answer": item.answer,
        "position": item.position,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _default_title(run: RunRow) -> str:
    source = (run.question or run.answer or "Pinned item").strip()
    snippet = source.splitlines()[0] if source else "Pinned item"
    return snippet[:120] if snippet else "Pinned item"


@router.post("/runs/{run_id}/pin")
def pin_run(
    run_id: str,
    body: PinRequest = PinRequest(),
    session: Session = Depends(get_session),
) -> dict:
    run = session.get(RunRow, run_id)
    if run is None:
        raise api_error("NOT_FOUND", f"Run {run_id} not found", 404)

    title = (body.title or "").strip() or _default_title(run)
    max_pos = session.query(func.max(PinnedItem.position)).scalar()
    next_pos = (max_pos + 1) if max_pos is not None else 0

    item = PinnedItem(
        run_id=run_id,
        title=title,
        chart_spec=run.chart_spec,
        answer=run.answer,
        position=next_pos,
    )
    session.add(item)
    session.flush()
    return ok(serialize_item(item))


@router.get("/dashboard")
def list_dashboard(session: Session = Depends(get_session)) -> dict:
    items = (
        session.query(PinnedItem)
        .order_by(PinnedItem.position.asc())
        .all()
    )
    return ok({"items": [serialize_item(i) for i in items]})


@router.delete("/dashboard/{item_id}")
def unpin(item_id: str, session: Session = Depends(get_session)) -> dict:
    item = session.get(PinnedItem, item_id)
    if item is None:
        raise api_error("NOT_FOUND", f"Pinned item {item_id} not found", 404)
    session.delete(item)
    return ok({"deleted": item_id})


@router.patch("/dashboard/{item_id}")
def reorder(
    item_id: str,
    body: ReorderRequest,
    session: Session = Depends(get_session),
) -> dict:
    item = session.get(PinnedItem, item_id)
    if item is None:
        raise api_error("NOT_FOUND", f"Pinned item {item_id} not found", 404)
    item.position = body.position
    session.flush()
    return ok(serialize_item(item))
