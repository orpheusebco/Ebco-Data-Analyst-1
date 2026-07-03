import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api._common import api_error
from datasets import store
from domain.run import AskRequest
from graph.runner import stream_ask

router = APIRouter()


def _sse(event: dict) -> str:
    event_type = event.get("type", "message")
    payload = {k: v for k, v in event.items() if k != "type"}
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


@router.post("/ask")
def ask(req: AskRequest):
    question = (req.question or "").strip()
    if not question:
        raise api_error("EMPTY_QUESTION", "Question must not be empty.", 400)
    for ds_id in req.dataset_ids:
        if not store.dataset_exists(ds_id):
            raise api_error("UNKNOWN_DATASET", f"Unknown dataset_id: {ds_id}", 400)

    def event_stream():
        try:
            for event in stream_ask(question, req.dataset_ids):
                yield _sse(event)
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
