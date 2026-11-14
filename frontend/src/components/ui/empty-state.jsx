import { cn } from '@/lib/utils'

// Stato vuoto (mockup `jobs-vuoto`): icona in cerchio 72 px, titolo, testo,
// azione facoltativa a tutta larghezza.
function EmptyState({ icon: Icon, title, description, action, className }) {
  return (
    <div className={cn('flex flex-col items-center gap-3.5 px-6 pt-14 text-center', className)}>
      {Icon ? (
        <div className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-primary-soft text-primary">
          <Icon className="h-8 w-8" aria-hidden="true" />
        </div>
      ) : null}
      {title ? <h2 className="text-xl font-bold text-foreground">{title}</h2> : null}
      {description ? <p className="text-[15px] leading-normal text-muted-foreground">{description}</p> : null}
      {action ? <div className="w-full pt-2">{action}</div> : null}
    </div>
  )
}

export { EmptyState }
