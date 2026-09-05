"""Reverse geocoding: coordinates to a place name."""

import logging

import httpx

from api.config.config import settings

logger = logging.getLogger("location")


class LocationRepository:
    """Looks up a human-readable place name for a latitude and longitude."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.http_client = http_client

    async def name_for(self, latitude: float, longitude: float) -> str | None:
        """Return a place name, or None if the lookup fails.

        None rather than an exception: a diary entry is still worth writing
        without a place name, so a geocoding outage must not fail the request.
        """
        url = settings.LOCATION_URL.format(lat=latitude, long=longitude)

        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            return response.json().get("name")
        except (httpx.HTTPError, ValueError):
            logger.warning("Could not resolve location for %s,%s", latitude, longitude)
            return None
