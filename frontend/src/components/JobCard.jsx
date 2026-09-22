import { Link } from 'react-router-dom'
import { Heart, UserRound } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import SwipeToArchive from '@/components/SwipeToArchive'
import { useLanguage } from '../i18n/LanguageContext'
import { scoreItemLabel } from '../utils/scoreItems'
import { formatShortDate } from '../utils/date'
import { applicantsLabel, isLowApplicants } from '../utils/applicants'

const SCORE_STYLE = {
  1: 'bg-score-1-soft text-score-1',
  2: 'bg-score-2-soft text-score-2',
  3: 'bg-score-3-soft text-score-3',
  4: 'bg-score-4-soft text-score-4',
  5: 'bg-score-5-soft text-score-5',
}

export default function JobCard({ job, onSwipe, swipeLabel, onGenerateCv, onToggleFavorite, generating }) {
  const { t, lang } = useLanguage()

  const statusBadge =
    job.status === 'new' ? (
      <Badge variant="neutral">{t('jobs.status_new')}</Badge>
    ) : (
      <Badge variant="primary">{t(`jobs.status_${job.status}`)}</Badge>
    )

  const applicantsText = applicantsLabel(job, t)
  const lowApplicants = isLowApplicants(job)

  const card = (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            {statusBadge}
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
          <h3 className="mt-2 text-base font-semibold text-foreground">{job.title}</h3>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <span>
              {job.company}
              {job.location && (
                <>
                  <span className="mx-1.5 text-muted-foreground/60">·</span>
                  {job.location}
                </>
              )}
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
                  <UserRound className="h-3.5 w-3.5" />
                </a>
              ) : (
                <span
                  title={`${t('jobs.recruiterIconLabel')} ${job.recruiter_name}`}
                  className="text-muted-foreground/70"
                >
                  <UserRound className="h-3.5 w-3.5" />
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
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => onToggleFavorite(job)}
            aria-label={job.is_favorite ? t('jobs.unfavorite') : t('jobs.favorite')}
            aria-pressed={job.is_favorite}
            className="text-muted-foreground hover:text-rose-500"
          >
            <Heart className={`h-5 w-5 ${job.is_favorite ? 'fill-rose-500 text-rose-500' : ''}`} />
          </button>
          {job.score != null && (
            <div
              className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-xl font-bold tabular-nums ${SCORE_STYLE[job.score]}`}
            >
              {job.score}
            </div>
          )}
        </div>
      </div>

      {job.score_gaps?.length > 0 && (
        <div className="rounded-md bg-secondary px-3 py-2">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('jobs.gaps')}
          </p>
          <ul className="flex flex-col gap-1 text-sm text-foreground">
            {job.score_gaps.slice(0, 4).map((item, index) => (
              <li key={index} className="flex gap-1.5">
                <span className="shrink-0 text-destructive">−</span>
                <span className="line-clamp-1">{scoreItemLabel(item)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2">
          <Button asChild variant="secondary" size="sm">
            <Link to={`/jobs/${job.id}`}>{t('jobs.details')}</Link>
          </Button>
          {onSwipe && (
            <Button type="button" variant="ghost" size="sm" onClick={() => onSwipe(job)}>
              {swipeLabel}
            </Button>
          )}
        </div>
        <Button
          type="button"
          size="sm"
          disabled={generating || job.cv_generation_in_progress}
          onClick={() => onGenerateCv(job)}
        >
          {generating || job.cv_generation_in_progress
            ? t('jobs.generating')
            : job.cv_pdf_url
              ? t('jobs.regenerateCv')
              : t('jobs.generateCv')}
        </Button>
      </div>
    </div>
  )

  if (!onSwipe) return card

  return (
    <SwipeToArchive onSwipe={() => onSwipe(job)} actionLabel={swipeLabel}>
      {card}
    </SwipeToArchive>
  )
}
