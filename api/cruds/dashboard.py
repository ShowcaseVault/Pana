from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.models.users import User
from api.schemas.users import UserResponse

async def get_user_profile(db: AsyncSession, google_id: str):
    stmt = select(User).where(User.google_id == google_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return UserResponse(**user.__dict__)
