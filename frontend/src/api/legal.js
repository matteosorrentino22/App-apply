import { apiFetch } from './client'

// Dati pubblici delle pagine legali (Sprint 67): versioni e date, titolare
// del trattamento, flag per login Google e invio email. Una sola richiesta
// per sessione della PWA: cambiano solo con un deploy.
let cached = null

export function fetchLegalInfo() {
  if (!cached) {
    cached = apiFetch('/api/legal/').catch((error) => {
      cached = null
      throw error
    })
  }
  return cached
}
