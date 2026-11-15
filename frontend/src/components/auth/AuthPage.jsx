import { cn } from '@/lib/utils'

// Impianto delle pagine di accesso (Sprint 79, mockup `login`, `register`,
// `forgot`, `reset`, `verify-*`, `register-email`): colonna stretta sotto la
// testata pubblica (logo e lingua, AppShell), titolo grande e contenuto.
// `centered` per le schermate di esito (icona in un cerchio, testo centrato).
export function AuthPage({ title, description, icon: Icon, tone = 'neutral', centered = false, children, footer }) {
  return (
    <div className={cn('mx-auto flex w-full max-w-sm flex-col gap-5 px-4 pb-8 pt-8', centered && 'items-center pt-14 text-center')}>
      {centered && title ? <h1 className="text-[26px] font-bold leading-tight tracking-[-0.01em] text-foreground">{title}</h1> : null}
      {Icon ? (
        <span
          className={cn(
            'flex h-16 w-16 items-center justify-center rounded-full',
            tone === 'error' ? 'bg-destructive-soft text-destructive-text' : tone === 'success' ? 'bg-success-soft text-success' : 'bg-primary-soft text-primary',
          )}
        >
          <Icon className="h-7 w-7" aria-hidden="true" />
        </span>
      ) : null}
      {!centered && title ? <h1 className="text-[32px] font-bold leading-tight tracking-[-0.01em] text-foreground">{title}</h1> : null}
      {description ? <p className="text-[15px] leading-normal text-muted-foreground">{description}</p> : null}
      <div className="flex w-full flex-col gap-4 text-left">{children}</div>
      {footer ? <div className="w-full text-center text-[15px] text-muted-foreground">{footer}</div> : null}
    </div>
  )
}
