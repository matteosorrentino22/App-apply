import { currentLanguage } from '../i18n/language'

const TOKEN_STORAGE_KEY = 'app_apply_token'

export function getToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  }
}

export class ApiError extends Error {
  constructor(status, data) {
    super((data && data.detail) || 'Errore di rete')
    this.status = status
    this.data = data
  }
}

// Evento emesso quando il backend rifiuta il token (401: sessione scaduta
// per inattività o revocata, Sprint 66): AuthContext lo ascolta e riporta
// l'utente al login.
export const AUTH_EXPIRED_EVENT = 'app-apply:auth-expired'
// Evento emesso quando il backend risponde 403 `legal_acceptance_required`
// (Sprint 67: nuova versione di informativa/termini non ancora accettata):
// AuthContext ricarica l'utente e la PWA mostra la schermata di accettazione.
export const LEGAL_REQUIRED_EVENT = 'app-apply:legal-required'

// Wrapper minimo su fetch: aggiunge il token se presente e la lingua
// dell'interfaccia (`Accept-Language`, Sprint 71: messaggi del backend in
// it/en) e normalizza gli errori in ApiError. Percorsi relativi (`/api/...`): in dev il proxy di
// Vite li inoltra al backend, in produzione Caddy fa da reverse proxy sullo
// stesso host — nessuna configurazione di base URL.
export async function apiFetch(path, { method = 'GET', body, isMultipart = false } = {}) {
  const headers = { 'Accept-Language': currentLanguage() }
  const token = getToken()
  if (token) {
    headers.Authorization = `Token ${token}`
  }
  if (!isMultipart && body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : isMultipart ? body : JSON.stringify(body),
  })

  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (response.status === 401 && token) {
    setToken(null)
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
  }
  if (response.status === 403 && data?.code === 'legal_acceptance_required') {
    window.dispatchEvent(new Event(LEGAL_REQUIRED_EVENT))
  }
  if (!response.ok) {
    throw new ApiError(response.status, data)
  }
  return data
}
