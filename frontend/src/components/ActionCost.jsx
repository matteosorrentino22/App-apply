import { useLanguage } from '../i18n/LanguageContext'
import { actionCostText } from '../lib/usage'
import { cn } from '@/lib/utils'

// Indicazione del costo della prossima richiesta di un'azione a massimale
// (Sprint 70): inclusa nel piano, a credito con il prezzo e il saldo, o
// bloccata. Dati da `useUsage` (lib/usage.js).
export function ActionCostHint({ usage, action, className }) {
  const { t, lang } = useLanguage()
  const text = actionCostText(t, lang, usage, action)
  if (!text) return null
  const next = usage.actions[action].next_charge
  return (
    <p
      data-testid={`action-cost-${action}`}
      className={cn(
        'text-xs',
        next === 'credit' ? 'font-medium text-foreground' : next === 'blocked' ? 'text-destructive' : 'text-muted-foreground',
        className,
      )}
    >
      {text}
    </p>
  )
}
