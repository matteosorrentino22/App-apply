import { useEffect, useState } from 'react'
import { BellOff, Clock, Lock, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { updateMe } from '../api/auth'
import { collectJobs } from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Badge } from '@/components/ui/badge'
import { Banner } from '@/components/ui/banner'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetBody, SheetContent, SheetFooter, SheetHeader } from '@/components/ui/sheet'
import { Spinner } from '@/components/ui/spinner'
import { Switch } from '@/components/ui/switch'
import { useUsage } from '@/lib/usage'
import { QUARTER_HOURS, collectionDoneText, timeZoneLabel } from '../utils/collection'

// Pannello "Raccogli nuovi job" (Sprint 74; Sprint 77 mockup `collect-pro`,
// `collect-free`, `collect-running`). Regola dello Sprint 77: **una raccolta
// al giorno**, automatica o manuale (giorno di Europe/Rome). "Raccogli ora"
// è la manuale (POST /api/jobs/collect/, sincrona); con la raccolta di oggi
// già fatta è disattivato e il motivo dice a che ora ("già eseguita oggi
// alle HH:MM", nel fuso dell'utente). Sotto, la raccolta automatica: per i
// Pro interruttore e orario a quarti d'ora (PATCH /api/accounts/me/); per i
// Free bloccata con l'invito al Pro. Il mockup `collect-pro` mostra
// automatica e manuale come due limiti separati: vale la quota unica.
export function CollectButton({ onClick }) {
  const { t } = useLanguage()
  return (
    <Button variant="secondary" size="icon" onClick={onClick} aria-label={t('home.collectTitle')} title={t('home.collectTitle')}>
      <RefreshCw className="h-5 w-5" aria-hidden="true" />
    </Button>
  )
}

function AutomaticCollection({ user, onChange, saving }) {
  const { t } = useLanguage()
  const isPro = user?.plan === 'pro'
  const enabled = Boolean(isPro && user?.auto_collection_enabled)
  const time = user?.auto_collection_time || '07:00'
  return (
    <section aria-labelledby="auto-collect-title" className="flex flex-col gap-3 border-t border-border pt-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2">
            <span id="auto-collect-title" className={isPro ? 'text-[17px] font-bold text-foreground' : 'text-[17px] font-bold text-muted-foreground'}>
              {t('home.autoCollectTitle')}
            </span>
            <Badge variant="neutral" className="gap-1 text-xs">
              {isPro ? null : <Lock className="h-3 w-3" aria-hidden="true" />}
              PRO
            </Badge>
          </p>
          <p className="mt-1 text-sm leading-normal text-muted-foreground">
            {isPro ? t('home.autoCollectHintPro') : t('home.autoCollectHintFree')}
          </p>
        </div>
        <Switch
          checked={enabled}
          disabled={!isPro || saving}
          label={t('home.autoCollectTitle')}
          onCheckedChange={(checked) => onChange({ auto_collection_enabled: checked })}
          className="mt-1"
        />
      </div>
      {isPro && enabled ? (
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[15px] font-semibold text-foreground" id="auto-collect-time-label">
              {t('home.autoCollectTimeLabel')}
            </p>
            <p className="text-[13px] text-muted-foreground">{timeZoneLabel(t, user.timezone)}</p>
          </div>
          <Select value={time} disabled={saving} onValueChange={(value) => onChange({ auto_collection_time: value })}>
            <SelectTrigger aria-labelledby="auto-collect-time-label" className="w-32 shrink-0 text-[17px] font-bold">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="max-h-72">
              {QUARTER_HOURS.map((value) => (
                <SelectItem key={value} value={value}>
                  {value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      ) : null}
      {isPro && enabled && user.notifications_enabled === false ? (
        // Sprint 80 (stato "notifiche disattivate", DESIGN.md §7): la raccolta
        // automatica avviene comunque, manca solo l'avviso di fine raccolta.
        <Banner
          variant="note"
          icon={BellOff}
          action={
            <Button asChild variant="secondary" className="w-full">
              <Link to="/settings">{t('home.autoCollectNotificationsOn')}</Link>
            </Button>
          }
        >
          {t('home.autoCollectNotificationsOff')}
        </Banner>
      ) : null}
      {!isPro ? (
        <Banner
          variant="note"
          icon={Lock}
          action={
            <Button asChild variant="secondary" className="w-full">
              <Link to="/settings">{t('home.autoCollectDiscoverPro')}</Link>
            </Button>
          }
        >
          {t('home.autoCollectProPitch')}
        </Banner>
      ) : null}
    </section>
  )
}

export default function CollectJobsSheet({ open, onOpenChange, onCollected }) {
  const { t, lang } = useLanguage()
  const { user, refreshUser } = useAuth()
  const { showToast } = useToast()
  const [collecting, setCollecting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [summary, setSummary] = useState(null)
  const { usage, refresh: refreshUsage } = useUsage()

  // Dati del consumo ricaricati a ogni apertura (il pannello è montato con
  // la lista: altrimenti resterebbero quelli dell'apertura della pagina, per
  // esempio prima di una raccolta automatica o fatta da un altro dispositivo).
  useEffect(() => {
    if (open) refreshUsage()
  }, [open, refreshUsage])

  const collection = usage?.actions?.collection
  const doneToday = collection?.next_charge === 'blocked'

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

  async function handleAutoChange(patch) {
    setSaving(true)
    try {
      await updateMe(patch)
      await refreshUser()
      showToast(t('account.settingsSaved'))
    } catch (err) {
      const detail = err instanceof ApiError ? Object.values(err.data || {}).flat()[0] : null
      showToast(typeof detail === 'string' ? detail : t('common.genericError'))
    } finally {
      setSaving(false)
    }
  }

  // Durante la raccolta il pannello resta aperto: chiuderlo non interrompe
  // la richiesta ma nasconderebbe l'esito.
  function handleOpenChange(next) {
    if (collecting && !next) return
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
              <Banner variant="note" icon={Clock}>
                {t('home.collect24h')}
              </Banner>
              <div className="flex flex-col gap-2">
                <Button size="lg" onClick={handleCollect} disabled={collecting || doneToday}>
                  <RefreshCw className="h-5 w-5" aria-hidden="true" />
                  {t('home.collectButton')}
                </Button>
                {doneToday ? (
                  <p data-testid="collect-done" className="text-center text-[13px] font-semibold text-foreground">
                    {collectionDoneText(t, lang, collection?.done_at, user?.timezone)}
                  </p>
                ) : null}
                <p className="text-center text-[13px] text-muted-foreground">
                  {t('home.collectDailyRule')}
                  {summary
                    ? ` · ${t('home.collectLastResult').replace('{collected}', summary.collected).replace('{kept}', summary.kept)}`
                    : ''}
                </p>
              </div>
              <AutomaticCollection user={user} onChange={handleAutoChange} saving={saving} />
            </>
          )}
        </SheetBody>
        {collecting ? (
          <SheetFooter>
            <Button size="lg" disabled>
              <RefreshCw className="h-5 w-5" aria-hidden="true" />
              {t('home.collecting')}
            </Button>
          </SheetFooter>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
