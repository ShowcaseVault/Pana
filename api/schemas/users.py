from datetime import datetime

from pydantic import BaseModel
from pydantic.config import ConfigDict


class UserResponse(BaseModel):
    id: int
    google_id: str
    email: str
    # Optional to match the model: Google does not guarantee either, and a
    # user without a profile photo must not fail serialization.
    name: str | None = None
    picture: str | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
