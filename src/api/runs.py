import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api._common import ok, api_error
from db.session import get_session
from db.models import RunRow

router = APIRouter()


def serialize_run(run: RunRow) -> dict:
    try:
        dataset_ids = json.loads(run.dataset_ids) if run.dataset_ids else []
    except Exception:  # noqa: BLE001
        dataset_ids = []
    return {
        "run_id": run.id,
        "dataset_ids": dataset_ids,
        "question": run.question,
        "plan": run.plan,
        "code": run.code,
        "attempts": run.attempts,
        "result_text": run.result_text,
        "answer": run.answer,
        "clarifying_question": run.clarifying_question,
        "status": run.status,
        "error": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = session.get(RunRow, run_id)
    if run is None:
        raise api_error("NOT_FOUND", f"Run {run_id} not found", 404)
    return ok(serialize_run(run))
