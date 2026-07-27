import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { fetchJobs, fetchJob, generateCv, archiveJob, unarchiveJob } from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import JobCard from '@/components/JobCard'

const SECTIONS = ['main', 'imported', 'archived']
const PERIODS = ['today', 'week', 'month', 'all']
const SCORES = [1, 2, 3, 4, 5]
const STATUSES = ['new', 'cv_generated', 'application_done']

export default function JobListPage() {
  const { t } = useLanguage()
  const { logout } = useAuth()
  const { showToast } = useToast()

  const [section, setSection] = useState('main')
  const [period, setPeriod] = useState('today')
  const [scores, setScores] = useState([])
  const [statuses, setStatuses] = useState([])
  const [query, setQuery] = useState('')
  const [queryInput, setQueryInput] = useState('')

  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [generatingIds, setGeneratingIds] = useState(() => new Set())

  const debounceRef = useRef(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await fetchJobs({ section, period, scores, statuses, q: query })
      setJobs(data)
    } catch {
      setError(t('jobs.loadError'))
    } finally {
      setLoading(false)
    }
  }, [section, period, scores, statuses, query, t])

  useEffect(() => {
    load()
  }, [load])

  function handleSearchChange(value) {
    setQueryInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => setQuery(value), 300)
  }

  function toggleValue(list, setList, value) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value])
  }

  async function handleGenerateCv(job) {
    setGeneratingIds((current) => new Set(current).add(job.id))
    try {
      await generateCv(job.id)
      const updated = await fetchJob(job.id)
      setJobs((current) => current.map((j) => (j.id === job.id ? updated : j)))
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        showToast(t('jobs.generationConflict'))
      } else {
        showToast(t('jobs.generationFailed'))
      }
    } finally {
      setGeneratingIds((current) => {
        const next = new Set(current)
        next.delete(job.id)
        return next
      })
    }
  }

  async function handleArchive(job) {
    setJobs((current) => current.filter((j) => j.id !== job.id))
    await archiveJob(job.id)
    showToast(t('jobs.archivedToast'), {
      action: {
        label: t('jobs.undo'),
        onClick: async () => {
          await unarchiveJob(job.id)
          load()
        },
      },
    })
  }

  async function handleUnarchive(job) {
    setJobs((current) => current.filter((j) => j.id !== job.id))
    await unarchiveJob(job.id)
    showToast(t('jobs.unarchivedToast'))
  }

  const searching = query.length > 0
  const swipeProps =
    section === 'archived'
      ? { onSwipe: handleUnarchive, swipeLabel: t('jobs.unarchive') }
      : { onSwipe: handleArchive, swipeLabel: t('jobs.archive') }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-4 py-10">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">{t('list.title')}</h1>
        <Button variant="secondary" size="sm" onClick={logout}>
          {t('list.logout')}
        </Button>
      </header>

      <div className="flex gap-2">
        {SECTIONS.map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setSection(value)}
            className={
              'rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ' +
              (section === value
                ? 'bg-primary text-primary-foreground'
                : 'bg-secondary text-muted-foreground hover:text-foreground')
            }
          >
            {t(`jobs.section_${value}`)}
          </button>
        ))}
      </div>

      <Input
        value={queryInput}
        onChange={(event) => handleSearchChange(event.target.value)}
        placeholder={t('jobs.searchPlaceholder')}
        aria-label={t('jobs.searchPlaceholder')}
      />

      <div className={'flex flex-wrap items-center gap-4' + (searching ? ' opacity-40' : '')}>
        <Select value={period} onValueChange={setPeriod} disabled={searching}>
          <SelectTrigger aria-label={t('jobs.periodLabel')} className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PERIODS.map((value) => (
              <SelectItem key={value} value={value}>
                {t(`jobs.period_${value}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">{t('jobs.scoreLabel')}</span>
          {SCORES.map((value) => (
            <button
              key={value}
              type="button"
              disabled={searching}
              onClick={() => toggleValue(scores, setScores, value)}
              aria-pressed={scores.includes(value)}
              className={
                'h-7 w-7 rounded-md text-sm font-semibold tabular-nums transition-colors ' +
                (scores.includes(value)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground hover:text-foreground')
              }
            >
              {value}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">{t('jobs.statusLabel')}</span>
          {STATUSES.map((value) => (
            <button
              key={value}
              type="button"
              disabled={searching}
              onClick={() => toggleValue(statuses, setStatuses, value)}
              aria-pressed={statuses.includes(value)}
              className={
                'rounded-full px-2.5 py-1 text-xs font-medium transition-colors ' +
                (statuses.includes(value)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground hover:text-foreground')
              }
            >
              {t(`jobs.status_${value}`)}
            </button>
          ))}
        </div>
      </div>
      {searching && <p className="text-xs text-muted-foreground">{t('jobs.filtersDisabledWhileSearching')}</p>}

      {error && (
        <p role="alert" className="rounded-md bg-destructive-soft px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {!loading && !error && jobs.length === 0 && (
        <p className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
          {t(`jobs.empty_${section}`)}
        </p>
      )}

      <div className="flex flex-col gap-3">
        {jobs.map((job) => (
          <JobCard
            key={job.id}
            job={job}
            onGenerateCv={handleGenerateCv}
            generating={generatingIds.has(job.id)}
            {...swipeProps}
          />
        ))}
      </div>
    </div>
  )
}
