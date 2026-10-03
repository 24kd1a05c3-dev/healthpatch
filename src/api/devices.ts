import { apiFetch } from './client';

export const listDevices = (): Promise<any> => apiFetch('/devices');

export const getDevice = (deviceId: string): Promise<any> => apiFetch(`/devices/${deviceId}`);

export const registerDevice = (data: any): Promise<any> => 
  apiFetch('/devices', { method: 'POST', body: JSON.stringify(data) });

export const pairDevice = (deviceId: string): Promise<any> => 
  apiFetch(`/devices/${deviceId}/pair`, { method: 'POST' });
