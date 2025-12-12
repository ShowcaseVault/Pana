from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserResponse(BaseModel):
    id: int
    google_id: str
    email: str
    name: str
    picture: str
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None