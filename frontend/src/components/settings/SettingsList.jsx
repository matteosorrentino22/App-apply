import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../../i18n/LanguageContext'
import { cn } from '@/lib/utils'

// Elenco a gruppi delle Impostazioni (Sprint 78, mockup `impostazioni`,
// `settings-privacy`): titolo del gruppo in maiuscoletto, poi una card con
// righe separate. Una riga è un link a una sottopagina (con ›), un pulsante
// che apre un pannello (con ›) oppure una riga con un controllo a destra
// (interruttore); `children` va sotto il testo (es. orario, stato).

export function SettingsGroup({ title, tone, children, className }) {
  return (
    <section className={cn('flex flex-col gap-2', className)} aria-label={title}>
      {title ? (
        <h2
          className={cn(
            'px-1 text-xs font-bold uppercase tracking-[0.08em]',
            tone === 'danger' ? 'text-destructive-text' : 'text-muted-foreground',
          )}
        >
          {title}
        </h2>
      ) : null}
      <div
        className={cn(
          'flex flex-col divide-y divide-border overflow-hidden rounded-card border bg-card shadow-card',
          tone === 'danger' ? 'border-destructive-border' : 'border-border',
        )}
      >
        {children}
      </div>
    </section>
  )
}

function RowBody({ icon: Icon, title, subtitle, children }) {
  return (
    <>
      {Icon ? (
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-field bg-secondary text-chip-foreground">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      ) : null}
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="break-words text-base font-semibold leading-tight text-foreground">{title}</span>
        {subtitle ? <span className="break-words text-sm leading-snug text-muted-foreground">{subtitle}</span> : null}
        {children}
      </span>
    </>
  )
}

const rowClass = 'flex min-h-16 w-full items-center gap-3.5 px-4 py-3 text-left'
const interactive = 'outline-none transition-colors hover:bg-tint focus-visible:bg-tint focus-visible:ring-3 focus-visible:ring-inset focus-visible:ring-ring/30'

export function SettingsRow({ icon, title, subtitle, to, onClick, trailing, children, testId }) {
  const body = (
    <RowBody icon={icon} title={title} subtitle={subtitle}>
      {children}
    </RowBody>
  )
  const chevron = <ChevronRight className="h-5 w-5 shrink-0 text-chip-foreground" aria-hidden="true" />
  if (to) {
    return (
      <Link to={to} className={cn(rowClass, interactive)} data-testid={testId}>
        {body}
        {chevron}
      </Link>
    )
  }
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn(rowClass, interactive)} data-testid={testId}>
        {body}
        {chevron}
      </button>
    )
  }
  return (
    <div className={rowClass} data-testid={testId}>
      {body}
      {trailing ? <div className="shrink-0">{trailing}</div> : null}
    </div>
  )
}

// Testata delle sottopagine (mockup `ricerche`, `settings-privacy`,
// `settings-limiti`): "‹ Impostazioni", titolo e descrizione.
export function SettingsSubpageHeader({ title, description }) {
  const { t } = useLanguage()
  return (
    <div className="flex flex-col gap-3">
      <Link
        to="/settings"
        className="-ml-2 flex min-h-11 w-fit items-center gap-1 rounded-field px-2 text-base font-semibold text-primary outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/30"
      >
        <ChevronLeft className="h-5 w-5" aria-hidden="true" />
        {t('account.title')}
      </Link>
      <div>
        <h1 className="text-[28px] font-bold leading-tight tracking-[-0.01em] text-foreground">{title}</h1>
        {description ? <p className="mt-1 text-[15px] leading-normal text-muted-foreground">{description}</p> : null}
      </div>
    </div>
  )
}
