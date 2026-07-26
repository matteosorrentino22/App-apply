import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'

export default function JobListPage() {
  const { t } = useLanguage()
  const { logout } = useAuth()

  return (
    <div className="list-page">
      <header className="list-header">
        <h1>{t('list.title')}</h1>
        <button type="button" onClick={logout}>
          {t('list.logout')}
        </button>
      </header>
      <p>{t('list.empty')}</p>
    </div>
  )
}
