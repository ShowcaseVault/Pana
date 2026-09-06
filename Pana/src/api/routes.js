/**
 * Centralized definition of all backend API routes.
 * These paths are relative to the BASE_API_URL configured in axiosClient.
 */
export const BASE_URL =
  import.meta.env.VITE_BASE_API_URL || "http://localhost:8000";

// Versioned root shared by every application route. Must match the backend's
// API_PREFIX + API_VERSION; a version bump is this one line.
export const API_ROOT = import.meta.env.VITE_API_ROOT || "/api/v1";

export const API_ROUTES = {
  // Auth sits outside the versioned root: the Google callback URL is
  // registered with Google and cannot move between versions.
  AUTH: {
    GOOGLE_LOGIN: "/auth/google",
    GOOGLE_CALLBACK: "/auth/google/callback",
    REFRESH: "/auth/refresh", // POST
    LOGOUT: "/auth/logout", // POST
  },
  HOME: `${API_ROOT}/home`, // GET - Home page data
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
  // Audio is now served by an authenticated route, not a static mount.
  AUDIO_BASE: `${API_ROOT}/recordings/file`,
};
