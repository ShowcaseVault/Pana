/**
 * Authentication.
 *
 * The browser flow is cookie-based: the backend sets httpOnly access and
 * refresh cookies on the Google callback, so there is no token for this code to
 * hold, store, or attach. Signing in is a full-page navigation to the backend,
 * not an XHR -- an OAuth consent screen cannot be fetched.
 *
 * @module services/auth.service
 */

import apiClient from '../lib/apiClient.js';
import { API_ROUTES } from '../api/routes.js';

/**
 * @import { User } from '../types/api.js'
 */

export class AuthService {
  /**
   * Fetch the signed-in user.
   *
   * Doubles as the session check: a 401 here means no valid session, which the
   * client's interceptor will first try to fix by refreshing.
   *
   * @param {Object} [options]
   * @param {AbortSignal} [options.signal]
   * @returns {Promise<User>}
   */
  async getCurrentUser({ signal } = {}) {
    const response = await apiClient.get(API_ROUTES.HOME, { signal });
    return response.data;
  }

  /**
   * Leave the app for Google's consent screen.
   *
   * Navigates the whole page rather than returning, so nothing after the call
   * runs.
   *
   * @returns {void}
   */
  startGoogleLogin() {
    window.location.href = `${API_ROUTES.ORIGIN}${API_ROUTES.AUTH.GOOGLE_LOGIN}`;
  }

  /**
   * Clear the session cookies server-side.
   *
   * @returns {Promise<void>}
   */
  async logout() {
    await apiClient.post(API_ROUTES.AUTH.LOGOUT);
  }
}

export const authService = new AuthService();
export default authService;
