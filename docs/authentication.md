# Authentication

Google is the only identity provider. Signing in proves who you are to Google;
the API then issues its own token pair and every later request is authenticated
against those, not against Google.

Two clients are supported and they share one implementation. Only the outermost
edge differs -- how a login starts, and how tokens travel back.

- [The two flows](#the-two-flows)
- [Tokens](#tokens)
- [Rotation and revocation](#rotation-and-revocation)
- [Endpoints](#endpoints)
- [Client guide](#client-guide)
- [Layers](#layers)
- [Configuration](#configuration)
- [Threat model](#threat-model)
- [Not built yet](#not-built-yet)

## The two flows

A browser cannot hold the Google client secret, so it gets an authorization
code and the server redeems it. A native app signs in through the platform SDK
and already holds a verified `id_token`, so it posts that directly.

```
Browser                                       Native app
───────                                       ──────────
GET /auth/google                              Google Sign-In SDK
  └─ 307 to Google consent                      └─ returns id_token
       └─ user consents
            └─ GET /auth/google/callback?code=…      POST /auth/mobile/google
                 └─ exchange_code(code)                   { "id_token": "…" }
                      → id_token
                           │                                    │
                           └──────────┬─────────────────────────┘
                                      ▼
                          verify_id_token(id_token)
                          • signature is Google's
                          • audience is one of ours
                                      ▼
                          upsert the user row
                                      ▼
                          issue an access + refresh pair
                          record the refresh token
                                      │
                ┌─────────────────────┴──────────────────────┐
                ▼                                            ▼
        Set-Cookie ×2, redirect to CLIENT_URL         200 { access_token,
        (body carries no tokens)                            refresh_token, … }
```

Everything below the fork is one code path -- `AuthService._authenticate` --
so the two clients cannot drift apart on what a login means.

**Why the audience check matters.** Any Google id_token is signed by Google,
including one an attacker obtained from an unrelated app they control. What
ties a token to *this* application is its `aud` claim. Verification therefore
rejects any token whose audience is not the web client or a configured mobile
client. Without that check, a valid token from any Google project would log
someone in.

## Tokens

Both are JWTs, signed with **separate secrets** (`JWT_ACCESS_SECRET_KEY` and
`JWT_REFRESH_SECRET_KEY`). There is no fallback between them: a token signed
with the wrong key is rejected, so an access token can never be presented where
a refresh token is required. Each also carries a `type` claim that is checked
on decode.

| | Access token | Refresh token |
|---|---|---|
| Lifetime | `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60) | `REFRESH_TOKEN_EXPIRE_DAYS` (default 14) |
| Purpose | authenticates each API request | obtains a new pair |
| Stored server-side | no | yes, as a SHA-256 hash |
| Revocable | no -- valid until it expires | yes |
| Claims | `sub`, `email`, `name`, `exp`, `type` | `sub`, `email`, `session_id`, `exp`, `type`, `jti` |

`sub` is the Google subject (`google_id`), not the local row id.

**Access tokens are deliberately stateless.** Checking a database row on every
request would put a query in front of every endpoint. The trade is that a
stolen access token works until it expires -- which is why the lifetime is
short and the refresh token is the one that is tracked.

The `jti` on a refresh token is a random unique value. Without it, two tokens
minted in the same second with the same claims would be byte-identical, hash
identically, and collide on the unique index.

### How a request is authenticated

`get_current_user` accepts either transport, header first:

```python
bearer_token(request.headers.get("authorization")) or request.cookies.get(cookie_name)
```

The header wins because a client that sets it explicitly means it, and a stale
cookie in the same browser should not shadow that choice. Every protected route
is therefore transport-agnostic -- it never knows which client it is serving.

Two dependencies are available:

- `Depends(get_current_user)` -- the decoded JWT claims, no database hit.
- `Depends(get_authorized_db_user)` -- the `User` row, 401 if the token is
  valid but the user is gone.

## Rotation and revocation

Every refresh token is recorded in `refresh_tokens`. **Only a SHA-256 hash is
stored**, for the same reason a password table holds no passwords: a dump of
the table yields nothing usable.

A plain hash is correct here, not a slow KDF -- the token is a long random
value with nothing to brute-force, and a KDF would add latency to every
refresh.

### Rotation

Each refresh token works exactly **once**. Presenting it revokes it and issues
a successor, chained by `replaced_by_hash` and sharing the login's `session_id`.

```
login ──► token A (live)
             │ POST refresh
             ▼
          token A (revoked: rotated, replaced_by → B)
          token B (live)
             │ POST refresh
             ▼
          token B (revoked: rotated, replaced_by → C)
          token C (live)
```

### Reuse detection

If a token that was already spent is presented again, two parties hold it and
one of them is an attacker. There is no way to tell which. So the entire
`session_id` family is revoked and both parties must sign in again:

```
token A (spent) ──► presented a second time
                      │
                      ▼
        every live token in the session revoked (reuse_detected)
        401 "Refresh token has already been used"
```

This is what limits the damage of a stolen refresh token. Either the real
client refreshes first, and the thief's copy is dead; or the thief refreshes
first, and the real client's next refresh trips the alarm and closes the
session.

That revocation is **committed before the 401 is raised**. The request-scoped
session rolls back when a route raises, so without its own commit the
revocation would be undone and the stolen chain would stay live. Hence
`revoke_session(..., commit=True)` on that path only.

### Sessions are per-login

Each login opens its own `session_id`, so revoking one family logs out one
device and leaves the user's other devices alone.

### Revocation reasons

`revoked_reason` records why a token died:

| Reason | Set when |
|---|---|
| `rotated` | spent normally in a refresh |
| `reuse_detected` | a replay burned the family |
| `logout` | the session was ended deliberately |
| `logout_all` | every session for the user was ended |

### Logout

Logout revokes the session server-side, so a refresh token copied from the
browser beforehand is dead too. The access token stays valid until it expires
-- minutes, by design, being the trade for stateless access tokens.

Logout is best effort: a client that has already lost its token still gets a
`200`, because there is nothing useful to tell it and nothing left to revoke.

## Endpoints

Auth routes sit at the root, **not** under `/api/v1`: the Google callback URL
is registered with Google and cannot move when the API version changes.

### Browser

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/auth/google` | redirect to Google's consent screen |
| `GET` | `/auth/google/callback` | complete the flow, set cookies, redirect to `CLIENT_URL` |
| `POST` | `/auth/refresh` | rotate the session, replace both cookies |
| `POST` | `/auth/logout` | revoke the session, clear cookies |

Cookies are `httponly`, with `secure` and `samesite` from settings.
`/auth/refresh` returns `data: null` -- the tokens are in cookies the page
cannot read, and putting them in the body would only expose them to scripts.

An OAuth failure lands in a browser mid-redirect, so the callback redirects to
`{CLIENT_URL}/login?error=…` rather than returning a JSON error a browser would
render as raw text.

### Native

| Method | Path | Body | Purpose |
|---|---|---|---|
| `POST` | `/auth/mobile/google` | `{ "id_token": "…" }` | exchange a Google id_token for a token pair |
| `POST` | `/auth/mobile/refresh` | `{ "refresh_token": "…" }` | rotate, returning a new pair |
| `POST` | `/auth/mobile/logout` | `{ "refresh_token": "…" }` | revoke the session |

No cookies are set on these. Every response is the standard `ApiResponse`
envelope:

```json
{
  "success": true,
  "message": "Logged in",
  "data": {
    "access_token": "eyJ…",
    "refresh_token": "eyJ…",
    "access_max_age": 3600,
    "refresh_max_age": 1209600
  }
}
```

`access_max_age` and `refresh_max_age` are lifetimes in seconds, so a client
can schedule a refresh instead of waiting for a 401.

### Failures

| Status | Meaning |
|---|---|
| 401 | missing, malformed, expired, unrecorded, or already-used token; audience mismatch; user gone |
| 422 | request body failed validation (empty or absent token field) |
| 502 | Google was unreachable, rejected the code exchange, or the token would not verify |

## Client guide

### Web

1. Send the user to `GET /auth/google`.
2. Cookies arrive automatically; the browser lands on `CLIENT_URL`.
3. Make normal requests -- the browser attaches the cookie.
4. On a 401, `POST /auth/refresh` once, then retry. Both cookies are replaced.
5. `POST /auth/logout` to end the session.

Requests must be credentialed (`fetch(..., { credentials: 'include' })`), and
the origin must be listed in `ALLOWED_ORIGINS` -- credentialed CORS forbids a
wildcard.

### Mobile

1. Complete Google sign-in with the platform SDK; take the `id_token`.
2. `POST /auth/mobile/google` with it.
3. Store **both** tokens in the Keychain or Keystore -- not in plain
   preferences, and not on disk unencrypted.
4. Send `Authorization: Bearer <access_token>` on every request.
5. On a 401, `POST /auth/mobile/refresh`, **replace both stored tokens**, then
   retry.
6. `POST /auth/mobile/logout` to end the session.

**The one rule that matters:** a refresh returns a new refresh token, and the
old one is spent. An app that keeps the old one will look like an attacker
replaying a stolen token on its next refresh, and the session will be revoked.
Persist the new pair before using it.

Refresh in a single-flight manner. Two concurrent refreshes with the same token
mean the second is a replay, and the session dies.

## Layers

Routes → services → repositories. A repository is the only thing that touches
something external; a service holds repositories and owns the logic; a route
reads the request, calls a service, and shapes the response.

```
api/routes/authentication.py    endpoints, cookies, Depends wiring
api/services/authentication.py  AuthService: login, rotation, logout
api/repositories/
  google_oauth_repository.py    Google: consent URL, code exchange, verify
  user_repository.py            the users table
  refresh_token_repository.py   the refresh_tokens table, plus hash_token
api/auth/
  jwt_utils.py                  mint and decode
  tokens.py                     pull a token off a request
  cookies.py                    set and clear the auth cookies
  dependencies.py               get_current_user, get_authorized_db_user
api/models/refresh_tokens.py    the RefreshToken model
api/schemas/authentication.py   GoogleProfile, AuthTokens, request bodies
```

Two service providers exist, and the split is deliberate:

- `get_auth_service` -- has both database repositories. Used by every route
  that reads or writes a token.
- `get_oauth_service` -- no database session at all. Used only by
  `GET /auth/google`, which merely builds a URL. Without the split, that route
  would check a connection out of the pool for a request that never uses it.

Cookies live in `api/auth/cookies.py`, not in the service: the service issues
tokens and does not know how they travel. That is what lets one service serve
both clients.

Google's blocking certificate fetch (`google-auth` uses `requests`) runs in a
worker thread via `anyio.to_thread.run_sync`, so a login does not stall the
event loop.

## Configuration

| Setting | Default | Notes |
|---|---|---|
| `GOOGLE_CLIENT_ID` | none | the web client; also an accepted audience |
| `GOOGLE_CLIENT_SECRET` | none | used only in the code exchange |
| `GOOGLE_REDIRECT_URI` | none | must match Google Cloud Console exactly |
| `GOOGLE_AUTH_URL` | none | Google's consent endpoint |
| `GOOGLE_TOKEN_URL` | none | Google's token endpoint |
| `GOOGLE_MOBILE_CLIENT_IDS` | empty | iOS/Android client IDs, comma-separated or JSON |
| `JWT_ACCESS_SECRET_KEY` | **required** | no default, by design |
| `JWT_REFRESH_SECRET_KEY` | **required** | must differ from the access secret |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | |
| `ACCESS_COOKIE_NAME` | `access_token` | |
| `REFRESH_COOKIE_NAME` | `refresh_token` | |
| `COOKIE_SECURE` | `False` | **must be `True` in production** |
| `COOKIE_SAMESITE` | `lax` | see the threat model below |
| `CLIENT_URL` | `http://localhost:5173/home` | where the callback lands |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | wildcard is rejected |

A missing `GOOGLE_*` value fails loudly with a 502 naming the setting. Each one
defaults to `None`, so without that check an unset variable would reach Google
as the literal string `"None"` and come back as an opaque OAuth error.

### Before mobile ships

Set `GOOGLE_MOBILE_CLIENT_IDS` to the client IDs from Google Cloud Console.
Until then `/auth/mobile/google` rejects every native token -- correctly, but
it will look broken.

### Before production

Set `COOKIE_SECURE=True`. With `False`, the cookie is sent over plaintext HTTP.

## Threat model

What each transport is exposed to, and what answers it:

| Attack | Browser (cookie) | Native (bearer) |
|---|---|---|
| XSS reads the token | blocked -- `httponly` | n/a, no browser |
| CSRF | see below | impossible -- no cookie is attached automatically |
| Stolen access token | works until expiry (minutes) | same |
| Stolen refresh token | one use, then detected | one use, then detected |
| Database dump | only hashes stored | only hashes stored |
| Token from another Google app | rejected on audience | rejected on audience |

**CSRF.** A browser attaches cookies based on where a request goes, not where
it came from, so a malicious page can make an authenticated request on the
user's behalf. `SameSite=lax` withholds the cookie on cross-site POST, PUT and
DELETE, which covers every write. It does still send the cookie on a
**top-level cross-site GET navigation**, so the remaining exposure would be any
GET route that changes state. As of this writing there are none -- every GET is
a pure read. Keep it that way, or add CSRF tokens.

**Why cookies for web rather than tokens in JavaScript.** `httponly` is a
guarantee that `localStorage` cannot replicate: script on the page simply
cannot read the token. Moving web to bearer tokens would trade a CSRF exposure
that is currently closed for an XSS exposure that would be permanently open.
The two clients keep different transports because they genuinely have different
threat models.

## Not built yet

- **No pruning of expired rows.** `RefreshTokenRepository.delete_expired()`
  exists but nothing calls it, so `refresh_tokens` grows without bound. A
  Celery beat task is the natural home.
- **`logout_everywhere()` has no route.** The service method is implemented and
  revokes every session a user holds; nothing exposes it yet.
- **No device or IP recorded** against a session, so a "your active sessions"
  screen cannot say where a session came from.
- **Access tokens cannot be revoked.** Inherent to keeping them stateless; the
  short lifetime is the mitigation.
