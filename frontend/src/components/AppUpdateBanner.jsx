import { RefreshCw } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'

// Avviso in cima alla pagina (Sprint 74, mockup `jobs-avvisi`).
export default function AppUpdateBanner() {
  const { t } = useLanguage()
  return (
    <Banner
      variant="info"
      action={
        <Button size="sm" variant="secondary" onClick={() => window.location.reload()}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          {t('appUpdate.reload')}
        </Button>
      }
    >
      {t('appUpdate.available')}
    </Banner>
  )
}
