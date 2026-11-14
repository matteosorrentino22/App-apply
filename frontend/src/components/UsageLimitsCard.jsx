import { useLanguage } from '../i18n/LanguageContext'
import { formatEuro } from '../utils/money'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'

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

export default function UsageLimitsCard({ usage, timeZone }) {
  const { t, lang } = useLanguage()
  if (!usage) return null

  const resetTime = formatResetTime(usage.resets_at, lang, timeZone)

  function extraLabel(action) {
    if (action.next_charge === 'unavailable') return t('usage.notOnPlan')
    if (action.price == null) return t('usage.noExtension')
    return formatEuro(action.price, lang)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('usage.title')}</CardTitle>
        <CardDescription>{t('usage.hint').replace('{time}', resetTime)}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th className="py-1 pr-2 font-semibold">{t('usage.colAction')}</th>
              <th className="py-1 pr-2 text-right font-semibold">{t('usage.colToday')}</th>
              <th className="py-1 text-right font-semibold">{t('usage.colExtra')}</th>
            </tr>
          </thead>
          <tbody>
            {ACTION_ORDER.filter((key) => usage.actions[key]).map((key) => {
              const action = usage.actions[key]
              return (
                <tr key={key} className="border-t border-border" data-testid={`usage-row-${key}`}>
                  <td className="py-2 pr-2">{t(`usage.action_${key}`)}</td>
                  <td className="py-2 pr-2 text-right tabular-nums">
                    {action.next_charge === 'unavailable' ? '—' : `${action.used} / ${action.limit}`}
                  </td>
                  <td className="py-2 text-right tabular-nums text-muted-foreground">{extraLabel(action)}</td>
                </tr>
              )
            })}
            {['cv_draft_chat', 'cover_letter_draft_chat'].map((key) => (
              <tr key={key} className="border-t border-border">
                <td className="py-2 pr-2">{t(`usage.action_${key}`)}</td>
                <td className="py-2 pr-2 text-right text-muted-foreground">{t('usage.alwaysCredit')}</td>
                <td className="py-2 text-right tabular-nums text-muted-foreground">
                  {t('usage.perMessage').replace('{price}', formatEuro(usage.chat_prices[key], lang))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-muted-foreground">{t('usage.creditRule')}</p>
      </CardContent>
    </Card>
  )
}
