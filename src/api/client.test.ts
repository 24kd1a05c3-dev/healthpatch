// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('session refresh coordination', () => {
  it('serializes shared-cookie rotation and deduplicates calls within a tab', async () => {
    vi.resetModules();
    const request = vi.fn(async (_name: string, callback: () => unknown) => callback());
    Object.defineProperty(navigator, 'locks', { configurable: true, value: { request } });
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ access_token: 'test-only', user: { id: 'qa' } }) }));
    vi.stubGlobal('fetch', fetchMock);
    const client = await import('./client');
    await Promise.all([client.refreshSession(), client.refreshSession()]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledWith('healthpatch-session', expect.any(Function));
    expect(client.getToken()).toBe('test-only');
    expect(localStorage.getItem('hp_token')).toBeNull();
  });

  it('clears the single-flight state after a failed refresh', async () => {
    vi.resetModules();
    Object.defineProperty(navigator, 'locks', { configurable: true, value: undefined });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce({
      ok: true, json: async () => ({ access_token: 'recovered', user: { id: 'qa' } }) }));
    const client = await import('./client');
    await expect(client.refreshSession()).rejects.toThrow('Session expired');
    await expect(client.refreshSession()).resolves.toMatchObject({ access_token: 'recovered' });
  });
});
