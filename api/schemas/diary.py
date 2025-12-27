from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict

class DiaryResponse(BaseModel):
    id: int
    user_id: int
    diary_date: date
    mood: Optional[str] = None
    content: Optional[str] = None
    actions: Optional[List[Dict]] = None
    recording_file_paths: Optional[List[str]] = []
    created_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)