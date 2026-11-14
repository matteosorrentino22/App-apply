import { useEffect, useId, useState } from 'react'
import { Briefcase, ChevronDown, ChevronUp, FileText, Send } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { fetchHomeStats } from '../api/jobs'

// Riepilogo delle statistiche in Jobs (Sprint 74, mockup `jobs-lista` e
// `jobs-stats`, SPEC-DELTA A1): chiuso mostra i job trovati oggi e negli
// ultimi 7 giorni; aperto le tre metriche della Home eliminata (job trovati
// con "di cui manuali", CV generati, candidature fatte; oggi, settimana,
// totali). Stessa API di prima (GET /api/jobs/stats/). `refreshKey` cambia
// dopo una raccolta manuale riuscita per ricaricare i numeri.

const EMPTY_METRIC = { today: 0, week: 0, total: 0 }

function useNumberFormat(lang) {
  const formatter = new Intl.NumberFormat(lang === 'it' ? 'it-IT' : 'en-US')
  return (value) => formatter.format(value ?? 0)
}

function MetricGroup({ icon: Icon, title, data, format, t, footer }) {
  const periods = [
    ['today', t('home.statsToday')],
    ['week', t('home.statsWeekShort')],
    ['total', t('home.statsTotal')],
  ]
  return (
    <div className="flex flex-col gap-2">
      <p className="flex items-center gap-2 text-[15px] font-semibold text-foreground">
        <Icon className="h-[18px] w-[18px] text-primary" aria-hidden="true" />
        {title}
      </p>
      <dl className="grid grid-cols-3 gap-2">
        {periods.map(([key, label]) => (
          <div key={key} className="flex min-w-0 flex-col-reverse">
            <dt className="truncate text-xs font-bold uppercase tracking-[0.06em] text-muted-foreground">{label}</dt>
            <dd className="text-2xl font-bold tabular-nums text-foreground">{format(data[key])}</dd>
          </div>
        ))}
      </dl>
      {footer ? <p className="text-[13px] text-muted-foreground">{footer}</p> : null}
    </div>
  )
}

export default function StatsSummary({ refreshKey }) {
  const { t, lang } = useLanguage()
  const format = useNumberFormat(lang)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(false)
  const [open, setOpen] = useState(false)
  const panelId = useId()

  useEffect(() => {
    let cancelled = false
    fetchHomeStats()
      .then((data) => {
        if (!cancelled) {
          setStats(data)
          setError(false)
        }
      })
      .catch(() => !cancelled && setError(true))
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  if (error && !stats) {
    return <p className="text-sm text-muted-foreground">{t('home.statsError')}</p>
  }
  if (!stats) return null

  const jobs = stats.jobs ?? EMPTY_METRIC
  const toggle = (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={panelId}
      onClick={() => setOpen((current) => !current)}
      className="flex min-h-11 shrink-0 items-center gap-1 rounded-field px-1 text-[15px] font-semibold text-primary outline-none focus-visible:ring-3 focus-visible:ring-ring/30"
    >
      {open ? t('home.statsClose') : t('home.statsOpen')}
      {open ? <ChevronUp className="h-4 w-4" aria-hidden="true" /> : <ChevronDown className="h-4 w-4" aria-hidden="true" />}
    </button>
  )

  return (
    <section className="rounded-card border border-border bg-card px-4 py-3 shadow-card" aria-label={t('home.statsTitle')}>
      {open ? (
        <div className="flex flex-col gap-4 pb-1">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-bold text-foreground">{t('home.statsTitle')}</h2>
            {toggle}
          </div>
          <div id={panelId} className="flex flex-col gap-4 [&>*:not(:first-child)]:border-t [&>*:not(:first-child)]:border-border [&>*:not(:first-child)]:pt-4">
            <MetricGroup
              icon={Briefcase}
              title={t('home.statsJobsTitle')}
              data={jobs}
              format={format}
              t={t}
              footer={t('home.statsManualLine')
                .replace('{today}', format(jobs.manual?.today))
                .replace('{week}', format(jobs.manual?.week))
                .replace('{total}', format(jobs.manual?.total))}
            />
            <MetricGroup icon={FileText} title={t('home.statsCvsTitle')} data={stats.cvs ?? EMPTY_METRIC} format={format} t={t} />
            <MetricGroup
              icon={Send}
              title={t('home.statsApplicationsTitle')}
              data={stats.applications ?? EMPTY_METRIC}
              format={format}
              t={t}
            />
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between gap-3">
          <dl className="flex min-w-0 items-stretch gap-4">
            <div className="flex min-w-0 flex-col-reverse">
              <dt className="text-sm text-muted-foreground">{t('home.statsNewToday')}</dt>
              <dd className="text-[26px] font-bold leading-tight tabular-nums text-foreground">{format(jobs.today)}</dd>
            </div>
            <div className="w-px shrink-0 bg-border" aria-hidden="true" />
            <div className="flex min-w-0 flex-col-reverse">
              <dt className="text-sm text-muted-foreground">{t('home.statsThisWeek')}</dt>
              <dd className="text-[26px] font-bold leading-tight tabular-nums text-foreground">{format(jobs.week)}</dd>
            </div>
          </dl>
          {toggle}
        </div>
      )}
    </section>
  )
}
