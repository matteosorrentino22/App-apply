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

// Wrapper minimo su fetch: aggiunge il token DRF se presente, invia i cookie
// di sessione (fallback per il login Google via django-allauth, Sprint 18)
// e normalizza gli errori in ApiError. Percorsi relativi (`/api/...`): in
// dev il proxy di Vite li inoltra al backend, in produzione Caddy fa da
// reverse proxy sullo stesso host — nessuna configurazione di base URL.
export async function apiFetch(path, { method = 'GET', body, isMultipart = false } = {}) {
  const headers = {}
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
    credentials: 'include',
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

  if (!response.ok) {
    throw new ApiError(response.status, data)
  }
  return data
}
