import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { resendVerification, verifyEmail } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'

// Pagina aperta dal link dell'email di verifica (Sprint 67): /verify-email?t=<token firmato>.
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

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>{t('verifyEmail.title')}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-sm">
          {status === 'verifying' && <p className="text-muted-foreground">{t('verifyEmail.verifying')}</p>}
          {status === 'success' && <p>{t('verifyEmail.success')}</p>}
          {(status === 'invalid' || status === 'expired') && (
            <form onSubmit={handleResend} className="flex flex-col gap-3" noValidate>
              <p className="text-destructive">{t(`verifyEmail.${status}`)}</p>
              <p className="text-muted-foreground">{t('verifyEmail.resendHint')}</p>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="verify-email">{t('login.email')}</Label>
                <Input
                  id="verify-email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="email"
                />
              </div>
              <Button type="submit" variant="secondary" className="w-fit" disabled={!email}>
                {t('verifyEmail.resendSubmit')}
              </Button>
              {resendMessage && <p className="text-muted-foreground">{resendMessage}</p>}
            </form>
          )}
        </CardContent>
        <CardFooter>
          <Button asChild variant={status === 'success' ? 'primary' : 'ghost'} className="w-full">
            <Link to={status === 'success' ? '/login?next=/onboarding' : '/login'}>{t('verifyEmail.goToLogin')}</Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
