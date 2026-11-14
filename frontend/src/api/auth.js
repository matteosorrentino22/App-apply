import { apiFetch, getToken, setToken } from './client'
import { currentPushSubscription } from '../lib/push'
import { browserTimeZone } from '../utils/date'

// Con la verifica dell'email attiva (Sprint 67) la registrazione non
// restituisce un token: `verification_required` dice alla PWA di mostrare
// "controlla la tua email" invece di entrare nell'app.
export async function register({ email, password, inviteCode = '', language, consents }) {
  const data = await apiFetch('/api/accounts/register/', {
    method: 'POST',
    body: {
      email,
      password,
      invite_code: inviteCode,
      interface_language: language,
      // Sprint 70: fuso del dispositivo come default dell'account.
      timezone: browserTimeZone(),
      accept_privacy: consents.privacy,
      accept_terms: consents.terms,
      confirm_age: consents.age,
    },
  })
  if (data.token) setToken(data.token)
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
// Sprint 70: il dispositivo smette anche di ricevere le notifiche push
// dell'account, sul server (endpoint mandato al logout) e nel browser.
export async function logout() {
  const subscription = await currentPushSubscription()
  if (getToken()) {
    try {
      await apiFetch('/api/accounts/logout/', {
        method: 'POST',
        body: subscription ? { push_endpoint: subscription.endpoint } : {},
      })
    } catch {
      // ignorato: il token locale viene rimosso in ogni caso
    }
  }
  setToken(null)
  if (subscription) {
    try {
      await subscription.unsubscribe()
    } catch {
      // sottoscrizione già scaduta o rimossa dal browser
    }
  }
}

export function fetchMe() {
  return apiFetch('/api/accounts/me/')
}

export function updateMe(payload) {
  return apiFetch('/api/accounts/me/', { method: 'PATCH', body: payload })
}

export function acceptLegal(consents) {
  return apiFetch('/api/accounts/legal-acceptance/', {
    method: 'POST',
    body: { accept_privacy: consents.privacy, accept_terms: consents.terms, confirm_age: consents.age },
  })
}

export function verifyEmail(token) {
  return apiFetch('/api/accounts/verify-email/', { method: 'POST', body: { token } })
}

export function resendVerification(email) {
  return apiFetch('/api/accounts/verify-email/resend/', { method: 'POST', body: { email } })
}

export function requestPasswordReset(email) {
  return apiFetch('/api/accounts/password-reset/', { method: 'POST', body: { email } })
}

export function confirmPasswordReset(uid, token, newPassword) {
  return apiFetch('/api/accounts/password-reset/confirm/', {
    method: 'POST',
    body: { uid, token, new_password: newPassword },
  })
}

// Il backend revoca tutti i token e ne restituisce uno nuovo per questo
// dispositivo: lo si salva subito, altrimenti la chiamata successiva è 401.
export async function changePassword(oldPassword, newPassword) {
  const data = await apiFetch('/api/accounts/password/change/', {
    method: 'POST',
    body: { old_password: oldPassword, new_password: newPassword },
  })
  setToken(data.token)
  return data
}

export async function deleteAccount(password) {
  await apiFetch('/api/accounts/delete/', { method: 'POST', body: { password, confirm: true } })
  setToken(null)
}

// Cambio dell'email di accesso (Sprint 70): il backend invia il link di
// conferma al nuovo indirizzo; l'email cambia solo alla conferma.
export function requestEmailChange(password, newEmail) {
  return apiFetch('/api/accounts/email/change/', {
    method: 'POST',
    body: { password, new_email: newEmail },
  })
}

export function confirmEmailChange(token) {
  return apiFetch('/api/accounts/email/change/confirm/', { method: 'POST', body: { token } })
}

// URL firmato (10 minuti) dello ZIP: si apre come un normale download.
export async function requestDataExport() {
  const data = await apiFetch('/api/accounts/export/', { method: 'POST' })
  return data.url
}

// Login Google (django-allauth, §3.7 tecniche): navigazione a piena pagina
// verso l'endpoint standard di allauth. Non configurato in produzione: dallo
// Sprint 66 l'API accetta solo token (niente SessionAuthentication), il
// collegamento sessione→token è da fare quando il login Google verrà attivato.
// Dallo Sprint 67 il pulsante compare solo se GET /api/legal/ riporta
// `google_login_enabled` (GOOGLE_OAUTH_CLIENT_ID valorizzato).
export function googleLoginUrl() {
  return '/accounts/google/login/?process=login'
}
