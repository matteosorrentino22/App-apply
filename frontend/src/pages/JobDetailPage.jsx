import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'
import {
  fetchJob,
  generateCv,
  enrichAndGenerateCv,
  markApplicationDone,
} from '../api/jobs'
import { fetchProfile } from '../api/profile'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import ChipInput from '@/components/ChipInput'

const SCORE_STYLE = {
  1: 'bg-score-1-soft text-score-1',
  2: 'bg-score-2-soft text-score-2',
  3: 'bg-score-3-soft text-score-3',
  4: 'bg-score-4-soft text-score-4',
  5: 'bg-score-5-soft text-score-5',
}

const EMPTY_ENRICHMENT = {
  experience_id: '',
  additional_bullets: [],
  save_to_profile: false,
}

export default function JobDetailPage() {
  const { id } = useParams()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [job, setJob] = useState(null)
  const [experiences, setExperiences] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [marking, setMarking] = useState(false)
  const [showEnrichment, setShowEnrichment] = useState(false)
  const [enrichment, setEnrichment] = useState(EMPTY_ENRICHMENT)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    Promise.all([fetchJob(id), fetchProfile()])
      .then(([jobData, profileData]) => {
        if (cancelled) return
        setJob(jobData)
        setExperiences(profileData.experiences || [])
      })
      .catch(() => {
        if (!cancelled) setError(t('jobs.notFound'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, t])

  // L'arricchimento va agganciato a un'esperienza già presente nel
  // profilo (Docs/03 §5.6): finché non è selezionata un'esperienza e non
  // c'è almeno un'attività aggiuntiva, non c'è nulla di valido da inviare.
  const enrichmentStarted = enrichment.experience_id || enrichment.additional_bullets.length > 0
  const enrichmentComplete = Boolean(enrichment.experience_id) && enrichment.additional_bullets.length > 0
  const enrichmentIncomplete = enrichmentStarted && !enrichmentComplete

  async function handleGenerate() {
    if (enrichmentIncomplete) return
    setGenerating(true)
    try {
      if (enrichmentComplete) {
        await enrichAndGenerateCv(id, enrichment)
      } else {
        await generateCv(id)
      }
      const updated = await fetchJob(id)
      setJob(updated)
      setEnrichment(EMPTY_ENRICHMENT)
      setShowEnrichment(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Il backend distingue più cause dietro lo stesso 409 (concorrenza,
        // profilo incompleto, massimale/credito esaurito): il messaggio
        // esatto arriva in `detail`, non va sostituito con un testo fisso
        // che nasconderebbe all'utente la vera causa del blocco.
        showToast(err.data?.detail || t('jobs.generationConflict'))
      } else {
        showToast(t('jobs.generationFailed'))
      }
    } finally {
      setGenerating(false)
    }
  }

  async function handleMarkApplicationDone() {
    setMarking(true)
    try {
      const updated = await markApplicationDone(id)
      setJob(updated)
    } catch (err) {
      showToast(
        err instanceof ApiError && err.status === 409
          ? t('jobs.applicationRejected')
          : t('common.genericError'),
      )
    } finally {
      setMarking(false)
    }
  }

  if (loading) {
    return <p className="mt-16 text-center text-sm text-muted-foreground">{t('common.loading')}</p>
  }

  if (error || !job) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <p role="alert" className="rounded-md bg-destructive-soft px-3 py-2 text-sm text-destructive">
          {error || t('jobs.notFound')}
        </p>
        <Button variant="secondary" className="mt-4" onClick={() => navigate('/list')}>
          {t('jobs.backToList')}
        </Button>
      </div>
    )
  }

  const cvGenerated = job.status !== 'new'

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
      <Link to="/list" className="text-sm font-medium text-primary hover:underline">
        ← {t('jobs.backToList')}
      </Link>

      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge data-testid="job-status-badge" variant={job.status === 'new' ? 'neutral' : 'primary'}>
                {t(`jobs.status_${job.status}`)}
              </Badge>
              {job.matched_search && <Badge variant="neutral">{job.matched_search}</Badge>}
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-balance">{job.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {job.company}
              {job.location && <> · {job.location}</>}
              {job.salary && <> · {job.salary}</>}
            </p>
          </div>
          {job.score != null && (
            <div
              className={`flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-2xl ${SCORE_STYLE[job.score]}`}
            >
              <span className="text-2xl font-bold tabular-nums leading-none">{job.score}</span>
            </div>
          )}
        </div>

        {job.score_reasoning && (
          <div className="mt-5">
            <h2 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t('jobs.whyThisScore')}
            </h2>
            <p className="text-sm text-foreground">{job.score_reasoning}</p>
          </div>
        )}

        {(job.score_match?.length > 0 || job.score_gaps?.length > 0) && (
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            {job.score_match?.length > 0 && (
              <div>
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t('jobs.matches')}
                </h2>
                <ul className="flex flex-col gap-1.5 text-sm">
                  {job.score_match.map((item, index) => (
                    <li key={index} className="flex gap-2">
                      <span className="shrink-0 text-success">✓</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {job.score_gaps?.length > 0 && (
              <div>
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t('jobs.gaps')}
                </h2>
                <ul className="flex flex-col gap-1.5 text-sm">
                  {job.score_gaps.map((item, index) => (
                    <li key={index} className="flex gap-2">
                      <span className="shrink-0 text-destructive">−</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="mt-5">
          <h2 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('jobs.description')}
          </h2>
          <p className="whitespace-pre-line text-sm text-foreground">{job.description}</p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <button
          type="button"
          onClick={() => setShowEnrichment((open) => !open)}
          className="text-sm font-medium text-primary hover:underline"
        >
          {showEnrichment ? '▾ ' : '▸ '}
          {t('jobs.enrichmentToggle')}
        </button>
        {showEnrichment && (
          <div className="mt-4 flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">{t('jobs.enrichmentHint')}</p>
            {experiences.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('jobs.enrichmentNoExperiences')}</p>
            ) : (
              <>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="enr-experience">{t('jobs.enrichmentExperience')}</Label>
                  <Select
                    value={enrichment.experience_id ? String(enrichment.experience_id) : ''}
                    onValueChange={(value) =>
                      setEnrichment({ ...enrichment, experience_id: Number(value) })
                    }
                  >
                    <SelectTrigger id="enr-experience">
                      <SelectValue placeholder={t('jobs.enrichmentExperiencePlaceholder')} />
                    </SelectTrigger>
                    <SelectContent>
                      {experiences.map((exp) => (
                        <SelectItem key={exp.id} value={String(exp.id)}>
                          {exp.role} — {exp.company}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="enr-bullets">{t('jobs.enrichmentBullets')}</Label>
                  <ChipInput
                    id="enr-bullets"
                    value={enrichment.additional_bullets}
                    onChange={(additional_bullets) =>
                      setEnrichment({ ...enrichment, additional_bullets })
                    }
                    placeholder={t('onboarding.activitiesPlaceholder')}
                  />
                </div>
                <label className="flex items-center gap-2.5 text-sm">
                  <Checkbox
                    checked={enrichment.save_to_profile}
                    onCheckedChange={(checked) =>
                      setEnrichment({ ...enrichment, save_to_profile: checked === true })
                    }
                  />
                  {t('jobs.enrichmentSaveToProfile')}
                </label>
                {enrichmentIncomplete && (
                  <p role="alert" className="text-sm text-destructive">
                    {t('jobs.enrichmentIncomplete')}
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          disabled={generating || job.cv_generation_in_progress || enrichmentIncomplete}
          onClick={handleGenerate}
        >
          {generating || job.cv_generation_in_progress
            ? t('jobs.generating')
            : enrichmentComplete
              ? t('jobs.generateWithEnrichment')
              : job.status === 'new'
                ? t('jobs.generateCv')
                : t('jobs.regenerateCv')}
        </Button>

        {job.cv_pdf_url && (
          <Button variant="secondary" asChild>
            <a href={job.cv_pdf_url} target="_blank" rel="noreferrer">
              {t('jobs.downloadPdf')}
            </a>
          </Button>
        )}

        {cvGenerated ? (
          <Button variant="secondary" asChild>
            <a href={job.apply_url} target="_blank" rel="noreferrer">
              {t('jobs.openApplyLink')}
            </a>
          </Button>
        ) : (
          <span className="text-sm text-muted-foreground">{t('jobs.applyLinkHint')}</span>
        )}

        {job.status === 'cv_generated' && (
          <Button variant="secondary" disabled={marking} onClick={handleMarkApplicationDone}>
            {t('jobs.markApplicationDone')}
          </Button>
        )}
      </div>
    </div>
  )
}
