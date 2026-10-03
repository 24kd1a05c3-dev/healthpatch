// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import SettingsScreen from './SettingsScreen';
import { apiFetch } from '../api/client';

vi.mock('../api/client', () => ({ apiFetch: vi.fn() }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it('does not offer fake verification or consent when provider is unconfigured', async () => {
  vi.mocked(apiFetch).mockResolvedValue({ enabled: false, phone: '+919876543210', verified: false,
                                        sms: false, voice: false, deliveries: [] });
  render(<SettingsScreen/>);
  await screen.findByText('Not configured');
  expect((screen.getByRole('button', { name: 'Send verification SMS' }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole('checkbox', { name: /SMS at/ }) as HTMLInputElement).disabled).toBe(true);
  expect((screen.getByRole('checkbox', { name: /voice calls/ }) as HTMLInputElement).checked).toBe(false);
});

it('displays an actual API error instead of a successful provider state', async () => {
  vi.mocked(apiFetch).mockRejectedValue(new Error('Request failed'));
  render(<SettingsScreen/>);
  expect((await screen.findByRole('alert')).textContent).toBe('Request failed');
});
