// `applicants_bucket` e `applicants_count` sono mutualmente esclusivi (vedi
// commento sul campo in backend/apps/jobs/models.py): quando LinkedIn non
// mostra un numero esatto, mostra una delle due fasce testuali agli estremi.
export function applicantsLabel(job, t) {
  if (job.applicants_bucket === 'under_25') return t('jobs.applicantsUnder25Badge')
  if (job.applicants_bucket === 'over_200') return t('jobs.applicantsOver200Badge')
  if (job.applicants_count != null) return `${job.applicants_count} ${t('jobs.applicantsCountSuffix')}`
  return null
}

// Sotto i 25 candidati è il segnale più interessante per l'utente (poca
// concorrenza): va evidenziato in modo diverso dalle altre fasce.
export function isLowApplicants(job) {
  return job.applicants_bucket === 'under_25' || (job.applicants_count != null && job.applicants_count < 25)
}
