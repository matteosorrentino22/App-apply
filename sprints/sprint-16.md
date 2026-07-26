# Sprint 16 — Candidatura

## Input
- Sprint 15 (stati job); `User.last_activity_reset` (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.10, §4.12 (parte inattività).

## Obiettivo
Endpoint per marcare un job come "candidatura fatta" (consentito solo se esiste già un CV per quel job), con aggiornamento di `date_application_done` e reset di `User.last_activity_reset`.

## Risultato atteso
Un job con CV generato può essere marcato come candidatura fatta; un job senza CV non può esserlo; la marcatura azzera il timer di inattività dell'utente.

## Criteri di verifica
- Marcare come "candidatura fatta" un Job in stato `cv_generated` → successo, `status='application_done'`, `date_application_done` valorizzato.
- Marcare come "candidatura fatta" un Job in stato `new` (senza CV) → richiesta rifiutata.
- Dopo la marcatura, `User.last_activity_reset` risulta aggiornato all'istante della richiesta (confrontabile con il valore precedente).

## Output per lo sprint successivo
`User.last_activity_reset` aggiornato correttamente, consumato dal task di notifica di inattività (Sprint 17).