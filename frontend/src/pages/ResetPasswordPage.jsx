import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CircleAlert, CircleCheck } from 'lucide-react'
import { confirmPasswordReset } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { AuthPage } from '@/components/auth/AuthPage'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

// Pagina del link di recupero password (Sprint 67): /reset-password?uid=…&token=…
// Aspetto Sprint 79 (mockup `reset`, `reset-invalid`, `reset-done`).
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

  if (status === 'success') {
    return (
      <AuthPage centered title={t('resetPassword.title')} icon={CircleCheck} tone="success" description={t('resetPassword.success')}>
        <Button asChild size="lg">
          <Link to="/login">{t('verifyEmail.goToLogin')}</Link>
        </Button>
      </AuthPage>
    )
  }

  if (status === 'invalid') {
    return (
      <AuthPage centered title={t('resetPassword.title')} icon={CircleAlert} tone="error" description={t('resetPassword.invalidLink')}>
        <Button asChild size="lg">
          <Link to="/forgot-password">{t('resetPassword.requestNew')}</Link>
        </Button>
      </AuthPage>
    )
  }

  return (
    <AuthPage title={t('resetPassword.title')}>
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
        <Field label={t('account.newPassword')} hint={t('settings.passwordHint')}>
          <Input
            id="reset-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
          />
        </Field>
        <Field label={t('account.confirmNewPassword')}>
          <Input
            id="reset-password-confirm"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
          />
        </Field>
        {error ? <Banner variant="error">{error}</Banner> : null}
        <Button type="submit" size="lg" disabled={submitting || !password}>
          {t('resetPassword.submit')}
        </Button>
      </form>
    </AuthPage>
  )
}
