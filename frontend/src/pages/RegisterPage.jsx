import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { AuthPage } from '@/components/auth/AuthPage'
import LegalConsents from '@/components/LegalConsents'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { allConsentsGiven, EMPTY_CONSENTS } from '@/lib/legalConsents'

// Registrazione (Sprint 66–67; aspetto Sprint 79, mockup `register`,
// `register-err`, `register-email`). Stesse regole: codice di invito, le tre
// spunte obbligatorie, conferma dell'email se l'invio è configurato. Gli
// errori del server si mostrano sotto il campo a cui si riferiscono (stesse
// chiavi della risposta 400), gli altri in un riquadro.
const FIELD_KEYS = ['email', 'password', 'invite_code']
const CONSENT_KEYS = ['accept_privacy', 'accept_terms', 'confirm_age']

function firstMessage(value) {
  const first = Array.isArray(value) ? value[0] : value
  return typeof first === 'string' ? first : null
}

export default function RegisterPage() {
  const { t, lang } = useLanguage()
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [consents, setConsents] = useState(EMPTY_CONSENTS)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [checkEmail, setCheckEmail] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setFieldErrors({})
    if (!allConsentsGiven(consents)) {
      setFieldErrors({ consents: t('register.consentsRequired') })
      return
    }
    setSubmitting(true)
    try {
      const data = await register({ email, password, inviteCode: inviteCode.trim(), language: lang, consents })
      if (data.verification_required) {
        setCheckEmail(true)
      } else {
        navigate('/onboarding')
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError(t('common.tooManyRequests'))
      } else if (err instanceof ApiError && err.data && typeof err.data === 'object') {
        const next = {}
        for (const key of FIELD_KEYS) {
          const message = firstMessage(err.data[key])
          if (message) next[key] = message
        }
        const consentMessage = CONSENT_KEYS.map((key) => firstMessage(err.data[key])).find(Boolean)
        if (consentMessage) next.consents = consentMessage
        const other = Object.entries(err.data)
          .filter(([key]) => !FIELD_KEYS.includes(key) && !CONSENT_KEYS.includes(key))
          .map(([, value]) => firstMessage(value))
          .find(Boolean)
        setFieldErrors(next)
        if (other || Object.keys(next).length === 0) setError(other || t('common.genericError'))
      } else {
        setError(t('common.genericError'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (checkEmail) {
    return (
      <AuthPage centered title={t('register.checkEmailTitle')} icon={Mail} description={t('register.checkEmailBody')}>
        <Button asChild variant="secondary" size="lg" className="border-primary">
          <Link to="/login">{t('verifyEmail.goToLogin')}</Link>
        </Button>
      </AuthPage>
    )
  }

  return (
    <AuthPage
      title={t('register.title')}
      footer={
        <>
          {t('register.hasAccount')}{' '}
          <Link to="/login" className="inline-flex min-h-11 items-center font-bold text-primary hover:underline">
            {t('register.loginLink')}
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
        <Field label={t('register.email')} error={fieldErrors.email}>
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
        <Field label={t('register.password')} hint={t('settings.passwordHint')} error={fieldErrors.password}>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="new-password"
          />
        </Field>
        <Field label={t('register.inviteCode')} hint={t('register.inviteCodeHint')} error={fieldErrors.invite_code}>
          <Input
            id="invite-code"
            type="text"
            value={inviteCode}
            onChange={(event) => setInviteCode(event.target.value)}
            autoComplete="off"
          />
        </Field>
        <div className="flex flex-col gap-2">
          <LegalConsents consents={consents} onChange={setConsents} idPrefix="register" />
          {fieldErrors.consents ? (
            <p role="alert" className="text-xs leading-snug text-destructive-text">
              {fieldErrors.consents}
            </p>
          ) : null}
        </div>
        {error ? <Banner variant="error">{error}</Banner> : null}
        <Button type="submit" size="lg" disabled={submitting}>
          {t('register.submit')}
        </Button>
      </form>
    </AuthPage>
  )
}
