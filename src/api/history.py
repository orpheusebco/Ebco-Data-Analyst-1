import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api._common import ok
from db.models import RunRow
from db.session import get_session

router = APIRouter()


@router.get("/datasets/{dataset_id}/runs")
def dataset_runs(dataset_id: str, session: Session = Depends(get_session)) -> dict:
    rows = (
        session.query(RunRow)
        .order_by(RunRow.created_at.desc())
        .all()
    )
    runs = []
    for r in rows:
        try:
            ids = json.loads(r.dataset_ids) if r.dataset_ids else []
        except Exception:  # noqa: BLE001
            ids = []
        if dataset_id not in ids:
            continue
        runs.append(
            {
                "run_id": r.id,
                "question": r.question,
                "code": r.code,
                "result_text": r.result_text,
                "answer": r.answer,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return ok({"runs": runs})
