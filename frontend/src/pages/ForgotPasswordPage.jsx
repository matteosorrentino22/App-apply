import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Info, MailCheck } from 'lucide-react'
import { requestPasswordReset } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import { AuthPage } from '@/components/auth/AuthPage'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

// Recupero password (Sprint 67): risposta sempre identica, che l'email sia
// registrata o no. Senza invio email configurato la funzione non è disponibile.
// Aspetto Sprint 79 (mockup `forgot`, `forgot-sent`).
export default function ForgotPasswordPage() {
  const { t } = useLanguage()
  const legalInfo = useLegalInfo()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const unavailable = legalInfo && !legalInfo.email_enabled

  async function handleSubmit(event) {
    event.preventDefault()
    setSent(false)
    setError('')
    setSubmitting(true)
    try {
      await requestPasswordReset(email)
      setSent(true)
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) setError(t('forgotPassword.unavailable'))
      else if (err instanceof ApiError && err.status === 429) setError(t('common.tooManyRequests'))
      else setError(t('common.genericError'))
    } finally {
      setSubmitting(false)
    }
  }

  const back = (
    <Link to="/login" className="inline-flex min-h-11 items-center font-bold text-primary hover:underline">
      {t('forgotPassword.backToLogin')}
    </Link>
  )

  if (sent) {
    return (
      <AuthPage centered title={t('forgotPassword.title')} icon={MailCheck} description={t('forgotPassword.sent')} footer={back} />
    )
  }

  return (
    <AuthPage title={t('forgotPassword.title')} description={unavailable ? null : t('forgotPassword.intro')} footer={back}>
      {unavailable ? (
        <Banner variant="note" icon={Info} role="alert">
          {t('forgotPassword.unavailable')}
          {legalInfo.controller?.email ? (
            <>
              {' '}
              <a href={`mailto:${legalInfo.controller.email}`} className="font-semibold underline">
                {legalInfo.controller.email}
              </a>
            </>
          ) : null}
        </Banner>
      ) : (
        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
          <Field label={t('login.email')}>
            <Input
              id="forgot-email"
              type="email"
              value={email}
              placeholder={t('auth.emailPlaceholder')}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </Field>
          {error ? <Banner variant="error">{error}</Banner> : null}
          <Button type="submit" size="lg" disabled={submitting || !email}>
            {t('forgotPassword.submit')}
          </Button>
        </form>
      )}
    </AuthPage>
  )
}
