import { HashRouter as Router, Routes, Route } from 'react-router-dom'
import { lazy, Suspense, useEffect } from 'react'
import ErrorBoundary from '@/components/ui/ErrorBoundary'
import { useCommandPalette } from '@/hooks/useCommandPalette'
import CommandPalette from '@/components/ui/CommandPalette'

// Route-level code-splitting: landing, onboarding and chat are independent bundles
const LandingPage = lazy(() => import('./pages/LandingPage'))
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))

function RouteFallback() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-[#0b1319]">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-green-500/40 border-t-green-500" />
    </div>
  )
}

// AppInner runs BELOW <Router> in the tree, so useCommandPalette() (which calls
// useNavigate()) sees the Router context. The command palette navigates, so it
// must stay inside the Router provider too.
function AppInner() {
  const { open, query, setQuery, inputRef, grouped, t, setOpen } = useCommandPalette()

  // Global Cmd+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [setOpen])

  return (
    <>
      {/* Skip to content link for a11y */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[200] focus:px-4 focus:py-2 focus:bg-green-500 focus:text-black focus:rounded-lg"
      >
        {t('a11y.skipToContent')}
      </a>

      <Routes>
        <Route
          path="/"
          element={
            <Suspense fallback={<RouteFallback />}>
              <LandingPage />
            </Suspense>
          }
        />
        <Route
          path="/onboarding"
          element={
            <Suspense fallback={<RouteFallback />}>
              <OnboardingPage />
            </Suspense>
          }
        />
        <Route
          path="/chat"
          element={
            <Suspense fallback={<RouteFallback />}>
              <ChatPage />
            </Suspense>
          }
        />
      </Routes>

      <CommandPalette
        open={open}
        query={query}
        setQuery={setQuery}
        inputRef={inputRef}
        grouped={grouped}
        t={t}
        onClose={() => setOpen(false)}
        onSelect={(cmd) => cmd.action()}
      />
    </>
  )
}

function App() {
  // Desktop-App (Tauri): direkt die Chat-UI öffnen statt der Marketing-Landingpage.
  // Der HashRouter liest den Hash beim Mount, also setzen wir ihn hier synchron
  // vor dem ersten Render — die PWA (Browser) behält weiterhin die Landingpage.
  if (typeof window !== 'undefined' && window.__TAURI__?.core?.invoke && !window.location.hash) {
    window.location.hash = '#/chat'
  }
  return (
    <ErrorBoundary>
      <Router>
        <AppInner />
      </Router>
    </ErrorBoundary>
  )
}

export default App
