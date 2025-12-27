import axiosClient from './axiosClient';
import { API_ROUTES } from './routes';

export const getGoogleSession = async (code) => {
  return axiosClient.get(`${API_ROUTES.AUTH.GOOGLE_SESSION}?code=${code}`);
};

export const getUser = async () => {
  return axiosClient.get(API_ROUTES.HOME);
};

export const logout = async () => {
  // Assuming there is a logout endpoint or we just clear client state
  return Promise.resolve();
};
