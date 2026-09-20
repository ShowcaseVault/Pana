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
  `android/app/src/debug/res/xml/network_security_config.xml`;
* drop `http://localhost` and the LAN origins from the backend's
  `ALLOWED_ORIGINS`, leaving `https://localhost` and `capacitor://localhost`
  for the packaged app.

Changing the scheme also changes where the WebView stores its data, so the app
is signed out once after this change -- the tokens were written under the old
origin.


## Signing

Release builds are signed with `secrets/pana-release.jks`. The passwords are in
`secrets/android_signing.env`, which `android/app/build.gradle` reads at
configure time. Both are mode 600 and git-ignored, like everything else in
`secrets/`.

An APK signed with the Android debug key is what Play Protect blocks as an
"unsafe app": the key is shared by every developer on every machine, so it
identifies nobody. The release key is Pana's own, which is what makes an
install from outside the Play Store unremarkable rather than alarming.

**The keystore cannot be replaced.** Android identifies an app by the
certificate that signed it, so an update must be signed with the same key as
the install it replaces. Lose the file and the only way to ship again is a new
application id, which is a new app: existing installs cannot be updated and
their data does not carry over. Back it up somewhere off this machine, with
`android_signing.env` beside it.

Its fingerprint, for the Google sign-in client in Cloud Console:

    SHA-1: 3D:04:F0:3E:E8:E8:56:5A:8C:9B:D8:28:EB:D4:9F:FD:0C:FB:FC:F9

A release build will not sign in until that fingerprint is registered
alongside the debug one, since Google checks the signing certificate as well as
the package name.

If `secrets/android_signing.env` is absent the build falls back to the debug
signature rather than failing, so CI and a fresh clone still work. `npm run
release` checks for it first and stops, since a release APK signed with the
debug key is the thing this is all meant to avoid.

## Size

The release build runs R8 (`minifyEnabled`, `shrinkResources`), which takes the
APK from about 8 MB to about 3.4 MB. Almost all of it is dex: the web bundle is
well under a megabyte, and the rest is Capacitor, AndroidX and Play Services
with the unreachable parts removed.

R8 finds classes by following references, and Capacitor's plugins are reached
only by reflection -- the bridge reads `@CapacitorPlugin` at runtime. They are
kept explicitly in `proguard-rules.pro`. Without those rules the build succeeds
and the app fails on the device the first time a plugin is called, so treat a
plugin that works in debug and not in release as a missing keep rule.

Splitting the APK per ABI was tried and removed: the app ships no native
libraries, so every split was byte-for-byte identical to the universal one.
