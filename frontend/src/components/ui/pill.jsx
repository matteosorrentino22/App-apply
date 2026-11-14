import { cn } from '@/lib/utils'

// Pillola selezionabile (DESIGN.md §6 FilterPill): sezioni della lista e
// valori dei filtri. `pressed` → aria-pressed e stile attivo.
function FilterPill({ pressed = false, className, children, ...props }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      className={cn(
        'inline-flex min-h-9 shrink-0 items-center justify-center whitespace-nowrap rounded-full px-3.5 text-[13px] font-semibold outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/30 disabled:pointer-events-none disabled:opacity-45',
        pressed ? 'bg-primary text-primary-foreground' : 'bg-secondary text-chip-foreground hover:bg-accent',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}

export { FilterPill }
