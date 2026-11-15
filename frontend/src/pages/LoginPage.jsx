import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Info, Mail } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { googleLoginUrl, resendVerification } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import { AuthPage } from '@/components/auth/AuthPage'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

// Accesso (Sprint 67; aspetto Sprint 79, mockup `login`, `login-err`,
// `login-not-verified`). Stessa logica: email e password, errore delle
// credenziali, email non ancora confermata con "Invia di nuovo il link",
// "Password dimenticata?". Il pulsante Google compare solo se il login Google
// è configurato (oggi non lo è in produzione: il codice allauth resta).
export default function LoginPage() {
  const { t } = useLanguage()
  const { login } = useAuth()
  const navigate = useNavigate()
  // Dopo la conferma dell'email (Sprint 67) il primo accesso prosegue con
  // l'onboarding, come faceva prima la registrazione: solo percorsi interni.
  const [params] = useSearchParams()
  const next = params.get('next') === '/onboarding' ? '/onboarding' : '/list'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  // Sprint 67: login rifiutato perché l'email non è ancora confermata.
  const [unverified, setUnverified] = useState(false)
  const [resendMessage, setResendMessage] = useState('')
  const legalInfo = useLegalInfo()

  async function handleResend() {
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

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setUnverified(false)
    setResendMessage('')
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(next)
    } catch (err) {
      if (err instanceof ApiError && err.status === 403 && err.data?.code === 'email_not_verified') {
        setUnverified(true)
      } else if (err instanceof ApiError && err.status === 400) {
        setError(t('login.invalidCredentials'))
      } else if (err instanceof ApiError && err.status === 429) {
        setError(t('common.tooManyRequests'))
      } else {
        setError(t('common.genericError'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthPage
      title={t('login.title')}
      footer={
        <>
          {t('login.noAccount')}{' '}
          <Link to="/register" className="inline-flex min-h-11 items-center font-bold text-primary hover:underline">
            {t('login.registerLink')}
          </Link>
        </>
      }
    >
      {unverified ? (
        <div className="flex flex-col gap-3" role="alert">
          <Banner variant="note" icon={Info}>
            {t('login.emailNotVerified')}
          </Banner>
          <Button type="button" variant="secondary" size="lg" onClick={handleResend}>
            <Mail className="h-5 w-5" aria-hidden="true" />
            {t('login.resendVerification')}
          </Button>
          {resendMessage ? <p className="text-sm text-muted-foreground">{resendMessage}</p> : null}
        </div>
      ) : null}
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
        <Field label={t('login.email')}>
          <Input
            id="email"
            type="email"
            value={email}
            placeholder={t('auth.emailPlaceholder')}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
          />
        </Field>
        <Field label={t('login.password')}>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
          />
        </Field>
        <Link to="/forgot-password" className="-my-2 inline-flex min-h-11 items-center self-end text-[15px] font-bold text-primary hover:underline">
          {t('login.forgotPassword')}
        </Link>
        {error ? <Banner variant="error">{error}</Banner> : null}
        <Button type="submit" size="lg" disabled={submitting}>
          {t('login.submit')}
        </Button>
        {/* Login Google nascosto finché non è configurato (Sprint 67). */}
        {legalInfo?.google_login_enabled ? (
          <>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="h-px flex-1 bg-border" />
              {t('common.or')}
              <span className="h-px flex-1 bg-border" />
            </div>
            <Button variant="secondary" size="lg" asChild>
              <a href={googleLoginUrl()}>{t('login.googleButton')}</a>
            </Button>
          </>
        ) : null}
      </form>
    </AuthPage>
  )
}
