"""Excel upload unit tests — sheet listing + sheet-aware loading. No LLM."""
import io

import pandas as pd

from datasets import store


def _make_xlsx_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(
            {"region": ["north", "south", "east"], "sales": [10, 20, 30]}
        ).to_excel(writer, sheet_name="Sales", index=False)
        pd.DataFrame(
            {"region": ["north", "south"], "cost": [5, 6]}
        ).to_excel(writer, sheet_name="Costs", index=False)
    return buf.getvalue()


def test_list_excel_sheets_returns_all_names():
    sheets = store.list_excel_sheets(_make_xlsx_bytes(), "book.xlsx")
    assert sheets == ["Sales", "Costs"]


def test_list_excel_sheets_invalid_raises():
    try:
        store.list_excel_sheets(b"not-an-excel-file", "bad.xlsx")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_load_excel_chosen_sheet(_isolated_db):
    result = store.load_excel(_make_xlsx_bytes(), "book.xlsx", sheet="Costs")
    assert result["kind"] == "xlsx"
    assert result["sheet"] == "Costs"
    assert result["row_count"] == 2
    assert result["column_count"] == 2
    ds_id = result["dataset_id"]
    df = store.get_dataframe(ds_id)
    assert df is not None
    assert list(df.columns) == ["region", "cost"]
    assert df.shape == (2, 2)


def test_load_excel_default_first_sheet(_isolated_db):
    result = store.load_excel(_make_xlsx_bytes(), "book.xlsx")
    ds_id = result["dataset_id"]
    df = store.get_dataframe(ds_id)
    # First sheet is "Sales" (3 rows, region+sales)
    assert result["row_count"] == 3
    assert set(df.columns) == {"region", "sales"}
