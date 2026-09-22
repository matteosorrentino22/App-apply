// Data breve per badge non invasivi (es. "Importato: 5 set"): usa il fuso
// del browser, non quello del profilo — qui serve solo un'indicazione
// leggibile, non un confine esatto tra "oggi" e "ieri" (a differenza del
// filtro periodo lato backend, che segue il fuso dell'utente).
export function formatShortDate(isoString, lang) {
  if (!isoString) return ''
  return new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short' }).format(new Date(isoString))
}

export function todayInputValue() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
