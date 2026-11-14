import { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { acceptLegal } from '../api/auth'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import LegalConsents from '@/components/LegalConsents'
import { allConsentsGiven, EMPTY_CONSENTS } from '@/lib/legalConsents'
import { DeleteAccountButton, ExportDataButton } from '@/components/AccountDataActions'

// Schermata bloccante (Sprint 67) per chi non ha ancora accettato le
// versioni correnti di informativa e termini (utenti precedenti allo
// sprint o nuova versione dei testi): ProtectedRoute la mostra al posto di
// qualunque pagina finché /api/accounts/me/ riporta legal_acceptance_required.
export default function LegalAcceptancePage() {
  const { t } = useLanguage()
  const { setUser, logout } = useAuth()
  const [consents, setConsents] = useState(EMPTY_CONSENTS)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

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
    <div className="mx-auto flex max-w-lg flex-col gap-6 px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>{t('legal.acceptanceTitle')}</CardTitle>
          <CardDescription>{t('legal.acceptanceIntro')}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <LegalConsents consents={consents} onChange={setConsents} idPrefix="gate" />
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </CardContent>
        <CardFooter>
          <Button
            type="button"
            className="w-full"
            disabled={submitting || !allConsentsGiven(consents)}
            onClick={handleSubmit}
          >
            {t('legal.acceptanceSubmit')}
          </Button>
        </CardFooter>
      </Card>
      <div className="flex flex-col gap-3 text-sm text-muted-foreground">
        <p>{t('legal.acceptanceDecline')}</p>
        <div className="flex flex-wrap gap-2">
          <ExportDataButton />
          <DeleteAccountButton />
          <Button type="button" variant="ghost" onClick={logout}>
            {t('account.logout')}
          </Button>
        </div>
      </div>
    </div>
  )
}
