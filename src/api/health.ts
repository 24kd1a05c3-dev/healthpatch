import { apiFetch } from './client';

export const getLatestData = (userId?: string): Promise<any> => {
  const q = userId ? `?user_id=${userId}` : '';
  return apiFetch(`/health-data/latest${q}`);
};

export const getHistory = (period: '1h'|'6h'|'24h'|'7d'|'30d', userId?: string): Promise<any> => {
  let q = `?period=${period}`;
  if (userId) q += `&user_id=${userId}`;
  return apiFetch(`/health-data/history${q}`);
};

export const getBaseline = (userId?: string): Promise<any> => {
  const q = userId ? `?user_id=${userId}` : '';
  return apiFetch(`/health-data/baseline${q}`);
};

export const getAnalysis = (userId?: string): Promise<any> => {
  const q = userId ? `?user_id=${userId}` : '';
  return apiFetch(`/health-data/analysis${q}`);
};

export const submitEmergency = (data: any): Promise<any> => 
  apiFetch('/emergency', { method: 'POST', body: JSON.stringify(data) });

export const getEmergencyHistory = (): Promise<any> => 
  apiFetch('/emergency/history');
