/**
 * Every backend path the app knows about.
 *
 * Paths live here and nowhere else, so a backend route move is a change in one
 * file. Services build requests from these; components should not import this
 * module directly -- they go through a service or a query hook.
 *
 * @module api/routes
 */

/** Origin of the API. Requests go through the client, which sets this as its baseURL. */
export const BASE_URL = import.meta.env.VITE_BASE_API_URL || 'http://localhost:8000';

/**
 * Versioned root shared by every application route. Must match the backend's
 * `API_PREFIX` + `API_VERSION`; a version bump is this one line.
 */
export const API_ROOT = import.meta.env.VITE_API_ROOT || '/api/v1';

export const API_ROUTES = {
  /**
   * The API origin, for the few cases that need an absolute URL rather than a
   * client request: an `<audio>` src, an `EventSource`, and the OAuth redirect.
   */
  ORIGIN: BASE_URL,

  /**
   * Auth sits outside the versioned root: the Google callback URL is registered
   * with Google and cannot move between versions.
   */
  AUTH: {
    GOOGLE_LOGIN: '/auth/google',
    GOOGLE_CALLBACK: '/auth/google/callback',
    REFRESH: '/auth/refresh',
    LOGOUT: '/auth/logout',
  },

  /** Current user and dashboard payload. */
  HOME: `${API_ROOT}/home`,

  RECORDINGS: {
    LIST: `${API_ROOT}/recordings`,
    CREATE: `${API_ROOT}/recordings`,
    /** @param {number|string} id */
    DETAIL: (id) => `${API_ROOT}/recordings/${id}`,
    /** @param {number|string} id */
    UPDATE: (id) => `${API_ROOT}/recordings/${id}`,
    /** @param {number|string} id */
    DELETE: (id) => `${API_ROOT}/recordings/${id}`,
  },

  /** Server-sent events for transcription completion. */
  TRANSCRIPTION_EVENTS: `${API_ROOT}/transcription-events`,

  TRANSCRIPTIONS: {
    /** @param {number|string} id */
    DETAIL: (id) => `${API_ROOT}/transcriptions/${id}`,
  },

  DIARY: {
    CREATE: `${API_ROOT}/diary`,
    GET: `${API_ROOT}/diary`,
  },

  HISTORY: {
    /**
     * @param {number} year
     * @param {number} month 1-indexed.
     */
    CALENDAR: (year, month) => `${API_ROOT}/history/calendar/${year}/${month}`,
  },

  /** Audio is served by an authenticated route, not a static mount. */
  AUDIO_BASE: `${API_ROOT}/recordings/file`,
};
