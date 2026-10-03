import { apiFetch } from './client'

export type ReplaySpeed = 1 | 2 | 5

export interface ReplayFailureSettings {
  packet_loss_percent: number
  duplicate_percent: number
  latency_ms: number
  disconnect_every_batches: number | null
  disconnect_duration_ms: number
}

export const getDatasets = () => apiFetch<any[]>('/replay/datasets')
export const getReplayStatus = () => apiFetch<any>('/replay/status')
export const startReplay = (recordId: string, speed: ReplaySpeed, failures: ReplayFailureSettings) =>
  apiFetch<any>('/replay/start', { method: 'POST', body: JSON.stringify({ dataset: 'BIDMC', record_id: recordId, speed, failures }) })
export const pauseReplay = () => apiFetch<any>('/replay/pause', { method: 'POST' })
export const resumeReplay = () => apiFetch<any>('/replay/resume', { method: 'POST' })
export const stopReplay = () => apiFetch<any>('/replay/stop', { method: 'POST' })
export const restartReplay = () => apiFetch<any>('/replay/restart', { method: 'POST' })
export const seekReplay = (position_seconds: number) =>
  apiFetch<any>('/replay/seek', { method: 'POST', body: JSON.stringify({ position_seconds }) })
export const setReplaySpeed = (speed: ReplaySpeed) =>
  apiFetch<any>('/replay/speed', { method: 'POST', body: JSON.stringify({ speed }) })
