import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import LegalConsents from '@/components/LegalConsents'
import { allConsentsGiven, EMPTY_CONSENTS } from '@/lib/legalConsents'

export default function RegisterPage() {
  const { t, lang } = useLanguage()
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [consents, setConsents] = useState(EMPTY_CONSENTS)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [checkEmail, setCheckEmail] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!allConsentsGiven(consents)) {
      setError(t('register.consentsRequired'))
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
      } else if (err instanceof ApiError && err.data) {
        const firstError = Object.values(err.data).flat()[0]
        setError(typeof firstError === 'string' ? firstError : t('common.genericError'))
      } else {
        setError(t('common.genericError'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (checkEmail) {
    return (
      <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-4 py-10">
        <Card>
          <CardHeader>
            <CardTitle>{t('register.checkEmailTitle')}</CardTitle>
            <CardDescription>{t('register.checkEmailBody')}</CardDescription>
          </CardHeader>
          <CardFooter>
            <Button asChild className="w-full">
              <Link to="/login">{t('register.loginLink')}</Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>{t('register.title')}</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit} noValidate>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">{t('register.email')}</Label>
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
              <Label htmlFor="password">{t('register.password')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="invite-code">{t('register.inviteCode')}</Label>
              <Input
                id="invite-code"
                type="text"
                value={inviteCode}
                onChange={(event) => setInviteCode(event.target.value)}
                autoComplete="off"
              />
              <p className="text-xs text-muted-foreground">{t('register.inviteCodeHint')}</p>
            </div>
            <LegalConsents consents={consents} onChange={setConsents} idPrefix="register" />
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
          </CardContent>
          <CardFooter>
            <Button type="submit" disabled={submitting} className="w-full">
              {t('register.submit')}
            </Button>
          </CardFooter>
        </form>
      </Card>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        {t('register.hasAccount')}{' '}
        <Link to="/login" className="font-medium text-primary hover:underline">
          {t('register.loginLink')}
        </Link>
      </p>
    </div>
  )
}
