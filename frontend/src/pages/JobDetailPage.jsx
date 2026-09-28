import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Heart, UserRound } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import {
  fetchJob,
  generateCv,
  markApplicationDone,
  generateCoverLetter,
  fetchCoverLetterInstructions,
  favoriteJob,
  unfavoriteJob,
} from '../api/jobs'
import { ApiError } from '../api/client'
import { useToast } from '@/components/ToastProvider'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { scoreItemLabel, scoreItemReason } from '../utils/scoreItems'
import { scoreStyle } from '../utils/scoreStyle'
import { formatShortDate } from '../utils/date'
import { applicantsLabel, isLowApplicants } from '../utils/applicants'

export default function JobDetailPage() {
  const { id } = useParams()
  const { t, lang } = useLanguage()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [marking, setMarking] = useState(false)
  const [showGapPanel, setShowGapPanel] = useState(false)
  const [selectedGaps, setSelectedGaps] = useState([])
  const [gapInstructions, setGapInstructions] = useState('')
  const [showReasons, setShowReasons] = useState(false)

  const [showCoverLetterDialog, setShowCoverLetterDialog] = useState(false)
  const [coverLetterText, setCoverLetterText] = useState('')
  const [pastInstructions, setPastInstructions] = useState([])
  const [selectedPastInstructions, setSelectedPastInstructions] = useState([])
  const [generatingCoverLetter, setGeneratingCoverLetter] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetchJob(id)
      .then((jobData) => {
        if (!cancelled) setJob(jobData)
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

  function toggleGap(text) {
    setSelectedGaps((current) =>
      current.includes(text) ? current.filter((item) => item !== text) : [...current, text],
    )
  }

  async function handleGenerate() {
    setGenerating(true)
    try {
      await generateCv(id, selectedGaps, gapInstructions)
      const updated = await fetchJob(id)
      setJob(updated)
      setSelectedGaps([])
      setGapInstructions('')
      setShowGapPanel(false)
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

  function openCoverLetterDialog() {
    setCoverLetterText('')
    setSelectedPastInstructions([])
    setShowCoverLetterDialog(true)
    fetchCoverLetterInstructions()
      .then((data) => setPastInstructions(data.instructions || []))
      .catch(() => setPastInstructions([]))
  }

  function togglePastInstruction(text) {
    setSelectedPastInstructions((current) =>
      current.includes(text) ? current.filter((item) => item !== text) : [...current, text],
    )
  }

  async function handleGenerateCoverLetter() {
    setGeneratingCoverLetter(true)
    try {
      const instructions = [...selectedPastInstructions, coverLetterText.trim()]
        .filter(Boolean)
        .join('\n\n')
      await generateCoverLetter(id, instructions)
      const updated = await fetchJob(id)
      setJob(updated)
      setShowCoverLetterDialog(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        showToast(err.data?.detail || t('jobs.generationConflict'))
      } else {
        showToast(t('jobs.coverLetterGenerationFailed'))
      }
    } finally {
      setGeneratingCoverLetter(false)
    }
  }

  async function handleToggleFavorite() {
    const nextFavorite = !job.is_favorite
    setJob((current) => ({ ...current, is_favorite: nextFavorite }))
    const updated = nextFavorite ? await favoriteJob(id) : await unfavoriteJob(id)
    setJob(updated)
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

  const hasCv = Boolean(job.cv_pdf_url)
  const hasExpandableReasons = [...(job.score_match || []), ...(job.score_gaps || [])].some(
    (item) => scoreItemReason(item),
  )
  const applicantsText = applicantsLabel(job, t)
  const lowApplicants = isLowApplicants(job)

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
              {applicantsText && (
                <span
                  className={
                    'rounded-full px-2 py-0.5 text-xs font-medium ' +
                    (lowApplicants
                      ? 'bg-success-soft text-success font-semibold'
                      : 'bg-secondary text-muted-foreground')
                  }
                >
                  {applicantsText}
                </span>
              )}
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight text-balance">{job.title}</h1>
            <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
              <span>
                {job.company}
                {job.location && <> · {job.location}</>}
                {job.salary && <> · {job.salary}</>}
              </span>
              {job.recruiter_name && (
                job.recruiter_profile_url ? (
                  <a
                    href={job.recruiter_profile_url}
                    target="_blank"
                    rel="noreferrer"
                    title={`${t('jobs.recruiterIconLabel')} ${job.recruiter_name}`}
                    className="text-muted-foreground/70 hover:text-foreground"
                  >
                    <UserRound className="h-4 w-4" />
                  </a>
                ) : (
                  <span
                    title={`${t('jobs.recruiterIconLabel')} ${job.recruiter_name}`}
                    className="text-muted-foreground/70"
                  >
                    <UserRound className="h-4 w-4" />
                  </span>
                )
              )}
            </p>
            {job.date_collected && (
              <p className="mt-0.5 text-xs text-muted-foreground/70">
                {t('jobs.importedOnPrefix')} {formatShortDate(job.date_collected, lang)}
              </p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <button
              type="button"
              onClick={handleToggleFavorite}
              aria-label={job.is_favorite ? t('jobs.unfavorite') : t('jobs.favorite')}
              aria-pressed={job.is_favorite}
              className="text-muted-foreground hover:text-rose-500"
            >
              <Heart className={`h-6 w-6 ${job.is_favorite ? 'fill-rose-500 text-rose-500' : ''}`} />
            </button>
            {job.score != null && (
              <div
                className={`flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-2xl ${scoreStyle(job.score)}`}
              >
                <span className="text-2xl font-bold tabular-nums leading-none">{job.score}</span>
              </div>
            )}
          </div>
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
          <div className="mt-5">
            {hasExpandableReasons && (
              <button
                type="button"
                onClick={() => setShowReasons((current) => !current)}
                className="mb-2 text-xs font-medium text-primary hover:underline"
              >
                {showReasons ? t('jobs.hideReasons') : t('jobs.expandReasons')}
              </button>
            )}
            <div className="grid gap-5 sm:grid-cols-2">
              {job.score_match?.length > 0 && (
                <div>
                  <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {t('jobs.matches')}
                  </h2>
                  <ul className="flex flex-col gap-1.5 text-sm">
                    {job.score_match.map((item, index) => (
                      <li key={index} className="flex flex-col gap-0.5">
                        <div className="flex gap-2">
                          <span className="shrink-0 text-success">✓</span>
                          {scoreItemLabel(item)}
                        </div>
                        {showReasons && scoreItemReason(item) && (
                          <p className="pl-5 text-xs text-muted-foreground">{scoreItemReason(item)}</p>
                        )}
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
                      <li key={index} className="flex flex-col gap-0.5">
                        <div className="flex gap-2">
                          <span className="shrink-0 text-destructive">−</span>
                          {scoreItemLabel(item)}
                        </div>
                        {showReasons && scoreItemReason(item) && (
                          <p className="pl-5 text-xs text-muted-foreground">{scoreItemReason(item)}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
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
          onClick={() => setShowGapPanel((open) => !open)}
          className="text-sm font-medium text-primary hover:underline"
        >
          {showGapPanel ? '▾ ' : '▸ '}
          {t('jobs.gapPanelToggle')}
        </button>
        {showGapPanel && (
          <div className="mt-4 flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">{t('jobs.gapPanelHint')}</p>
            {job.score_gaps?.length > 0 ? (
              <div className="flex flex-col gap-2">
                {job.score_gaps.map((item, index) => {
                  const label = scoreItemLabel(item)
                  const reason = scoreItemReason(item)
                  // Il testo inviato al backend include il motivo, quando
                  // c'è: più contesto per il modello su perché è un gap,
                  // non solo la sua etichetta breve mostrata in lista.
                  const gapText = reason ? `${label} (${reason})` : label
                  return (
                    <label key={index} className="flex items-start gap-2.5 text-sm">
                      <Checkbox
                        checked={selectedGaps.includes(gapText)}
                        onCheckedChange={() => toggleGap(gapText)}
                      />
                      <span className="text-foreground">
                        {index + 1}. {label}
                      </span>
                    </label>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t('jobs.gapPanelNoGaps')}</p>
            )}
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="gap-instructions">{t('jobs.gapInstructionsLabel')}</Label>
              <Textarea
                id="gap-instructions"
                value={gapInstructions}
                onChange={(event) => setGapInstructions(event.target.value)}
                placeholder={t('jobs.gapInstructionsPlaceholder')}
              />
              {selectedGaps.length > 0 && !gapInstructions.trim() && (
                <p className="text-xs text-muted-foreground">{t('jobs.gapInstructionsDefaultHint')}</p>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" disabled={generating || job.cv_generation_in_progress} onClick={handleGenerate}>
          {generating || job.cv_generation_in_progress
            ? t('jobs.generating')
            : hasCv
              ? t('jobs.regenerateCv')
              : t('jobs.generateCv')}
        </Button>

        {job.cv_pdf_url && (
          <Button variant="secondary" asChild>
            <a href={job.cv_pdf_url} download={job.cv_download_filename} target="_blank" rel="noreferrer">
              {t('jobs.downloadCv')}
            </a>
          </Button>
        )}

        <Button
          type="button"
          variant="secondary"
          disabled={generatingCoverLetter || job.cover_letter_generation_in_progress}
          onClick={openCoverLetterDialog}
        >
          {generatingCoverLetter || job.cover_letter_generation_in_progress
            ? t('jobs.generatingCoverLetter')
            : t('jobs.generateCoverLetter')}
        </Button>

        {job.cover_letter_pdf_url && (
          <Button variant="secondary" asChild>
            <a
              href={job.cover_letter_pdf_url}
              download={job.cover_letter_download_filename}
              target="_blank"
              rel="noreferrer"
            >
              {t('jobs.downloadCoverLetter')}
            </a>
          </Button>
        )}

        {job.apply_url ? (
          <Button variant="secondary" asChild>
            <a href={job.apply_url} target="_blank" rel="noreferrer">
              {t('jobs.openApplyLink')}
            </a>
          </Button>
        ) : (
          <span className="text-sm text-muted-foreground">{t('jobs.applyLinkHint')}</span>
        )}

        {job.status !== 'application_done' && (
          <Button variant="secondary" disabled={marking} onClick={handleMarkApplicationDone}>
            {t('jobs.markApplicationDone')}
          </Button>
        )}
      </div>

      <Dialog open={showCoverLetterDialog} onOpenChange={setShowCoverLetterDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('jobs.coverLetterDialogTitle')}</DialogTitle>
            <DialogDescription>{t('jobs.coverLetterDialogHint')}</DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cover-letter-instructions">
                {t('jobs.coverLetterInstructionsLabel')}
              </Label>
              <Textarea
                id="cover-letter-instructions"
                value={coverLetterText}
                onChange={(event) => setCoverLetterText(event.target.value)}
                placeholder={t('jobs.coverLetterInstructionsPlaceholder')}
              />
            </div>

            {pastInstructions.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <Label>{t('jobs.coverLetterPastInstructionsLabel')}</Label>
                <div className="flex max-h-40 flex-col gap-2 overflow-y-auto rounded-lg border border-border p-3">
                  {pastInstructions.map((text, index) => (
                    <label key={index} className="flex items-start gap-2.5 text-sm">
                      <Checkbox
                        checked={selectedPastInstructions.includes(text)}
                        onCheckedChange={() => togglePastInstruction(text)}
                      />
                      <span className="text-foreground">{text}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="secondary" onClick={() => setShowCoverLetterDialog(false)}>
              {t('jobs.cancel')}
            </Button>
            <Button type="button" disabled={generatingCoverLetter} onClick={handleGenerateCoverLetter}>
              {generatingCoverLetter ? t('jobs.generatingCoverLetter') : t('jobs.generateCoverLetter')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
