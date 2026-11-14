import { useEffect } from 'react'
import { cn } from '@/lib/utils'

// Barra azione fissa in basso (Sprint 75, DESIGN.md §2 e §6 `ActionBar`,
// mockup `detail-nuovo`, `desk-detail`): nelle schermate che la usano
// sostituisce la barra di tab. Bordo superiore, sfondo bianco, padding
// inferiore 28 px o area sicura iOS; contenuto allineato alla colonna di
// 640 px anche da 1024 px. Mentre è montata aggiunge `has-actionbar` a
// <html>: index.css nasconde la barra di tab e porta `--app-bottom-bar`
// all'altezza di questa barra (contenuto e toast restano sopra).
function ActionBar({ className, children }) {
  useEffect(() => {
    document.documentElement.classList.add('has-actionbar')
    return () => document.documentElement.classList.remove('has-actionbar')
  }, [])

  return (
    <div
      data-testid="action-bar"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-card px-[max(16px,env(safe-area-inset-left))] pt-3 pb-[max(28px,calc(12px_+_env(safe-area-inset-bottom)))]"
    >
      <div className={cn('mx-auto flex w-full max-w-[640px] flex-col gap-2', className)}>{children}</div>
    </div>
  )
}

export { ActionBar }
