import axiosClient from './axiosClient';
import { API_ROUTES } from './routes';

export const getUser = async () => {
  return axiosClient.get(API_ROUTES.HOME);
};

export const logout = async () => {
  return axiosClient.post(API_ROUTES.AUTH.LOGOUT);
};
