import { Info } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext'
import { Banner } from '@/components/ui/banner'

// Anteprima dell'editor (Sprint 76, mockup `cv-preview`): PDF reale
// renderizzato dal server, mostrato in un iframe da un blob URL, con la
// didascalia.
// Sprint 82: su iPhone (Safari) e Android (Chrome) l'anteprima restava
// bianca. Dallo Sprint 76 l'altezza dell'iframe dipendeva solo da
// `aspect-ratio` dentro un contenitore flex centrato; nello Sprint 69, quando
// funzionava anche da mobile, aveva un'altezza esplicita (h-[70vh]). Torna
// l'altezza esplicita (con un minimo) e la proporzione A4 resta solo da
// desktop (lg), dove l'anteprima funzionava.
export default function EditorPreview({ previewUrl, unavailable, title }) {
  const { t } = useLanguage()
  if (unavailable) return <Banner variant="note" icon={Info}>{t('cvEditor.previewUnavailable')}</Banner>
  // Sprint 83: Chrome per Android non ha un visualizzatore PDF incorporato
  // (`navigator.pdfViewerEnabled === false`): l'iframe resterebbe bianco e un
  // link scaricherebbe il file. Al suo posto un avviso; l'indicatore delle
  // pagine in testata resta. Su iPhone l'iframe funziona dallo Sprint 83
  // (header frame-ancestors 'self', Caddyfile.prod).
  if (typeof navigator !== 'undefined' && navigator.pdfViewerEnabled === false) {
    return (
      <Banner variant="note" icon={Info} data-testid="preview-no-viewer">
        {t('cvEditor.previewNoViewer')}
      </Banner>
    )
  }
  return (
    <div className="flex w-full flex-col gap-3">
      {previewUrl ? (
        <iframe
          title={title}
          src={previewUrl}
          className="mx-auto block h-[70vh] min-h-[420px] w-full max-w-[640px] rounded-[4px] border border-border bg-card shadow-card lg:h-auto lg:min-h-0 lg:aspect-[210/297]"
        />
      ) : (
        <p className="py-10 text-center text-sm text-muted-foreground">{t('cvEditor.loading')}</p>
      )}
      <p className="text-center text-sm text-muted-foreground">{t('cvEditor.previewCaption')}</p>
    </div>
  )
}
