import { Navigate } from 'react-router-dom'
import { WifiOff } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { getToken } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
import LegalAcceptancePage from '../pages/LegalAcceptancePage'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'

export default function ProtectedRoute({ children }) {
  const { user, loading, connectionError, retryConnection } = useAuth()
  const { t } = useLanguage()

  if (loading) {
    return <p className="mt-16 text-center text-sm text-muted-foreground">{t('common.loading')}</p>
  }
  // Sprint 80 (stato "errore di rete", DESIGN.md §7): con una sessione
  // salvata ma il server irraggiungibile all'avvio non si manda al login.
  if (!user && connectionError && getToken()) {
    return (
      <div className="mx-auto max-w-sm px-4">
        <EmptyState
          icon={WifiOff}
          title={t('common.offlineTitle')}
          description={t('common.networkError')}
          action={
            <Button size="lg" className="w-full" onClick={retryConnection}>
              {t('common.retry')}
            </Button>
          }
        />
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  // Gate delle accettazioni legali (Sprint 67): lo stesso controllo è
  // applicato dal backend (403 legal_acceptance_required).
  if (user.legal_acceptance_required) {
    return <LegalAcceptancePage />
  }
  return children
}
