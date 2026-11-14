# Sprint 62 — Decisioni accetta/rifiuta della chat persistite lato server

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `ecc38b4`

## Input
Il committente segnala che il bug dello Sprint 59 persiste: dopo aver
accettato/rifiutato una proposta, riaprendo la chat "in un secondo
momento" i pulsanti Accetta/Rifiuta tornano attivi.

## Decisioni prese
- Il fix `8c304ef` (pannello sempre montato) copriva solo chiudi/riapri
  nella stessa sessione sulla pagina; con un reload la decisione, tenuta
  solo nello stato React, andava persa. La decisione va salvata sul server,
  dentro l'azione stessa in `chat_history`.
- La registrazione della decisione non applica né annulla nulla sul
  `content_json`: l'applicazione resta responsabilità del frontend (via
  autosave).
- Se la chiamata di registrazione fallisce, la card resta comunque
  disabilitata per la sessione; nessun retry (rischio residuo giudicato
  minimo).

## Implementazione

### Backend
- `draft_chat.py`: nuova `record_action_decision(job, message_index,
  action_index, decision)`; valida `decision ∈ {"accepted","rejected"}`,
  che il messaggio esista e sia di ruolo `assistant` e che l'indice azione
  sia nel range (`InvalidChatDecision` altrimenti); scrive
  `actions[i]["decision"]` e salva.

### API
- `PATCH /api/jobs/<id>/cv-draft/chat/` con
  `{message_index, action_index, decision}` → 204; 400 se indici non
  interi o decisione/indici non validi.

### Frontend
- `api/jobs.js`: `recordCvDraftChatDecision`.
- `CvDraftChatPanel.jsx`: al caricamento della cronologia inizializza lo
  stato `decisions` dal campo `decision` salvato in ogni azione;
  `handleDecide` aggiorna lo stato locale, applica l'azione se accettata e
  invia il PATCH.

## Verifica
- PATCH + GET verificati sia a livello di funzione sia via HTTPS: la
  decisione risulta in `chat_history` e il GET la restituisce.
- Suite `apps.cv` 49/49; build frontend con verifica dell'hash servito.

## Note / cosa manca
- Nessun test automatico per `record_action_decision` / PATCH.
- Lo storico non riporta una conferma del committente dopo questo fix: la
  sessione riprende il 20/10 con la cover letter (Sprint 63).
