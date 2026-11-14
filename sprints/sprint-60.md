# Sprint 60 — Riferimento esplicito alle esperienze dalla chat AI

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `536b34e`

## Input
Il committente chiede una soluzione perché dalla chat si possa far
riferimento facilmente a specifiche esperienze, e quali opzioni esistono.

## Decisioni prese
- Opzioni presentate: (A) nessuna modifica, solo testo libero;
  (B) selettore di contesto a tendina sopra l'input della chat
  (consigliata); (C) @mention con autocompletamento nel messaggio;
  (D) pulsante diretto su ogni scheda esperienza dell'editor.
- Scelta del committente: **solo D**, con selezione cumulabile su più
  schede; la chat deve restare aperta mentre si clicca sulle schede;
  pulsante senza testo, solo icona, sotto la spunta "Mostra nel CV".
- Il riferimento è un aiuto per risolvere pronomi e frasi generiche, non
  un vincolo assoluto: se il testo nomina chiaramente un'altra azienda, il
  modello segue il testo.

## Implementazione

### Backend
- `draft_chat.py`: `_build_user_content` e `send_chat_message` accettano
  `focus_experience_ids`; le esperienze corrispondenti della bozza vengono
  passate al modello in un blocco "ESPERIENZE PUNTATE DALL'UTENTE"; nuovo
  paragrafo del system prompt con la regola sopra.

### API
- `POST /api/jobs/<id>/cv-draft/chat/` accetta `focus_experience_ids`
  (lista; tenuti solo gli interi).

### Frontend
- `CvDraftEditorPage.jsx`: stato `focusedExperienceIds` (non persistito,
  si azzera lasciando la pagina); pulsante icona (`MessageCircle`) sotto
  la spunta "Mostra nel CV" di ogni scheda, evidenziato quando attivo.
- `CvDraftChatPanel.jsx`: etichetta "Contesto:" con i nomi azienda delle
  esperienze puntate, sotto il titolo del pannello; **rimosso l'overlay a
  tutta pagina** (presente dallo Sprint 59; il fix `faea846` gli aveva
  aggiunto la chiusura al clic sullo sfondo): ora il pannello è un drawer
  laterale fisso e si chiude solo con la X.
- `api/jobs.js`: `sendCvDraftChatMessage(id, message, focusExperienceIds)`.
- i18n: `cvEditor.chatFocusToggle`, `cvEditor.chatFocusLabel` (it/en).

## Verifica
- Prova dal vivo: istruzione generica senza nome azienda risolta
  sull'esperienza puntata; puntando un'esperienza non pertinente alla
  richiesta, il modello lo ha segnalato e non ha inventato contenuto.
- Suite `apps.cv` 49/49; build frontend con verifica dell'hash del bundle
  servito.

## Note / cosa manca
- Superato poche ore dopo dallo Sprint 61: il committente voleva il
  riferimento al singolo bullet, non all'intera esperienza.
