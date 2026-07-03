from fastapi import APIRouter, File, UploadFile

from api._common import ok, api_error
from config.settings import get_settings
from datasets import store

router = APIRouter()


@router.post("/datasets")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    name = file.filename or "upload.csv"
    if not name.lower().endswith(".csv"):
        raise api_error(
            "UNSUPPORTED_TYPE",
            "Only CSV files are supported in this phase.",
            400,
        )
    contents = await file.read()
    if not contents:
        raise api_error("EMPTY_FILE", "Uploaded file is empty.", 400)
    if len(contents) > get_settings().max_upload_bytes:
        raise api_error("FILE_TOO_LARGE", "File exceeds the ~100 MB limit.", 413)
    try:
        result = store.load_csv(contents, name)
    except ValueError as exc:
        raise api_error("UNREADABLE_FILE", str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        raise api_error("LOAD_FAILED", f"Failed to load dataset: {exc}", 500)
    return ok(result)


@router.get("/datasets")
def list_datasets() -> dict:
    return ok({"datasets": store.list_datasets()})
