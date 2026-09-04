from datetime import date

from pydantic import BaseModel, ConfigDict


class DiaryResponse(BaseModel):
    diary_date: date
    mood: str | None = None
    content: str | None = None
    actions: list[dict] | None = None
    recording_file_paths: list[str] | None = []

    model_config = ConfigDict(from_attributes=True)
