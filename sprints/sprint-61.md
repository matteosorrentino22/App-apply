# Sprint 61 — Il riferimento della chat punta singoli bullet

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `fc4603c`

## Input
Feedback sullo Sprint 60: il contesto deve riferirsi a una singola
attività/bullet, non all'intera esperienza. Il pulsante va sotto la spunta
attiva/disattiva di ogni bullet, con lo stesso simbolo "a stella" della
chat AI; l'etichetta di contesto va subito sopra il campo di testo della
chat, non sotto il titolo "Assistente bozza".

## Decisioni prese
- Il pulsante per bullet **sostituisce** quello per esperienza (nessun
  puntamento a livello di esperienza).
- Etichetta del contesto: estratto del testo del bullet (scelto dal
  committente rispetto ad "azienda + numero bullet"), per distinguere più
  bullet della stessa esperienza.
- Rischio accettato e segnalato: il puntamento è posizionale
  (`profile_experience_id` + indice del bullet); riordinare o eliminare
  bullet della stessa esperienza tra puntamento e invio può spostarlo sul
  bullet sbagliato. Nessuna contromisura.

## Implementazione

### Backend
- `draft_chat.py`: `focus_experience_ids` → `focus_bullets`
  (`[{profile_experience_id, bullet_index}]`). Riferimenti a esperienze o
  indici inesistenti vengono scartati; per gli altri il modello riceve un
  blocco "BULLET PUNTATI DALL'UTENTE" con `profile_experience_id`,
  `company`, `role`, `bullet_index`, `bullet_text`. Paragrafo del system
  prompt riscritto di conseguenza (aiuto per i casi ambigui, non vincolo
  assoluto).

### API
- `POST /api/jobs/<id>/cv-draft/chat/` accetta `focus_bullets` (solo
  oggetti con `profile_experience_id` e `bullet_index` interi).

### Frontend
- `CvDraftEditorPage.jsx`: stato `focusedBullets`
  (`[{profileExperienceId, bulletIndex}]`, non persistito); pulsante con
  icona `Sparkles` sotto la checkbox mostra/nascondi di ogni bullet,
  cumulabile anche tra esperienze diverse; rimosso il pulsante
  `MessageCircle` sulla scheda esperienza.
- `CvDraftChatPanel.jsx`: riga "Contesto:" spostata sopra la textarea, con
  chip dell'estratto (40 caratteri) di ciascun bullet puntato.
- `api/jobs.js`: `sendCvDraftChatMessage(id, message, focusedBullets)`
  converte in snake_case.

## Verifica
- Prova dal vivo: puntato il secondo bullet di un'esperienza con 14
  bullet e chiesto di renderlo più sintetico senza nominare l'azienda: il
  modello ha modificato esattamente quel bullet.
- Suite `apps.cv` 49/49; build frontend con verifica dell'hash servito.

## Note / cosa manca
- Il rischio posizionale descritto sopra resta aperto.
