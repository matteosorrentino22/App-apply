import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const { t } = useLanguage()

  if (loading) {
    return <p className="mt-16 text-center text-sm text-muted-foreground">{t('common.loading')}</p>
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return children
}
