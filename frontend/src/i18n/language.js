// Lingua dell'interfaccia (it/en) fuori da React (Sprint 71): l'API la
// riceve in `Accept-Language` a ogni chiamata (api/client.js), così i testi
// del backend (errori, validazioni) arrivano nella stessa lingua della PWA.
// Stessa regola di LanguageContext: scelta salvata, altrimenti dispositivo.
export const LANG_STORAGE_KEY = 'app_apply_lang'

export const SUPPORTED_LANGUAGES = ['it', 'en']

export function detectDeviceLanguage() {
  const raw = (typeof navigator !== 'undefined' && navigator.language) || 'en'
  return raw.toLowerCase().startsWith('it') ? 'it' : 'en'
}

export function readStoredLanguage() {
  const stored = localStorage.getItem(LANG_STORAGE_KEY)
  return SUPPORTED_LANGUAGES.includes(stored) ? stored : null
}

export function currentLanguage() {
  return readStoredLanguage() || detectDeviceLanguage()
}
