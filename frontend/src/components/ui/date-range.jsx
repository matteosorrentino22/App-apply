import { cn } from '@/lib/utils'
import { Input } from './input'
import { Label } from './label'

// Coppia di campi data (Sprint 81): esperienze e istruzione del profilo e
// dell'onboarding, filtro date della lista. Su iPhone gli input type=date
// hanno una larghezza propria e affiancati uscivano dalla card; qui sono in
// una griglia minmax(0, 1fr) e impilati quando il contenitore è più stretto
// di 20rem (container query, non la larghezza dello schermo: lo stesso
// campo sta in una card, in un riquadro annidato o in un pannello).
// Stile del campo in index.css (`input[type=date]`).
function DateRangeFields({ startId, endId, startLabel, endLabel, start, end, onStartChange, onEndChange, endDisabled = false, className }) {
  return (
    <div className={cn('@container', className)}>
      <div className="grid grid-cols-1 gap-4 @[20rem]:grid-cols-2 @[20rem]:gap-3">
        <div className="flex min-w-0 flex-col gap-1.5">
          <Label htmlFor={startId}>{startLabel}</Label>
          <Input id={startId} type="date" value={start || ''} onChange={(event) => onStartChange(event.target.value)} />
        </div>
        <div className="flex min-w-0 flex-col gap-1.5">
          <Label htmlFor={endId}>{endLabel}</Label>
          <Input
            id={endId}
            type="date"
            value={end || ''}
            disabled={endDisabled}
            onChange={(event) => onEndChange(event.target.value)}
          />
        </div>
      </div>
    </div>
  )
}

export { DateRangeFields }
