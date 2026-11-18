// Valori dei filtri della lista job (Sprint 74): condivisi tra la pagina
// (lettura della query string) e il pannello dei filtri.
export const SCORES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
export const STATUSES = ['new', 'cv_generated', 'application_done']
export const APPLICANTS_RANGES = ['under_25', '25_50', '51_100', '101_200', 'over_200']
// Sprint 82 (SPEC-DELTA A16): contratti proposti nel pannello Filtri (il
// server ne conosce altri: A contratto, Stage, Volontariato, Altro, che si
// vedono nel dettaglio ma non si filtrano). Stipendio: tutti / con / senza.
export const CONTRACT_TYPES = ['full_time', 'part_time', 'temporary']
export const SALARY_VALUES = ['yes', 'no']
// Sprint 84 (A18): modalità di lavoro del job, ricavata dall'AI.
export const WORK_MODES = ['remote', 'hybrid', 'on_site', 'not_indicated']
