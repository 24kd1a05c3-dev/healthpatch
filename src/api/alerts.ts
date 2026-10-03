import { apiFetch } from './client';

export const getAlerts = (level?: string, userId?: string, limit?: number): Promise<any> => {
  const params = new URLSearchParams();
  if (level) params.append('level', level);
  if (userId) params.append('user_id', userId);
  if (limit) params.append('limit', limit.toString());
  const q = params.toString() ? `?${params.toString()}` : '';
  return apiFetch(`/alerts${q}`);
};

export const getAlert = (alertId: string): Promise<any> => apiFetch(`/alerts/${alertId}`);

export const acknowledgeAlert = (alertId: string): Promise<any> => 
  apiFetch(`/alerts/${alertId}/acknowledge`, { method: 'POST' });
