import { Link } from 'react-router-dom'
import { SearchX } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'

// Pagina non trovata (Sprint 80, DESIGN.md §7): prima un indirizzo
// sconosciuto mostrava una pagina vuota. Rimanda ai job (o all'accesso).
export default function NotFoundPage() {
  const { t } = useLanguage()
  const { user } = useAuth()
  return (
    <div className="mx-auto max-w-sm px-4">
      <EmptyState
        icon={SearchX}
        title={t('notFound.title')}
        description={t('notFound.body')}
        action={
          <Button asChild size="lg" className="w-full">
            <Link to={user ? '/list' : '/login'}>{user ? t('notFound.goToJobs') : t('verifyEmail.goToLogin')}</Link>
          </Button>
        }
      />
    </div>
  )
}
