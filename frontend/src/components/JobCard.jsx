import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import SwipeToArchive from '@/components/SwipeToArchive'
import { useLanguage } from '../i18n/LanguageContext'

const SCORE_STYLE = {
  1: 'bg-score-1-soft text-score-1',
  2: 'bg-score-2-soft text-score-2',
  3: 'bg-score-3-soft text-score-3',
  4: 'bg-score-4-soft text-score-4',
  5: 'bg-score-5-soft text-score-5',
}

export default function JobCard({ job, onSwipe, swipeLabel, onGenerateCv, generating }) {
  const { t } = useLanguage()

  const statusBadge =
    job.status === 'new' ? (
      <Badge variant="neutral">{t('jobs.status_new')}</Badge>
    ) : (
      <Badge variant="primary">{t(`jobs.status_${job.status}`)}</Badge>
    )

  const card = (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          {statusBadge}
          <h3 className="mt-2 text-base font-semibold text-foreground">{job.title}</h3>
          <p className="text-sm text-muted-foreground">
            {job.company}
            {job.location && (
              <>
                <span className="mx-1.5 text-muted-foreground/60">·</span>
                {job.location}
              </>
            )}
          </p>
        </div>
        {job.score != null && (
          <div
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-xl font-bold tabular-nums ${SCORE_STYLE[job.score]}`}
          >
            {job.score}
          </div>
        )}
      </div>

      {job.score_reasoning && (
        <p className="line-clamp-2 rounded-md bg-secondary px-3 py-2 text-sm text-foreground">
          {job.score_reasoning}
        </p>
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
            : job.status === 'new'
              ? t('jobs.generateCv')
              : t('jobs.regenerateCv')}
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
