import { Sparkles } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import { ActionCostHint } from '../ActionCost'
import { Button } from '@/components/ui/button'
import { SheetClose, SheetFooter } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'

// Pezzi comuni dei pannelli di generazione del dettaglio (Sprint 75, mockup
// `detail-gap`, `detail-cover-letter`, `detail-message`).

// "123/2000" accanto a un suggerimento facoltativo.
export function CharCountHint({ length, max, children }) {
  return (
    <span className="flex items-start justify-between gap-3">
      <span>{children}</span>
      <span className="shrink-0 tabular-nums">
        {length}/{max}
      </span>
    </span>
  )
}

// Indicazioni date in precedenza, riusabili con un tocco (pillole).
export function PastInstructions({ label, items, selected, onToggle }) {
  if (items.length === 0) return null
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-[13px] font-semibold leading-snug text-label">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {items.map((text, index) => {
          const pressed = selected.includes(text)
          return (
            <button
              key={index}
              type="button"
              aria-pressed={pressed}
              title={text}
              onClick={() => onToggle(text)}
              className={cn(
                'max-w-full rounded-[18px] px-3.5 py-2 text-left text-[13px] font-semibold leading-snug outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/30',
                pressed ? 'bg-primary text-primary-foreground' : 'bg-secondary text-chip-foreground hover:bg-accent',
              )}
            >
              <span className="line-clamp-3 break-words">{text}</span>
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}

// Piede: costo della prossima richiesta, motivo del blocco, azione, Annulla.
// Con massimale e saldo esauriti il pulsante è disattivato e il motivo è
// il testo del costo stesso (DESIGN.md §5).
export function GenerationFooter({ usage, action, submitLabel, onSubmit, disabled, reason }) {
  const { t } = useLanguage()
  const blocked = usage?.actions?.[action]?.next_charge === 'blocked'
  return (
    <SheetFooter>
      <ActionCostHint usage={usage} action={action} className="text-center text-[13px] font-semibold" />
      {reason ? (
        <p role="alert" className="text-center text-[13px] text-destructive-text">
          {reason}
        </p>
      ) : null}
      <Button size="lg" onClick={onSubmit} disabled={disabled || blocked}>
        <Sparkles className="h-5 w-5" aria-hidden="true" />
        {submitLabel}
      </Button>
      <SheetClose asChild>
        <Button variant="text">{t('common.cancel')}</Button>
      </SheetClose>
    </SheetFooter>
  )
}
