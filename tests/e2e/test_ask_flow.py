"""End-to-end HTTP flow — REAL Gemini. Upload a CSV, consume the /ask SSE stream,
assert a real answer with the correct full-data number and a persisted run.
"""
import io
import json

import pandas as pd
import pytest

ROWS = 50_000


def _csv_bytes() -> bytes:
    amount = [i % 100 for i in range(ROWS)]  # full mean 49.5, head-sample 9.5
    df = pd.DataFrame({"amount": amount})
    return df.to_csv(index=False).encode("utf-8")


@pytest.mark.usefixtures("_require_llm_key")
def test_upload_then_ask_sse(api_client):
    up = api_client.post(
        "/datasets", files={"file": ("big.csv", io.BytesIO(_csv_bytes()), "text/csv")}
    )
    assert up.status_code == 200
    dataset_id = up.json()["data"]["dataset_id"]
    assert up.json()["data"]["row_count"] == ROWS

    events: list[tuple[str, dict]] = []
    tokens: list[str] = []
    with api_client.stream(
        "POST",
        "/ask",
        json={
            "dataset_ids": [dataset_id],
            "question": "What is the mean of the amount column over all rows?",
        },
    ) as r:
        assert r.status_code == 200
        cur_event = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                cur_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
                events.append((cur_event, data))
                if cur_event == "token":
                    tokens.append(data.get("text", ""))

    types = {e for e, _ in events}
    assert "status" in types
    assert "token" in types
    assert "done" in types

    answer = "".join(tokens).replace(",", "")
    assert "49.5" in answer or "49.50" in answer, f"answer missing full mean: {answer}"

    done = [d for e, d in events if e == "done"][0]
    assert done["status"] == "completed"
    run_id = done["run_id"]

    detail = api_client.get(f"/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["code"]
    assert body["answer"]

    hist = api_client.get(f"/datasets/{dataset_id}/runs")
    assert hist.status_code == 200
    assert any(run["run_id"] == run_id for run in hist.json()["data"]["runs"])
