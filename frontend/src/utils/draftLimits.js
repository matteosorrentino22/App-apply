// Limiti delle bozze uguali a quelli del server
// (backend/apps/cv/draft_validation.py, backend/apps/jobs/serializers.py):
// l'editor li mostra (pulsanti "Aggiungi" disattivati con il motivo,
// contatore della chat, maxLength dei campi semplici) senza cambiarli
// (Sprint 76).
export const CV_LIMITS = {
  areas: 20,
  bulletsPerExperience: 30,
  educations: 20,
  languages: 30,
  educationText: 300,
  educationDates: 100,
}
export const COVER_LETTER_LIMITS = { paragraphs: 15, paragraphText: 3000 }
export const MAX_CHAT_MESSAGE_LENGTH = 2000

// Testo semplice di un campo con marcatori **grassetto** (riassunto della
// sezione chiusa).
export function plainText(value) {
  return (value || '').replace(/\*\*/g, '')
}
