import { ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Menu } from './menu'

// Bottone primario con ▾ attaccato (Sprint 75, DESIGN.md §6 `SplitButton`,
// mockup `detail-nuovo`): l'azione principale a sinistra, il menu delle
// azioni collegate a destra (si apre verso l'alto: sta nella barra in
// basso). `disabled` spegne solo l'azione principale; `menuDisabled` il ▾.
function SplitButton({ icon: Icon, children, onClick, disabled, menuLabel, items, menuDisabled, className }) {
  const half =
    'inline-flex min-h-[52px] items-center justify-center bg-primary text-primary-foreground outline-none transition-colors hover:bg-primary/90 focus-visible:ring-3 focus-visible:ring-ring/30 disabled:pointer-events-none disabled:opacity-45'
  return (
    <div className={cn('flex w-full items-stretch', className)}>
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className={cn(half, 'min-w-0 flex-1 gap-2 rounded-l-button px-5 py-3 text-center text-base font-bold leading-tight')}
      >
        {Icon ? <Icon className="h-5 w-5 shrink-0" aria-hidden="true" /> : null}
        {children}
      </button>
      <Menu
        label={menuLabel}
        items={items}
        side="top"
        align="end"
        trigger={(props) => (
          <button
            {...props}
            aria-label={menuLabel}
            disabled={menuDisabled}
            className={cn(half, 'h-full w-14 rounded-r-button border-l border-primary-foreground/30')}
          >
            <ChevronUp className="h-5 w-5" aria-hidden="true" />
          </button>
        )}
      />
    </div>
  )
}

export { SplitButton }
