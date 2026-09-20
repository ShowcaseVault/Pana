/**
 * Where the token pair lives on a device.
 *
 * The web client never sees its tokens -- they are httpOnly cookies the browser
 * attaches by itself. A native app has no such mechanism: it receives the pair
 * in a response body and must hold it, so this module is the only place that
 * knows where. Capacitor Preferences maps to the platform's own store
 * (SharedPreferences on Android, UserDefaults on iOS).
 *
 * Reads are served from an in-memory copy because the request interceptor needs
 * the access token synchronously on every call, and Preferences is async.
 *
 * @module lib/tokenStore
 */

import { Preferences } from '@capacitor/preferences';

const ACCESS_KEY = 'pana.access_token';
const REFRESH_KEY = 'pana.refresh_token';

/** @type {{access: string|null, refresh: string|null}} */
const cache = { access: null, refresh: null };

/**
 * Load the persisted pair into memory. Call once at startup, before the first
 * request: until it resolves, `getAccessToken` reports no session even when one
 * is stored.
 *
 * @returns {Promise<void>}
 */
export async function hydrate() {
  const [access, refresh] = await Promise.all([
    Preferences.get({ key: ACCESS_KEY }),
    Preferences.get({ key: REFRESH_KEY }),
  ]);
  cache.access = access.value ?? null;
  cache.refresh = refresh.value ?? null;
}

/** @returns {string|null} */
export function getAccessToken() {
  return cache.access;
}

/** @returns {string|null} */
export function getRefreshToken() {
  return cache.refresh;
}

/**
 * Persist a freshly issued pair.
 *
 * @param {{access_token: string, refresh_token: string}} tokens
 * @returns {Promise<void>}
 */
export async function setTokens({ access_token, refresh_token }) {
  cache.access = access_token;
  cache.refresh = refresh_token;
  await Promise.all([
    Preferences.set({ key: ACCESS_KEY, value: access_token }),
    Preferences.set({ key: REFRESH_KEY, value: refresh_token }),
  ]);
}

/**
 * Forget the session, in memory and on disk.
 *
 * @returns {Promise<void>}
 */
export async function clearTokens() {
  cache.access = null;
  cache.refresh = null;
  await Promise.all([
    Preferences.remove({ key: ACCESS_KEY }),
    Preferences.remove({ key: REFRESH_KEY }),
  ]);
}
