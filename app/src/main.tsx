import { createRoot } from 'react-dom/client'
import { Suspense } from 'react'
import './i18n'
import App from './App'
import './styles/globals.css'
import './styles/highlight.css'

// Register Service Worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js')
      .then((reg) => console.log('✅ SW registered:', reg.scope))
      .catch((err) => console.error('❌ SW failed:', err))
  })
}

// Mount the app — i18n must be imported above; wrapped in Suspense for lazy init
const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Root element not found')
}
const root = createRoot(rootElement)
root.render(
  <Suspense fallback={null}>
    <App />
  </Suspense>
)