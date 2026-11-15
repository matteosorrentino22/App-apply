import { useAuth } from '../../auth/AuthContext'
import { useLanguage } from '../../i18n/LanguageContext'
import UsageLimitsCard from '@/components/UsageLimitsCard'
import { SettingsSubpageHeader } from '@/components/settings/SettingsList'
import { Spinner } from '@/components/ui/spinner'
import { useUsage } from '@/lib/usage'
import { formatEuro } from '../../utils/money'

// "I tuoi limiti di oggi" (Sprint 70; dallo Sprint 78 sottopagina
// /settings/limits, mockup `settings-limiti`): saldo del credito e, per ogni
// azione, usate oggi / massimale e prezzo oltre il massimale.
export default function LimitsPage() {
  const { t, lang } = useLanguage()
  const { user } = useAuth()
  const { usage } = useUsage()
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 pb-6 pt-3 lg:pt-6">
      <SettingsSubpageHeader title={t('usage.title')} />
      {usage ? (
        <>
          <div className="flex items-center justify-between gap-3 rounded-card border border-border bg-card px-4 py-3.5 shadow-card">
            <span className="text-[15px] text-muted-foreground">{t('account.creditBalance')}</span>
            <span className="text-2xl font-bold tabular-nums text-foreground">{formatEuro(usage.extra_credit, lang)}</span>
          </div>
          <UsageLimitsCard usage={usage} timeZone={user?.timezone} />
        </>
      ) : (
        <div className="flex justify-center py-10">
          <Spinner size={28} />
        </div>
      )}
    </div>
  )
}
