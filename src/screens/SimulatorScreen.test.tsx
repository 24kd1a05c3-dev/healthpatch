// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import SimulatorScreen from './SimulatorScreen'

vi.mock('../api/client', () => ({ apiFetch: async () => ({ state: 'PAUSED', scenario: 'RUNNING', speed: 5, signal_quality: 0.75, battery: 99.5, scenarios: ['RESTING', 'RUNNING'] }) }))
vi.mock('./PatientWorkspace', () => ({ default: () => <div>Patient workspace</div> }))
afterEach(cleanup)

it('restores scenario, speed, quality and battery from the server on revisit', async () => {
  render(<SimulatorScreen />)
  await waitFor(() => expect((screen.getByRole('combobox', { name: 'Scenario' }) as HTMLSelectElement).value).toBe('RUNNING'))
  expect((screen.getByRole('combobox', { name: 'Speed' }) as HTMLSelectElement).value).toBe('5')
  expect((screen.getByRole('slider') as HTMLInputElement).value).toBe('0.75')
  expect(screen.getByText('Modeled battery: 99.5%')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'resume' })).toBeTruthy()
})
