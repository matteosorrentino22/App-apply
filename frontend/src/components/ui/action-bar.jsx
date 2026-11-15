import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

// Barra azione fissa in basso (Sprint 75, DESIGN.md §2 e §6 `ActionBar`,
// mockup `detail-nuovo`, `desk-detail`). Bordo superiore, sfondo bianco,
// contenuto allineato alla colonna di 640 px anche da 1024 px.
// - Predefinita (dettaglio job, editor, onboarding): sostituisce la barra di
//   tab; `has-actionbar` su <html> la nasconde e porta `--app-bottom-bar`
//   all'altezza di questa barra. Si torna indietro dalla testata.
// - `stacked` (Sprint 81: Profilo, Ricerche, sezioni principali): sta SOPRA
//   la barra di tab, che resta visibile (mockup `profilo`, `ricerche`);
//   `has-actionbar-stacked` somma le due altezze in `--app-bottom-bar`.
function ActionBar({ className, children, stacked = false }) {
  const ref = useRef(null)
  useEffect(() => {
    const root = document.documentElement
    const cls = stacked ? 'has-actionbar-stacked' : 'has-actionbar'
    root.classList.add(cls)
    // Sprint 81: l'altezza reale (i pulsanti possono andare a capo a 320 px)
    // finisce in --app-actionbar-h, usata da index.css per lo spazio in fondo.
    const update = () => {
      if (ref.current) root.style.setProperty('--app-actionbar-h', `${Math.ceil(ref.current.getBoundingClientRect().height)}px`)
    }
    update()
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(update)
    if (observer && ref.current) observer.observe(ref.current)
    return () => {
      observer?.disconnect()
      root.classList.remove(cls)
      root.style.removeProperty('--app-actionbar-h')
    }
  }, [stacked])

  return (
    <div
      ref={ref}
      data-testid="action-bar"
      className={cn(
        'fixed inset-x-0 z-30 border-t border-border bg-card px-[max(16px,env(safe-area-inset-left))] pt-3',
        stacked
          ? 'bottom-[var(--app-tabbar,0px)] pb-3 lg:bottom-0 lg:pb-[max(28px,calc(12px_+_env(safe-area-inset-bottom)))]'
          : 'bottom-0 pb-[max(28px,calc(12px_+_env(safe-area-inset-bottom)))]',
      )}
    >
      <div className={cn('mx-auto flex w-full max-w-[640px] flex-col gap-2', className)}>{children}</div>
    </div>
  )
}

export { ActionBar }
