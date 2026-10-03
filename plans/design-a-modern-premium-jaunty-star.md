# HealthPatch — Implementation Plan

## Context

Build a complete, premium healthcare IoT web application called "HealthPatch" that monitors patients in real-time via ESP32 wearable patches. The app should feel like a polished product at the intersection of Apple Health, Fitbit, Philips Healthcare, and modern SaaS dashboards — not a prototype or student project.

Twelve screens are required, each backed by a full design system. The existing project is a blank Vite + React 19 + Tailwind CSS v4 scaffold with a dot-grid background in App.tsx.

---

## Aesthetic Stance

**Swiss-Medical**: Strict typographic grid, generous whitespace, precise alignment, functional beauty. Medical blue + teal + emerald palette on a near-white ground. Glassmorphism applied selectively (modals, alerts, overlay cards only). Clean edges and subtle depth — no decorative noise.

**Fonts** (Google Fonts via `@import` in `src/index.css`):
- `DM Sans` (400, 500, 600, 700) — UI body, labels, navigation
- `DM Mono` (400, 500) — vital readings, BPM numbers, data values

**Color palette** (Tailwind CSS v4 `@theme` block in `src/index.css`):
```
--color-hp-bg: #F5F8FC          (page ground)
--color-hp-surface: #FFFFFF     (cards, panels)
--color-hp-blue: #1A6BCC        (primary medical blue)
--color-hp-blue-light: #E8F1FB  (blue tint backgrounds)
--color-hp-teal: #0D9488        (teal accent)
--color-hp-teal-light: #CCFBF1  (teal tint)
--color-hp-emerald: #10B981     (positive/healthy)
--color-hp-emerald-light: #D1FAE5
--color-hp-red: #EF4444         (critical alerts)
--color-hp-red-light: #FEE2E2
--color-hp-amber: #F59E0B       (warning)
--color-hp-amber-light: #FEF3C7
--color-hp-slate: #64748B       (muted text)
--color-hp-border: #E2E8F0      (hairline dividers)
--color-hp-dark: #0F172A        (dark nav, deep panels)
```

---

## Architecture

**Single-page React app** with screen state in `App.tsx`. No router — just a `currentScreen` state variable and a navigation sidebar.

```
src/
  App.tsx                   ← root; holds screen state + sidebar
  index.css                 ← @import fonts first, then @import tailwindcss, then @theme tokens + global CSS
  screens/
    SplashScreen.tsx
    LoginScreen.tsx
    RegisterScreen.tsx
    DashboardScreen.tsx
    LiveMonitoringScreen.tsx
    PatientProfileScreen.tsx
    DevicePairingScreen.tsx
    AIInsightsScreen.tsx
    AlertCenterScreen.tsx
    HealthHistoryScreen.tsx
    DoctorDashboardScreen.tsx
    SettingsScreen.tsx
  components/
    Sidebar.tsx             ← persistent left nav (collapsible on mobile)
    TopBar.tsx              ← breadcrumb + user avatar + notifications bell
    VitalCard.tsx           ← reusable metric card (value, label, trend, icon)
    ChartCard.tsx           ← wrapper that adds title + period selector to recharts
    AlertBadge.tsx          ← status chip (critical / warning / resolved)
    ECGLine.tsx             ← animated SVG ECG waveform (CSS animation)
    StatusDot.tsx           ← animated pulsing dot for live/offline/warning
    EmergencyButton.tsx     ← large red CTA with confirmation modal
    ToastContainer.tsx      ← stack of toast notifications
    Modal.tsx               ← glassmorphism overlay
```

---

## Dependencies to Install

```bash
pnpm add recharts lucide-react
```

- **recharts** — AreaChart, LineChart, BarChart, RadarChart for all data visualizations
- **lucide-react** — icon set (Activity, Heart, Thermometer, Wind, Battery, Wifi, etc.)

---

## Screen-by-Screen Plan

### 1. SplashScreen
- Full-viewport dark-navy background (`hp-dark`)
- Centered HealthPatch logo (SVG cross + pulse line, animated via CSS keyframes)
- Logo scales in → text fades in → circular progress arc fills → transitions to Login
- Auto-advance after 3 seconds

### 2. LoginScreen
- Split layout: left panel (brand art + tagline illustration), right panel (form)
- Email + password inputs with floating labels
- Forgot password link, Sign In button (primary blue), Sign Up link
- Glass card style on white ground

### 3. RegisterScreen
- 4-step stepper (Patient Info → Emergency Contact → Medical History → Account)
- Progress bar + step indicators at top
- Form fields with validation states, medical history checkboxes

### 4. DashboardScreen (primary screen)
- Top row: 6 `VitalCard`s (Heart Rate, SpO₂, Temperature, Stress, Battery, Signal)
- Wide ECG card: animated SVG waveform scrolling continuously
- Two-column: Vital signs recharts AreaChart (24h) + Health Score radial gauge
- AI Recommendation card (teal accent, lightbulb icon)
- Emergency button (fixed bottom-right, red, pulsing ring animation)
- Today's summary timeline

### 5. LiveMonitoringScreen
- Header: device status + signal + battery indicators
- 2×2 grid of live recharts LineCharts (Heart Rate, SpO₂, Temperature, Movement)
  - Each chart auto-updates via `setInterval` with simulated data
- Device status panel: battery progress bar, signal bars, connection quality

### 6. PatientProfileScreen
- Left sidebar: avatar, name, patient ID, assigned doctor, emergency contacts
- Right: tabbed sections (Personal Info | Medical History | Medications | Allergies)
- Each tab renders a card grid of information rows

### 7. DevicePairingScreen
- Centered card with Bluetooth scan animation (scanning rings CSS animation)
- Device list with pairing status
- Status grid: Bluetooth / WiFi / Sensors / Battery / Firmware / Calibration
- Step-by-step pairing wizard

### 8. AIInsightsScreen
- Header: Health Score gauge (large radial chart)
- Tab row: Daily | Weekly | Risk Analysis | Trends | Recommendations
- Risk analysis radar chart
- Trend prediction area chart with confidence band (two overlapping areas)
- Early warning alert cards (amber/red)

### 9. AlertCenterScreen
- Filter bar: All | Critical | Warning | Resolved
- Alert list: each item has severity dot, timestamp, description, patient name, action button
- Timeline visualization on the right (vertical line with event nodes)

### 10. HealthHistoryScreen
- Period selector: Day | Week | Month | Year
- Primary area chart (Heart Rate history) filling full width
- Below: 3-column grid of secondary metric charts
- Export PDF button (top-right, secondary style)

### 11. DoctorDashboardScreen
- Topbar with search + filter (Critical | Warning | Stable)
- Patient grid cards: avatar, name, vitals summary, status badge, "Monitor" CTA
- Critical patient list (highlighted red border) pinned at top
- Right panel: selected patient live vitals

### 12. SettingsScreen
- Left nav tabs: Appearance | Notifications | Emergency | Language | Privacy | Devices
- Dark Mode toggle (styled switch)
- Notification preference rows with toggles
- Device management list

---

## CSS / Global Styles (`src/index.css`)

```css
/* 1. Google Font imports — MUST be first */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* 2. Tailwind */
@import 'tailwindcss';

/* 3. Theme tokens */
@theme {
  --color-hp-bg: #F5F8FC;
  /* ... all tokens ... */
  --font-sans: 'DM Sans', system-ui, sans-serif;
  --font-mono: 'DM Mono', monospace;
}

/* 4. Global resets and scrollbar hiding */
/* 5. ECG keyframe animations */
/* 6. Pulse ring animation for emergency button */
/* 7. Glassmorphism utility class */
```

---

## Key Technical Details

- **Recharts charts**: wrapped in `ResponsiveContainer width="100%" height={200}`. Use `AreaChart` with gradient fills for vitals. Stroke color matches hp-blue/teal/emerald. No axis gridlines (hidden) except for subtle horizontal lines.
- **ECG animation**: SVG `<path>` with a CSS `stroke-dashoffset` animation that scrolls the waveform left continuously, or use a canvas-free approach with CSS `translateX`.
- **Live data simulation**: `useEffect` + `setInterval(100ms)` in LiveMonitoringScreen adds data points to a rolling window (last 50 points) using `useState`.
- **Toast system**: `useReducer` in App.tsx, dispatched from any screen. `ToastContainer` positioned fixed bottom-left.
- **Emergency modal**: clicking the emergency button opens a glassmorphism confirmation modal with a 5-second countdown auto-cancel.
- **Responsive**: Sidebar collapses to a bottom tab bar at `<768px`. Cards reflow from 3-col to 1-col grid.
- **Dark mode**: `class="dark"` on `<html>` toggled from Settings. CSS variables swap in the dark block.

---

## File Write Order

1. `src/index.css` — fonts + theme tokens + global CSS
2. `src/components/` — all shared components
3. `src/screens/SplashScreen.tsx`
4. `src/screens/LoginScreen.tsx`
5. `src/screens/RegisterScreen.tsx`
6. `src/screens/DashboardScreen.tsx` (most complex — ECG, charts, emergency)
7. `src/screens/LiveMonitoringScreen.tsx`
8. `src/screens/PatientProfileScreen.tsx`
9. `src/screens/DevicePairingScreen.tsx`
10. `src/screens/AIInsightsScreen.tsx`
11. `src/screens/AlertCenterScreen.tsx`
12. `src/screens/HealthHistoryScreen.tsx`
13. `src/screens/DoctorDashboardScreen.tsx`
14. `src/screens/SettingsScreen.tsx`
15. `src/App.tsx` — wires all screens + sidebar

---

## Verification

1. Splash auto-advances to Login after animation
2. Login "Sign In" navigates to Dashboard
3. Sidebar links navigate to all 12 screens
4. Live Monitoring charts animate continuously (setInterval)
5. Emergency button opens modal with countdown
6. Alert filter tabs work
7. Settings dark mode toggle applies dark class
8. All charts render without errors (recharts + lucide-react installed)
9. Mobile: sidebar collapses at 768px breakpoint
10. No TypeScript errors in build
