import { ApiError } from '../api/client'

// DRF restituisce gli errori di validazione come {campo: [messaggi]}: senza
// questo, l'utente vede solo un messaggio generico senza sapere quale campo
// correggere (es. una data lasciata vuota in un formato che il backend non
// accetta).
export function formatApiErrorDetail(err) {
  if (!(err instanceof ApiError) || !err.data || typeof err.data !== 'object') return ''
  return Object.entries(err.data)
    .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(' ') : messages}`)
    .join(' — ')
}
