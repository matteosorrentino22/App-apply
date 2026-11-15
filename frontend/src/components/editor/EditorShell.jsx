import { useEffect, useRef, useState } from 'react'
import { Check, ChevronLeft, Info, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../../i18n/LanguageContext'
import { ActionBar } from '@/components/ui/action-bar'
import { Badge } from '@/components/ui/badge'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { SegmentedControl } from '@/components/ui/segmented'
import { Sheet, SheetContent, SheetHeader } from '@/components/ui/sheet'
import { useKeyboardInset, useMediaQuery } from '@/lib/useMediaQuery'
import { cn } from '@/lib/utils'

// Impianto comune dei due editor (Sprint 76, mockup `cv-editor`,
// `cv-preview`, `cover-editor`, `desk-editor`): testata (torna al job,
// stato del salvataggio, titolo, job, pagine), segmento Modifica /
// Anteprima, avviso multipagina, barra azione in basso con "Assistente" e
// "Genera PDF finale" al posto della barra di tab. La chat è una sola
// istanza: da 1024 px in una colonna fissa a destra (400 px, gap 24,
// larghezza massima 1112 px), sotto in un pannello dal basso aperto da
// "Assistente", sopra la tastiera dell'iPhone (`useKeyboardInset`).
// Altezza della colonna della chat da 1024 px: dal suo bordo superiore
// (sotto eventuali avvisi in cima alla pagina, poi fissa a 88 px scorrendo)
// fino alla barra azione, così il campo di testo resta sempre visibile.
function useAsideHeight(active) {
  const ref = useRef(null)
  const [height, setHeight] = useState(null)
  useEffect(() => {
    if (!active) return
    function update() {
      const node = ref.current
      if (!node) return
      const barTop = document.querySelector('[data-testid="action-bar"]')?.getBoundingClientRect().top ?? window.innerHeight
      const top = Math.max(node.getBoundingClientRect().top, 88)
      setHeight(Math.max(360, Math.round(barTop - top - 24)))
    }
    update()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [active])
  return [ref, height]
}

function SaveStatus({ status }) {
  const { t } = useLanguage()
  if (status === 'saving') return <span className="text-sm text-muted-foreground">{t('cvEditor.saving')}</span>
  if (status === 'saved') {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
        <Check className="h-4 w-4 text-success" aria-hidden="true" />
        {t('cvEditor.saved')}
      </span>
    )
  }
  if (status === 'error') return <span className="text-sm font-semibold text-destructive-text">{t('cvEditor.saveError')}</span>
  return null
}

export default function EditorShell({
  jobId,
  saveStatus,
  title,
  subtitle,
  pageCount,
  multiPageText,
  mode,
  onModeChange,
  editor,
  preview,
  chatTitle,
  renderChat,
  chatOpen,
  onChatOpenChange,
  finalizeLabel,
  finalizing,
  onFinalize,
  children,
}) {
  const { t } = useLanguage()
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const sheetOpen = chatOpen && !isDesktop
  useKeyboardInset(sheetOpen)
  const [asideRef, asideHeight] = useAsideHeight(isDesktop)

  return (
    <div className="mx-auto w-full max-w-[1144px] px-4 pb-6 pt-3 lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-6 lg:pt-6">
      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <Link
            to={`/jobs/${jobId}`}
            className="-ml-2 flex min-h-11 items-center gap-1 rounded-field px-2 text-base font-semibold text-primary outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/30"
          >
            <ChevronLeft className="h-5 w-5" aria-hidden="true" />
            {t('cvEditor.backToJob')}
          </Link>
          <div aria-live="polite">
            <SaveStatus status={saveStatus} />
          </div>
        </div>

        <header className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-[26px] font-bold leading-tight tracking-[-0.01em] text-foreground">{title}</h1>
            {subtitle ? <p className="mt-1 break-words text-[15px] text-muted-foreground">{subtitle}</p> : null}
          </div>
          {pageCount != null ? (
            <Badge
              data-testid="editor-page-count"
              variant={pageCount > 1 ? 'destructive' : 'success'}
              className="mt-1.5 shrink-0 px-3 py-1 text-[13px]"
            >
              {pageCount <= 1 ? t('cvEditor.pageCountOk') : t('cvEditor.pageCountWarning').replace('{count}', pageCount)}
            </Badge>
          ) : null}
        </header>

        <SegmentedControl
          name="editor-mode"
          label={t('cvEditor.modeLabel')}
          value={mode}
          onChange={onModeChange}
          options={[
            { value: 'edit', label: t('cvEditor.modeEdit') },
            { value: 'preview', label: t('cvEditor.previewLabel') },
          ]}
        />

        {multiPageText ? (
          <Banner variant="note" icon={Info}>
            {multiPageText}
          </Banner>
        ) : null}

        {mode === 'edit' ? editor : preview}
      </div>

      {isDesktop ? (
        <aside
          ref={asideRef}
          aria-label={chatTitle}
          style={asideHeight ? { height: asideHeight } : undefined}
          className="sticky top-[88px] flex h-[calc(100dvh-88px-var(--app-bottom-bar)-24px)] flex-col self-start overflow-hidden rounded-card border border-border bg-card shadow-card"
        >
          {renderChat(true)}
        </aside>
      ) : (
        <Sheet open={sheetOpen} onOpenChange={onChatOpenChange}>
          <SheetContent
            style={{
              bottom: 'var(--keyboard-inset, 0px)',
              height: 'min(88dvh, calc(var(--visual-height, 100dvh) - 24px))',
              maxHeight: 'none',
            }}
          >
            <SheetHeader title={chatTitle} />
            {renderChat(false)}
          </SheetContent>
        </Sheet>
      )}

      <ActionBar className="max-w-[1112px] flex-row items-center gap-3">
        <Button variant="secondary" size="lg" className="w-auto flex-none gap-1.5 px-3.5 lg:hidden" onClick={() => onChatOpenChange(true)}>
          <Sparkles className="h-5 w-5" aria-hidden="true" />
          {t('cvEditor.assistantButton')}
        </Button>
        <Button
          size="lg"
          className={cn('min-w-0 flex-1 px-3 lg:ml-auto lg:w-auto lg:flex-none lg:px-10')}
          disabled={finalizing}
          onClick={onFinalize}
        >
          {finalizing ? t('cvEditor.finalizing') : finalizeLabel}
        </Button>
      </ActionBar>
      {children}
    </div>
  )
}
