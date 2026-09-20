# Configuration notes

## `server.androidScheme: "http"`

Capacitor serves the bundled app from `https://localhost` by default. That is
the right default -- but it breaks development against a plain-HTTP API on the
LAN, in two ways at once:

* the page's origin becomes `https://localhost`, which must be listed in the
  backend's `ALLOWED_ORIGINS` or every request fails CORS;
* a page on `https://` calling `http://192.168.1.11:8000` is mixed content, and
  the WebView blocks it outright. The app reports only that it could not reach
  the server.

Setting the scheme to `http` makes the page origin `http://localhost`, so the
API calls are no longer mixed content. `cleartext: true` permits the plain-HTTP
traffic itself.

**Both are development settings.** Before shipping to real users, the API needs
to be served over HTTPS, and then:

* remove `server` from `capacitor.config.json` entirely, restoring the
  `https://localhost` default;
* remove `android.allowMixedContent`;
* remove the LAN address from
  `android/app/src/main/res/xml/network_security_config.xml`;
* drop `http://localhost` and the LAN origins from the backend's
  `ALLOWED_ORIGINS`, leaving `https://localhost` and `capacitor://localhost`
  for the packaged app.

Changing the scheme also changes where the WebView stores its data, so the app
is signed out once after this change -- the tokens were written under the old
origin.
