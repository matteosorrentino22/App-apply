import { useEffect, useState } from 'react'
import { Briefcase, FileText, Send } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { collectJobs, fetchHomeStats } from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'

function formatNumber(value, lang) {
  return new Intl.NumberFormat(lang === 'it' ? 'it-IT' : 'en-US').format(value ?? 0)
}

function StatPeriod({ value, label, manualValue, manualLabel, lang }) {
  return (
    <div className="flex flex-1 flex-col items-center gap-1 px-2 py-3 text-center">
      <p className="text-2xl font-semibold text-foreground">{formatNumber(value, lang)}</p>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      {manualLabel != null && (
        <p className="text-[11px] text-muted-foreground/80">
          {manualLabel} {formatNumber(manualValue, lang)}
        </p>
      )}
    </div>
  )
}

function StatsCard({ icon, title, data, showManual, t, lang }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2 pb-2">
        {icon}
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex divide-x divide-border">
          <StatPeriod
            value={data.today}
            label={t('home.statsToday')}
            manualLabel={showManual ? t('home.statsManualPrefix') : null}
            manualValue={data.manual?.today}
            lang={lang}
          />
          <StatPeriod
            value={data.week}
            label={t('home.statsWeek')}
            manualLabel={showManual ? t('home.statsManualPrefix') : null}
            manualValue={data.manual?.week}
            lang={lang}
          />
          <StatPeriod
            value={data.total}
            label={t('home.statsTotal')}
            manualLabel={showManual ? t('home.statsManualPrefix') : null}
            manualValue={data.manual?.total}
            lang={lang}
          />
        </div>
      </CardContent>
    </Card>
  )
}

const EMPTY_METRIC = { today: 0, week: 0, total: 0 }

export default function HomePage() {
  const { t, lang } = useLanguage()
  const { showToast } = useToast()

  const [collecting, setCollecting] = useState(false)
  const [summary, setSummary] = useState(null)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchHomeStats()
      .then(setStats)
      .catch(() => showToast(t('home.statsError')))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleCollect() {
    setCollecting(true)
    setSummary(null)
    try {
      const result = await collectJobs()
      setSummary(result)
      showToast(t('home.collectSuccess'))
      fetchHomeStats().then(setStats).catch(() => {})
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        showToast(err.data?.detail || t('home.collectConflict'))
      } else {
        showToast(t('home.collectFailed'))
      }
    } finally {
      setCollecting(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
      <h1 className="text-3xl font-bold tracking-tight">{t('home.title')}</h1>

      <div className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {t('home.statsTitle')}
        </h2>

        {stats && (
          <>
            <StatsCard
              icon={<Briefcase className="h-4 w-4 text-primary" />}
              title={t('home.statsJobsTitle')}
              data={stats.jobs}
              showManual
              t={t}
              lang={lang}
            />
            <StatsCard
              icon={<FileText className="h-4 w-4 text-primary" />}
              title={t('home.statsCvsTitle')}
              data={stats.cvs ?? EMPTY_METRIC}
              t={t}
              lang={lang}
            />
            <StatsCard
              icon={<Send className="h-4 w-4 text-primary" />}
              title={t('home.statsApplicationsTitle')}
              data={stats.applications ?? EMPTY_METRIC}
              t={t}
              lang={lang}
            />
          </>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('home.collectTitle')}</CardTitle>
          <CardDescription>{t('home.collectHint')}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Button onClick={handleCollect} disabled={collecting} className="self-start">
            {collecting ? t('home.collecting') : t('home.collectButton')}
          </Button>

          {summary && (
            <div className="flex items-center gap-8">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t('home.collectedLabel')}
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums">{summary.collected}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t('home.keptLabel')}
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums">{summary.kept}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
