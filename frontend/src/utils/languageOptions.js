import { translations } from '../i18n/translations'

// Opzioni per i menu a tendina di lingua/livello nel profilo (Sprint 41):
// stessi codici validati lato server (apps.profiles.language_options),
// etichette solo it/en perché l'interfaccia supporta solo queste due lingue.
export function getLanguageNameOptions(lang) {
  return Object.entries(translations[lang].languageNames)
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label))
}

// Ordine di inserimento (non alfabetico): riflette una progressione
// elementary → intermediate → fluent → mother_tongue.
export function getLanguageLevelOptions(lang) {
  return Object.entries(translations[lang].languageLevels).map(([value, label]) => ({ value, label }))
}
