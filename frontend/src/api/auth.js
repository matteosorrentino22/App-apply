import { apiFetch, getToken, setToken } from './client'

export async function register(email, password, inviteCode = '') {
  const data = await apiFetch('/api/accounts/register/', {
    method: 'POST',
    body: { email, password, invite_code: inviteCode },
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

// Revoca il token lato server (Sprint 66); il token locale si cancella
// comunque, anche se la chiamata fallisce (rete assente, token già scaduto).
export async function logout() {
  if (getToken()) {
    try {
      await apiFetch('/api/accounts/logout/', { method: 'POST' })
    } catch {
      // ignorato: il token locale viene rimosso in ogni caso
    }
  }
  setToken(null)
}

export function fetchMe() {
  return apiFetch('/api/accounts/me/')
}

export function updateMe(payload) {
  return apiFetch('/api/accounts/me/', { method: 'PATCH', body: payload })
}

// Login Google (django-allauth, §3.7 tecniche): navigazione a piena pagina
// verso l'endpoint standard di allauth. Non configurato in produzione: dallo
// Sprint 66 l'API accetta solo token (niente SessionAuthentication), il
// collegamento sessione→token è da fare quando il login Google verrà attivato.
export function googleLoginUrl() {
  return '/accounts/google/login/?process=login'
}
