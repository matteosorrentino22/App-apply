import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { Button } from '@/components/ui/button'

export default function JobListPage() {
  const { t } = useLanguage()
  const { logout } = useAuth()

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">{t('list.title')}</h1>
        <Button variant="secondary" size="sm" onClick={logout}>
          {t('list.logout')}
        </Button>
      </header>
      <p className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
        {t('list.empty')}
      </p>
    </div>
  )
}
