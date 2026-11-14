import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { googleLoginUrl, resendVerification } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'

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
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>{t('login.title')}</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit} noValidate>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">{t('login.email')}</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">{t('login.password')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            {unverified && (
              <div role="alert" className="flex flex-col gap-2 text-sm">
                <p className="text-destructive">{t('login.emailNotVerified')}</p>
                <Button type="button" variant="secondary" size="sm" className="w-fit" onClick={handleResend}>
                  {t('login.resendVerification')}
                </Button>
                {resendMessage && <p className="text-muted-foreground">{resendMessage}</p>}
              </div>
            )}
            <Link to="/forgot-password" className="w-fit text-sm text-primary hover:underline">
              {t('login.forgotPassword')}
            </Link>
          </CardContent>
          <CardFooter className="flex-col items-stretch gap-3">
            <Button type="submit" disabled={submitting} className="w-full">
              {t('login.submit')}
            </Button>
            {/* Login Google nascosto finché non è configurato (Sprint 67). */}
            {legalInfo?.google_login_enabled && (
              <>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="h-px flex-1 bg-border" />
                  {t('common.or')}
                  <span className="h-px flex-1 bg-border" />
                </div>
                <Button variant="secondary" asChild className="w-full">
                  <a href={googleLoginUrl()}>{t('login.googleButton')}</a>
                </Button>
              </>
            )}
          </CardFooter>
        </form>
      </Card>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        {t('login.noAccount')}{' '}
        <Link to="/register" className="font-medium text-primary hover:underline">
          {t('login.registerLink')}
        </Link>
      </p>
    </div>
  )
}
