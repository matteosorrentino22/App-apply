import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

// Profilo incompleto (Sprint 70, §8.A punto 41): un banner fisso con il
// link, invece di un rimando automatico all'onboarding, per non disturbare
// chi usa già l'app. Stessa regola della generazione CV (almeno un titolo
// di studio, `profile_status` di /api/accounts/me/). Con il profilo ancora
// vuoto porta all'onboarding (c'è l'import del CV), altrimenti al Profilo.
const HIDDEN_ON = ['/onboarding', '/profile']

export default function ProfileCompletionBanner() {
  const { user } = useAuth()
  const { t } = useLanguage()
  const { pathname } = useLocation()

  if (!user || user.legal_acceptance_required || !user.profile_status || user.profile_status === 'complete') {
    return null
  }
  if (HIDDEN_ON.includes(pathname)) return null

  const empty = user.profile_status === 'empty'
  return (
    <div
      role="status"
      data-testid="profile-completion-banner"
      className="mx-auto mt-3 flex max-w-2xl flex-wrap items-center justify-between gap-2 px-4"
    >
      <p className="flex-1 rounded-md bg-primary-soft px-3 py-2 text-sm text-primary">
        {t(empty ? 'profileBanner.empty' : 'profileBanner.incomplete')}{' '}
        <Link to={empty ? '/onboarding' : '/profile'} className="font-semibold underline">
          {t(empty ? 'profileBanner.emptyLink' : 'profileBanner.incompleteLink')}
        </Link>
      </p>
    </div>
  )
}
