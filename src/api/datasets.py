from fastapi import APIRouter, File, Form, UploadFile

from api._common import ok, api_error
from config.settings import get_settings
from datasets import store

router = APIRouter()

_EXCEL_EXTS = (".xlsx", ".xls")


@router.post("/datasets/excel/sheets")
async def excel_sheets(file: UploadFile = File(...)) -> dict:
    name = file.filename or "upload.xlsx"
    if not name.lower().endswith(_EXCEL_EXTS):
        raise api_error(
            "UNSUPPORTED_TYPE",
            "Only .xlsx/.xls files are supported for sheet listing.",
            400,
        )
    contents = await file.read()
    if not contents:
        raise api_error("EMPTY_FILE", "Uploaded file is empty.", 400)
    try:
        sheets = store.list_excel_sheets(contents, name)
    except ValueError as exc:
        raise api_error("UNREADABLE_FILE", str(exc), 400)
    return ok({"sheets": sheets})


@router.post("/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    sheet: str | None = Form(None),
) -> dict:
    name = file.filename or "upload.csv"
    lower = name.lower()
    is_csv = lower.endswith(".csv")
    is_excel = lower.endswith(_EXCEL_EXTS)
    if not (is_csv or is_excel):
        raise api_error(
            "UNSUPPORTED_TYPE",
            "Only CSV and Excel (.xlsx/.xls) files are supported.",
            400,
        )
    contents = await file.read()
    if not contents:
        raise api_error("EMPTY_FILE", "Uploaded file is empty.", 400)
    if len(contents) > get_settings().max_upload_bytes:
        raise api_error("FILE_TOO_LARGE", "File exceeds the ~100 MB limit.", 413)
    try:
        if is_csv:
            result = store.load_csv(contents, name)
        else:
            result = store.load_excel(contents, name, sheet)
    except ValueError as exc:
        raise api_error("UNREADABLE_FILE", str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        raise api_error("LOAD_FAILED", f"Failed to load dataset: {exc}", 500)
    return ok(result)


@router.get("/datasets")
def list_datasets() -> dict:
    return ok({"datasets": store.list_datasets()})


@router.get("/datasets/{dataset_id}/profile")
def get_dataset_profile(dataset_id: str) -> dict:
    if not store.dataset_exists(dataset_id):
        raise api_error("DATASET_NOT_FOUND", "Unknown dataset_id.", 404)
    return ok({"profile": store.get_profile(dataset_id)})
