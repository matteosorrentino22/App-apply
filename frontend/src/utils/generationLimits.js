// Limiti dei testi liberi inviati alle generazioni del dettaglio job, uguali
// ai `max_length` del server (backend/apps/jobs/serializers.py): il campo li
// rispetta da solo (maxLength) e un contatore li mostra (Sprint 75).
export const MAX_INSTRUCTIONS_LENGTH = 2000
export const MAX_RECIPIENT_NAME_LENGTH = 255
export const MAX_RECIPIENT_LINKEDIN_URL_LENGTH = 500

// Indicazioni passate selezionate + testo nuovo, come le invia la pagina
// (stesso formato di prima: blocchi separati da una riga vuota).
export function joinInstructions(selected, text) {
  return [...selected, text.trim()].filter(Boolean).join('\n\n')
}
