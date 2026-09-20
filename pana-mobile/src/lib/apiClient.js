/**
 * The single HTTP entry point for the native client.
 *
 * Same contract as the web client -- a successful body is unwrapped into an
 * `ApiResponse`, every failure becomes an `ApiError` -- so the shared services
 * and query hooks work unchanged against either.
 *
 * What differs is the transport of credentials. The browser has httpOnly
 * cookies and `withCredentials`; a device has neither, so the access token is
 * attached here as a bearer header and the refresh token is posted in the body
 * of the refresh call. `withCredentials` is deliberately absent: there are no
 * cookies to send, and a wildcard CORS origin would reject the request if there
 * were.
 *
 * @module lib/apiClient
 */

import axios from 'axios';
import { ApiError, ApiResponse } from '@app/lib/ApiResponse.js';
import { API_ROUTES, BASE_URL } from './routes.js';
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './tokenStore.js';

/** Requests that must never trigger a refresh-and-retry cycle. */
const AUTH_ENDPOINTS = [API_ROUTES.AUTH.REFRESH, API_ROUTES.AUTH.LOGOUT, API_ROUTES.AUTH.GOOGLE];

const http = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * In-flight refresh, shared by every request that hits a 401 at once.
 *
 * The backend rotates the refresh token on use, so parallel refreshes would
 * present a token that has already been spent and end the session mid-use.
 * Holding the promise means later callers await the first one.
 *
 * @type {Promise<void>|null}
 */
let refreshInFlight = null;

/** Listeners notified when the session ends and cannot be recovered. */
const sessionExpiryListeners = new Set();

/**
 * Register a callback for an unrecoverable 401.
 *
 * @param {() => void} listener
 * @returns {() => void} Unsubscribe.
 */
export function onSessionExpired(listener) {
  sessionExpiryListeners.add(listener);
  return () => sessionExpiryListeners.delete(listener);
}

function notifySessionExpired() {
  for (const listener of sessionExpiryListeners) {
    try {
      listener();
    } catch (error) {
      console.error('Session-expiry listener failed', error);
    }
  }
}

http.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/** Rotate the token pair, collapsing concurrent callers onto one request. */
function refreshSession() {
  refreshInFlight ??= (async () => {
    const refresh_token = getRefreshToken();
    // No stored refresh token means there is nothing to rotate; fail here
    // rather than sending a request that cannot succeed.
    if (!refresh_token) throw new Error('No refresh token');

    const response = await http.post(API_ROUTES.AUTH.REFRESH, { refresh_token });
    const parsed = ApiResponse.parse(response.data);
    await setTokens(parsed.data);
  })().finally(() => {
    refreshInFlight = null;
  });

  return refreshInFlight;
}

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    const status = error.response?.status;

    const isRetryable =
      status === 401 &&
      request &&
      !request._retry &&
      !AUTH_ENDPOINTS.some((endpoint) => request.url?.includes(endpoint));

    if (!isRetryable) {
      if (status === 401) notifySessionExpired();
      return Promise.reject(error);
    }

    request._retry = true;

    try {
      await refreshSession();
      return await http(request);
    } catch (refreshError) {
      // The refresh token is gone or rejected: the session is unrecoverable,
      // so drop what is stored rather than retrying it on every later request.
      await clearTokens();
      notifySessionExpired();
      return Promise.reject(refreshError);
    }
  },
);

/**
 * Perform a request and unwrap its envelope.
 *
 * @template T
 * @param {import('axios').AxiosRequestConfig} config
 * @returns {Promise<ApiResponse<T>>}
 * @throws {ApiError} On any failure, including a malformed body.
 */
async function request(config) {
  try {
    const response = await http.request(config);
    return ApiResponse.parse(response.data);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw ApiError.fromAxios(error);
  }
}

export const apiClient = {
  get: (url, config) => request({ ...config, method: 'GET', url }),
  post: (url, data, config) => request({ ...config, method: 'POST', url, data }),
  patch: (url, data, config) => request({ ...config, method: 'PATCH', url, data }),
  delete: (url, config) => request({ ...config, method: 'DELETE', url }),

  /**
   * Upload multipart form data.
   *
   * Content-Type is unset on purpose: the runtime must generate it so that it
   * carries the multipart boundary.
   */
  upload: (url, formData, config) =>
    request({
      ...config,
      method: 'POST',
      url,
      data: formData,
      headers: { ...config?.headers, 'Content-Type': undefined },
    }),
};

export default apiClient;
