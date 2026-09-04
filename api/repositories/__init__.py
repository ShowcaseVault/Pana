"""Repositories: the single point of external access.

A repository is the only place that talks to something outside the process --
the database, Redis, an HTTP API, an LLM. Dependencies arrive through the
constructor, so a service holds a repository and never a session or a client.

Import from here rather than from the individual modules:

    from api.repositories import UserRepository
"""

from api.repositories.google_oauth_repository import GoogleOAuthRepository
from api.repositories.user_repository import UserRepository

__all__ = [
    "GoogleOAuthRepository",
    "UserRepository",
]
