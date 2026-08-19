from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    dataset_ids: list[str] = Field(min_length=1)
    question: str


class DatasetResponse(BaseModel):
    dataset_id: str
    name: str
    kind: str
    row_count: int
    column_count: int
    profile: dict | None = None
