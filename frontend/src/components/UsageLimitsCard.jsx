import { useLanguage } from '../i18n/LanguageContext'
import { formatEuro } from '../utils/money'

const ACTION_ORDER = ['cv', 'cover_letter', 'referral_message', 'manual_job', 'import', 'collection', 'cv_import']

// "I tuoi limiti di oggi" in Impostazioni (Sprint 70): per ogni azione a
// massimale usate oggi / massimale del piano e prezzo oltre il massimale,
// più il prezzo a messaggio delle chat degli editor.
function formatResetTime(isoString, lang, timeZone) {
  // Mezzanotte Europe/Rome, mostrata nel fuso dell'utente.
  const options = { hour: '2-digit', minute: '2-digit' }
  try {
    return new Intl.DateTimeFormat(lang, { ...options, timeZone }).format(new Date(isoString))
  } catch {
    return new Intl.DateTimeFormat(lang, options).format(new Date(isoString))
  }
}

// Sprint 78 (mockup `settings-limiti`): una riga per azione con "usate /
// massimale", barra di avanzamento e prezzo oltre il massimale; le chat
// "sempre a credito". Stessi dati di GET /api/accounts/usage/.
export default function UsageLimitsCard({ usage, timeZone, showHint = true }) {
  const { t, lang } = useLanguage()
  if (!usage) return null

  const resetTime = formatResetTime(usage.resets_at, lang, timeZone)

  function extraLabel(action) {
    if (action.next_charge === 'unavailable') return t('usage.notOnPlan')
    if (action.price == null) return t('usage.noExtension')
    return formatEuro(action.price, lang)
  }

  return (
    <section aria-label={t('usage.title')} className="flex flex-col gap-3">
      {showHint ? <p className="text-[15px] leading-normal text-muted-foreground">{t('usage.hint').replace('{time}', resetTime)}</p> : null}
      <ul className="flex flex-col divide-y divide-border rounded-card border border-border bg-card px-4 shadow-card">
        {ACTION_ORDER.filter((key) => usage.actions[key]).map((key) => {
          const action = usage.actions[key]
          const unavailable = action.next_charge === 'unavailable'
          const reached = !unavailable && action.limit > 0 && action.used >= action.limit
          const percent = unavailable || !action.limit ? 0 : Math.min(100, Math.round((action.used / action.limit) * 100))
          return (
            <li key={key} className="flex flex-col gap-2 py-3.5" data-testid={`usage-row-${key}`}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="min-w-0 text-base font-semibold text-foreground">{t(`usage.action_${key}`)}</span>
                <span className="shrink-0 text-base font-bold tabular-nums text-foreground">
                  {unavailable ? '—' : `${action.used} / ${action.limit}`}
                  {reached ? <span className="ml-1 text-xs font-semibold text-muted-foreground">· {t('usage.reached')}</span> : null}
                </span>
              </div>
              {unavailable ? null : (
                <div
                  className="h-1.5 overflow-hidden rounded-full bg-secondary"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={action.limit}
                  aria-valuenow={action.used}
                  aria-label={t(`usage.action_${key}`)}
                >
                  <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
                </div>
              )}
              <div className="flex items-baseline justify-between gap-3 text-[13px]">
                <span className="text-muted-foreground">{t('usage.colExtra')}</span>
                <span className="font-semibold tabular-nums text-foreground">{extraLabel(action)}</span>
              </div>
            </li>
          )
        })}
        {['cv_draft_chat', 'cover_letter_draft_chat'].map((key) => (
          <li key={key} className="flex flex-col gap-1.5 py-3.5">
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 text-base font-semibold text-foreground">{t(`usage.action_${key}`)}</span>
              <span className="shrink-0 text-sm text-muted-foreground">{t('usage.alwaysCredit')}</span>
            </div>
            <div className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-muted-foreground">{t('usage.colExtra')}</span>
              <span className="font-semibold tabular-nums text-foreground">
                {t('usage.perMessage').replace('{price}', formatEuro(usage.chat_prices[key], lang))}
              </span>
            </div>
          </li>
        ))}
      </ul>
      <p className="text-[13px] leading-normal text-muted-foreground">{t('usage.creditRule')}</p>
    </section>
  )
}
