"""Minimal ARI client.

Only what the voice service needs: a WebSocket for Stasis events and a handful
of REST calls to drive a live channel. Deliberately not a general-purpose ARI
binding -- there is no third-party library here to keep the dependency surface
of a telephony control channel small.

ARI is bound to loopback (http.conf) and its password is generated at Asterisk
start into a volume. Both are why this connects to 127.0.0.1 and why the
password has no default -- see docs/telephony.md.
"""

import logging
from typing import Any
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger("voice.ari")


class AriClient:
    """REST + WebSocket access to one Asterisk instance."""

    def __init__(self, base_url: str, username: str, password: str, app: str) -> None:
        self._base = base_url.rstrip("/")
        self._auth = aiohttp.BasicAuth(username, password)
        self._app = app
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "AriClient":
        self._session = aiohttp.ClientSession(auth=self._auth)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError("AriClient used outside its context manager")
        return self._session

    async def events(self):
        """Yield Stasis events for this app, as decoded JSON.

        The WebSocket carries its own credentials in the query string because
        Asterisk does not accept a Basic auth header on the events upgrade.
        """
        query = urlencode({"app": self._app, "subscribeAll": "false"})
        url = f"{self._base}/ari/events?{query}"
        async with self.session.ws_connect(url, heartbeat=30) as ws:
            logger.info("subscribed to Stasis app %r", self._app)
            async for message in ws:
                if message.type is aiohttp.WSMsgType.TEXT:
                    yield message.json()
                elif message.type is aiohttp.WSMsgType.ERROR:
                    raise RuntimeError(f"ARI websocket failed: {ws.exception()}")

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base}/ari{path}"
        async with self.session.request(method, url, **kwargs) as response:
            # A channel can hang up between an event and the command reacting
            # to it; that races by design, so 404 is not an error here.
            if response.status == 404:
                logger.debug("%s %s: channel is gone", method, path)
                return None
            response.raise_for_status()
            if response.status == 204 or not response.content_length:
                return None
            return await response.json()

    async def answer(self, channel_id: str) -> None:
        await self._request("POST", f"/channels/{channel_id}/answer")

    async def hangup(self, channel_id: str) -> None:
        await self._request("DELETE", f"/channels/{channel_id}")

    async def play(self, channel_id: str, media: str) -> str | None:
        """Play media (e.g. `sound:pana/cid_whistle`) and return the playback id."""
        result = await self._request(
            "POST", f"/channels/{channel_id}/play", params={"media": media}
        )
        return result["id"] if result else None

    async def record(self, channel_id: str, name: str, max_seconds: int, max_silence: int) -> None:
        """Record the caller until they stop talking or the ceiling is hit.

        `maxSilenceSeconds` is what ends a normal turn; `maxDurationSeconds` is
        the backstop for an open line with constant noise, which would otherwise
        record until the call's own timeout.
        """
        await self._request(
            "POST",
            f"/channels/{channel_id}/record",
            params={
                "name": name,
                "format": "ulaw",
                "maxDurationSeconds": str(max_seconds),
                "maxSilenceSeconds": str(max_silence),
                "ifExists": "overwrite",
                "beep": "false",
                "terminateOn": "none",
            },
        )

    async def stored_recording(self, name: str) -> bytes:
        """Download a stored recording's audio."""
        url = f"{self._base}/ari/recordings/stored/{name}/file"
        async with self.session.get(url) as response:
            if response.status == 404:
                return b""
            response.raise_for_status()
            return await response.read()

    async def delete_recording(self, name: str) -> None:
        await self._request("DELETE", f"/recordings/stored/{name}")
