// Ultima query string della lista job (sezione e filtri, Sprint 68): la
// scrive JobListPage, la legge il link "Torna alla lista" del dettaglio.
// Solo stato dell'interfaccia della scheda corrente, nessun dato.
export const JOB_LIST_SEARCH_STORAGE_KEY = 'app_apply_job_list_search'

export function jobListHref() {
  return `/list${sessionStorage.getItem(JOB_LIST_SEARCH_STORAGE_KEY) || ''}`
}
