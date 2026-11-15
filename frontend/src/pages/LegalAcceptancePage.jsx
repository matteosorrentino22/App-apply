import { useState } from 'react'
import { Download, LogOut } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { acceptLegal } from '../api/auth'
import { useLanguage } from '../i18n/LanguageContext'
import { useToast } from '@/components/ToastProvider'
import { DeleteAccountButton } from '@/components/AccountDataActions'
import { AuthPage } from '@/components/auth/AuthPage'
import LegalConsents from '@/components/LegalConsents'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { useDataExport } from '@/lib/dataExport'
import { allConsentsGiven, EMPTY_CONSENTS } from '@/lib/legalConsents'

// Schermata bloccante (Sprint 67) per chi non ha ancora accettato le
// versioni correnti di informativa e termini (utenti precedenti allo
// sprint o nuova versione dei testi): ProtectedRoute la mostra al posto di
// qualunque pagina finché /api/accounts/me/ riporta legal_acceptance_required.
// Aspetto Sprint 79 (mockup `legal-gate`): stesse tre spunte, "Continua",
// e per chi non vuole accettare export, eliminazione dell'account ed "Esci".
export default function LegalAcceptancePage() {
  const { t } = useLanguage()
  const { setUser, logout } = useAuth()
  const { showToast } = useToast()
  const [consents, setConsents] = useState(EMPTY_CONSENTS)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { busy: exporting, exportData } = useDataExport((key) => showToast(t(key)))

  async function handleSubmit() {
    setError('')
    setSubmitting(true)
    try {
      setUser(await acceptLegal(consents))
    } catch {
      setError(t('common.genericError'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthPage title={t('legal.acceptanceTitle')} description={t('legal.acceptanceIntro')}>
      <LegalConsents consents={consents} onChange={setConsents} idPrefix="gate" />
      {error ? <Banner variant="error">{error}</Banner> : null}
      <Button type="button" size="lg" disabled={submitting || !allConsentsGiven(consents)} onClick={handleSubmit}>
        {t('legal.acceptanceSubmit')}
      </Button>
      <div className="flex flex-col gap-3 border-t border-border pt-4">
        <p className="text-[15px] leading-normal text-muted-foreground">{t('legal.acceptanceDecline')}</p>
        <Button type="button" variant="secondary" size="lg" disabled={exporting} onClick={exportData}>
          <Download className="h-5 w-5" aria-hidden="true" />
          {exporting ? t('account.exportPreparing') : t('account.exportButton')}
        </Button>
        <DeleteAccountButton fullWidth />
        <Button type="button" variant="text" onClick={logout}>
          <LogOut className="h-5 w-5" aria-hidden="true" />
          {t('account.logout')}
        </Button>
      </div>
    </AuthPage>
  )
}
