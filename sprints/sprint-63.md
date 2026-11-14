# Sprint 63 — Filtro "Ricerca" multi-selezione + editor e chat AI della cover letter

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-19/20 · **Commit:** `3b46009` (parte A, 19/10) e `9bbcbf8` (parte B, 20/10) — due commit distinti con lo stesso numero di sprint

## Parte A — Filtro "Ricerca" della lista job a selezione multipla e scorrevole

### Input
Richiesta dell'utente (sessione `ed44ecc2`, 19/10):
- il filtro che seleziona i job per ricerca di provenienza (es. "Azienda: … – città") deve essere a selezione multipla;
- il menu a tendina deve scorrere: con molte ricerche attive, le voci in fondo non erano raggiungibili;
- il layout resta quello attuale, con una spunta accanto a ogni ricerca selezionata e, a menu chiuso, il numero di ricerche selezionate;
- prima porre domande sulle criticità, poi sviluppare, fare il deploy e pushare su GitHub.

### Decisioni prese
- Rimossa la voce esplicita "Tutte le ricerche" (decisione confermata dall'utente): nessuna selezione equivale a nessun filtro, come per Punteggio, Stato e Candidati.
- Le ricerche selezionate si combinano in **OR** tra loro e in AND con gli altri filtri.
- Un id che non corrisponde a nessuna `SavedSearch` dell'utente non aggiunge nulla all'OR. Nella versione a selezione singola rendeva invece vuoto l'intero risultato (`queryset.none()`). Se è l'unico selezionato, il risultato resta vuoto.
- Riutilizzato il componente `MultiSelectFilter` (introdotto nello Sprint 47 per il Punteggio), senza nuove dipendenze.

### Implementazione
**Backend:**
- `apps/jobs/list_service.py`: `_apply_matched_search_filter(queryset, user, search_ids)` accetta una lista. Il token `"none"` corrisponde a `matched_search=""`; per ogni id valido, `_saved_search_match_q` ricostruisce la stringa di provenienza:
  - per le ricerche Company, `matched_search__iexact=keywords`;
  - per le ricerche Job role, `matched_search == "<keywords> - <city>, <country>"`.
- `list_jobs(..., search_ids=None)`.

**API:**
- `GET /api/jobs/?search=` accetta un CSV di id numerici e/o `none` (es. `search=12,15,none`); un valore diverso restituisce 400. Rimosso il valore `all`.

**Frontend:**
- `components/MultiSelectFilter.jsx`:
  - nuova prop `layout` (`'grid'` di default, `'list'` per una colonna singola con etichette lunghe);
  - il pannello ha ora `max-h-64 overflow-y-auto`, una regola che vale per entrambi i layout;
  - il trigger mostra `Etichetta (N)` quando ci sono selezioni.
- `pages/JobListPage.jsx`:
  - lo stato `searchFilter` (stringa) diventa `searchFilters` (array);
  - le opzioni sono tutte le ricerche salvate dell'utente (attive e non attive, da `fetchSearches`) più "Nessuna ricerca";
  - il filtro è nascosto nella sezione Importati, dove `searchIds` è ignorato.
- `api/jobs.js`: parametro `searchIds`, unito in CSV.
- i18n: rimossa la chiave `jobs.searchFilter_all` (it/en).

### Verifica
Dalla sessione:
- nuovi test backend `test_no_search_filter_returns_everything`, `test_search_filter_combines_multiple_ids_with_or`, `test_search_filter_ignores_unknown_id_when_combined_with_a_valid_one`;
- suite 227/227, lint e build del frontend puliti, nessuna migrazione;
- e2e aggiunto ("il filtro ricerca è multi-selezione: più spunte contemporanee e contatore nel trigger"), esecuzione non documentata;
- deploy con `docker-compose.prod.yml`;
- prova su dati reali di produzione: due ricerche selezionate restituiscono 92 + 22 = 114 job, senza perdite né doppioni;
- pushato su `origin/main`.

### Note
- Prima di iniziare, la sessione ha rilevato che il repository era avanzato di 16 sprint (47→62) fatti in altre sessioni. Ha verificato che la produzione fosse già allineata.

---

## Parte B — Editor interattivo e chat AI della cover letter (mirror del CV)

### Input
Richiesta del committente (20/10): portare sulla cover letter quanto già
fatto per la modifica del CV, cioè l'editor della bozza (Sprint 51) e la
chat AI con proposta e conferma (Sprint 59–62). Il committente si
aspettava un lavoro più semplice e ha chiesto di segnalare le criticità e
di fare tutte le domande necessarie prima di procedere.

Prima di fare domande l'assistente ha verificato la struttura esistente.
La cover letter dello Sprint 42 è un semplice elenco di paragrafi
(`paragraphs: [string]`). Oggetto, saluto e chiusura sono fissi per lingua
e non vengono mai generati dall'AI. Non c'è nessuna logica di
selezione/taglio, e `CoverLetterDocument` non aveva ancora un
`content_json`.

### Decisioni prese
Le risposte del committente (domande a scelta) sono state:
- **Stile del PDF invariato**: non si portano sulla cover letter i ritocchi
  fatti al template del CV negli Sprint 52–58 (Cambria, dimensione fissa,
  colori, giustificato). Restano i 3 livelli di compattamento della
  cover letter.
- **Nessun "puntamento" di un singolo paragrafo** come contesto della chat
  (opzione consigliata): con 3-5 paragrafi basta il riferimento testuale.
- **Nessun grassetto automatico sulle keyword** (Sprint 58): resta solo
  sul CV.

Allineati per default al CV, come proposto dall'assistente senza obiezioni:
- pulsante "Modifica Cover Letter" separato e aggiuntivo rispetto a quello
  di generazione;
- bozza e chat con lo stesso pattern proposta → conferma;
- decisioni accetta/rifiuta persistite lato server fin da subito (il CV le
  ha ottenute solo con lo Sprint 62);
- editing, anteprima e finalizzazione gratuiti; scala credito extra solo
  ogni messaggio della chat, con un prezzo indipendente.

### Implementazione

#### Modello dati
- `CoverLetterDocument.content_json` (JSONField, default `{}`): snapshot
  `{content_language, translated_city, paragraphs}`. Per le lettere
  generate prima di questo sprint resta vuoto.
- Nuovo `CoverLetterDraft`: OneToOne su `Job` (`related_name="cover_letter_draft"`),
  con `user`, `content_json`, `chat_history`, `created_at` e `updated_at`.
- Migrazioni `cv/0008_coverletterdocument_content_json_coverletterdraft`
  e `jobs/0014_alter_runlog_task_type`, che aggiunge
  `RunLog.TaskType.COVER_LETTER_DRAFT_CHAT`.

#### Backend
- `cover_letter_generation.generate_cover_letter` ora salva anche
  `content_json`.
- Nuovo `apps/cv/cover_letter_draft.py`, mirror di `draft.py` molto
  ridotto:
  - `seed_cover_letter_draft_for_job` usa `update_or_create` partendo
    dall'ultima `CoverLetterDocument`. Solleva `NoCoverLetterDocumentToEdit`
    se il documento non c'è o se il suo `content_json` è vuoto.
  - `render_context_from_cover_letter_draft`: oggetto, saluto e chiusura
    restano fissi da `COVER_LETTER_LABELS`; dalla bozza arrivano solo i
    paragrafi e la città tradotta.
  - `render_cover_letter_draft_preview` e `finalize_cover_letter_draft`:
    il secondo crea una nuova `CoverLetterDocument` senza chiamare Claude
    e senza consumare quota o credito.
- Nuovo `apps/cv/cover_letter_draft_chat.py`, mirror di `draft_chat.py`:
  - 3 tipi di azione (`update_paragraph`, `add_paragraph`,
    `remove_paragraph`) con lo schema piatto `{type, paragraph_index, text}`,
    contro le 16 del CV;
  - grounding identico al CV: si può amplificare il testo solo su
    richiesta esplicita dell'utente, ed è sempre vietato inventare aziende,
    ruoli o risultati;
  - `_sanitize_actions` scarta solo gli indici fuori range: non serve un
    filtro su skill o certificazioni come nel CV;
  - ogni messaggio costa credito (`PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE`,
    default 0,20, sempre a credito, senza tetto giornaliero). Se la
    chiamata fallisce il credito viene rimborsato e si scrive un `RunLog`
    FAILURE;
  - `record_action_decision` scrive `decision` (accepted o rejected)
    dentro `chat_history`.
- `config/settings.py` e `.env.example`: `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE`.

#### API
- `GET`/`POST`/`PATCH /api/jobs/<id>/cover-letter-draft/`:
  - `GET` legge la bozza (404 se non c'è);
  - `POST` la apre o riapre dall'ultima lettera (201; 409 se non c'è niente
    da aprire);
  - `PATCH` sostituisce tutto il `content_json` (autosave).
- `POST /api/jobs/<id>/cover-letter-draft/preview/`: restituisce il PDF
  binario con l'header `X-Page-Count`. Il body facoltativo contiene il
  contenuto corrente.
- `POST /api/jobs/<id>/cover-letter-draft/finalize/`: 201
  `{cover_letter_document_id}`.
- `GET`/`POST`/`PATCH /api/jobs/<id>/cover-letter-draft/chat/`:
  - `GET` restituisce la cronologia;
  - `POST {message}` risponde `{reply, actions}`; 400 se il messaggio è
    vuoto, 402 se il credito non basta, 502 se la chiamata AI fallisce;
  - `PATCH {message_index, action_index, decision}` risponde 204.

  A differenza della chat del CV, non c'è il parametro `focus_bullets`.

#### Frontend
- Route `/jobs/:id/cover-letter-editor` (`App.jsx`).
- `JobDetailPage.jsx`: pulsante "Modifica Cover Letter", visibile quando
  esiste un PDF di cover letter.
- `pages/CoverLetterDraftEditorPage.jsx`:
  - elenco di paragrafi in textarea, con sposta su/giù, elimina e
    "+ Aggiungi paragrafo". Non c'è mostra/nascondi;
  - autosave con debounce di 1,2 s e anteprima PDF live con il conteggio
    pagine;
  - pulsante "Genera PDF finale".
- `components/CoverLetterChatPanel.jsx`: pannello laterale con le card
  delle azioni (prima/dopo) e i pulsanti Accetta/Rifiuta. Alla riapertura
  le decisioni vengono ricaricate da `chat_history`.
- `api/jobs.js`: funzioni `*CoverLetterDraft*`; `previewCoverLetterDraft`
  usa una fetch diretta perché la risposta è un PDF.
- `i18n`: namespace `coverLetterEditor.*` (it/en). Per la chat riusa le
  chiavi `cvEditor.chat*`.

### Verifica
Dalla sessione:
- `manage.py check` pulito; `makemigrations --check --dry-run` riporta
  "No changes detected".
- Suite `apps.cv`: 49/49 OK. Suite `apps.cv apps.jobs`: 173 test con 22
  failure e 2 errori, attribuiti in sessione a redirect 301 preesistenti
  nell'ambiente di produzione (es. `301 != 409`) e non legati al nuovo
  codice. Nessun test nuovo per la cover letter.
- Prove reali sul backend di produzione:
  - generazione: 5 paragrafi;
  - apertura della bozza;
  - un messaggio di chat che ha prodotto un'azione `update_paragraph`, con
    la decisione registrata;
  - anteprima di 1 pagina;
  - finalizzazione: nuovo documento con 5 paragrafi.
- Verifica HTTPS degli endpoint bozza/chat sul sito pubblicato.
- Frontend: oxlint senza warning sui file toccati, build di produzione OK.

### Note / cosa manca
- Le lettere generate prima di questo sprint hanno `content_json` vuoto.
  Il pulsante "Modifica Cover Letter" compare lo stesso, ma l'apertura
  fallisce con "Genera prima una cover letter": bisogna rigenerarle.
- L'editor fa `GET` della bozza e chiama `POST` (seed) solo se riceve 404.
  Nessun percorso risemina una bozza già esistente: dopo una nuova
  generazione AI, l'editor riapre la bozza precedente e non la nuova
  lettera. Lo stesso vale per l'editor CV, perché il codice è un mirror.
  La docstring di `CVDraft` dice il contrario.
- Il pannello chat riusa i testi `cvEditor.chatEmpty`/`chatPlaceholder`,
  che parlano di "CV" e di "sommario".
- Le azioni della chat usano indici posizionali: se si accettano più azioni
  di `remove`/`add` dello stesso turno, gli indici successivi possono
  puntare a un paragrafo diverso da quello proposto.
- Nessun test automatico per la cover letter (generazione, bozza, chat).

## Nota sui test (verifica del 2026-11-14)
I "22 failure e 2 errori" (`301 != …`) visti in sessione sono un artefatto d'ambiente: lanciata nel container di produzione la suite usa `DJANGO_DEBUG=false` e il redirect HTTPS risponde 301 a ogni chiamata del test client. Rieseguita il 2026-11-14 con `-e DJANGO_DEBUG=true` (vedi `DEPLOY.md` §4.4): **234/234 OK**.
