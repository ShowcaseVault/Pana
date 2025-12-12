/**
 * Centralized definition of all backend API routes.
 * These paths are relative to the BASE_API_URL configured in axiosClient.
 */
export const API_ROUTES = {
  AUTH: {
    GOOGLE_LOGIN: '/auth/google',
    GOOGLE_CALLBACK: '/auth/google/callback',
    GOOGLE_SESSION: '/auth/google/session', // GET ?code=...
    REFRESH: '/auth/refresh',               // POST
    DASHBOARD: '/dashboard',                              // GET
  },
};
