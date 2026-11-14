import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { collectJobs, fetchHomeStats } from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader, SheetTrigger } from '@/components/ui/sheet'
import { ActionCostHint } from '@/components/ActionCost'
import { useUsage } from '@/lib/usage'

// Raccolta manuale e statistiche, spostate dalla Home eliminata (Sprint 73,
// SPEC-DELTA A1). Ponte verso lo Sprint 74, che le ridisegna in Jobs
// (StatsSummary, pannelli `collect-*`): qui il comportamento è identico a
// quello della vecchia Home (stessa API, stesso limite di 1 raccolta
// manuale al giorno, stesso riepilogo), solo dentro un pannello aperto dal
// pulsante accanto al titolo della lista, dove lo mettono i mockup.

function formatNumber(value, lang) {
  return new Intl.NumberFormat(lang === 'it' ? 'it-IT' : 'en-US').format(value ?? 0)
}

const EMPTY_METRIC = { today: 0, week: 0, total: 0 }

function StatsRow({ title, data, showManual, t, lang }) {
  const periods = [
    ['today', t('home.statsToday')],
    ['week', t('home.statsWeek')],
    ['total', t('home.statsTotal')],
  ]
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <div className="grid grid-cols-3 divide-x divide-border rounded-field border border-border">
        {periods.map(([key, label]) => (
          <div key={key} className="flex min-w-0 flex-col items-center gap-0.5 px-1.5 py-2.5 text-center">
            <p className="text-xl font-bold tabular-nums text-foreground">{formatNumber(data[key], lang)}</p>
            <p className="text-xs text-muted-foreground">{label}</p>
            {showManual && (
              <p className="text-[11px] leading-tight text-muted-foreground">
                {t('home.statsManualPrefix')} {formatNumber(data.manual?.[key], lang)}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function CollectJobsSheet({ onCollected }) {
  const { t, lang } = useLanguage()
  const { showToast } = useToast()
  const [open, setOpen] = useState(false)
  const [collecting, setCollecting] = useState(false)
  const [summary, setSummary] = useState(null)
  const [stats, setStats] = useState(null)
  const { usage, refresh: refreshUsage } = useUsage()

  useEffect(() => {
    if (!open) return
    fetchHomeStats()
      .then(setStats)
      .catch(() => showToast(t('home.statsError')))
    refreshUsage()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  async function handleCollect() {
    setCollecting(true)
    setSummary(null)
    try {
      const result = await collectJobs()
      setSummary(result)
      showToast(t('home.collectSuccess'))
      fetchHomeStats().then(setStats).catch(() => {})
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

  // Durante la raccolta (sincrona, può durare minuti) il pannello resta
  // aperto: chiuderlo non interrompe la richiesta ma nasconderebbe l'esito.
  function handleOpenChange(next) {
    if (collecting && !next) return
    setOpen(next)
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetTrigger asChild>
        <Button variant="secondary" size="icon" aria-label={t('home.collectTitle')} title={t('home.collectTitle')}>
          <RefreshCw className="h-5 w-5" aria-hidden="true" />
        </Button>
      </SheetTrigger>
      <SheetContent aria-describedby={undefined}>
        <SheetHeader title={t('home.collectTitle')} />
        <SheetBody>
          <p className="text-sm leading-normal text-muted-foreground">{t('home.collectHint')}</p>

          {summary && (
            <div className="grid grid-cols-2 gap-3 rounded-field bg-tint p-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.06em] text-muted-foreground">{t('home.collectedLabel')}</p>
                <p className="mt-1 text-xl font-bold tabular-nums">{summary.collected}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.06em] text-muted-foreground">{t('home.keptLabel')}</p>
                <p className="mt-1 text-xl font-bold tabular-nums">{summary.kept}</p>
              </div>
            </div>
          )}

          {stats && (
            <div className="flex flex-col gap-3 pt-1">
              <h3 className="text-xs font-bold uppercase tracking-[0.06em] text-muted-foreground">{t('home.statsTitle')}</h3>
              <StatsRow title={t('home.statsJobsTitle')} data={stats.jobs} showManual t={t} lang={lang} />
              <StatsRow title={t('home.statsCvsTitle')} data={stats.cvs ?? EMPTY_METRIC} t={t} lang={lang} />
              <StatsRow
                title={t('home.statsApplicationsTitle')}
                data={stats.applications ?? EMPTY_METRIC}
                t={t}
                lang={lang}
              />
            </div>
          )}
        </SheetBody>
        <SheetFooter>
          <ActionCostHint usage={usage} action="collection" className="text-center" />
          <Button size="lg" onClick={handleCollect} disabled={collecting}>
            <RefreshCw className={collecting ? 'h-5 w-5 animate-spin motion-reduce:animate-none' : 'h-5 w-5'} aria-hidden="true" />
            {collecting ? t('home.collecting') : t('home.collectButton')}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
