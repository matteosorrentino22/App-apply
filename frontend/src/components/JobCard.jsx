import { Link } from 'react-router-dom'
import { Heart, Star } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { ScoreChip } from '@/components/ui/score-chip'
import SwipeToArchive from '@/components/SwipeToArchive'
import RecruiterIcon from '@/components/RecruiterIcon'
import { useLanguage } from '../i18n/LanguageContext'
import { scoreItemLabel } from '../utils/scoreItems'
import { formatShortDate } from '../utils/date'
import { applicantsLabel, isLowApplicants } from '../utils/applicants'

const VISIBLE_GAPS = 2

// Card ridotta della lista (Sprint 74, mockup `jobs-lista`, SPEC-DELTA A2/A7):
// stato e candidati, titolo, azienda · località con icona del recruiter, i
// primi 2 gap, data e cuoricino. Tutta la card porta al dettaglio (link
// "stirato" sul titolo); il cuoricino e il profilo del recruiter restano
// controlli separati. Niente più Dettagli / Archivia / Genera CV: si genera
// dal dettaglio, si archivia con lo swipe (e dal dettaglio dallo Sprint 75).
export default function JobCard({ job, onSwipe, swipeLabel, onToggleFavorite }) {
  const { t, lang } = useLanguage()

  const applicantsText = applicantsLabel(job, t)
  const gaps = job.score_gaps || []
  const hiddenGaps = gaps.length - VISIBLE_GAPS

  const card = (
    <article className="relative flex flex-col gap-3 rounded-card border border-border bg-card p-4 shadow-card outline-none has-[a[data-card-link]:focus-visible]:ring-3 has-[a[data-card-link]:focus-visible]:ring-ring/30">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant={job.status === 'new' ? 'neutral' : 'primary'}>{t(`jobs.status_${job.status}`)}</Badge>
            {job.is_wish_match ? (
              <Badge variant="wish" className="gap-1" data-testid="job-wish-badge">
                <Star className="h-3 w-3 fill-current" aria-hidden="true" />
                {t('jobs.wishBadge')}
              </Badge>
            ) : null}
            {applicantsText && <Badge variant={isLowApplicants(job) ? 'success' : 'neutral'}>{applicantsText}</Badge>}
          </div>
          <h3 className="text-base leading-snug font-[650] text-foreground">
            <Link
              to={`/jobs/${job.id}`}
              data-card-link
              draggable={false}
              className="outline-none after:absolute after:inset-0 after:content-['']"
            >
              {job.title}
            </Link>
          </h3>
          <p className="text-sm text-muted-foreground">
            {job.company}
            {job.location && <> · {job.location}</>}
            <RecruiterIcon job={job} />
          </p>
        </div>
        {job.score != null && <ScoreChip score={job.score} />}
      </div>

      {gaps.length > 0 && (
        <div className="rounded-field bg-tint px-3.5 py-3">
          <p className="mb-1.5 text-xs font-bold uppercase tracking-[0.06em] text-muted-foreground">{t('jobs.gaps')}</p>
          <ul className="flex flex-col gap-1 text-[15px] leading-snug text-foreground">
            {gaps.slice(0, VISIBLE_GAPS).map((item, index) => (
              <li key={index} className="flex gap-2">
                <span className="shrink-0 font-bold text-destructive" aria-hidden="true">
                  —
                </span>
                <span className="line-clamp-2">{scoreItemLabel(item)}</span>
              </li>
            ))}
          </ul>
          {hiddenGaps > 0 && (
            <p className="mt-1.5 text-sm font-semibold text-primary">
              {hiddenGaps === 1 ? t('jobs.gapsMoreOne') : t('jobs.gapsMoreMany').replace('{count}', hiddenGaps)}
            </p>
          )}
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <p className="text-[13px] text-muted-foreground">
          {job.date_collected && (
            <>
              {t('jobs.importedOnPrefix')} {formatShortDate(job.date_collected, lang)}
            </>
          )}
        </p>
        <button
          type="button"
          onClick={() => onToggleFavorite(job)}
          aria-label={job.is_favorite ? t('jobs.unfavorite') : t('jobs.favorite')}
          aria-pressed={job.is_favorite}
          className="relative z-10 -m-2.5 flex h-11 w-11 items-center justify-center rounded-full text-primary outline-none hover:text-destructive focus-visible:ring-3 focus-visible:ring-ring/30"
        >
          <Heart className={`h-[22px] w-[22px] ${job.is_favorite ? 'fill-destructive text-destructive' : ''}`} aria-hidden="true" />
        </button>
      </div>
    </article>
  )

  if (!onSwipe) return card

  return (
    <SwipeToArchive onSwipe={() => onSwipe(job)} actionLabel={swipeLabel}>
      {card}
    </SwipeToArchive>
  )
}
