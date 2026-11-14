# Sprint 59 — Chat AI nell'editor CV (Fase 2) con pattern proposta/conferma

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `9be1947` (+ fix `faea846`, `8c304ef`)

## Input
Il committente, soddisfatto di Fase 1 e ritocchi grafici, chiede come verrà
integrata l'AI che aiuta a modificare tutti i testi del CV, prima di
svilupparla. Dallo Sprint 51 restavano fissati: pattern "la chat propone,
l'utente conferma" e grounding coerente con il resto dell'app, con
possibilità di amplificare su richiesta esplicita.

## Decisioni prese
- Pannello di chat apribile sopra l'editor esistente (additivo, layout di
  Fase 1 invariato); una conversazione unica per bozza, non per campo.
- A ogni messaggio il modello riceve l'intero `content_json` della bozza
  (con gli id interni, es. `profile_experience_id`), l'offerta e la
  cronologia.
- Ogni risposta = testo + elenco di **azioni puntuali distinte**, ciascuna
  mostrata come card "prima → dopo" con Accetta/Rifiuta. Mai applicate in
  automatico: accettare richiama le stesse funzioni di stato dell'editor
  manuale (autosave e anteprima invariati, nessun endpoint di
  applicazione).
- Cronologia persistita nella bozza.
- Grounding (confermato dal committente): testo narrativo amplificabile
  solo su richiesta esplicita dell'utente; skills/certifications sempre
  vincolate al profilo reale, **nessuna eccezione** neppure su richiesta
  esplicita (stessa linea del "colma i gap").
- Costo (scelto dal committente tra: credito per messaggio / N messaggi
  gratuiti / incluso): **ogni messaggio scala credito extra**, nessun
  massimale giornaliero né messaggi gratuiti.

## Implementazione

### Modello dati
- `CVDraft.chat_history` (JSONField, default `[]`): lista di turni
  `{role: "user"|"assistant", message, actions?}`. Migrazione
  `cv/0007_cvdraft_chat_history`.
- `RunLog.TaskType.CV_DRAFT_CHAT = "cv_draft_chat"`. Migrazione
  `jobs/0013_alter_runlog_task_type`.

### Backend
- Nuovo `apps/cv/draft_chat.py`:
  - `CHAT_ACTION_TYPES` (16 tipi): `update_summary`,
    `update_qualification`, `update_role`, `update_bullet`, `add_bullet`,
    `hide_bullet`, `show_bullet`, `hide_experience`, `show_experience`,
    `update_area`, `add_area`, `remove_area`, `toggle_skill`,
    `toggle_certification`, `update_education_notes`,
    `update_language_level`.
  - `CHAT_ACTION_SCHEMA` "piatto" (un oggetto con `type` + campi nullable
    `profile_experience_id`, `bullet_index`, `area_index`,
    `education_index`, `language_index`, `text`, `name`, `level`), senza
    `oneOf`, per compatibilità con il tool-use forzato su Bedrock;
    `CHAT_SCHEMA = {reply, actions[]}`.
  - `CHAT_SYSTEM_PROMPT`: niente applicazione diretta; domanda senza
    richiesta di modifica → nessuna azione; regole di grounding; semantica
    di ogni azione; indici 0-based sulla posizione nell'elenco fornito.
  - `_sanitize_actions`: filtro difensivo lato server che scarta toggle
    skill/certification con nome non presente nel profilo e livelli lingua
    fuori da `elementary/intermediate/fluent/mother_tongue`.
  - `send_chat_message`: riserva `PRICE_CV_DRAFT_CHAT_MESSAGE` dal credito
    (`ChatMessageRejected` se insufficiente), chiama
    `call_claude_structured` (modello `BEDROCK_CV_GENERATION_MODEL`,
    `max_tokens=2000`, `effort="medium"`); su errore rimborsa, scrive un
    `RunLog` di fallimento e solleva `ChatMessageFailed`; su successo
    accoda turno utente + risposta in `chat_history`. Non modifica mai
    `content_json`.
- `config/settings.py` e `.env.example`: `PRICE_CV_DRAFT_CHAT_MESSAGE`
  (default 0.20 €).

### API
- `GET /api/jobs/<id>/cv-draft/chat/` → `{history}` (404 senza bozza).
- `POST /api/jobs/<id>/cv-draft/chat/` con `{message}` → `{reply, actions}`;
  400 messaggio vuoto, 402 credito insufficiente, 502 errore AI.

### Frontend
- Nuovo `CvDraftChatPanel.jsx`: cronologia, card azione con etichetta,
  "prima" e "dopo" calcolati dallo stato corrente della bozza
  (`describeAction`), pulsanti Accetta/Rifiuta, invio con Invio
  (Shift+Invio per andare a capo), messaggi di errore per credito
  insufficiente / errore generico.
- `CvDraftEditorPage.jsx`: `applyChatAction` mappa ogni tipo di azione
  sulle funzioni di stato esistenti (`setField`, `updateExperience`,
  `updateBullet`, `addBullet`, `updateArea`, `addArea`, `removeArea`,
  `toggleSkill`, `toggleCertification`, `updateEducation`,
  `updateLanguage`); `addBullet`/`addArea` accettano un testo iniziale.
- `api/jobs.js`: `fetchCvDraftChat`, `sendCvDraftChatMessage`.
- Chiavi i18n `cvEditor.chat*` (it/en).

### Fix `faea846` (stesso giorno)
- Le etichette mostravano la chiave grezza (es. `cvEditor.chat.reject`):
  il componente usava percorsi annidati, `translations.js` chiavi piatte
  (`cvEditor.chatReject`). Allineati tutti i lookup.
- Restyling su richiesta del committente: pulsante di apertura da inline
  accanto al titolo a FAB in basso a destra (icona `Sparkles`, "Chiedi
  all'AI"); pannello con bordo arrotondato e chiusura cliccando sullo
  sfondo; card con "prima" rosso barrato e "dopo" verde, stile diff.
- Primo deploy del fix inefficace: il bundle era stato ricostruito da
  un'immagine frontend non aggiornata; rifatto con verifica dell'hash del
  bundle servito.

### Fix `8c304ef` (stesso giorno)
- Bug segnalato: chiudendo e riaprendo la chat, le azioni già accettate
  avevano di nuovo Accetta/Rifiuta attivi (rischio di riapplicarle, es.
  bullet duplicato). Causa: il pannello era montato con
  `{chatOpen && <CvDraftChatPanel/>}` e perdeva lo stato. Ora resta sempre
  montato (prop `open`, `if (!open) return null` dopo gli hook). Copriva
  solo la stessa sessione sulla pagina (→ Sprint 62).

## Verifica
- Prove dirette in produzione: sommario condensato su richiesta; richiesta
  di aggiungere una skill non presente nel profilo rifiutata dal modello e
  spiegata in chat; cronologia persistita dopo ricarica; GET/POST testati
  via HTTPS.
- Suite `apps.cv` 49/49. Un'esecuzione di `apps.cv apps.jobs` con la
  configurazione di produzione ha dato 22 fallimenti + 2 errori nei test
  API di `apps.jobs`, tutti con risposta 301 (redirect) al posto dell'atteso:
  giudicati non legati alla chat e non approfonditi.
- Lint e build frontend puliti.

## Note / cosa manca
- Nessun test automatico per `draft_chat.py` né per l'endpoint chat.
- Nessun `RunLog` per i messaggi riusciti (solo per i fallimenti).
- Al modello si passa la cronologia senza le azioni proposte né le
  decisioni prese; lo stato effettivo arriva solo dal `content_json`
  salvato sul server (l'autosave ha un debounce di 1,2 s).
- Il filtro difensivo non valida indici/id delle azioni: un'azione con
  esperienza inesistente viene ignorata dal frontend, gli indici fuori
  range non sono controllati.
