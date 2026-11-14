import { Check, ChevronDown, ChevronUp, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

// Contatore espandibile "7 corrispondenze" / "1 gap" (Sprint 75, DESIGN.md
// §6 `CounterToggle`, mockup `detail-nuovo`). Il numero non va mai a capo;
// l'etichetta sì, se in italiano non sta nella metà dello schermo a 360 px.
const TONES = {
  success: { box: 'border-success-border bg-success-soft text-success', icon: Check },
  destructive: { box: 'border-destructive-border bg-destructive-soft text-destructive-text', icon: Minus },
}

function CounterToggle({ tone, count, label, expanded, controls, onClick, className }) {
  const { box, icon: Icon } = TONES[tone]
  const Chevron = expanded ? ChevronUp : ChevronDown
  return (
    <button
      type="button"
      aria-expanded={expanded}
      aria-controls={controls}
      onClick={onClick}
      className={cn(
        'flex min-h-12 items-center gap-2 rounded-field border px-3 py-2 text-left text-base font-bold leading-tight outline-none focus-visible:ring-3 focus-visible:ring-ring/30',
        box,
        className,
      )}
    >
      <Icon className="h-5 w-5 shrink-0" strokeWidth={2.4} aria-hidden="true" />
      <span className="flex min-w-0 flex-1 flex-wrap gap-x-1">
        <span className="whitespace-nowrap tabular-nums">{count}</span>
        <span className="min-w-0 break-words">{label}</span>
      </span>
      <Chevron className="h-5 w-5 shrink-0" aria-hidden="true" />
    </button>
  )
}

export { CounterToggle }
