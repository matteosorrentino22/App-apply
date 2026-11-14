import { UserRound } from 'lucide-react'
import { useLanguage } from '../i18n/LanguageContext'
import { cn } from '@/lib/utils'

// Icona del recruiter (DESIGN.md §5, SPEC-DELTA A7): cerchietto su
// --primary-soft accanto alla località, quando l'annuncio ha un recruiter;
// link al suo profilo se disponibile (come prima dello Sprint 74). Sta sopra
// il link "stirato" della card (relative z-10), così resta cliccabile.
export default function RecruiterIcon({ job, className }) {
  const { t } = useLanguage()
  if (!job.recruiter_name) return null
  const label = `${t('jobs.recruiterIconLabel')} ${job.recruiter_name}`
  const classes = cn(
    'relative z-10 ml-1.5 inline-flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded-full bg-primary-soft align-middle text-primary',
    className,
  )
  const icon = <UserRound className="h-3.5 w-3.5" strokeWidth={2.2} aria-hidden="true" />
  return job.recruiter_profile_url ? (
    <a href={job.recruiter_profile_url} target="_blank" rel="noreferrer" title={label} aria-label={label} className={classes}>
      {icon}
    </a>
  ) : (
    <span role="img" title={label} aria-label={label} className={classes}>
      {icon}
    </span>
  )
}
