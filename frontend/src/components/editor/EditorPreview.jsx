import { Info } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import { Banner } from '@/components/ui/banner'

// Anteprima dell'editor (Sprint 76, mockup `cv-preview`): stesso meccanismo
// di prima (PDF reale renderizzato dal server, mostrato in un iframe da un
// blob URL), in proporzione A4, con la didascalia.
export default function EditorPreview({ previewUrl, unavailable, title }) {
  const { t } = useLanguage()
  if (unavailable) return <Banner variant="note" icon={Info}>{t('cvEditor.previewUnavailable')}</Banner>
  return (
    <div className="flex flex-col items-center gap-3">
      {previewUrl ? (
        <iframe
          title={title}
          src={previewUrl}
          className="aspect-[210/297] w-full max-w-[640px] rounded-[4px] border border-border bg-card shadow-card"
        />
      ) : (
        <p className="py-10 text-sm text-muted-foreground">{t('cvEditor.loading')}</p>
      )}
      <p className="text-center text-sm text-muted-foreground">{t('cvEditor.previewCaption')}</p>
    </div>
  )
}

