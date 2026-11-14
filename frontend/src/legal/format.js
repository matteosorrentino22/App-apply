// Helpers non-componente per i testi legali (Sprint 67).

export function normalizeLang(lang) {
  return lang === 'it' ? 'it' : 'en'
}

// "2026-11-14" -> "14 novembre 2026" / "14 November 2026"
export function formatLegalDate(date, lang) {
  if (!date) return ''
  const parsed = new Date(date + 'T00:00:00Z')
  if (Number.isNaN(parsed.getTime())) return date
  return new Intl.DateTimeFormat(lang === 'it' ? 'it-IT' : 'en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(parsed)
}
