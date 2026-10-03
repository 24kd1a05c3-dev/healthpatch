import { useState, type FormEvent } from 'react'
import { Activity, ArrowRight, Database, Eye, EyeOff, LockKeyhole, Radio, ShieldCheck } from 'lucide-react'
import type { Screen } from '../components/Sidebar'
import { useAuth } from '../context/AuthContext'
import patchImage from '../assets/healthpatch-device.png'
import PasswordResetScreen from './PasswordResetScreen'

interface Props { onNavigate: (screen: Screen) => void }

export default function LoginScreen({ onNavigate }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [resetMode, setResetMode] = useState(window.location.pathname === '/reset-password')
  const { login } = useAuth()
  const valid = email.trim().includes('@') && password.length > 0

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!valid || loading) return
    setLoading(true)
    setLoginError(null)
    try {
      await login(email.trim().toLowerCase(), password)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to sign in'
      setLoginError(message === 'Invalid credentials' ? 'Email or password is incorrect.' : message)
      setLoading(false)
    }
  }

  if (resetMode) return <PasswordResetScreen onBack={() => setResetMode(false)} />
  return (
    <main className="min-h-screen grid lg:grid-cols-[1.08fr_0.92fr] bg-[#F6F8FB]">
      <section className="hidden lg:flex relative overflow-hidden bg-[#07111F] min-h-screen p-10 xl:p-14 flex-col justify-between text-white">
        <div className="absolute inset-0 twin-grid opacity-40" />
        <div className="relative z-10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-[#14B8A6] flex items-center justify-center"><Activity size={19} /></div>
          <div><div className="font-semibold text-lg">HealthPatch</div><div className="text-[10px] uppercase text-[#6F8499]">Physiological telemetry platform</div></div>
        </div>

        <div className="relative z-10 flex-1 flex flex-col justify-center max-w-2xl mx-auto w-full">
          <div className="relative h-[390px] flex items-center justify-center">
            <div className="absolute w-[340px] h-[340px] rounded-full border border-[#2DD4BF]/20 twin-orbit" />
            <div className="absolute w-[430px] h-[430px] rounded-full border border-dashed border-[#38BDF8]/10 twin-orbit-reverse" />
            <img src={patchImage} alt="HealthPatch wearable sensor" className="relative z-10 w-[590px] max-w-[92%] object-contain drop-shadow-[0_30px_55px_rgba(0,0,0,.5)]" />
          </div>
          <div className="grid grid-cols-3 border-y border-[#17283D]">
            <Source icon={<Radio size={14} />} label="Simulator" value="Available" />
            <Source icon={<Database size={14} />} label="Dataset replay" value="BIDMC" />
            <Source icon={<ShieldCheck size={14} />} label="Provenance" value="Tracked" />
          </div>
          <h1 className="mt-8 text-3xl xl:text-4xl font-semibold leading-tight max-w-xl">A visible digital twin for every telemetry source.</h1>
          <p className="mt-3 text-sm text-[#8296AA] max-w-lg leading-relaxed">Inspect the patch, replay state, signal quality, physiological waveforms, and source history from one operational view.</p>
        </div>
        <div className="relative z-10 text-[11px] text-[#52677C]">Dataset replay is recorded data, never a live patient connection.</div>
      </section>

      <section className="flex items-center justify-center px-5 py-10 sm:px-10">
        <div className="w-full max-w-[430px]">
          <div className="lg:hidden flex items-center gap-2 mb-10"><div className="w-9 h-9 rounded-md bg-[#0D9488] text-white flex items-center justify-center"><Activity size={18} /></div><span className="font-semibold text-lg">HealthPatch</span></div>
          <div className="mb-8">
            <div className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase text-[#0D9488] mb-3"><LockKeyhole size={13} />Secure access</div>
            <h2 className="text-3xl font-semibold text-[#0F172A]">Sign in</h2>
            <p className="text-sm text-[#64748B] mt-2">Use the account created by your HealthPatch administrator.</p>
          </div>

          <form onSubmit={submit} className="space-y-5" noValidate>
            <label className="block text-[13px] font-medium text-[#1E293B]">Email address
              <input aria-label="Email address" autoComplete="email" inputMode="email" type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="name@organization.com" className="mt-2 w-full h-12 px-4 rounded-lg border border-[#CBD5E1] bg-white text-sm focus:border-[#0D9488] focus:ring-2 focus:ring-[#CCFBF1]" />
            </label>
            <label className="block text-[13px] font-medium text-[#1E293B]">Password
              <span className="relative block mt-2">
                <input aria-label="Password" autoComplete="current-password" type={showPassword ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)} placeholder="Enter your password" className="w-full h-12 px-4 pr-12 rounded-lg border border-[#CBD5E1] bg-white text-sm focus:border-[#0D9488] focus:ring-2 focus:ring-[#CCFBF1]" />
                <button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(value => !value)} className="absolute right-1 top-1 w-10 h-10 flex items-center justify-center text-[#64748B] hover:text-[#0D9488]">{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button>
              </span>
            </label>
            <button type="button" onClick={() => setResetMode(true)} className="text-xs font-medium text-[#0D9488]">Forgot password?</button>
            {loginError && <div role="alert" className="border-l-2 border-[#DC2626] bg-[#FEF2F2] px-3 py-2.5 text-xs text-[#B91C1C]">{loginError}</div>}
            <button type="submit" disabled={!valid || loading} className="w-full h-12 rounded-lg bg-[#0F766E] hover:bg-[#115E59] text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-45 disabled:cursor-not-allowed">{loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <>Continue <ArrowRight size={16} /></>}</button>
          </form>

          <div className="mt-8 pt-6 border-t border-[#E2E8F0] text-center text-sm text-[#64748B]">Need a patient account? <button onClick={() => onNavigate('register')} className="font-semibold text-[#0D9488] hover:underline">Register securely</button></div>
          <div className="mt-8 flex items-center justify-center gap-2 text-[11px] text-[#94A3B8]"><ShieldCheck size={13} />Credentials are verified by the HealthPatch API</div>
        </div>
      </section>
    </main>
  )
}

function Source({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="py-3 px-4 border-r border-[#17283D] last:border-r-0"><div className="flex items-center gap-1.5 text-[10px] text-[#6F8499] uppercase">{icon}{label}</div><div className="mt-1 text-xs font-data text-[#DCEAF5]">{value}</div></div>
}
