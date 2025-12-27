from datetime import date
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict

class DiaryResponse(BaseModel):
    diary_date: date
    mood: Optional[str] = None
    content: Optional[str] = None
    actions: Optional[List[Dict]] = None
    recording_file_paths: Optional[List[str]] = []

    model_config = ConfigDict(from_attributes=True)