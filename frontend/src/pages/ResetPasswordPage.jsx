import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmPasswordReset } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'

// Pagina del link di recupero password (Sprint 67): /reset-password?uid=…&token=…
export default function ResetPasswordPage() {
  const { t } = useLanguage()
  const [params] = useSearchParams()
  const uid = params.get('uid') || ''
  const token = params.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [status, setStatus] = useState(uid && token ? 'form' : 'invalid')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError(t('account.passwordMismatch'))
      return
    }
    setSubmitting(true)
    try {
      await confirmPasswordReset(uid, token, password)
      setStatus('success')
    } catch (err) {
      if (err instanceof ApiError && err.data?.code === 'invalid_link') {
        setStatus('invalid')
      } else if (err instanceof ApiError && Array.isArray(err.data?.new_password)) {
        setError(err.data.new_password.join(' '))
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
          <CardTitle>{t('resetPassword.title')}</CardTitle>
        </CardHeader>
        {status === 'form' ? (
          <form onSubmit={handleSubmit} noValidate>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="reset-password">{t('account.newPassword')}</Label>
                <Input
                  id="reset-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="reset-password-confirm">{t('account.confirmNewPassword')}</Label>
                <Input
                  id="reset-password-confirm"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </div>
              {error && (
                <p role="alert" className="text-sm text-destructive">
                  {error}
                </p>
              )}
            </CardContent>
            <CardFooter>
              <Button type="submit" className="w-full" disabled={submitting || !password}>
                {t('resetPassword.submit')}
              </Button>
            </CardFooter>
          </form>
        ) : (
          <>
            <CardContent>
              <p className={status === 'success' ? 'text-sm' : 'text-sm text-destructive'}>
                {status === 'success' ? t('resetPassword.success') : t('resetPassword.invalidLink')}
              </p>
            </CardContent>
            <CardFooter>
              <Button asChild className="w-full" variant={status === 'success' ? 'primary' : 'secondary'}>
                <Link to={status === 'success' ? '/login' : '/forgot-password'}>
                  {status === 'success' ? t('verifyEmail.goToLogin') : t('resetPassword.requestNew')}
                </Link>
              </Button>
            </CardFooter>
          </>
        )}
      </Card>
    </div>
  )
}
