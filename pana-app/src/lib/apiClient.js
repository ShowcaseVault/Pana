/**
 * The single HTTP entry point.
 *
 * Wraps Axios so that the rest of the app never sees an Axios type. Two things
 * happen at this boundary and nowhere else:
 *
 *   - a successful body is parsed into an `ApiResponse`, so callers get the
 *     payload rather than an envelope;
 *   - every failure becomes an `ApiError`, so a `catch` block handles one type
 *     regardless of whether the server, the network, or the contract failed.
 *
 * Authentication rides on httpOnly cookies, so there is no token handling here;
 * `withCredentials` is what matters, and it must stay on for every request.
 *
 * @module lib/apiClient
 */

import axios from 'axios';
import { ApiError, ApiResponse } from './ApiResponse.js';
import { API_ROUTES, BASE_URL } from '../api/routes.js';

/** Requests that should never trigger a refresh-and-retry cycle. */
const AUTH_ENDPOINTS = [API_ROUTES.AUTH.REFRESH, API_ROUTES.AUTH.LOGOUT];

const http = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * In-flight refresh, shared by every request that hits a 401 at once.
 *
 * Without this, a page that fires several requests in parallel would send one
 * refresh each; they race, and every one after the first presents a refresh
 * token the backend has already rotated away, so the user is logged out
 *mid-session. Holding the promise means the second and later callers await the
 * same refresh.
 *
 * @type {Promise<void>|null}
 */
let refreshInFlight = null;

/** Listeners notified when the session ends and cannot be recovered. */
const sessionExpiryListeners = new Set();

/**
 * Register a callback for an unrecoverable 401.
 *
 * The auth context subscribes so it can clear user state and redirect. This is
 * a callback rather than a direct import because the client must not depend on
 * React.
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

/** Refresh the access cookie, collapsing concurrent callers onto one request. */
function refreshSession() {
  refreshInFlight ??= http
    .post(API_ROUTES.AUTH.REFRESH)
    .then(() => undefined)
    .finally(() => {
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
      // A 401 from the refresh endpoint itself means the refresh token is gone
      // too; there is nothing left to try.
      if (status === 401) notifySessionExpired();
      return Promise.reject(error);
    }

    request._retry = true;

    try {
      await refreshSession();
      return await http(request);
    } catch (refreshError) {
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
    // Already normalised -- a parse failure from ApiResponse.parse.
    if (error instanceof ApiError) throw error;
    throw ApiError.fromAxios(error);
  }
}

export const apiClient = {
  /**
   * @template T
   * @param {string} url
   * @param {import('axios').AxiosRequestConfig} [config]
   * @returns {Promise<ApiResponse<T>>}
   */
  get: (url, config) => request({ ...config, method: 'GET', url }),

  /**
   * @template T
   * @param {string} url
   * @param {unknown} [data]
   * @param {import('axios').AxiosRequestConfig} [config]
   * @returns {Promise<ApiResponse<T>>}
   */
  post: (url, data, config) => request({ ...config, method: 'POST', url, data }),

  /**
   * @template T
   * @param {string} url
   * @param {unknown} [data]
   * @param {import('axios').AxiosRequestConfig} [config]
   * @returns {Promise<ApiResponse<T>>}
   */
  patch: (url, data, config) => request({ ...config, method: 'PATCH', url, data }),

  /**
   * @template T
   * @param {string} url
   * @param {import('axios').AxiosRequestConfig} [config]
   * @returns {Promise<ApiResponse<T>>}
   */
  delete: (url, config) => request({ ...config, method: 'DELETE', url }),

  /**
   * Upload multipart form data.
   *
   * The Content-Type header is deliberately unset: the browser must generate it
   * so that it carries the multipart boundary. Setting it by hand produces a
   * body the server cannot split.
   *
   * @template T
   * @param {string} url
   * @param {FormData} formData
   * @param {import('axios').AxiosRequestConfig} [config]
   * @returns {Promise<ApiResponse<T>>}
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
