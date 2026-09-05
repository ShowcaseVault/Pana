"""Home screen business logic."""

from api.exceptions import NotFoundError
from api.models.users import User
from api.repositories import UserRepository


class HomeService:
    """What the home screen needs: the signed-in user's profile."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_profile(self, google_id: str) -> User:
        """Return the user behind a JWT subject.

        A valid token whose user is gone is a 404 rather than a 401: the caller
        is authenticated, the row just is not there.
        """
        user = await self.user_repository.get_by_google_id(google_id)
        if user is None:
            raise NotFoundError("User not found")
        return user
