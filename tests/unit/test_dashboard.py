"""Phase 3 backend: pin/dashboard + export contract tests (sqlite driver, no LLM)."""
import csv
import io
import json

import pandas as pd

from db.models import RunRow
from db.session import create_db_session


def _make_run(**overrides) -> str:
    run = RunRow(
        status="completed",
        question="total sales by region?",
        plan="group by region and sum sales",
        code="result = df.groupby('region')['sales'].sum().reset_index()",
        result_text="region  sales\nnorth   30\nsouth   70",
        answer="North totals 30, South totals 70.",
        chart_spec=json.dumps({"data": [{"type": "bar"}]}),
        dataset_ids=json.dumps([]),
    )
    for k, v in overrides.items():
        setattr(run, k, v)
    with create_db_session() as session:
        session.add(run)
        session.flush()
        rid = run.id
    return rid


# ---------- Pin flow ----------

def test_pin_list_and_delete(api_client):
    rid = _make_run()

    # Pin (happy path)
    r = api_client.post(f"/runs/{rid}/pin", json={"title": "My Region Chart"})
    assert r.status_code == 200
    item = r.json()["data"]
    assert item["run_id"] == rid
    assert item["title"] == "My Region Chart"
    assert item["answer"] == "North totals 30, South totals 70."
    assert item["chart_spec"] == {"data": [{"type": "bar"}]}
    assert item["position"] == 0
    item_id = item["id"]

    # List
    r = api_client.get("/dashboard")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == item_id

    # Delete
    r = api_client.delete(f"/dashboard/{item_id}")
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] == item_id

    # Empty again
    r = api_client.get("/dashboard")
    assert r.json()["data"]["items"] == []


def test_pin_default_title_and_positions(api_client):
    # Edge case: blank title falls back to a question snippet; positions increment.
    rid = _make_run()
    r1 = api_client.post(f"/runs/{rid}/pin", json={})
    assert r1.status_code == 200
    assert r1.json()["data"]["title"].startswith("total sales by region")
    assert r1.json()["data"]["position"] == 0

    r2 = api_client.post(f"/runs/{rid}/pin", json={"title": "second"})
    assert r2.json()["data"]["position"] == 1

    # Ordered asc
    items = api_client.get("/dashboard").json()["data"]["items"]
    assert [i["position"] for i in items] == [0, 1]


def test_pin_run_not_found(api_client):
    # Error path
    r = api_client.post("/runs/does-not-exist/pin", json={"title": "x"})
    assert r.status_code == 404


def test_reorder_and_delete_missing(api_client):
    rid = _make_run()
    item_id = api_client.post(f"/runs/{rid}/pin", json={}).json()["data"]["id"]

    r = api_client.patch(f"/dashboard/{item_id}", json={"position": 5})
    assert r.status_code == 200
    assert r.json()["data"]["position"] == 5

    r = api_client.delete("/dashboard/nope")
    assert r.status_code == 404
    r = api_client.patch("/dashboard/nope", json={"position": 1})
    assert r.status_code == 404


# ---------- Export CSV ----------

def test_export_csv_reexecutes_code(api_client):
    from datasets import store

    df = pd.DataFrame({"region": ["north", "south", "north"], "sales": [10, 70, 20]})
    ds_id = "ds-export-1"
    store.register_dataframe(ds_id, df)

    rid = _make_run(dataset_ids=json.dumps([ds_id]))

    r = api_client.post(f"/runs/{rid}/export", json={"format": "csv"})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]

    rows = list(csv.DictReader(io.StringIO(r.text)))
    by_region = {row["region"]: float(row["sales"]) for row in rows}
    assert by_region == {"north": 30.0, "south": 70.0}


def test_export_csv_fallback_on_bad_code(api_client):
    # Edge/error path: unresolvable dataset -> falls back to result_text CSV.
    rid = _make_run(
        dataset_ids=json.dumps(["missing-ds"]),
        code="result = df.foo()",
        result_text="fallback content here",
    )
    r = api_client.post(f"/runs/{rid}/export", json={"format": "csv"})
    assert r.status_code == 200
    assert "fallback content here" in r.text


def test_export_report_markdown(api_client):
    rid = _make_run()
    r = api_client.post(f"/runs/{rid}/export", json={"format": "report"})
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    body = r.text
    assert "total sales by region?" in body
    assert "result = df.groupby('region')['sales'].sum()" in body
    assert "## Answer" in body


def test_export_run_not_found(api_client):
    r = api_client.post("/runs/nope/export", json={"format": "csv"})
    assert r.status_code == 404


def test_export_bad_format(api_client):
    rid = _make_run()
    r = api_client.post(f"/runs/{rid}/export", json={"format": "pdf"})
    assert r.status_code == 400
