/**
 * Backend paths for the native client.
 *
 * Mirrors `pana-app/src/api/routes.js` and adds the `/auth/mobile/*` group:
 * a device signs in with an id_token from the platform SDK and carries its
 * tokens in request bodies, so those three endpoints have no web counterpart.
 *
 * @module lib/routes
 */

export const API_ROOT = import.meta.env.VITE_API_ROOT || '/api/v1';

// The origin is not here. A debug build can be pointed at a different server
// while running, so it lives in serverStore and is read at the moment of the
// request; a constant captured at import time would go stale the first time
// someone changed it.
export const API_ROUTES = {

  /** Native auth. Tokens travel in the body, for the device keychain. */
  AUTH: {
    GOOGLE: '/auth/mobile/google',
    REFRESH: '/auth/mobile/refresh',
    LOGOUT: '/auth/mobile/logout',
  },

  HOME: `${API_ROOT}/home`,

  RECORDINGS: {
    LIST: `${API_ROOT}/recordings`,
    CREATE: `${API_ROOT}/recordings`,
    DETAIL: (id) => `${API_ROOT}/recordings/${id}`,
    UPDATE: (id) => `${API_ROOT}/recordings/${id}`,
    DELETE: (id) => `${API_ROOT}/recordings/${id}`,
  },

  TRANSCRIPTION_EVENTS: `${API_ROOT}/transcription-events`,

  TRANSCRIPTIONS: {
    DETAIL: (id) => `${API_ROOT}/transcriptions/${id}`,
  },

  DIARY: {
    CREATE: `${API_ROOT}/diary`,
    GET: `${API_ROOT}/diary`,
  },

  HISTORY: {
    CALENDAR: (year, month) => `${API_ROOT}/history/calendar/${year}/${month}`,
  },

  AUDIO_BASE: `${API_ROOT}/recordings/file`,
};
