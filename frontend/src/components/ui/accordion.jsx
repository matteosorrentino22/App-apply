import { useId, useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'

// Sezione a fisarmonica senza dipendenze (Sprint 76, DESIGN.md §6, mockup
// `cv-editor`): pulsante con aria-expanded/aria-controls, titolo a sinistra,
// riassunto (es. "6 aree") e freccia a destra. `nested` per le esperienze
// dentro "Esperienze" (bordo più leggero, niente ombra).
function AccordionSection({ title, summary, defaultOpen = false, nested = false, headingLevel = 2, className, children, ...props }) {
  const [open, setOpen] = useState(defaultOpen)
  const panelId = useId()
  const Heading = `h${headingLevel}`
  const Chevron = open ? ChevronUp : ChevronDown
  return (
    <section
      className={cn('rounded-card border border-border bg-card', nested ? '' : 'shadow-card', className)}
      {...props}
    >
      <Heading>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((current) => !current)}
          className="flex min-h-14 w-full items-center gap-3 rounded-card px-4 py-3 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/30"
        >
          <span className="min-w-0 flex-1 text-base font-bold leading-tight text-foreground">{title}</span>
          {summary ? (
            <span className="min-w-0 max-w-[45%] truncate text-sm font-normal text-muted-foreground">{summary}</span>
          ) : null}
          <Chevron className="h-5 w-5 shrink-0 text-chip-foreground" aria-hidden="true" />
        </button>
      </Heading>
      {open ? (
        <div id={panelId} className="flex flex-col gap-4 px-4 pb-4">
          {children}
        </div>
      ) : null}
    </section>
  )
}

export { AccordionSection }
