// Data breve per badge non invasivi (es. "Importato: 5 set"): usa il fuso
// del browser, non quello del profilo — qui serve solo un'indicazione
// leggibile, non un confine esatto tra "oggi" e "ieri" (a differenza del
// filtro periodo lato backend, che segue il fuso dell'utente).
export function formatShortDate(isoString, lang) {
  if (!isoString) return ''
  return new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short' }).format(new Date(isoString))
}

// "Oggi" in formato YYYY-MM-DD. Sprint 70: nel fuso dell'utente (lo stesso
// che il backend usa per il filtro date della lista), non in quello del
// dispositivo; senza fuso, o con un nome non riconosciuto dal browser, si
// ripiega sulla data del dispositivo.
export function todayInputValue(timeZone) {
  if (timeZone) {
    try {
      // en-CA formatta le date come YYYY-MM-DD.
      return new Intl.DateTimeFormat('en-CA', {
        timeZone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date())
    } catch {
      // fuso non supportato dal browser: data del dispositivo
    }
  }
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function browserTimeZone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  } catch {
    return ''
  }
}

// Elenco IANA dal browser (Intl.supportedValuesOf, Safari 15.4+); i fusi
// passati in `extra` (quello salvato, quello del dispositivo) ci sono sempre.
export function timeZoneOptions(extra = []) {
  let zones = []
  try {
    zones = Intl.supportedValuesOf?.('timeZone') ?? []
  } catch {
    zones = []
  }
  return [...new Set([...zones, 'UTC', ...extra.filter(Boolean)])].sort()
}
