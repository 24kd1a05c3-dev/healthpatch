import {
  Activity, LayoutDashboard, Radio, User, Cpu, Brain,
  Bell, BarChart3, Users, Settings, LogOut, ChevronLeft, ChevronRight, Menu, X
} from 'lucide-react'

export type Screen =
  | 'splash' | 'login' | 'register'
  | 'dashboard' | 'live' | 'signals' | 'simulator' | 'profile' | 'pairing'
  | 'insights' | 'alerts' | 'history' | 'doctor' | 'settings'

interface NavItem {
  id: Screen
  label: string
  icon: React.ReactNode
  badge?: number
}

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
  { id: 'live', label: 'Patch Digital Twin', icon: <Radio size={18} /> },
  { id: 'signals', label: 'Signal Lab', icon: <Activity size={18} /> },
  { id: 'simulator', label: 'Research Simulator', icon: <Cpu size={18} /> },
  { id: 'insights', label: 'Observations', icon: <Brain size={18} /> },
  { id: 'alerts', label: 'Alert Center', icon: <Bell size={18} /> },
  { id: 'history', label: 'Health History', icon: <BarChart3 size={18} /> },
  { id: 'profile', label: 'Patient Profile', icon: <User size={18} /> },
  { id: 'doctor', label: 'Doctor Dashboard', icon: <Users size={18} /> },
  { id: 'pairing', label: 'Device Pairing', icon: <Cpu size={18} /> },
  { id: 'settings', label: 'Settings', icon: <Settings size={18} /> },
]

interface Props {
  current: Screen
  onNavigate: (s: Screen) => void
  collapsed: boolean
  onToggle: () => void
  mobileOpen: boolean
  onMobileToggle: () => void
  onLogout?: () => void
  role?: string
}

export default function Sidebar({ current, onNavigate, collapsed, onToggle, mobileOpen, onMobileToggle, onLogout }: Props) {
  const handleNav = (id: Screen) => {
    onNavigate(id)
  }

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={onMobileToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed left-0 top-0 h-full z-50 flex flex-col
          bg-[#0F172A] transition-all duration-300 ease-in-out
          ${collapsed ? 'w-[68px]' : 'w-[240px]'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
        `}
        style={{ boxShadow: '4px 0 24px rgba(0,0,0,0.12)' }}
      >
        {/* Logo */}
        <div className={`flex items-center h-16 px-4 border-b border-[#1E293B] shrink-0 ${collapsed ? 'justify-center' : 'gap-3'}`}>
          <div className="w-8 h-8 rounded-lg gradient-blue flex items-center justify-center shrink-0"
            style={{ background: 'linear-gradient(135deg, #1A6BCC 0%, #0D9488 100%)' }}>
            <Activity size={16} className="text-white" />
          </div>
          {!collapsed && (
            <div>
              <div className="text-white font-semibold text-[15px] leading-tight">HealthPatch</div>
              <div className="text-[#64748B] text-[10px] uppercase tracking-widest">IoT Monitor</div>
            </div>
          )}
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {navItems.map(item => {
            const active = current === item.id
            return (
              <button
                key={item.id}
                onClick={() => handleNav(item.id)}
                className={`
                  w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium
                  transition-all duration-150 relative group
                  ${active
                    ? 'text-white bg-[#1E293B]'
                    : 'text-[#94A3B8] hover:text-white hover:bg-[#1E293B]/60'
                  }
                  ${collapsed ? 'justify-center' : ''}
                `}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 rounded-r bg-[#1A6BCC]" />
                )}
                <span className={active ? 'text-[#60A5FA]' : ''}>{item.icon}</span>
                {!collapsed && <span className="truncate">{item.label}</span>}
                {!collapsed && item.badge && (
                  <span className="ml-auto bg-[#EF4444] text-white text-[10px] font-bold rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
                    {item.badge}
                  </span>
                )}
                {collapsed && item.badge && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#EF4444] rounded-full" />
                )}
                {/* Tooltip */}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-[#1E293B] text-white text-xs rounded-md whitespace-nowrap
                    opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                    {item.label}
                  </div>
                )}
              </button>
            )
          })}
        </nav>

        {/* Bottom: collapse + logout */}
        <div className="border-t border-[#1E293B] p-3 space-y-1 shrink-0">
          <button
            onClick={() => onLogout ? onLogout() : handleNav('login')}
            className={`w-full flex items-center gap-3 px-3 py-2 text-sm text-[#94A3B8] hover:text-[#EF4444] hover:bg-[#1E293B]/60 rounded-lg transition-all ${collapsed ? 'justify-center' : ''}`}
          >
            <LogOut size={16} />
            {!collapsed && <span>Sign Out</span>}
          </button>
          <button
            onClick={onToggle}
            className={`hidden md:flex w-full items-center gap-3 px-3 py-2 text-sm text-[#64748B] hover:text-white hover:bg-[#1E293B]/60 rounded-lg transition-all ${collapsed ? 'justify-center' : ''}`}
          >
            {collapsed ? <ChevronRight size={16} /> : <><ChevronLeft size={16} /><span>Collapse</span></>}
          </button>
        </div>
      </aside>

      {/* Mobile hamburger */}
      <button
        onClick={onMobileToggle}
        className="md:hidden fixed top-4 left-4 z-30 w-9 h-9 bg-[#0F172A] rounded-lg flex items-center justify-center text-white"
      >
        {mobileOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      <nav className="fixed bottom-0 left-0 right-0 z-30 grid grid-cols-5 border-t border-[#E2E8F0] bg-white md:hidden">
        {navItems.slice(0, 5).map(item => {
          const active = current === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`relative flex h-16 flex-col items-center justify-center gap-1 text-[10px] font-medium ${
                active ? 'text-[#1A6BCC]' : 'text-[#64748B]'
              }`}
            >
              {item.icon}
              <span className="max-w-[64px] truncate">{item.label.replace(' Monitoring', '')}</span>
              {item.badge && (
                <span className="absolute right-4 top-2 h-2 w-2 rounded-full bg-[#EF4444]" />
              )}
            </button>
          )
        })}
      </nav>
    </>
  )
}
