"""Authentication schemas: Google's claims and the tokens we issue.

Separate from `api.schemas.users`, which describes the user as a resource.
Nothing here outlives a login or a refresh.
"""

from pydantic import BaseModel, Field


class GoogleProfile(BaseModel):
    """The subset of Google's id_token claims the application uses."""

    sub: str
    email: str
    name: str | None = None
    picture: str | None = None


class AuthTokens(BaseModel):
    """A freshly issued token pair, plus how long each one is good for."""

    access_token: str
    refresh_token: str
    access_max_age: int
    refresh_max_age: int


class GoogleIdTokenRequest(BaseModel):
    """A native app posting the id_token its Google SDK returned."""

    id_token: str = Field(min_length=1, description="The id_token from the Google Sign-In SDK")


class RefreshTokenRequest(BaseModel):
    """A native app asking for a new access token.

    The refresh token travels in the body because a mobile client keeps it in
    the device keychain rather than in a cookie.
    """

    refresh_token: str = Field(min_length=1)
