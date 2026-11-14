# Sprint 51 — Editor interattivo del CV (Fase 1: bozza manuale, senza chat)

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `7782dc9`

## Input
Richiesta del committente: dopo la generazione AI, poter "finetunare
attivamente" il CV tramite un layout interattivo e un chatbot di supporto,
con un pulsante finale che produce il PDF definitivo. Funzione dichiarata
chiave per l'applicazione: deve essere user-friendly e portare a un CV
ottimo. Prima dell'implementazione è stata chiesta e discussa una proposta
di design completa.

## Decisioni prese
Prese con il committente prima di scrivere codice (domande a scelta
multipla in sessione):
- **Fasatura in due fasi**: Fase 1 = editor manuale strutturato + anteprima
  live + "Genera PDF finale", senza chat; Fase 2 (chat) solo dopo il test
  della Fase 1 da parte del committente (→ Sprint 59).
- **Punto di ingresso additivo**: nuovo pulsante "Modifica CV", visibile
  solo quando esiste già un CV per il job. "Genera CV" resta identico
  (stessa quota/credito, stessa pipeline): nessun rischio sul flusso
  esistente.
- **Pool completo di bullet**: la bozza contiene *tutti* i bullet prodotti
  dall'AI per ogni esperienza del profilo (non solo quelli sopravvissuti al
  taglio al budget), ciascuno con un flag mostra/nascondi già impostato
  secondo la selezione automatica. Stesso principio per le esperienze
  escluse dal cap di 5: presenti con `shown=false`, mai eliminate.
- **Ruolo modificabile** nella bozza (richiesta del committente); azienda,
  località e date restano dati del profilo, non modificabili nell'editor.
- **Istruzione e lingue modificabili** nella bozza (es. un corso specifico
  per quel job, una lingua aggiunta/tolta), ma **solo localmente al CV**:
  nessuna scrittura sul profilo master, nessuna opzione "salva anche nel
  profilo" (scelta "solo locale" per semplicità).
- Skills/certifications: solo selezione (checkbox) tra le voci reali del
  profilo, nessun testo libero.
- Anteprima renderizzata **lato server** con lo stesso template/WeasyPrint
  del PDF finale (nessuna duplicazione CSS lato client), senza chiamate AI.
- Autosave: PATCH dell'intero `content_json` (nessuna operazione granulare).
- "Genera PDF finale" **non consuma** quota né credito: non è una nuova
  generazione AI.
- Già fissato per la Fase 2: pattern "proposta → conferma" (la chat propone,
  l'utente accetta), stesso grounding del resto dell'app con possibilità di
  amplificare su richiesta esplicita.

## Implementazione

### Modello dati
- `CVDocument.content_json` (JSONField, default `{}`): snapshot strutturato
  del contenuto, salvato a ogni generazione. Vuoto per i CV generati prima
  di questo sprint (non riapribili nell'editor).
- Nuovo modello `CVDraft`: `job` (OneToOne, `related_name="cv_draft"`),
  `user`, `content_json`, `created_at`, `updated_at`. Una sola bozza
  corrente per job, mai uno storico.
- Migrazione `cv/0006_cv_draft_editor`.

### Backend
- `generation.py`:
  - `_attach_facts` aggiunge `profile_experience_id` a ogni esperienza
    prodotta dall'AI (chiave di aggancio tra contenuto AI, profilo e bozza).
  - `_build_shown_experiences` restituisce anche il pool completo
    (`with_facts`) prima del taglio.
  - Nuova `build_draft_content_json(...)`: costruisce la struttura
    editabile (`summary`, `qualification`, `translated_city`,
    `content_language`, `areas_of_expertise` come lista di stringhe,
    `experiences[]` con `profile_experience_id/company/role/location/
    dates/technologies/shown/bullets[{text, shown}]`, `educations[]`,
    `skills`, `certifications`, `languages[{language, level}]` come codici).
  - `generate_cv` salva `content_json` sul `CVDocument`.
- Nuovo `apps/cv/draft.py`: `seed_draft_for_job` (update_or_create dalla
  bozza a partire dall'ultimo `CVDocument`; eccezione `NoCvDocumentToEdit`
  se manca o se `content_json` è vuoto), `render_context_from_draft` (nessun
  taglio automatico: solo esperienze/bullet con `shown=true`, lingue
  tradotte nella lingua del CV), `render_draft_preview` (PDF + numero
  pagine), `finalize_cv_draft` (nuovo `CVDocument` con
  `generation_type=manual`, stesso `content_json` della bozza; eccezione
  `NoDraftToFinalize`).

### API
- `GET/POST/PATCH /api/jobs/<id>/cv-draft/` (`CvDraftView`): GET bozza
  (404 se assente), POST apre/riapre dall'ultimo CV (201; 409 se nessun CV
  riapribile), PATCH sostituisce l'intero `content_json`.
- `POST /api/jobs/<id>/cv-draft/preview/` (`CvDraftPreviewView`): accetta
  nel body il contenuto corrente (anche non ancora salvato), risponde con
  il PDF binario e l'header `X-Page-Count`.
- `POST /api/jobs/<id>/cv-draft/finalize/` (`FinalizeCvDraftView`): 201
  con `{cv_document_id}`; 409 se non c'è bozza.

### Frontend
- Nuova pagina `CvDraftEditorPage.jsx` su route `/jobs/:id/cv-editor`:
  carica la bozza (se 404 la apre con POST), sezioni per sommario,
  qualifica, aree di competenza (aggiungi/rimuovi/riordina con frecce),
  esperienze (spunta "Mostra nel CV", ruolo editabile, bullet con spunta
  mostra/nascondi, modifica, aggiungi, rimuovi, riordina), istruzione
  (tutti i campi, aggiungi/rimuovi), competenze/certificazioni (checkbox
  sulle voci del profilo), lingue (select lingua/livello, aggiungi/rimuovi).
- Colonna destra: anteprima PDF in iframe con indicatore "1 pagina ✓" /
  "N pagine ⚠", e pulsante "Genera PDF finale".
- Autosave e anteprima con un unico debounce di 1200 ms.
- `JobDetailPage.jsx`: pulsante "Modifica CV" accanto a "Scarica CV".
- `api/jobs.js`: `openCvDraft`, `fetchCvDraft`, `updateCvDraft`,
  `finalizeCvDraft`, `previewCvDraft` (fetch diretto, legge blob e header).
- Nuovo namespace i18n `cvEditor` (it/en).

## Verifica
- Suite `apps.cv`: 49/49.
- Verifica end-to-end in produzione: generazione → `content_json` → seed
  bozza → anteprima (1 pagina anche con 3 bullet riaccesi) → modifica →
  finalize, prima a livello di funzione e poi via HTTP reale
  (GET/PATCH/preview/finalize attraverso Caddy).
- Build frontend pulita.
- Push su GitHub inizialmente fallito per credenziali mancanti sul server,
  riuscito dopo l'aggiornamento del token da parte del committente.

## Note / cosa manca
- Nessun test automatico dedicato a `draft.py` né agli endpoint
  `cv-draft` (la suite resta a 49 test).
- Il frontend apre la bozza con POST solo se il GET restituisce 404: una
  bozza esistente non viene mai riseminata, nemmeno dopo una nuova
  generazione del CV (il docstring di `CVDraft` dice invece che "generare
  un nuovo CV sovrascrive il draft esistente" — non implementato).
- `finalize_cv_draft` non aggiorna stato/data del Job (il job ha già un CV)
  e non attende l'autosave pendente lato frontend.
- I CV generati prima di questo sprint mostrano comunque "Modifica CV", ma
  l'apertura fallisce con messaggio "Genera prima un CV per questo job".
