from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api.models.users import User

async def get_user_by_sub(db: AsyncSession, sub: str) -> User:
    stmt = select(User).where(User.google_id == sub)
    result = await db.execute(stmt)
    return result.scalars().first()