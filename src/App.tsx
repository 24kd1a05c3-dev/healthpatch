import { lazy, Suspense, useState, useCallback, useEffect, useReducer, type CSSProperties } from 'react'
import Sidebar, { type Screen } from './components/Sidebar'
import TopBar from './components/TopBar'
import ToastContainer, { type Toast } from './components/ToastContainer'

import LoginScreen from './screens/LoginScreen'
const RegisterScreen = lazy(() => import('./screens/RegisterScreen'))
const PatientWorkspace = lazy(() => import('./screens/PatientWorkspace'))
const LiveMonitoringScreen = lazy(() => import('./screens/LiveMonitoringScreen'))
const SignalLabScreen = lazy(() => import('./screens/SignalLabScreen'))
const PatientProfileScreen = lazy(() => import('./screens/PatientProfileScreen'))
const DevicePairingScreen = lazy(() => import('./screens/DevicePairingScreen'))
const DoctorDashboardScreen = lazy(() => import('./screens/DoctorDashboardScreen'))
const SettingsScreen = lazy(() => import('./screens/SettingsScreen'))
const SimulatorScreen = lazy(() => import('./screens/SimulatorScreen'))

import { AuthProvider, useAuth } from './context/AuthContext'
import { HealthDataProvider, useHealthData } from './context/HealthDataContext'

type ToastAction =
  | { type: 'ADD'; payload: Omit<Toast, 'id'> }
  | { type: 'DISMISS'; id: string }

function toastReducer(state: Toast[], action: ToastAction): Toast[] {
  switch (action.type) {
    case 'ADD':
      return [...state, { ...action.payload, id: Math.random().toString(36).slice(2) }]
    case 'DISMISS':
      return state.filter(t => t.id !== action.id)
    default:
      return state
  }
}

const AUTH_SCREENS: Screen[] = ['splash', 'login', 'register']

function AppContent() {
  const { isAuthenticated, user, loading, logout } = useAuth()
  const { alerts } = useHealthData()
  
  const [screen, setScreen] = useState<Screen>('login')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const darkMode = false
  const [toasts, dispatchToast] = useReducer(toastReducer, [])

  const navigate = useCallback((s: Screen) => {
    setScreen(s)
    setMobileOpen(false)
  }, [])

  const dismissToast = useCallback((id: string) => {
    dispatchToast({ type: 'DISMISS', id })
  }, [])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    document.body.style.backgroundColor = darkMode ? '#0F172A' : '#F5F8FC'
  }, [darkMode])

  useEffect(() => {
    if (alerts && alerts.length > 0) {
      const latest = alerts[0];
      if (latest && !latest.notified) {
        dispatchToast({
          type: 'ADD',
          payload: { 
            type: latest.level === 'critical' ? 'error' : (latest.level === 'warning' ? 'warning' : 'info'), 
            title: latest.type || 'New Alert', 
            message: latest.message || 'Alert received' 
          }
        })
        latest.notified = true;
      }
    }
  }, [alerts])

  useEffect(() => {
    if (toasts.length === 0) return
    const oldest = toasts[0]
    const t = setTimeout(() => dispatchToast({ type: 'DISMISS', id: oldest.id }), 5000)
    return () => clearTimeout(t)
  }, [toasts])

  useEffect(() => {
    if (!loading && !isAuthenticated && !AUTH_SCREENS.includes(screen)) {
      setScreen('login');
    }
    if (!loading && isAuthenticated && AUTH_SCREENS.includes(screen)) {
      setScreen(user?.role === 'doctor' ? 'doctor' : 'dashboard');
    }
  }, [isAuthenticated, loading, screen, user])

  const isAuth = AUTH_SCREENS.includes(screen)
  const sidebarWidth = sidebarCollapsed ? 68 : 240

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen bg-[#F5F8FC] dark:bg-[#0F172A]">Loading...</div>;
  }

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-[#0F172A]' : 'bg-[#F5F8FC]'}`}>
      <Suspense fallback={<p role="status" className="p-6">Loading workspace...</p>}>
      {isAuth ? (
        <>
          {screen === 'login' && <LoginScreen onNavigate={navigate} />}
          {screen === 'register' && <RegisterScreen onNavigate={navigate} />}
        </>
      ) : (
        <div className="min-h-screen">
          <Sidebar
            current={screen}
            onNavigate={navigate}
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed(c => !c)}
            mobileOpen={mobileOpen}
            onMobileToggle={() => setMobileOpen(o => !o)}
            onLogout={() => { void logout().catch(() => dispatchToast({ type: 'ADD', payload: { type: 'error', title: 'Sign out failed', message: 'Server session could not be revoked. Check your connection and retry.' } })) }}
            role={user?.role}
          />

          <div
            className="flex flex-col flex-1 min-h-screen pb-16 transition-all duration-300 md:pb-0 md:ml-[var(--sidebar-width)]"
            style={{ '--sidebar-width': `${sidebarWidth}px` } as CSSProperties}
          >
            <TopBar current={screen} alertCount={alerts?.filter(alert => !alert.acknowledged).length ?? 0} onNavigate={navigate} />

            <main className="flex-1 overflow-y-auto">
              {screen === 'dashboard' && <PatientWorkspace />}
              {screen === 'live' && <LiveMonitoringScreen />}
              {screen === 'signals' && <SignalLabScreen />}
              {screen === 'simulator' && <SimulatorScreen />}
              {screen === 'profile' && <PatientProfileScreen />}
              {screen === 'pairing' && <DevicePairingScreen />}
              {screen === 'insights' && <PatientWorkspace view="insights" />}
              {screen === 'alerts' && <PatientWorkspace view="alerts" />}
              {screen === 'history' && <PatientWorkspace view="history" />}
              {screen === 'doctor' && <DoctorDashboardScreen />}
              {screen === 'settings' && <SettingsScreen />}
            </main>
          </div>
        </div>
      )}

      </Suspense>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <HealthDataProvider>
        <AppContent />
      </HealthDataProvider>
    </AuthProvider>
  )
}
