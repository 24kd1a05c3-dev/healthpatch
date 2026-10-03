import { useEffect, useState } from 'react';
import { Bell, Phone, Save, Send, ShieldCheck } from 'lucide-react';
import { apiFetch } from '../api/client';

interface NotificationSettings {
  enabled: boolean;
  phone: string | null;
  verified: boolean;
  sms: boolean;
  voice: boolean;
  deliveries: { id: string; created_at: string; notifications: Record<string, { state: string; provider_status?: string }> }[];
}

export default function SettingsScreen() {
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const load = async () => setSettings(await apiFetch<NotificationSettings>('/notifications/preferences'));
  useEffect(() => { load().catch(error => setError(error instanceof Error ? error.message : 'Could not load notification settings')); }, []);
  const command = async (operation: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(''); setStatus('');
    try { await operation(); await load(); setStatus(success); }
    catch (error) { setError(error instanceof Error ? error.message : 'Request failed'); }
    finally { setBusy(false); }
  };
  const button = 'inline-flex items-center gap-2 rounded border px-3 py-2 text-sm disabled:opacity-50';
  return <section className="mx-auto max-w-3xl p-6">
    <h2 className="text-lg font-semibold">Notification preferences</h2>
    {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    {status && <p role="status" className="mt-4 text-sm text-green-700">{status}</p>}
    {!settings ? <p className="mt-4">Loading notification settings...</p> : <>
      <dl className="mt-5 divide-y text-sm">
        <div className="grid gap-2 py-4 sm:grid-cols-[160px_1fr]"><dt>Delivery provider</dt><dd>{settings.enabled ? 'Twilio configured' : 'Not configured'}</dd></div>
        <div className="grid gap-2 py-4 sm:grid-cols-[160px_1fr]"><dt>Primary phone</dt><dd>{settings.phone || 'No saved number'} {settings.verified && <span className="ml-2 text-green-700">Verified</span>}</dd></div>
      </dl>
      {!settings.verified && <div className="flex flex-wrap items-end gap-3 border-t py-5">
        <button className={button} disabled={busy || !settings.enabled || !settings.phone} onClick={() => command(() => apiFetch('/notifications/verification/start', { method: 'POST', body: JSON.stringify({ channel: 'sms' }) }), 'Verification SMS requested.')}><Send size={16}/>Send verification SMS</button>
        <button className={button} disabled={busy || !settings.enabled || !settings.phone} onClick={() => command(() => apiFetch('/notifications/verification/start', { method: 'POST', body: JSON.stringify({ channel: 'call' }) }), 'Verification call requested.')}><Phone size={16}/>Call with verification code</button>
        <label className="flex flex-col gap-1 text-sm">Verification code<input value={code} onChange={event => setCode(event.target.value)} inputMode="numeric" autoComplete="one-time-code" maxLength={10} className="w-40 rounded border px-3 py-2" /></label>
        <button className={button} disabled={busy || !settings.enabled || !/^\d{4,10}$/.test(code)} onClick={() => command(() => apiFetch('/notifications/verification/check', { method: 'POST', body: JSON.stringify({ code }) }), 'Phone number verified.')}><ShieldCheck size={16}/>Verify</button>
      </div>}
      <fieldset className="space-y-4 border-t py-5" disabled={busy}>
        <legend className="pt-4 font-medium">Monitoring alerts</legend>
        <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={settings.sms} disabled={!settings.sms && (!settings.enabled || !settings.verified)} onChange={event => setSettings({ ...settings, sms: event.target.checked })}/><Bell size={16} className="shrink-0"/><span>I consent to automated monitoring SMS at my verified primary number.</span></label>
        <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={settings.voice} disabled={!settings.voice && (!settings.enabled || !settings.verified)} onChange={event => setSettings({ ...settings, voice: event.target.checked })}/><Phone size={16} className="shrink-0"/><span>I consent to automated monitoring voice calls at my verified primary number.</span></label>
        <p className="text-sm text-slate-600">Verification and delivery share your phone number with Twilio. Alerts contain no physiological readings. Recorded and simulated streams do not send alerts. Delivery can fail and is not emergency dispatch.</p>
        <button className={button} onClick={() => command(() => apiFetch('/notifications/preferences', { method: 'PUT', body: JSON.stringify({ sms: settings.sms, voice: settings.voice }) }), 'Notification preferences saved.')}><Save size={16}/>Save preferences</button>
      </fieldset>
      <h3 className="border-t pt-5 font-medium">Recent delivery attempts</h3>
      {settings.deliveries.length === 0 ? <p className="mt-3 text-sm text-slate-600">No delivery attempts recorded.</p> : <ul className="mt-3 divide-y text-sm">{settings.deliveries.map(delivery => <li key={delivery.id} className="py-3"><time>{new Date(delivery.created_at).toLocaleString()}</time><div className="mt-1 flex flex-wrap gap-4">{Object.entries(delivery.notifications).map(([channel, state]) => <span key={channel}>{channel}: {state.provider_status || state.state}</span>)}</div></li>)}</ul>}
    </>}
  </section>;
}
