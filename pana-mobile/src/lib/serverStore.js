/**
 * Which server this install talks to.
 *
 * The API origin is normally fixed at build time from `VITE_BASE_API_URL`.
 * That is right for a shipped build, which talks to one known API over HTTPS,
 * but it makes a distributed debug build useless to anybody else: it would
 * point at whichever machine happened to build it.
 *
 * So a debug build can override it, and remembers the answer. The value is
 * read synchronously by the HTTP client on its first request, which is why it
 * is hydrated into a module variable at startup rather than awaited per call.
 *
 * Release builds ignore all of this and use the compiled-in origin: a shipped
 * app that can be pointed at an arbitrary server is a way to hand someone
 * else's server a real session token.
 *
 * @module lib/serverStore
 */

import { Preferences } from '@capacitor/preferences';

const KEY = 'server_origin';

/** The compiled-in origin, and the fallback whenever nothing is stored. */
export const DEFAULT_ORIGIN = import.meta.env.VITE_BASE_API_URL || 'http://localhost:8000';

/**
 * Whether this build lets the origin be changed.
 *
 * Both APKs are produced by `vite build`, so `import.meta.env.DEV` is false in
 * each and cannot tell them apart: the debug bundle is built with
 * VITE_ALLOW_SERVER_OVERRIDE set, and the release bundle without it.
 *
 * Vite substitutes the value at build time, so in a release bundle this is the
 * literal `false` and the override paths are dropped by the minifier rather
 * than merely left unreachable.
 */
export const CAN_OVERRIDE =
  import.meta.env.DEV || import.meta.env.VITE_ALLOW_SERVER_OVERRIDE === 'true';

let current = DEFAULT_ORIGIN;

/** The origin to use now. Synchronous, for the axios instance. */
export const getServerOrigin = () => current;

/** Load the stored origin. Called once, before the first request. */
export async function hydrateServerOrigin() {
  if (!CAN_OVERRIDE) return DEFAULT_ORIGIN;

  try {
    const { value } = await Preferences.get({ key: KEY });
    if (value) current = value;
  } catch (error) {
    // A device that cannot read its own preferences is not a reason to fail
    // to start; the compiled-in origin is a working default.
    console.error('Could not read the stored server address', error);
  }
  return current;
}

/**
 * Point this install at a different server.
 *
 * @param {string} origin An absolute origin, e.g. `http://192.168.1.50:8000`.
 */
export async function setServerOrigin(origin) {
  if (!CAN_OVERRIDE) return;

  const trimmed = origin.trim().replace(/\/+$/, '');
  current = trimmed || DEFAULT_ORIGIN;

  if (trimmed) {
    await Preferences.set({ key: KEY, value: trimmed });
  } else {
    await Preferences.remove({ key: KEY });
  }
}
