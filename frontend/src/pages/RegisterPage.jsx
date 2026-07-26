import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'

export default function RegisterPage() {
  const { t } = useLanguage()
  const { register } = useAuth()
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
      await register(email, password)
      navigate('/onboarding')
    } catch (err) {
      if (err instanceof ApiError && err.data) {
        const firstError = Object.values(err.data).flat()[0]
        setError(typeof firstError === 'string' ? firstError : t('common.genericError'))
      } else {
        setError(t('common.genericError'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <h1>{t('register.title')}</h1>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          {t('register.email')}
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label>
          {t('register.password')}
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="new-password"
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" disabled={submitting}>
          {t('register.submit')}
        </button>
      </form>
      <p>
        {t('register.hasAccount')} <Link to="/login">{t('register.loginLink')}</Link>
      </p>
    </div>
  )
}
