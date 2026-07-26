import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { googleLoginUrl } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'

export default function LoginPage() {
  const { t } = useLanguage()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/onboarding')
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 400
          ? t('login.invalidCredentials')
          : t('common.genericError'),
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <h1>{t('login.title')}</h1>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          {t('login.email')}
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label>
          {t('login.password')}
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" disabled={submitting}>
          {t('login.submit')}
        </button>
      </form>
      <a className="google-button" href={googleLoginUrl()}>
        {t('login.googleButton')}
      </a>
      <p>
        {t('login.noAccount')} <Link to="/register">{t('login.registerLink')}</Link>
      </p>
    </div>
  )
}
