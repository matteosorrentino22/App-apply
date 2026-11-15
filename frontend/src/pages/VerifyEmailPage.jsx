import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CircleAlert, CircleCheck, Mail } from 'lucide-react'
import { resendVerification, verifyEmail } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { AuthPage } from '@/components/auth/AuthPage'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'

// Pagina aperta dal link dell'email di verifica (Sprint 67): /verify-email?t=<token firmato>.
// Aspetto Sprint 79 (mockup `verify-ok`, `verify-expired`): esito con icona;
// link scaduto o non valido con "Invia un nuovo link".
export default function VerifyEmailPage() {
  const { t } = useLanguage()
  const [params] = useSearchParams()
  const token = params.get('t') || ''
  const [status, setStatus] = useState(token ? 'verifying' : 'invalid')
  const [email, setEmail] = useState('')
  const [resendMessage, setResendMessage] = useState('')
  const started = useRef(false)

  useEffect(() => {
    // Una sola chiamata anche con StrictMode (effetti doppi in sviluppo).
    if (!token || started.current) return
    started.current = true
    verifyEmail(token)
      .then(() => setStatus('success'))
      .catch((err) => setStatus(err instanceof ApiError && err.data?.code === 'expired' ? 'expired' : 'invalid'))
  }, [token])

  async function handleResend(event) {
    event.preventDefault()
    setResendMessage('')
    try {
      await resendVerification(email)
      setResendMessage(t('login.verificationResent'))
    } catch (err) {
      setResendMessage(
        err instanceof ApiError && err.status === 429 ? t('common.tooManyRequests') : t('common.genericError'),
      )
    }
  }

  if (status === 'verifying') {
    return (
      <AuthPage centered title={t('verifyEmail.title')}>
        <div className="flex flex-col items-center gap-3">
          <Spinner framed label={t('verifyEmail.verifying')} />
          <p className="text-[15px] text-muted-foreground">{t('verifyEmail.verifying')}</p>
        </div>
      </AuthPage>
    )
  }

  if (status === 'success') {
    return (
      <AuthPage centered title={t('verifyEmail.title')} icon={CircleCheck} tone="success" description={t('verifyEmail.success')}>
        <Button asChild size="lg">
          <Link to="/login?next=/onboarding">{t('verifyEmail.goToLogin')}</Link>
        </Button>
      </AuthPage>
    )
  }

  return (
    <AuthPage centered title={t('verifyEmail.title')} icon={CircleAlert} tone="error" description={t(`verifyEmail.${status}`)}>
      <form onSubmit={handleResend} className="flex flex-col gap-4" noValidate>
        <p className="text-[15px] text-muted-foreground">{t('verifyEmail.resendHint')}</p>
        <Field label={t('login.email')}>
          <Input
            id="verify-email"
            type="email"
            value={email}
            placeholder={t('auth.emailPlaceholder')}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
          />
        </Field>
        <Button type="submit" size="lg" disabled={!email}>
          <Mail className="h-5 w-5" aria-hidden="true" />
          {t('verifyEmail.resendSubmit')}
        </Button>
        {resendMessage ? <p role="status" className="text-sm text-muted-foreground">{resendMessage}</p> : null}
        <Button asChild variant="text">
          <Link to="/login">{t('verifyEmail.goToLogin')}</Link>
        </Button>
      </form>
    </AuthPage>
  )
}
