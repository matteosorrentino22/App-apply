import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CircleAlert, CircleCheck } from 'lucide-react'
import { confirmEmailChange } from '../api/auth'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { AuthPage } from '@/components/auth/AuthPage'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'

// Pagina aperta dal link inviato al nuovo indirizzo (Sprint 70):
// /confirm-email-change?t=<token firmato>. Pubblica, come la conferma
// dell'email: il link può essere aperto su un dispositivo non collegato.
// Aspetto Sprint 79 (mockup `confirm-email`).
export default function ConfirmEmailChangePage() {
  const { t } = useLanguage()
  const { user, refreshUser } = useAuth()
  const [params] = useSearchParams()
  const token = params.get('t') || ''
  const [status, setStatus] = useState(token ? 'confirming' : 'invalid')
  const started = useRef(false)

  useEffect(() => {
    if (!token || started.current) return
    started.current = true
    confirmEmailChange(token)
      .then(() => {
        setStatus('success')
        refreshUser().catch(() => {})
      })
      .catch((err) => {
        const code = err instanceof ApiError ? err.data?.code : null
        setStatus(['expired', 'email_taken'].includes(code) ? code : 'invalid')
      })
  }, [token, refreshUser])

  const action = (
    <Button asChild size="lg" variant={status === 'success' ? 'primary' : 'secondary'}>
      <Link to={user ? '/settings' : '/login'}>{user ? t('emailChange.goToSettings') : t('verifyEmail.goToLogin')}</Link>
    </Button>
  )

  if (status === 'confirming') {
    return (
      <AuthPage centered title={t('emailChange.confirmTitle')}>
        <div className="flex flex-col items-center gap-3">
          <Spinner framed label={t('emailChange.confirming')} />
          <p className="text-[15px] text-muted-foreground">{t('emailChange.confirming')}</p>
        </div>
      </AuthPage>
    )
  }
  if (status === 'success') {
    return (
      <AuthPage centered title={t('emailChange.confirmTitle')} icon={CircleCheck} tone="success" description={t('emailChange.confirmed')}>
        {action}
      </AuthPage>
    )
  }
  return (
    <AuthPage
      centered
      title={t('emailChange.confirmTitle')}
      icon={CircleAlert}
      tone="error"
      description={t(`emailChange.${status === 'email_taken' ? 'taken' : status}`)}
    >
      {action}
    </AuthPage>
  )
}
