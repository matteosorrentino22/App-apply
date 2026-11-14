import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmEmailChange } from '../api/auth'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'

// Pagina aperta dal link inviato al nuovo indirizzo (Sprint 70):
// /confirm-email-change?t=<token firmato>. Pubblica, come la conferma
// dell'email: il link può essere aperto su un dispositivo non collegato.
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

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>{t('emailChange.confirmTitle')}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {status === 'confirming' && <p className="text-muted-foreground">{t('emailChange.confirming')}</p>}
          {status === 'success' && <p>{t('emailChange.confirmed')}</p>}
          {status !== 'confirming' && status !== 'success' && (
            <p className="text-destructive">{t(`emailChange.${status === 'email_taken' ? 'taken' : status}`)}</p>
          )}
        </CardContent>
        <CardFooter>
          <Button asChild variant={status === 'success' ? 'primary' : 'ghost'} className="w-full">
            <Link to={user ? '/settings' : '/login'}>
              {user ? t('emailChange.goToSettings') : t('verifyEmail.goToLogin')}
            </Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
