import { cn } from '@/lib/utils'

// Riga di un documento del job (Sprint 75, DESIGN.md §6 `DocumentRow`,
// mockup `detail-cv-generato`, `detail-docs-pages`): icona in un riquadro,
// nome, stato (verde se pronto) e azioni a destra; sotto, eventuali avvisi
// (`children`, es. Banner "occupa 2 pagine").
function DocumentRow({ icon: Icon, title, status, ready = false, actions, children, className, ...props }) {
  return (
    <div className={cn('flex flex-col gap-3 py-3.5 first:pt-0 last:pb-0', className)} {...props}>
      <div className="flex items-center gap-3">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-field bg-secondary text-chip-foreground">
          <Icon className="h-6 w-6" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-base font-bold leading-tight text-foreground">{title}</p>
          <p className={cn('mt-0.5 text-sm leading-snug', ready ? 'font-semibold text-success' : 'text-muted-foreground')}>
            {status}
          </p>
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-0.5">{actions}</div> : null}
      </div>
      {children}
    </div>
  )
}

export { DocumentRow }
