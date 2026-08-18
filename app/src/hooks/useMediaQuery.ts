import { useEffect, useState } from 'react'

/**
 * Reaktiver CSS-Media-Query-Hook.
 *
 * Verwendet z. B. für responsives UI-Verhalten, das JAVASCRIPT-Entscheidungen
 * braucht (z. B. framer-motion Animationen): die Sidebar ist auf Desktop (lg+)
 * eine ständige Spalte, auf Mobile ein Drawer. Ein reiner CSS-Approach
 * (Transform-Klassen) kollidiert mit framer-motions Inline-Styles.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false,
  )

  useEffect(() => {
    const mql = window.matchMedia(query)
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches)
    // initiale Sync (SSR-/Re-Hydration-Safety)
    setMatches(mql.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [query])

  return matches
}
