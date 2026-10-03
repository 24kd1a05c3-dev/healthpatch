// @vitest-environment jsdom
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { HealthDataProvider, useHealthData } from './HealthDataContext'

const { listeners } = vi.hoisted(() => ({ listeners: new Map<string, (packet: any) => void>() }))
vi.mock('./AuthContext', () => ({ useAuth: () => ({ isAuthenticated: true, user: { id: 'test-user' } }) }))
vi.mock('../api/health', () => ({ getLatestData: async () => null }))
vi.mock('../api/alerts', () => ({ getAlerts: async () => [] }))
vi.mock('../api/websocket', () => ({ wsClient: { connected: true, on: (event: string, callback: (packet: any) => void) => {
  listeners.set(event, callback)
  return () => listeners.delete(event)
} } }))

function Probe() {
  const { normalizedTelemetry, waveformHistory } = useHealthData()
  return <output data-testid="telemetry">{JSON.stringify({ packet: normalizedTelemetry, history: waveformHistory.ppg })}</output>
}
afterEach(cleanup)

it('updates every simulator packet, ignores duplicates and isolates patients', async () => {
  render(<HealthDataProvider><Probe /></HealthDataProvider>)
  const send = (sequence_number: number, heart_rate: number, user_id = 'test-user') => act(() => {
    listeners.get('normalized_telemetry')!({ user_id, stream_id: 'stream', source_type: 'SYNTHETIC_SIMULATOR', sequence_number, vitals: { heart_rate } })
  })
  await send(0, 70)
  await send(1, 75)
  await send(1, 99)
  await send(0, 60)
  await send(2, 120, 'someone-else')
  expect(JSON.parse(screen.getByTestId('telemetry').textContent!).packet.vitals.heart_rate).toBe(75)
})

it('keeps missing waveform sample positions', async () => {
  render(<HealthDataProvider><Probe /></HealthDataProvider>)
  await act(() => listeners.get('normalized_telemetry')!({ user_id: 'test-user', source_type: 'DATASET_REPLAY', stream_id: 'record', sequence_number: 0,
    waveforms: { start_offset_seconds: 2, sample_interval_ms: 8, ppg: [1, null, 3] }, vitals: {} }))
  expect(JSON.parse(screen.getByTestId('telemetry').textContent!).history).toEqual([{ t: 2, v: 1 }, { t: 2.008, v: null }, { t: 2.016, v: 3 }])
})
