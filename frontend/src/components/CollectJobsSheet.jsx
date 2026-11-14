import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { collectJobs } from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader } from '@/components/ui/sheet'
import { Spinner } from '@/components/ui/spinner'
import { ActionCostHint } from '@/components/ActionCost'
import { useUsage } from '@/lib/usage'

// Raccolta manuale "Raccogli ora" (Sprint 74, mockup `collect-free` e
// `collect-running`). Comportamento invariato (POST /api/jobs/collect/,
// 1 raccolta manuale al giorno su tutti i piani, sincrona): cambia solo
// l'aspetto. Il riquadro "Raccolta automatica" dei mockup arriva con lo
// Sprint 77; fino ad allora resta valida la raccolta notturna, che il testo
// ricorda. Le statistiche sono in StatsSummary. Apertura controllata dal
// genitore (`open`/`onOpenChange`): la apre sia il pulsante accanto al
// titolo sia lo stato vuoto della lista.
export function CollectButton({ onClick }) {
  const { t } = useLanguage()
  return (
    <Button variant="secondary" size="icon" onClick={onClick} aria-label={t('home.collectTitle')} title={t('home.collectTitle')}>
      <RefreshCw className="h-5 w-5" aria-hidden="true" />
    </Button>
  )
}

export default function CollectJobsSheet({ open, onOpenChange, onCollected }) {
  const { t } = useLanguage()
  const { showToast } = useToast()
  const [collecting, setCollecting] = useState(false)
  const [summary, setSummary] = useState(null)
  const { usage, refresh: refreshUsage } = useUsage()

  async function handleCollect() {
    setCollecting(true)
    try {
      const result = await collectJobs()
      setSummary(result)
      showToast(t('home.collectSuccess'))
      onCollected?.()
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        showToast(err.data?.detail || t('home.collectConflict'))
      } else {
        showToast(t('home.collectFailed'))
      }
    } finally {
      setCollecting(false)
      refreshUsage()
    }
  }

  // Durante la raccolta il pannello resta aperto: chiuderlo non interrompe
  // la richiesta ma nasconderebbe l'esito.
  function handleOpenChange(next) {
    if (collecting && !next) return
    if (next) refreshUsage()
    onOpenChange(next)
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent aria-describedby={undefined}>
        <SheetHeader title={t('home.collectTitle')} />
        <SheetBody>
          {collecting ? (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <Spinner framed label={t('home.collecting')} />
              <p className="text-[17px] font-bold">{t('home.collecting')}</p>
              <p className="text-sm leading-normal text-muted-foreground">{t('home.collectRunningHint')}</p>
            </div>
          ) : (
            <>
              <p className="text-[15px] leading-normal text-muted-foreground">{t('home.collectIntro')}</p>
              <div className="rounded-button border border-note-border bg-note px-3.5 py-3 text-sm leading-[1.45] text-note-foreground">
                {t('home.collect24h')}
              </div>
              <p className="text-sm leading-normal text-muted-foreground">{t('home.collectNightly')}</p>
            </>
          )}
        </SheetBody>
        <SheetFooter>
          <Button size="lg" onClick={handleCollect} disabled={collecting}>
            <RefreshCw className="h-5 w-5" aria-hidden="true" />
            {collecting ? t('home.collecting') : t('home.collectButton')}
          </Button>
          <ActionCostHint usage={usage} action="collection" className="text-center" />
          {summary && !collecting && (
            <p className="text-center text-xs text-muted-foreground">
              {t('home.collectLastResult').replace('{collected}', summary.collected).replace('{kept}', summary.kept)}
            </p>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
