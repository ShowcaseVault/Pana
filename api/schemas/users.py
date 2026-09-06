from pydantic import BaseModel
from pydantic.config import ConfigDict


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    picture: str | None = None

    model_config = ConfigDict(from_attributes=True)
