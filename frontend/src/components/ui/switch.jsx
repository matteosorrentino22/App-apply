import { cn } from '@/lib/utils'

// Interruttore senza dipendenze (Sprint 76, DESIGN.md §6 `Switch`):
// <button role="switch" aria-checked>, attivabile con Spazio/Invio. Stessa
// API "checked / onCheckedChange" della Checkbox che sostituisce.
function Switch({ checked, onCheckedChange, label, id, disabled, className }) {
  return (
    <button
      type="button"
      role="switch"
      id={id}
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        'relative inline-flex h-8 w-[52px] shrink-0 items-center rounded-full transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/30 disabled:opacity-45',
        checked ? 'bg-primary' : 'bg-input',
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'inline-block h-6 w-6 rounded-full bg-card shadow-card transition-transform',
          checked ? 'translate-x-6' : 'translate-x-1',
        )}
      />
    </button>
  )
}

export { Switch }
