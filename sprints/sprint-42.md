# Sprint 42 — Lettera di presentazione (cover letter) in PDF, quota/credito dedicati, nomi file CV/cover letter

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-08-22 · **Commit:** `0833bdb` (commit cumulativo di recupero del 2026-08-22 che contiene insieme Sprint 39–42, vedi `sprint-43.md`, "Nota preliminare")

## Input
Richiesta del committente: nel dettaglio di ogni job serve un pulsante "Genera
cover letter". Il pulsante apre un popup che:
- chiede eventuali indicazioni specifiche o informazioni da inserire, con un
  campo di testo;
- offre un menu da cui selezionare una o più indicazioni usate nelle
  generazioni precedenti, dalla più recente.

La cover letter va prodotta in PDF, con formato semplice ed entro una pagina.
Il committente ha fornito un PDF di esempio, poi allegato in chat. Il pulsante
del CV va rinominato "Scarica CV", e se ne aggiunge uno "Scarica Cover Letter",
tradotto nelle lingue dell'app. Il committente ha chiesto di chiarire tutti i
dubbi prima di sviluppare.

## Decisioni prese (con il committente, 2026-08-22)
- **Quota:** il massimale giornaliero è **separato** da quello del CV ma ha gli
  stessi tetti: Free 1/giorno, Pro 10/giorno. Oltre il massimale si prosegue a
  credito, con un prezzo dedicato.
- **Storico delle indicazioni:** attinge a **tutte** le cover letter
  dell'utente, su qualunque job, dalla più recente.
- **Indicazioni dell'utente:** possono essere sia tono/enfasi sia fatti reali
  non ancora presenti nel profilo (risposta "entrambi"). La responsabilità di
  veridicità resta all'utente, come nell'arricchimento del CV.
- **Generazione:** solo manuale, su qualunque job, che il CV esista o no.
  Nessuna generazione automatica notturna.
- **Nomi file**, fissi in ogni lingua del contenuto: `Cover letter {Nome
  Cognome} - {Posizione}.pdf`. Il committente ha esteso la regola al CV:
  `CV {Nome Cognome} - {Posizione}.pdf`.
- **Dipendenza:** aggiunta `@radix-ui/react-dialog` per il popup, con conferma
  esplicita del committente. È della stessa famiglia Radix già in uso.
- **Formato:** fedele all'esempio. Nome, riga contatti **senza LinkedIn**, riga
  oggetto, saluto, 3–5 paragrafi, chiusura e firma. Oggetto, saluto e chiusura
  sono testi fissi tradotti in modo deterministico (it/en/fr/de/es); l'AI
  scrive solo i paragrafi del corpo.
- **Scelte implementative non concordate,** segnalate al committente a fine
  sessione:
  - le indicazioni precedenti sono una **checklist** (checkbox) invece di un
    menu a tendina;
  - la città nei contatti usa il formato del CV ("Rome, IT") invece del nome
    paese esteso dell'esempio.

## Implementazione
### Modello dati
- Nuovo `apps/cv/models.py: CoverLetterDocument`, sul modello di `CVDocument`.
  Campi: `job`, `user`, `html_source`, `pdf_file` (`cover_letter_documents/`),
  `generated_at`, `instructions_used`.
- `Job.cover_letter_generation_in_progress`: guardia di concorrenza
  indipendente da quella del CV. Non tocca `Job.status`.
- `DailyQuota.cover_letter_count`.
- `RunLog.TaskType.COVER_LETTER_GENERATION`, con `task_type.max_length` portato
  a 25.
- Migrazioni: `jobs/0005_cover_letter_support`, `jobs/0006_alter_runlog_task_type`,
  `cv/0003_cover_letter_support`.
### Backend
- `apps/cv/cover_letter_content.py`:
  - `COVER_LETTER_LABELS` per 5 lingue;
  - `COVER_LETTER_JSON_SCHEMA`: `content_language`, `translated_city`,
    `paragraphs`;
  - il prompt richiede grounding e indicazioni dell'utente pienamente usate;
  - chiamata via `call_claude_structured` (`BEDROCK_CV_GENERATION_MODEL`,
    `max_tokens=2000`, effort medium);
  - la lingua segue la stessa regola del CV (`_resolve_language`,
    `_resolve_html_lang`).
- `apps/cv/cover_letter_generation.py`: `generate_cover_letter(job, instructions)`.
  La riga contatti è "Città, PAESE | telefono | email". Il PDF è salvato
  nella cartella media `cover_letter_documents/`.
- `apps/cv/rendering.py`:
  - `COVER_LETTER_COMPACT_LEVELS`, 3 livelli di compattamento (10.5/10/9 pt) per
    stare in 1 pagina;
  - `render_cover_letter`;
  - helper comune `_render_with_compact_retry`.
- Nuovo template `apps/cv/templates/cv/cover_letter_template.html` (A4, senza
  foto).
- `apps/cv/cover_letter_manual_generation.py`:
  - `COVER_LETTER_PLAN_LIMITS = {"free": 1, "pro": 10}`;
  - riserva atomica di quota o credito (`select_for_update`);
  - restituzione della riserva in caso di fallimento, con un `RunLog` di tipo
    failure;
  - `get_recent_instructions(user, limit=20)`: indicazioni distinte, dalla più
    recente.
- `config/settings.py` / `.env.example`: `PRICE_COVER_LETTER_EXTRA`, default
  `1.50`.
- `apps/jobs/serializers.py` (`JobSerializer`):
  - nuovi campi `cover_letter_pdf_url` (ultima generata) e
    `cover_letter_download_filename`;
  - `cv_download_filename` cambiato in `CV {Nome Cognome} - {Titolo}.pdf`;
  - i caratteri non ammessi nei nomi file sono rimossi
    (`_FILENAME_UNSAFE_CHARS`);
  - se nome e cognome mancano si usa l'email di login.
### API
- `POST /api/jobs/<id>/generate-cover-letter/`, body `{instructions}`.
  Risposte: 201 `{cover_letter_document_id}`; 409 per job già in generazione o
  limite/credito esauriti; 502 per generazione fallita.
- `GET /api/cover-letter-instructions/` restituisce `{instructions: [...]}`.
### Frontend
- Nuovo `components/ui/dialog.jsx`, in stile shadcn su `@radix-ui/react-dialog`.
- `api/jobs.js`: `generateCoverLetter(id, instructions)` e
  `fetchCoverLetterInstructions()`.
- `pages/JobDetailPage.jsx`:
  - pulsante "Genera Cover Letter", disabilitato durante la generazione;
  - pulsante "Scarica Cover Letter" con l'attributo `download` (nome file dal
    server); "Scarica PDF" diventa "Scarica CV".
  - Popup:
    - textarea per le indicazioni libere;
    - checklist delle indicazioni precedenti;
    - all'invio le indicazioni selezionate e il testo libero vengono uniti con
      una riga vuota tra l'uno e l'altro (`\n\n`) e inviati come unica
      stringa.
- `i18n/translations.js`: chiavi `jobs.downloadCv`, `jobs.generateCoverLetter`,
  `jobs.downloadCoverLetter`, `jobs.coverLetter*` (it/en).

## Verifica
Risultati riportati nella sessione del 2026-08-22:
- **Generazione reale in produzione** su un utente di test, con e senza
  indicazioni: PDF di 1 pagina, ispezionato visivamente e servito via Caddy.
- **Quote:** quota CV e quota cover letter risultano indipendenti.
- **Build e check:** il bundle frontend contiene le nuove stringhe;
  `manage.py check` pulito.
- **Test automatici:**
  - `apps.cv` 50/50 verdi, dopo aver allineato la fixture `_fake_content` al
    campo `content_language` dello Sprint 41;
  - **nessun test aggiunto** per la cover letter (servizio, quota, endpoint,
    nomi file);
  - le suite `apps.jobs`/`apps.profiles` lanciate nella sessione avevano
    fallimenti, non analizzati nella sessione. È plausibile che fossero gli
    stessi già noti da sprint-39 (redirect 301 con `DJANGO_DEBUG=false`), ma
    non è verificato.

## Note / cosa manca
- **Profilo inviato al modello:** è lo stesso contesto del CV
  (`_build_profile_context`: sommario, città, esperienze, skill,
  certificazioni). Istruzione e lingue **non** vengono passate al modello per
  la cover letter.
- **Storico delle indicazioni:** l'unione delle indicazioni selezionate viene
  salvata come un nuovo testo in `instructions_used`, quindi le combinazioni
  compaiono come voci separate nello storico. La deduplica avviene solo per
  testo identico.
- **Archiviazione:** a differenza del CV, generare una cover letter non fa
  uscire il job dall'Archivio e non cambia lo stato.
- **Admin:** `CoverLetterDocument` non è registrato in Django Admin.
- **Evoluzioni successive:**
  - `CoverLetterDocument.content_json`, `CoverLetterDraft`, editor e chat della
    cover letter (Sprint 63, migrazione `cv/0008`);
  - `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE` (Sprint 63).
- **Specifiche:** la cover letter non compare in nessuna specifica, né madre né
  `Docs/03`. Le specifiche funzionali §5.12 ("nessun editor in-app") e §4.11
  ("due pool separati") non tengono conto di questo massimale aggiuntivo.
