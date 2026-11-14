import { useState } from 'react'
import { requestEmailChange } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// Cambio dell'email di accesso (Sprint 70, diritto di rettifica): password e
// nuovo indirizzo; l'email cambia solo quando si apre il link inviato al
// nuovo indirizzo. Senza invio email configurato non è disponibile.
export default function EmailChangeForm({ currentEmail }) {
  const { t } = useLanguage()
  const legalInfo = useLegalInfo()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [sentTo, setSentTo] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSentTo('')
    setSubmitting(true)
    try {
      await requestEmailChange(form.password, form.email)
      setSentTo(form.email)
      setForm({ email: '', password: '' })
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError(t('common.tooManyRequests'))
      } else if (err instanceof ApiError && err.status === 503) {
        setError(t('emailChange.unavailable'))
      } else if (err instanceof ApiError && err.data?.password) {
        setError(t('account.wrongPassword'))
      } else if (err instanceof ApiError && err.data?.new_email) {
        setError(err.data.new_email[0] || t('common.genericError'))
      } else {
        setError(t('common.genericError'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-foreground">{t('emailChange.title')}</h3>
      <p className="text-sm text-muted-foreground">
        {t('emailChange.current')} <span className="font-medium text-foreground">{currentEmail}</span>
      </p>
      {legalInfo && !legalInfo.email_enabled ? (
        <p className="text-sm text-muted-foreground">{t('emailChange.unavailable')}</p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3" noValidate>
          <div className="flex flex-wrap gap-3">
            <div className="flex min-w-40 flex-1 flex-col gap-1.5">
              <Label htmlFor="new-login-email">{t('emailChange.newEmail')}</Label>
              <Input
                id="new-login-email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                autoComplete="email"
              />
            </div>
            <div className="flex min-w-40 flex-1 flex-col gap-1.5">
              <Label htmlFor="email-change-password">{t('emailChange.password')}</Label>
              <Input
                id="email-change-password"
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                autoComplete="current-password"
              />
            </div>
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {sentTo && (
            <p role="status" className="text-sm text-foreground">
              {t('emailChange.sent').replace('{email}', sentTo)}
            </p>
          )}
          <Button
            type="submit"
            variant="secondary"
            className="w-fit"
            disabled={submitting || !form.email || !form.password}
          >
            {t('emailChange.submit')}
          </Button>
        </form>
      )}
    </div>
  )
}
