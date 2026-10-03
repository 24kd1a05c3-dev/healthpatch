import { apiFetch, setToken, clearToken, withSessionLock } from './client';

export const login = async (email: string, password: string): Promise<any> => {
  const res = await withSessionLock(() => apiFetch<any>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  }));
  if (res.access_token) setToken(res.access_token);
  return res;
};

export const register = async (data: any): Promise<any> => {
  const res = await withSessionLock(() => apiFetch<any>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data)
  }));
  if (res.access_token) setToken(res.access_token);
  return res;
};

export const logout = async (): Promise<void> => {
  await withSessionLock(() => apiFetch('/auth/logout', { method: 'POST' }));
  clearToken();
};

export const getProfile = (): Promise<any> => apiFetch('/users/me');

export const updateProfile = (data: any): Promise<any> => 
  apiFetch('/users/me', { method: 'PUT', body: JSON.stringify(data) });
