/**
 * Native authentication.
 *
 * The browser flow leaves the app for a consent screen and comes back with
 * cookies set. A device does neither: the platform's account picker appears
 * over the app and hands back an `id_token`, which is posted to
 * `/auth/mobile/google` for a token pair of ours. Nothing navigates, and the
 * pair is stored by `tokenStore`.
 *
 * @module lib/auth.service
 */

import { SocialLogin } from '@capgo/capacitor-social-login';
import apiClient from './apiClient.js';
import { API_ROUTES } from './routes.js';
import { clearTokens, getRefreshToken, setTokens } from './tokenStore.js';

/**
 * The *web* client ID, deliberately, on every platform.
 *
 * Android identifies the app by its package name and signing certificate, not
 * by a client ID in the bundle; what it needs here is the ID of the client the
 * token is minted *for*. Passing the Android client ID instead yields a token
 * whose `aud` the backend will reject.
 */
const WEB_CLIENT_ID = '142546023096-3r4a074qginqvg5b9suu7p6evqqn2a5v.apps.googleusercontent.com';

/**
 * Prepare the platform SDK. Must run once before any sign-in attempt.
 *
 * @returns {Promise<void>}
 */
export async function initGoogleAuth() {
  await SocialLogin.initialize({
    google: { webClientId: WEB_CLIENT_ID },
  });
}

/** The plugin rejects with this code when the user dismisses the picker. */
export const USER_CANCELLED = 'USER_CANCELLED';

/**
 * Sign in through the platform SDK and exchange the result for our own tokens.
 *
 * @returns {Promise<void>}
 * @throws {ApiError} If the backend rejects the id_token.
 */
export async function signInWithGoogle() {
  // No `scopes` option, deliberately. The plugin already requests openid,
  // email and profile -- exactly what the backend reads -- and naming any
  // scope explicitly makes it demand a modified MainActivity for the
  // authorization flow those extra scopes would need.
  const { result } = await SocialLogin.login({
    provider: 'google',
    options: {},
  });

  // Authentication is the id_token's job; the access token the plugin may also
  // return is for calling Google's own APIs, which this app never does.
  const idToken = result?.idToken;
  if (!idToken) throw new Error('Google sign-in returned no id_token');

  const response = await apiClient.post(API_ROUTES.AUTH.GOOGLE, { id_token: idToken });
  await setTokens(response.data);
}

/**
 * End the session on the device and revoke it server-side.
 *
 * The local tokens are dropped whatever the server answers: a failed revoke
 * must not leave the user apparently signed in on the handset.
 *
 * @returns {Promise<void>}
 */
export async function signOut() {
  const refresh_token = getRefreshToken();
  try {
    if (refresh_token) await apiClient.post(API_ROUTES.AUTH.LOGOUT, { refresh_token });
    await SocialLogin.logout({ provider: 'google' });
  } catch (error) {
    console.warn('Sign-out did not complete cleanly', error);
  } finally {
    await clearTokens();
  }
}

/**
 * Fetch the signed-in user. Doubles as the session check at startup: a 401 is
 * first retried through the client's refresh, so a failure here means there is
 * genuinely no session.
 *
 * @returns {Promise<import('@app/types/api.js').User>}
 */
export async function getCurrentUser() {
  const response = await apiClient.get(API_ROUTES.HOME);
  return response.data;
}
