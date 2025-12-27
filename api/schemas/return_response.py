from typing import Any, Literal
from pydantic import BaseModel
from api.constants.auth import AUTH

class SuccessResponse(BaseModel):
    code: Literal[AUTH.SUCCESS] = AUTH.SUCCESS
    data: Any
    message: str

class FailureResponse(BaseModel):
    code: Literal[AUTH.FAILURE] = AUTH.FAILURE
    data: None = None
    message: str