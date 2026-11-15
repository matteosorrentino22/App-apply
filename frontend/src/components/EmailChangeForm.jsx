import { useState } from 'react'
import { requestEmailChange } from '../api/auth'
import { ApiError } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import { useLegalInfo } from '../legal/useLegalInfo'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Info, MailCheck } from 'lucide-react'
import { Banner } from '@/components/ui/banner'
import { Field } from '@/components/ui/field'

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

  // Sprint 78: dentro il pannello "Email di accesso" (mockup `settings-email`,
  // `settings-email-sent`); stessa logica di prima.
  return (
    <div className="flex flex-col gap-4">
      <p className="text-[15px] text-muted-foreground">
        {t('emailChange.current')} <span className="break-all font-semibold text-foreground">{currentEmail}</span>
      </p>
      {legalInfo && !legalInfo.email_enabled ? (
        <Banner variant="note" icon={Info}>
          {t('emailChange.unavailable')}
        </Banner>
      ) : sentTo ? (
        <Banner variant="success" icon={MailCheck} role="status">
          {t('emailChange.sent').replace('{email}', sentTo)}
        </Banner>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          <Field label={t('emailChange.newEmail')}>
            <Input
              id="new-login-email"
              type="email"
              value={form.email}
              placeholder={t('emailChange.newEmailPlaceholder')}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              autoComplete="email"
            />
          </Field>
          <Field label={t('emailChange.password')}>
            <Input
              id="email-change-password"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              autoComplete="current-password"
            />
          </Field>
          {error && (
            <p role="alert" className="text-sm text-destructive-text">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" disabled={submitting || !form.email || !form.password}>
            {t('emailChange.submit')}
          </Button>
        </form>
      )}
    </div>
  )
}
