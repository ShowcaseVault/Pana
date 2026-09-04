import axios from 'axios';
import { API_ROUTES, BASE_URL } from './routes';

const axiosClient = axios.create({
  baseURL: BASE_URL,
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
