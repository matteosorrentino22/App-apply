import { apiFetch, setToken } from './client'

export async function register(email, password) {
  const data = await apiFetch('/api/accounts/register/', {
    method: 'POST',
    body: { email, password },
  })
  setToken(data.token)
  return data
}

export async function login(email, password) {
  const data = await apiFetch('/api/accounts/login/', {
    method: 'POST',
    body: { email, password },
  })
  setToken(data.token)
  return data
}

export function logout() {
  setToken(null)
}

export function fetchMe() {
  return apiFetch('/api/accounts/me/')
}

export function updateMe(payload) {
  return apiFetch('/api/accounts/me/', { method: 'PATCH', body: payload })
}

// Login Google (django-allauth, §3.7 tecniche): nessun flusso OAuth custom,
// solo una navigazione a piena pagina verso l'endpoint standard di allauth.
// Al ritorno l'utente è autenticato via cookie di sessione (Django), già
// supportato da SessionAuthentication lato API (settings.py) — nessun
// token DRF necessario per questo percorso.
export function googleLoginUrl() {
  return '/accounts/google/login/?process=login'
}
