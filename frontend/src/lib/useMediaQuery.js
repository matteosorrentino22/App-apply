import { useEffect, useSyncExternalStore } from 'react'

// true se la media query è soddisfatta, aggiornato al ridimensionamento
// (Sprint 76: editor con chat in colonna da 1024 px, in un pannello sotto).
export function useMediaQuery(query) {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query)
      list.addEventListener('change', onChange)
      return () => list.removeEventListener('change', onChange)
    },
    () => window.matchMedia(query).matches,
    () => false,
  )
}

// Tastiera a schermo (Sprint 76): su iPhone Safari non riduce il viewport
// di layout, quindi un pannello fisso in basso finirebbe sotto la tastiera.
// Mentre `active`, scrive su <html> `--keyboard-inset` (altezza coperta in
// basso) e `--visual-height` (altezza visibile), letti dal pannello della
// chat. Senza tastiera valgono 0 e 100dvh.
export function useKeyboardInset(active) {
  useEffect(() => {
    const viewport = window.visualViewport
    const root = document.documentElement
    if (!active || !viewport) return
    function update() {
      const inset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop)
      root.style.setProperty('--keyboard-inset', `${Math.round(inset)}px`)
      root.style.setProperty('--visual-height', `${Math.round(viewport.height)}px`)
    }
    update()
    viewport.addEventListener('resize', update)
    viewport.addEventListener('scroll', update)
    return () => {
      viewport.removeEventListener('resize', update)
      viewport.removeEventListener('scroll', update)
      root.style.removeProperty('--keyboard-inset')
      root.style.removeProperty('--visual-height')
    }
  }, [active])
}
