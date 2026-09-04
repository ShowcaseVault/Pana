"""Authentication schemas: Google's claims and the tokens we issue.

Separate from `api.schemas.users`, which describes the user as a resource.
Nothing here outlives a login or a refresh.
"""

from pydantic import BaseModel


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


class AccessToken(BaseModel):
    """A reissued access token, as returned by the refresh endpoint."""

    access_token: str
    token_type: str = "bearer"
