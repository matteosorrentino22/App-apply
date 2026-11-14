import { useState } from 'react'
import { Link } from 'react-router-dom'
import { requestPasswordReset } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'

// Recupero password (Sprint 67): risposta sempre identica, che l'email sia
// registrata o no. Senza invio email configurato la funzione non è disponibile.
export default function ForgotPasswordPage() {
  const { t } = useLanguage()
  const legalInfo = useLegalInfo()
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const unavailable = legalInfo && !legalInfo.email_enabled

  async function handleSubmit(event) {
    event.preventDefault()
    setMessage('')
    setError('')
    setSubmitting(true)
    try {
      await requestPasswordReset(email)
      setMessage(t('forgotPassword.sent'))
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) setError(t('forgotPassword.unavailable'))
      else if (err instanceof ApiError && err.status === 429) setError(t('common.tooManyRequests'))
      else setError(t('common.genericError'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>{t('forgotPassword.title')}</CardTitle>
          {!unavailable && <CardDescription>{t('forgotPassword.intro')}</CardDescription>}
        </CardHeader>
        {unavailable ? (
          <CardContent>
            <p role="alert" className="text-sm text-muted-foreground">
              {t('forgotPassword.unavailable')}
              {legalInfo.controller?.email && (
                <>
                  {' '}
                  <a href={`mailto:${legalInfo.controller.email}`} className="text-primary underline">
                    {legalInfo.controller.email}
                  </a>
                </>
              )}
            </p>
          </CardContent>
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="forgot-email">{t('login.email')}</Label>
                <Input
                  id="forgot-email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="email"
                  required
                />
              </div>
              {message && <p className="text-sm text-foreground">{message}</p>}
              {error && (
                <p role="alert" className="text-sm text-destructive">
                  {error}
                </p>
              )}
            </CardContent>
            <CardFooter>
              <Button type="submit" className="w-full" disabled={submitting || !email}>
                {t('forgotPassword.submit')}
              </Button>
            </CardFooter>
          </form>
        )}
      </Card>
      <p className="mt-4 text-center text-sm">
        <Link to="/login" className="font-medium text-primary hover:underline">
          {t('forgotPassword.backToLogin')}
        </Link>
      </p>
    </div>
  )
}
