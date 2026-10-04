import React from 'react'
import ReactDOM from 'react-dom/client'
import { lazy, Suspense } from 'react'
const App = lazy(() => import.meta.env.VITE_PUBLIC_DEMO === 'true' ? import('./DemoApp') : import('./App'))
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Suspense fallback={<p role="status">Loading HealthPatch...</p>}><App /></Suspense>
  </React.StrictMode>,
)

