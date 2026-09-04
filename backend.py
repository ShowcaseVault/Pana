"""Run the Pana API server.

The FastAPI app lives in `api.app`. Celery workers are started separately via
the Makefile (`make celery`).
"""

import uvicorn

from api.config.config import settings


def main() -> None:
    uvicorn.run(
        "api.app:app",
        host=str(settings.SERVER_HOST),
        port=int(settings.SERVER_PORT),
        reload=settings.SERVER_RELOAD,
    )


if __name__ == "__main__":
    main()
