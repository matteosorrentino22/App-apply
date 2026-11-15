// Raccolta del giorno (Sprint 77): orari a quarti d'ora per la raccolta
// automatica e testo "già eseguita oggi alle HH:MM" nel fuso dell'utente
// (la quota è sul giorno di Europe/Rome, l'ora si mostra dove vive l'utente).
export const QUARTER_HOURS = Array.from({ length: 96 }, (_, index) => {
  const hours = String(Math.floor(index / 4)).padStart(2, '0')
  const minutes = String((index % 4) * 15).padStart(2, '0')
  return `${hours}:${minutes}`
})

function safeZone(timeZone) {
  try {
    new Intl.DateTimeFormat('en', { timeZone }).format(0)
    return timeZone
  } catch {
    return 'Europe/Rome'
  }
}

export function collectionDoneText(t, lang, doneAt, timeZone) {
  if (!doneAt) return t('home.collectDoneToday')
  const zone = safeZone(timeZone || 'Europe/Rome')
  const locale = lang === 'it' ? 'it-IT' : 'en-GB'
  const when = new Date(doneAt)
  const time = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit', timeZone: zone }).format(when)
  const day = (date) => new Intl.DateTimeFormat('en-CA', { timeZone: zone }).format(date)
  if (day(when) === day(new Date())) return t('home.collectDoneAt').replace('{time}', time)
  const date = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', timeZone: zone }).format(when)
  return t('home.collectDoneOn').replace('{date}', date).replace('{time}', time)
}

export function timeZoneLabel(t, timeZone) {
  return !timeZone || timeZone === 'Europe/Rome' ? t('home.autoCollectItalianTime') : timeZone
}
