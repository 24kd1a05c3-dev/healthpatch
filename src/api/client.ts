const API_BASE = import.meta.env.VITE_API_BASE || `${window.location.protocol}//${window.location.hostname}:8000`;

// Token management
let accessToken: string | null = null;
localStorage.removeItem('hp_token');
function getToken(): string | null { return accessToken; }
function setToken(token: string): void { accessToken = token; }
function clearToken(): void { accessToken = null; }
let refreshInFlight: Promise<any> | null = null;
export async function withSessionLock<T>(operation: () => Promise<T>): Promise<T> {
  return navigator.locks ? await navigator.locks.request('healthpatch-session', operation) : await operation();
}
export function refreshSession(): Promise<any> {
  const refresh = () => fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'include', signal: AbortSignal.timeout(15000) })
    .then(async res => { if (!res.ok) throw new Error('Session expired'); const data = await res.json(); setToken(data.access_token); window.dispatchEvent(new Event('hp:token-refreshed')); return data; })
  // Cookies are shared across tabs: serialize rotation without persisting bearer tokens.
  if (!refreshInFlight) refreshInFlight = withSessionLock(refresh).finally(() => { refreshInFlight = null; });
  return refreshInFlight;
}

// Generic fetch wrapper
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const request = () => fetch(`${API_BASE}${path}`, { ...options, signal: options?.signal ?? AbortSignal.timeout(15000), credentials: 'include', headers: { ...headers, ...options?.headers } });
  let res = await request();
  if (res.status === 401 && token && !path.startsWith('/auth/')) {
    try {
      await refreshSession();
      headers.Authorization = `Bearer ${getToken()}`;
      res = await request();
    } catch { clearToken(); window.dispatchEvent(new CustomEvent('hp:session-expired')); }
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = error.detail;
    const message = Array.isArray(detail)
      ? detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.slice(1).join('.') || 'Input'}: ${item.msg || 'Invalid value'}`).join('; ')
      : typeof detail === 'string' ? detail : 'Request failed';
    throw new Error(message);
  }
  return res.json();
}

export { API_BASE, getToken, setToken, clearToken, apiFetch };
