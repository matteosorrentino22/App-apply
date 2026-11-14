import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { APP_UPDATE_EVENT, isAppUpdateAvailable } from '../lib/appUpdate'
import { Button } from '@/components/ui/button'

// Avviso di nuova versione (Sprint 70): la pagina si ricarica solo quando
// l'utente preme "Aggiorna".
export default function AppUpdateBanner() {
  const { t } = useLanguage()
  const [visible, setVisible] = useState(isAppUpdateAvailable)

  useEffect(() => {
    const show = () => setVisible(true)
    window.addEventListener(APP_UPDATE_EVENT, show)
    return () => window.removeEventListener(APP_UPDATE_EVENT, show)
  }, [])

  if (!visible) return null
  return (
    <div
      role="status"
      className="fixed inset-x-0 bottom-4 z-50 mx-auto flex w-fit max-w-[calc(100%-2rem)] items-center gap-3 rounded-full border border-border bg-card px-4 py-2 text-sm shadow-lg"
    >
      <span>{t('appUpdate.available')}</span>
      <Button size="sm" className="rounded-full" onClick={() => window.location.reload()}>
        <RefreshCw className="h-3.5 w-3.5" />
        {t('appUpdate.reload')}
      </Button>
    </div>
  )
}
