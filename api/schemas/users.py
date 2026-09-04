from datetime import datetime

from pydantic import BaseModel
from pydantic.config import ConfigDict


class UserResponse(BaseModel):
    id: int
    google_id: str
    email: str
    name: str
    picture: str

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
