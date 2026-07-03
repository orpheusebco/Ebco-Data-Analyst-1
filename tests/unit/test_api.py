"""API contract tests — no LLM key required, graph is not invoked."""
import io

import pandas as pd


def test_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_datasets_list_empty(api_client):
    r = api_client.get("/datasets")
    assert r.status_code == 200
    assert r.json()["data"]["datasets"] == []


def test_upload_and_list_dataset(api_client):
    df = pd.DataFrame({"amount": range(10), "region": ["a", "b"] * 5})
    buf = io.BytesIO(df.to_csv(index=False).encode())
    r = api_client.post("/datasets", files={"file": ("sales.csv", buf, "text/csv")})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["row_count"] == 10
    assert data["column_count"] == 2
    assert data["kind"] == "csv"
    assert data["profile"] is None

    r2 = api_client.get("/datasets")
    names = [d["name"] for d in r2.json()["data"]["datasets"]]
    assert "sales.csv" in names


def test_upload_rejects_non_csv(api_client):
    buf = io.BytesIO(b"not a csv")
    r = api_client.post("/datasets", files={"file": ("data.txt", buf, "text/plain")})
    assert r.status_code == 400


def test_ask_empty_question_rejected(api_client):
    r = api_client.post("/ask", json={"dataset_ids": ["x"], "question": "  "})
    assert r.status_code == 400


def test_ask_unknown_dataset_rejected(api_client):
    r = api_client.post("/ask", json={"dataset_ids": ["nope"], "question": "average?"})
    assert r.status_code == 400


def test_ask_requires_dataset_ids(api_client):
    r = api_client.post("/ask", json={"dataset_ids": [], "question": "x"})
    assert r.status_code == 422


def test_get_run_not_found(api_client):
    r = api_client.get("/runs/nonexistent-id")
    assert r.status_code == 404
