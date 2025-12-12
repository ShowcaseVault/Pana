import axios from 'axios';

const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_BASE_API_URL || 'http://localhost:8000', // Fallback or use env
  withCredentials: true, // Critical for cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

axiosClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        // Attempt to refresh token
        // We need to import API_ROUTES here, but circular dependency might be an issue if routes.js imports something.
        // routes.js is pure constants so it's fine.
        const { API_ROUTES } = await import('./routes'); 
        await axiosClient.post(API_ROUTES.AUTH.REFRESH);
        // Retry original request
        return axiosClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, let auth context handle logout
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
