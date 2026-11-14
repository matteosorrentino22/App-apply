# Specifiche Tecniche — App di ricerca lavoro e generazione CV

> **Documento:** 02 — Specifiche tecniche
> **Versione:** 5 — descrizione **as-is al 2026-11-14** (Sprint 66, sicurezza)
> **Stato:** documento vivo, va aggiornato nello stesso commit di ogni sprint che cambia il comportamento (regola in `CLAUDE.md`, "Workflow sprint")
> **Ambito:** *come* è costruita l'applicazione: architettura, stack, modello dati, flussi, generazione dei documenti, deploy, amministrazione, API, test, limiti tecnici. Il *cosa* è in `Docs/01-specifiche-funzionali-v6.md`. Le regole di contenuto e impaginazione del CV sono in `Docs/03-specifiche-funzionali-contenuto-cv-v5.md`, che per quei temi prevale su questo documento. Procedure operative, variabili d'ambiente e runbook: `DEPLOY.md`.
>
> **Vincoli guida** (dichiarati dal committente, invariati dalla v1):
> 1. Semplicità prima di tutto: soluzione **monolitica**, non microservizi.
> 2. Manutenibile da **una persona / piccolo team**.
> 3. Tecnologie **mature, ben documentate, ampia community**.
> 4. Copertura: backend, frontend, database, hosting/deploy, autenticazione.
> 5. MVP per una **cerchia ristretta di utenti di test**: nessun requisito di scala.
>
> **Numerazione.** La numerazione dei paragrafi §1–§11 delle versioni precedenti è mantenuta, perché il codice la cita nei commenti (es. §3.5, §3.8, §5.1, §5.2, §5.3, §5.5, §6.3, §8.4). Le parti nuove sono aggiunte in coda ai paragrafi esistenti (§4.9–§4.14, §5.6–§5.13, §6.6–§6.7) o come nuove sezioni (§12 API REST, §13 Test). I commenti nel codice citano ancora `02-specifiche-tecniche-v3.md`: vanno letti come riferimenti a questo documento.

### Nota di versione (v5)

La v5 nasce dalla fusione delle due versioni divergenti che esistevano fino al 2026-11-14 (`02-specifiche-tecniche-v3.md` in radice, aggiornata fino allo Sprint 47; `Docs/02-specifiche-tecniche-v4.md`, che aveva recepito il documento 03 ma non gli sprint 39/47) e dall'allineamento completo al codice. Nessuna delle due descriveva gli sprint 40–64. Le fonti sono il codice a HEAD, le schede `sprints/sprint-40.md` … `sprint-64.md` (in buona parte retroattive) e `DEPLOY.md`.

Novità principali rispetto alle versioni precedenti, per sprint:

| Sprint | Cambiamento tecnico | § |
|---|---|---|
| 39 | Ricerche di tipo *Job role* / *Company*; chiamate Apify raggruppate per (tipo, città, paese); `companyInclude` per le Company | §4.3, §5.3 |
| 40 | Motore AI migrato da API Anthropic diretta a **Claude via AWS Bedrock**; helper unico `apps/common/ai.py` con tool-use forzato e validazione `jsonschema` | §3.5 |
| 40, 63 | Filtro lista per ricerca di provenienza (poi multi-selezione) | §12 |
| 41 | CV multilingua (etichette in it/en/fr/de/es), lingue e livelli a valori fissi, `Profile.email` | §4.2, §6.2 |
| 42 | Cover letter PDF con quota/credito propri | §4.10, §5.10 |
| 43 | Creazione manuale di un job | §5.8 |
| 44 | Statistiche Home; "colma i gap" al posto dell'arricchimento (`extra_instructions_used`) | §4.5, §6.2 |
| 44–45 | Raccolta manuale sincrona dalla Home, gunicorn `--timeout 1800 --workers 4`, scoring parallelo; **rimozione dei CV automatici** | §5.1, §5.6, §8.2 |
| 46 | Rimozione del tetto 50/100 job/notte e del cap di intake 15; Preferiti; candidati/recruiter; filtri per date/location; match/gap come `{label, reason}`; candidatura senza CV | §4.4, §5.1 |
| 47–49 | Score 1–10 con rubrica; cap deterministico sulla lingua; scarto delle offerte con campi oltre `max_length` | §5.9 |
| 50 | Messaggi di networking (LinkedIn/email) | §4.12, §5.11 |
| 51 | Editor del CV: `CVDocument.content_json`, `CVDraft`, anteprima e finalizzazione | §4.9, §5.12 |
| 52–58 | Template CV a dimensione fissa con font Caladea; grassetto sulle keyword | §3.6, §6 |
| 59–62 | Chat AI dell'editor CV (proposta → conferma, puntamento dei bullet, decisioni persistite) | §5.13 |
| 63 | Editor e chat della cover letter (`CoverLetterDraft`) | §4.11, §5.12, §5.13 |
| 64 | Filtri preferiti salvabili (`JobFilterPreset`) | §4.13 |
| 66 | Sicurezza: download con URL firmati e nomi file casuali, token con scadenza per inattività e logout, throttling, registrazione su invito, limiti di input, header HTTP, push in allowlist, container non-root, log | §3.7, §4.15, §7.1, §8, §12 |

Decisioni delle versioni precedenti **superate dal codice** e quindi tolte da questo documento: limite di raccolta 50/100 job per utente per notte; cap di intake di 15 job/giorno con tie-break; generazione automatica dei CV per i job 4–5; una sola chiamata Apify per utente; scoring fallito = offerta scartata; scala 1–5; "riserva all'accodamento" con task Celery per le generazioni manuali; 3 livelli di compattamento del CV; selezione delle 3 voci di istruzione più recenti; budget bullet 12/10/9 distribuito per peso; arricchimento del profilo salvabile; `Education.end_date` obbligatoria; voucher.

### Storico versioni (condensato)

- **v1–v2** (luglio 2026): architettura monolitica Django + Celery, modello dati, flussi del ciclo notturno, deploy su VPS con Docker Compose. Batch alle 02:00 Europe/Rome, riserva della quota con restituzione su fallimento, foto on/off, pipeline di parsing del CV caricato.
- **v3** (luglio 2026, revisione criticità): credito come saldo in euro con listino; niente Word; una chiamata Apify per utente con limite 50/100; reset quote a mezzanotte Europe/Rome; notifica basata su `last_notified_at`; guardia di concorrenza. Aggiornata poi in place con gli sprint 39 e 47.
- **v4** (01/08/2026): recepisce il documento 03 v3 (pipeline CV con budget deterministico e loop di ripiego, `Education.start_date/end_date`, rimozione di `key_achievements`).
- **v5** (14/11/2026): fusione di v3 e v4, allineamento all'as-is degli sprint 40–64, aggiunte le sezioni API REST (§12) e Test (§13).

Le versioni superate sono conservate in `Docs/archivio/` solo come storico (vedi `Docs/CHANGELOG.md`).

---

## 1. Sintesi delle decisioni

| Area | Scelta (as-is) | In una frase |
|---|---|---|
| Architettura | Monolite modulare | Un unico progetto Django con un'app per dominio funzionale. |
| Backend | Python + Django 5.1 + Django REST Framework | API REST consumata dalla PWA, Django Admin per l'amministrazione. |
| Esecuzione dei lavori | **Sincrona** nella richiesta HTTP per le azioni dell'utente; **Celery + Redis + Beat** solo per i lavori programmati | Generazioni, chat, import e raccolta manuale girano dentro gunicorn (`--timeout 1800`); ciclo notturno, notifiche e backup girano sul worker. |
| Frontend | React 19 come PWA (Vite, Tailwind, shadcn/ui su Radix) | Installabile sul telefono, push; nessuna cache offline dei dati. |
| Database | PostgreSQL 16 | Dati relazionali per utente. |
| Fonte offerte | Apify (actor `cheap_scraper~linkedin-job-scraper`) dietro un'interfaccia interna; API guest di LinkedIn per l'import da URL | Una chiamata per gruppo (tipo ricerca × città × paese), al massimo 150 risultati per chiamata, nessun tetto per piano. |
| Motore AI | Claude via **AWS Bedrock** (`AnthropicBedrock`), helper unico `apps/common/ai.py` | Output strutturato con tool-use forzato e validazione `jsonschema`, modelli per uso configurabili da env. |
| Usi dell'AI | Scoring, parsing del CV caricato, contenuti del CV, cover letter, messaggi di networking, chat degli editor | Sette punti di chiamata, tutti dallo stesso helper. |
| Documenti | Template HTML/CSS → PDF con WeasyPrint (CV in Caladea a dimensione fissa; cover letter a 3 livelli di compattamento) | Solo PDF; editor in-app con bozza e chat AI. |
| Credito | Saldo in € (`Decimal`) + listino prezzi unitari da env | Oltre il massimale giornaliero si paga a credito; le chat sono sempre a credito. |
| Autenticazione | Email/password con token propri (`AuthToken`, scadenza dopo 30 giorni di inattività) + login Google (django-allauth) | Google è implementato ma **non configurato in produzione**; registrazione su invito opzionale. |
| Notifiche | Web Push (VAPID, `pywebpush`) | Notifica mattutina alle 10 locali e promemoria di inattività a 7 giorni. |
| Hosting | VPS singolo economico | Tutto lo stack su un server con Docker. |
| Deploy | Docker Compose (`docker-compose.prod.yml`) + Caddy | HTTPS automatico; un solo file compose in produzione. |
| Backup | Task Celery `pg_dump` + media verso storage S3-compatibile | Implementato ma **non configurato in produzione** (§8.4). |
| Amministrazione | Django Admin | Piani e credito si gestiscono solo da Admin; non esistono voucher né checkout. |

L'app deriva dal **prototipo n8n** del committente (workflow *01 Job Collection*, *02 Job Scoring*, *03 CV Generation*), da cui sono stati recuperati l'actor Apify, l'impianto dei prompt e il layout del CV; Google Sheets e Google Drive sono stati sostituiti da PostgreSQL e dalla generazione PDF sul server (§10).

---

## 2. Architettura generale

### 2.1 Il principio: un monolite

L'applicazione è un **unico progetto Django** che espone:

- un'**API REST** (`/api/...`) consumata dalla PWA (§12);
- il **Django Admin** (path da `DJANGO_ADMIN_PATH`, default `/admin/`) per l'amministrazione (§9);
- gli URL di **django-allauth** (`/accounts/...`) per il login Google;
- alcuni **lavori programmati** eseguiti dal worker Celery (ciclo notturno, notifiche, backup).

La PWA React è un progetto separato (`frontend/`) compilato in file statici serviti da Caddy; parla solo con l'API.

### 2.2 I processi a runtime

| Processo | Comando | Cosa fa |
|---|---|---|
| `web` | `gunicorn config.wsgi:application --workers 4 --timeout 1800` | Risponde a tutte le richieste della PWA. **Esegue in modo sincrono** anche le operazioni lente richieste dall'utente: generazione di CV, cover letter e messaggi di networking, messaggi delle chat degli editor, import da link e creazione manuale (con scoring), raccolta manuale "Collect now" (raccolta + scoring di tutte le ricerche attive), parsing del CV caricato. |
| `worker` | `celery -A config worker` | Esegue solo i task schedulati da Beat: ciclo notturno, notifiche, backup. Concorrenza = numero di CPU (oggi 1). |
| `beat` | `celery -A config beat` con `DatabaseScheduler` | Fa partire i task alle ore previste; le pianificazioni stanno nel DB e sono modificabili da Admin (§5.1, §5.5, §8.4). |

Nel codice applicativo **non c'è nessuna chiamata `.delay()` / `apply_async()`**: nessun lavoro viene accodato su Celery a partire da una richiesta dell'utente. Redis serve solo da broker/result backend per i task di Beat. Il timeout di 30 minuti di gunicorn esiste proprio perché raccolta manuale e generazioni girano dentro la richiesta (Sprint 44–45, §8.2); la PWA mostra un indicatore di caricamento e attende la risposta.

Tutti i processi condividono lo stesso codice (un'unica immagine `backend/Dockerfile`) e lo stesso database.

### 2.3 Schema a blocchi

```
                 ┌──────────────────────────────────────────┐
                 │          UTENTE (smartphone/desktop)      │
                 │     PWA React (service worker: push +     │
                 │     precache dei soli asset statici)      │
                 └─────────────────────┬────────────────────┘
                                       │ HTTPS
                                       ▼
                 ┌──────────────────────────────────────────┐
                 │  Caddy: TLS automatico, file statici PWA, │
                 │  /static/* diretti; /media/* → 404        │
                 │  /api/*, admin, /accounts/* → web         │
                 └─────────────────────┬────────────────────┘
                                       ▼
 ┌──────────────────────────────────────────────────────────────────────┐
 │ web — Django + DRF su gunicorn (4 worker, timeout 1800 s)            │
 │  • API REST, Django Admin, allauth                                    │
 │  • SINCRONO nella richiesta: generazioni CV / cover letter /          │
 │    messaggi, chat editor, import da URL, job manuale (+ scoring),     │
 │    raccolta manuale (+ scoring parallelo ×5), parsing CV caricato     │
 └───────┬──────────────────────────┬───────────────────────┬───────────┘
         │                          │                       │
         ▼                          ▼                       │
 ┌───────────────┐        ┌───────────────────┐             │
 │ PostgreSQL 16 │◄───────│ Redis (broker)    │             │
 └───────────────┘        └─────────┬─────────┘             │
         ▲                          ▼                       │
         │          ┌───────────────────────────────────┐   │
         └──────────│ worker + beat (Celery)            │   │
                    │  • 02:00 ciclo notturno           │   │
                    │    (raccolta + scoring)           │   │
                    │  • ogni 15': notifica 10:00 e     │   │
                    │    promemoria inattività          │   │
                    │  • 03:30 backup (se configurato)  │   │
                    └──────┬──────────────┬─────────────┘   │
                           │              │                 │
     ┌─────────────────────┼──────────────┼─────────────────┼──────────────┐
     ▼                     ▼              ▼                 ▼              ▼
┌──────────┐   ┌──────────────────┐ ┌──────────┐ ┌──────────────────┐ ┌──────────┐
│ Apify    │   │ AWS Bedrock      │ │ Web Push │ │ LinkedIn guest   │ │ Nominatim│
│ (raccolta│   │ (Claude: scoring,│ │ (VAPID)  │ │ API (import da   │ │ (OSM,    │
│ offerte) │   │ CV, cover letter,│ │          │ │ URL, solo web)   │ │ autocom- │
│          │   │ messaggi, chat,  │ │          │ │                  │ │ plete    │
│          │   │ parsing CV)      │ │          │ │                  │ │ città)   │
└──────────┘   └──────────────────┘ └──────────┘ └──────────────────┘ └──────────┘
                                                        Storage S3-compatibile
                                                        (backup, non configurato)
```

Apify e Bedrock sono chiamati sia dal `web` (azioni manuali) sia dal `worker` (ciclo notturno). Web Push è usato solo dal worker. LinkedIn guest API e Nominatim solo dal `web`.

Tutti i container girano sullo **stesso VPS**, orchestrati da `docker-compose.prod.yml` (§8).

### 2.4 Organizzazione del codice

App Django in `backend/apps/` (una per dominio):

| App | Contenuto principale |
|---|---|
| `accounts` | `User` custom, `AuthToken` e autenticazione a token con scadenza, registrazione (su invito)/login/logout, throttle del login, limite dei login all'admin, `/me`, comando `set_e2e_account` |
| `common` | `ai.py` (helper Bedrock), `files.py` (nomi casuali, URL firmati, ricodifica foto) e view `/api/files/…`, task di backup, comandi `restore_backup` e `secure_media_files`, test di isolamento multi-utente |
| `profiles` | `Profile` e sezioni, opzioni lingua/livello (`language_options.py`), import CV (`cv_import.py`) |
| `searches` | `SavedSearch`, limiti di piano (`services.py`), downgrade (`signals.py`), proxy Nominatim (`geo.py`) |
| `jobs` | `Job`, `DailyQuota`, `RunLog`, `JobFilterPreset`; fonte offerte (`sources/`), raccolta, scoring, import, job manuale, lista/filtri, statistiche, ciclo notturno (`tasks.py`); **tutte** le view dei job, incluse quelle di CV, cover letter, messaggi ed editor |
| `cv` | `CVDocument`, `CVDraft`, `CoverLetterDocument`, `CoverLetterDraft`, `ReferralMessageDocument`; pipeline CV (`ai_content`, `selection`, `generation`, `rendering`), gap filling, cover letter, messaggi, editor (`draft*`, `cover_letter_draft*`), template HTML |
| `notifications` | `PushSubscription`, invio push, task notifiche |

Frontend in `frontend/src/`: `pages/` (Login, Register, Onboarding, Home, JobList, JobDetail, CvDraftEditor, CoverLetterDraftEditor, Account/Impostazioni, Profile), `components/`, `api/` (client fetch e funzioni per endpoint), `i18n/` (traduzioni it/en), `sw.js` (service worker).

---

## 3. Stack tecnologico in dettaglio

### 3.1 Backend — Python + Django

Django 5.1 + Django REST Framework 3.15 (`backend/requirements.txt`). Settings unico in `config/settings.py`, configurato solo da variabili d'ambiente; dev e prod differiscono per `.env` e per il file compose. `DJANGO_DEBUG` vale `true` se non impostato; con `DEBUG=false` sono attivi `SECURE_SSL_REDIRECT`, cookie sicuri e `SECURE_PROXY_SSL_HEADER` (Caddy davanti). `TIME_ZONE = "Europe/Rome"`, `USE_TZ = True`. Nessuna cache configurata: vale la `LocMemCache` di default, per processo (usata solo dal proxy Nominatim).

Dipendenze principali: `celery`, `redis`, `psycopg2-binary`, `Pillow`, `django-allauth`, `django-celery-beat`, `anthropic` (+ `boto3`), `jsonschema`, `pdfplumber`, `python-docx`, `weasyprint`, `pywebpush`, `requests`, `gunicorn`.

### 3.2 Task in background — Celery + Redis

Celery con broker e result backend Redis (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`), serializzazione JSON, fuso `Europe/Rome`, scheduler `django_celery_beat.schedulers:DatabaseScheduler`. I task esistenti sono:

| Task | Pianificazione (creata da migrazione dati) |
|---|---|
| `apps.jobs.tasks.run_nightly_cycle` | crontab 02:00 Europe/Rome (`jobs/0003_schedule_nightly_cycle`); il nome del PeriodicTask è ancora quello storico "Ciclo notturno (raccolta, scoring, cap di intake)" |
| `apps.notifications.tasks.send_morning_notifications` | ogni 15 minuti (`notifications/0002_schedule_notification_tasks`) |
| `apps.notifications.tasks.send_inactivity_notifications` | ogni 15 minuti (stessa migrazione) |
| `apps.common.tasks.backup_database` | crontab 03:30 Europe/Rome (`common/0001_schedule_backup`) |
| `apps.common.tasks.add` | nessuna; task di prova |

Le pianificazioni sono righe di `django_celery_beat` modificabili da Admin. Le azioni dell'utente **non** passano da Celery (§2.2).

### 3.3 Frontend — React come PWA

React 19 + React Router 7, build con Vite 7, Tailwind CSS 4, componenti in stile shadcn/ui su primitive Radix (checkbox, dialog, label, radio-group, select, slot), icone `lucide-react`. Lint con `oxlint`, test e2e con Playwright (§13).

**PWA.** `vite-plugin-pwa` in modalità `injectManifest` con service worker proprio (`src/sw.js`): precache con Workbox dei soli asset di build (installabilità), `skipWaiting` + `clients.claim`, gestione di `push` e `notificationclick` (apre `/`). **Nessuna runtime cache per `/api`**: le chiamate API vanno sempre in rete. "Apertura lista immediata" resta un requisito di reattività dell'API, non di cache locale.

**Client API** (`src/api/client.js`): `fetch` su percorsi relativi `/api/...`, header `Authorization: Token <token>` se presente nel `localStorage` (chiave `app_apply_token`). Gli errori diventano `ApiError` con `status` e `detail`; un 401 con token presente (sessione scaduta o revocata) cancella il token locale ed emette l'evento `app-apply:auth-expired`, che `AuthContext` usa per tornare al login (Sprint 66). Le anteprime PDF degli editor usano un `fetch` diretto per leggere blob e header `X-Page-Count`.

**i18n.** Dizionario proprio in `src/i18n/translations.js`, lingue `it` ed `en`; lingua iniziale da `localStorage` o dal dispositivo, poi `User.interface_language` dopo il login. I messaggi d'errore del backend e i testi delle notifiche push sono solo in italiano.

**iPhone.** Le push via web funzionano su iOS solo con la PWA aggiunta alla schermata Home; l'app lo segnala in Impostazioni quando rileva iOS fuori dalla modalità standalone.

### 3.4 Database — PostgreSQL

PostgreSQL 16 (`postgres:16-alpine`), volume `postgres_data`. Tutti i dati applicativi sono legati a un `user` (§7). Migrazioni sempre committate; alcune migrazioni sono **migrazioni dati** che creano i PeriodicTask (§3.2) o normalizzano dati (`profiles/0007_normalize_language_data`).

### 3.5 Motore AI — Claude via AWS Bedrock

**Client.** Tutte le chiamate passano dall'unica funzione `call_claude_structured(model, system, user_content, schema, max_tokens, effort=None)` in `apps/common/ai.py` (Sprint 40). Usa `AnthropicBedrock(aws_region=settings.AWS_BEDROCK_REGION)` dell'SDK `anthropic`, creato a ogni chiamata; le credenziali `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` sono lette da boto3 dall'ambiente. L'API Anthropic diretta non è più usata (dal 18/08/2026, credito esaurito sulla chiave).

**Output strutturato via tool-use forzato.** Bedrock rifiuta il parametro nativo `output_config.format` (json_schema). Ogni chiamata dichiara quindi un solo tool `output` con `input_schema = schema` e `tool_choice = {"type": "tool", "name": "output"}`; la descrizione del tool vieta chiavi contenitore (es. `jsonPayload`) e campi extra. Sempre `thinking = {"type": "disabled"}`; `output_config = {"effort": …}` solo se `effort` è indicato.

**Validazione e retry.** L'input del blocco `tool_use` è validato con `jsonschema.validate`. Se non è conforme si ritenta, fino a `_MAX_ATTEMPTS = 3`, poi si solleva `StructuredOutputError`. Gli errori di rete o API di Bedrock **non** sono ritentati e si propagano al chiamante, che decide (rimborso, `RunLog`, 502…). Gli schemi non usano `minItems` / `maxItems`: i vincoli di quantità (es. 4–6 Areas of Expertise) stanno solo nei prompt.

**Modelli per uso** (variabili d'ambiente, default in `settings.py`):

| Variabile | Default | Usata da |
|---|---|---|
| `AWS_BEDROCK_REGION` | `us-east-1` | client |
| `BEDROCK_SCORING_MODEL` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | scoring |
| `BEDROCK_CV_GENERATION_MODEL` | `us.anthropic.claude-opus-5` | contenuti CV, cover letter, messaggi di networking, chat editor CV e cover letter |
| `BEDROCK_CV_PARSING_MODEL` | `us.anthropic.claude-opus-5` | import CV in onboarding |

**Punti di chiamata:**

| Uso | Modulo | Schema (sintesi) | `max_tokens` | `effort` |
|---|---|---|---|---|
| Scoring | `apps/jobs/ai_scoring.py` | `score`, `score_match[{label,reason}]`, `score_gaps[{label,reason}]`, `score_reasoning`, `language_check` | 2000 | — |
| Import CV | `apps/profiles/cv_import.py` | summary, phone, email, experiences, educations, skills, certifications, languages | 8000 | medium |
| Contenuti CV | `apps/cv/ai_content.py` | §6.2 | 4000 | medium |
| Cover letter | `apps/cv/cover_letter_content.py` | `content_language`, `translated_city`, `paragraphs[]` | 2000 | medium |
| Messaggio di networking | `apps/cv/referral_message_content.py` | `subject`, `message` | 1500 | medium |
| Chat editor CV | `apps/cv/draft_chat.py` | `reply`, `actions[]` (16 tipi) | 2000 | medium |
| Chat editor cover letter | `apps/cv/cover_letter_draft_chat.py` | `reply`, `actions[]` (3 tipi) | 2000 | medium |

**Lingua dei contenuti.** `_resolve_language` (in `ai_content.py`) passa al modello "English" se `User.cv_language_mode = english`, altrimenti "la stessa lingua della job description" con i primi 200 caratteri dell'offerta. CV e cover letter restituiscono `content_language` (enum `SUPPORTED_CV_LANGUAGES = it, en, fr, de, es`); le etichette fisse dei documenti seguono quella lingua, con fallback `en`.

**Parsing del CV caricato.** Estrazione del testo lato server (`pdfplumber` per PDF, `python-docx` per .docx: unico uso di python-docx, nessuna generazione Word), poi strutturazione con Claude sul solo testo. Dettaglio in §5.4.

### 3.6 Generazione dei documenti — HTML → PDF (WeasyPrint)

- Template Django HTML/CSS in `apps/cv/templates/cv/`: `cv_template.html` (CV) e `cover_letter_template.html` (cover letter), entrambi A4.
- `apps/cv/rendering.py` renderizza con `weasyprint.HTML(string=…).render()`, conta le pagine (`document.pages`) e scrive il PDF. Helper comune `_render_with_compact_retry(template, context, levels)`: prova i livelli in ordine e si ferma al primo che produce 1 pagina.
  - **CV**: `COMPACT_LEVELS` ha **un solo livello** a dimensione fissa (corpo 9pt, interlinea 1.25, margine 1cm, `section_gap` 8pt, `heading_gap` 4pt, `item_gap` 6pt, foto 65pt). Se il CV non entra in una pagina interviene il loop di ripiego sui bullet (§6.2); il font non si riduce mai.
  - **Cover letter**: `COVER_LETTER_COMPACT_LEVELS` ha 3 livelli (10.5pt/1.4/10pt/2.2cm → 10pt/1.3/8pt/1.8cm → 9pt/1.25/6pt/1.4cm). Se anche l'ultimo livello eccede, il PDF esce multipagina senza avvisi.
- **Font.** Il CV dichiara `"Cambria", "Caladea", "DejaVu Serif", serif`; nell'immagine è installato `fonts-crosextra-caladea` (Caladea, metricamente compatibile con Cambria, che non è redistribuibile), quindi il font effettivo è Caladea. La cover letter usa Helvetica/Arial (in pratica il sans-serif di fallback del container).
- **Dipendenze di sistema** nell'immagine: librerie Pango/Cairo/gdk-pixbuf per WeasyPrint, `postgresql-client` per backup/ripristino, font Caladea.
- **Solo PDF.** Nessuna pipeline Word. L'HTML usato per il PDF è salvato in `html_source`; lo snapshot strutturato `content_json` (§4.5, §4.10) permette di riaprire il documento nell'editor.

### 3.7 Autenticazione

- **Email + password.** `User` custom (`AbstractUser`, `email` unica; `username` = email alla registrazione). `POST /api/accounts/register/` e `/login/` creano ogni volta un **nuovo token** (`AuthToken`, §4.15: uno per login/dispositivo, 256 bit casuali da `secrets.token_urlsafe(32)`), che la PWA salva nel `localStorage` e invia come `Authorization: Token …`. Nel DB c'è solo lo SHA-256 del token.
- **Scadenza per inattività (Sprint 66).** L'autenticazione DRF è solo `apps.accounts.authentication.ExpiringTokenAuthentication` (niente `TokenAuthentication` né `SessionAuthentication` di DRF): un token non usato da più di `AUTH_TOKEN_IDLE_DAYS = 30` giorni viene cancellato e la richiesta riceve 401; a ogni uso `last_used_at` viene aggiornato, al massimo una volta l'ora. `POST /api/accounts/logout/` cancella il solo token della richiesta (gli altri dispositivi restano collegati); `apps.accounts.tokens.revoke_all_tokens(user)` li cancella tutti (per cambio password e cancellazione account, non ancora esistenti). I token DRF esistenti sono stati cancellati dalla migrazione `accounts/0008` (tutti gli utenti hanno rifatto il login); l'app `rest_framework.authtoken` non è più installata (la sua tabella resta, vuota).
- **Registrazione su invito.** Se `REGISTRATION_INVITE_CODE` è valorizzato, la registrazione richiede `invite_code` uguale (confronto a tempo costante con `hmac.compare_digest`); il controllo precede quello sull'email già registrata, quindi senza codice valido non si scopre se un'email esiste. Vuoto = registrazione aperta.
- **Login.** Messaggio d'errore unico ("Credenziali non valide.") per email inesistente e password errata; anche con email inesistente si passa da `authenticate()` (che calcola comunque un hash), così i tempi non rivelano se l'account esiste. Limiti di frequenza in §7.1.
- **Django Admin.** Usa la propria sessione Django (non l'API). Path configurabile con `DJANGO_ADMIN_PATH`; i tentativi di login falliti sono limitati per IP (§7.1).
- **Login Google.** django-allauth (`allauth.account`, `allauth.socialaccount`, provider Google, `SITE_ID = 1`), URL sotto `/accounts/` proxati da Caddy; la PWA apre `/accounts/google/login/?process=login` a piena pagina. Dallo Sprint 66 l'API non accetta più la sessione Django: al ritorno da Google l'utente avrebbe una sessione ma nessun token, quindi il percorso va completato (sessione → token) prima di attivare il login Google. Login solo via email, verifica email disattivata (`ACCOUNT_EMAIL_VERIFICATION = "none"`). Credenziali da `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`: **oggi vuote in produzione**, quindi il login Google non è attivo. `LOGIN_REDIRECT_URL` non è impostato (vale il default Django) e il ritorno da Google non è stato verificato.
- Password solo come hash (default Django), validatori standard; lunghezza massima 128 caratteri in registrazione/login.
- **Non esistono**: recupero o cambio password, cancellazione account, export dati.

### 3.8 Notifiche — Web Push

Standard Web Push con chiavi VAPID (`VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL`), invio con `pywebpush.webpush` (`apps/notifications/services.py`). La PWA legge la chiave pubblica da `GET /api/notifications/vapid-public-key/`, fa `PushManager.subscribe` e registra la sottoscrizione con `POST /api/notifications/push-subscriptions/` (`update_or_create` per utente + endpoint). Nessun servizio esterno a pagamento. Meccanismo di invio in §5.5. Non esiste un endpoint per annullare la sottoscrizione. Dallo Sprint 66 l'endpoint della sottoscrizione è accettato solo se `https`, senza porta esplicita né credenziali, con host di un push service noto (`fcm.googleapis.com`, `updates.push.services.mozilla.com`, `*.push.apple.com`, `*.notify.windows.com`); al massimo 10 sottoscrizioni per utente (oltre si eliminano le più vecchie).

---

## 4. Modello dati

Modelli Django reali, con i campi rilevanti. Tutti i timestamp sono salvati in UTC (`USE_TZ`). Salvo dove indicato, ogni record è legato direttamente o indirettamente a un `User`, con cancellazione a cascata.

### 4.1 `User` (`apps/accounts/models.py`)

Estende `AbstractUser` (quindi anche `username`, `password`, `first_name`, `last_name`, `is_staff`, `is_superuser`, `date_joined`…).

| Campo | Tipo | Significato |
|---|---|---|
| `email` | Email, unica | Identificativo di login (lo `username` è valorizzato uguale) |
| `first_name`, `last_name` | testo | Nome mostrato su CV, cover letter, firma dei messaggi e nei nomi file; se mancano si usa l'email di login |
| `plan` | `free` \| `pro` (default `free`) | Piano; modificabile solo da Admin. Il passaggio Pro→Free disattiva tutte le ricerche (segnale in `apps/searches/signals.py`) |
| `timezone` | testo, default `Europe/Rome` | Fuso per la notifica delle 10:00, per "oggi" della lista e delle statistiche. Nessuna UI per impostarlo (è scrivibile via `PATCH /api/accounts/me/`, solo con un nome IANA valido) |
| `interface_language` | `it` \| `en` (default `it`) | Lingua dell'interfaccia; non usata dal backend |
| `cv_language_mode` | `english` \| `job_language` (default `job_language`) | Lingua di CV, cover letter e messaggi |
| `cv_include_photo` | bool (default false) | Foto nel CV on/off |
| `objective_statement` | testo (max 2.000 via API) | Situazione/obiettivo raccolto in onboarding; **inerte** (non usato da nessun prompt) |
| `created_at` | datetime | Creazione; valore iniziale dei due timestamp sotto |
| `last_activity_reset` | datetime | Inizio del periodo di inattività: inizializzato a `created_at` in `save()`, aggiornato a ogni "candidatura fatta" |
| `last_notified_at` | datetime | Ultima notifica mattutina inviata; "nuovi job" = `date_collected > last_notified_at` |
| `last_inactivity_notified_at` | datetime, null | Ultimo promemoria di inattività; impedisce di rinviarlo a ogni giro finché `last_activity_reset` non cambia |
| `extra_credit` | `Decimal(8,2)`, default 0 | Saldo del credito in euro; caricato da Admin, scalato e riaccreditato in modo atomico |
| `collection_in_progress` | bool | Guardia di concorrenza della raccolta manuale (per utente) |
| `collection_started_at` | datetime, null | Inizio della raccolta in corso; la guardia è considerata stantia dopo 2 ore o se il timestamp manca |

### 4.2 `Profile` e sezioni (`apps/profiles/models.py`)

Un solo profilo master per utente. Non esiste un campo `key_achievements`: le Areas of Expertise sono calcolate dal modello a ogni generazione.

- **`Profile`**: `user` (OneToOne, `related_name="profile"`), `summary` (max 5.000 via API), `photo` (ImageField in `profile_photos/`, nome casuale `<uuid4>.<ext>`; vedi §4.15 per la ricodifica e il download), contatti per l'intestazione dei documenti: `phone`, `email` (email da mostrare sul CV, separata da quella di login; se vuota nessuna email sul CV — Sprint 41), `city`, `country_code` (ISO 3166-1 alpha-2), `linkedin_url`. La property `is_complete` è vera se esiste **almeno una voce di istruzione**; è verificata solo al momento della generazione del CV, non al salvataggio.
- **`Experience`**: `profile`, `company`, `role`, `location`, `location_country_code`, `start_date` (null), `end_date` (null = in corso), `bullets` (JSON, lista di stringhe), `technologies` (JSON, lista; nessuna UI la modifica, solo API/Admin). Via API (Sprint 66): al massimo 30 bullet da 2.000 caratteri e 50 tecnologie da 200; nessun limite al numero di esperienze.
- **`Education`**: `profile`, `institution`, `title`, `location`, `location_country_code`, `start_date` (null), `end_date` (**null ammesso** = in corso, Sprint 34), `notes` (max 3.000 via API). Mai riscritta dall'AI.
- **`Skill`**, **`Certification`**: solo `name`.
- **`Language`**: `language` (choices `LANGUAGE_CHOICES`: 36 codici ISO a 2 lettere), `level` (choices `LANGUAGE_LEVEL_CHOICES`: `elementary`, `intermediate`, `fluent`, `mother_tongue`; può essere vuoto). Le etichette tradotte in it/en/fr/de/es (`LANGUAGE_NAME_LABELS`, `LANGUAGE_LEVEL_LABELS` in `language_options.py`) servono al rendering del CV e al cap lingua dello scoring. I dati preesistenti sono stati normalizzati da `profiles/0007_normalize_language_data` (best-effort, i valori non riconosciuti restano).

### 4.3 `SavedSearch` (`apps/searches/models.py`)

- `user`, `search_type` (`job_role` "Job role keyword" | `company` "Company", default `job_role`), `keywords`, `city`, `country`, `is_active` (default **false**: una ricerca nuova nasce disattivata e si attiva con l'endpoint dedicato), `created_at`.
- Non ci sono `name` né un campo `location` unico; città e paese arrivano dall'autocomplete Nominatim.
- Limiti di piano (`apps/searches/services.py`): Free max 10 salvate e **1 attiva per tipo** (attivandone un'altra dello stesso tipo la precedente si disattiva, l'API la restituisce in `deactivated_previous`); Pro max 100 salvate e 50 attive in totale. Oltre → 400. La `PATCH` che cambia `search_type` di una ricerca attiva non ripassa dai limiti.

### 4.4 `Job` (`apps/jobs/models.py`)

Un record per offerta e per utente.

| Gruppo | Campi | Note |
|---|---|---|
| Identità | `user`, `source` (`linkedin` \| `manual`), `external_id` (255) | Unicità su (`user`, `source`, `external_id`): è la deduplica. Job manuali: `external_id = "manual-<uuid4>"` |
| Annuncio | `title`, `company`, `location` (255), `description`, `apply_url` (URL 1000, facoltativo), `published_at` (null), `salary` (255) | `published_at` è nullo per gli import da link |
| Provenienza | `matched_search` (255) | Testo libero, non FK: per le ricerche Job role `"<keywords> - <città>, <paese>"` (dal `searchString` Apify), per le Company il nome azienda; vuoto per import e job manuali |
| Dati LinkedIn | `applicants_count` (int, null), `applicants_bucket` (`under_25` \| `over_200` \| vuoto), `recruiter_name` (255), `recruiter_profile_url` (URL 500) | Valorizzati solo dalla raccolta Apify; count e bucket mai insieme |
| Sezione | `origin` (`collected` \| `imported`), `is_archived`, `is_favorite` | Sezioni: Raccolti (`collected`, non archiviati), Importati (`imported`, non archiviati: import da link **e** job manuali), Preferiti (`is_favorite`, non archiviati), Archiviati |
| Stato | `status` (`new` \| `cv_generated` \| `application_done`, default `new`) | Tre stati stabili. Tutti i job nascono `new` |
| Guardie | `cv_generation_in_progress`, `cover_letter_generation_in_progress`, `referral_message_generation_in_progress` | Flag transitori indipendenti, guardie di concorrenza (§5.2). Solo il primo corrisponde allo stato visibile "CV in generazione"; nessuno ha un timeout |
| Storico | `discarded_by_cap` | Residuo del cap di intake rimosso: non più impostato, non filtrato da lista né statistiche, visibile solo in Admin |
| Scoring | `score` (1–10, null), `score_match`, `score_gaps` (JSON), `score_reasoning` | `score` nullo = scoring fallito o mai eseguito. Match/gap sono liste di `{label, reason}`; i job scorati prima del 09/09/2026 hanno stringhe semplici, quelli prima dello Sprint 47 punteggi su 1–5 (mai riscalati) |
| Date | `date_collected` (auto all'inserimento), `date_scored`, `date_cv_generated`, `date_application_done` | `date_collected` è la base del filtro date, della riga "Importato:", delle statistiche e della notifica mattutina |

### 4.5 `CVDocument` (`apps/cv/models.py`)

Un record per ogni PDF di CV prodotto (generazione AI o finalizzazione dall'editor); mai cancellato. In UI si usa l'ultimo per `-generated_at, -id`.

- `job` (FK, `related_name="cv_documents"`), `user`;
- `html_source`: HTML usato per il PDF;
- `pdf_file`: file nella cartella media `cv_documents/`, nome casuale `<uuid4>.pdf` (Sprint 66, `apps.common.files.cv_document_upload_to`; prima `cv_<job>_<doc>.pdf`); scaricabile solo con URL firmato (§4.15);
- `generated_at`;
- `generation_type`: `automatic` | `manual`. Oggi si scrive sempre `manual`; `automatic` resta solo per i record storici;
- `extra_instructions_used`: testo "gap da colmare + indicazioni" usato nella generazione (Sprint 44, ex `enrichment_used`); vuoto per i documenti finalizzati dall'editor;
- `areas_of_expertise_grounding`: lista `[{label, grounding_reference}]` restituita dal modello, solo per diagnosi; vuota per i documenti finalizzati dall'editor;
- `content_json`: snapshot strutturato (Sprint 51), `{}` per i CV precedenti, che quindi non sono riapribili nell'editor.

Struttura di `content_json` (uguale in `CVDraft`):

```
{
  "summary": str,
  "qualification": str,
  "translated_city": str,
  "content_language": "it"|"en"|"fr"|"de"|"es",   # lingua HTML risolta
  "areas_of_expertise": [str],
  "experiences": [                                   # TUTTE le esperienze del profilo, nell'ordine del modello
    {"profile_experience_id": int, "company": str, "role": str,
     "location": str, "dates": str, "technologies": [str],
     "shown": bool,                                  # false per le escluse dal cap di 5
     "bullets": [{"text": str, "shown": bool}]}      # pool completo prodotto dall'AI, testo con **grassetto**
  ],
  "educations": [{"institution", "title", "location", "dates", "notes"}],  # stringhe già formattate
  "skills": [str], "certifications": [str],          # selezione corrente, sottoinsieme del profilo
  "languages": [{"language": codice, "level": codice}]
}
```

`shown` di un bullet indica se è sopravvissuto al taglio al budget e al loop di ripiego. Un CV già prodotto **non** cambia se il profilo viene modificato dopo.

### 4.6 `DailyQuota` (contatori giornalieri) e listino prezzi

Un record per (`user`, `date`), unico; `date` è il giorno **Europe/Rome** (`timezone.localtime(now).date()` con `TIME_ZONE = Europe/Rome`), quindi i contatori ripartono da zero alla mezzanotte di Roma. Sette contatori indipendenti:

| Contatore | Azione | Free | Pro | Oltre il massimale | Prezzo (env, default) |
|---|---|---|---|---|---|
| `manual_cv_count` | Generazione CV (anche rigenerazione, con o senza gap) | 1/g | 10/g | credito | `PRICE_MANUAL_CV_EXTRA` = 1,50 € |
| `cover_letter_count` | Generazione cover letter | 1/g | 10/g | credito | `PRICE_COVER_LETTER_EXTRA` = 1,50 € |
| `referral_message_count` | Messaggio di networking | 1/g | 10/g | credito | `PRICE_REFERRAL_MESSAGE_EXTRA` = 1,00 € |
| `import_count` | Import job da link LinkedIn | **non consentito** | 3/g | credito | `PRICE_IMPORT_EXTRA` = 0,50 € |
| `manual_job_count` | Creazione manuale di un job | 3/g | 3/g | credito | `PRICE_MANUAL_JOB_EXTRA` = 0,50 € |
| `collection_count` | Raccolta manuale "Collect now" | 1/g | 1/g | **nessuna estensione** | — |
| `cv_import_count` | Import/parsing del CV caricato (Sprint 66) | 5/g | 5/g | **nessuna estensione** (409) | — |

Azioni **sempre a credito**, senza contatore né massimale:

| Azione | Prezzo (env, default) |
|---|---|
| Messaggio nella chat dell'editor CV | `PRICE_CV_DRAFT_CHAT_MESSAGE` = 0,20 € |
| Messaggio nella chat dell'editor cover letter | `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE` = 0,20 € |

Gratuite: import/parsing del CV in onboarding (entro `CV_IMPORT_DAILY_LIMIT = 5` al giorno, senza credito; restituito se la chiamata AI fallisce), ciclo notturno, anteprime e finalizzazione delle bozze, archivio/preferiti/candidatura, filtri preferiti.

I massimali sono costanti nel codice (`MANUAL_CV_PLAN_LIMITS`, `COVER_LETTER_PLAN_LIMITS`, `REFERRAL_MESSAGE_PLAN_LIMITS`, `IMPORT_DAILY_LIMIT`, `MANUAL_JOB_DAILY_LIMIT`, `COLLECTION_DAILY_LIMIT`, `CV_IMPORT_DAILY_LIMIT`); i prezzi sono `Decimal` letti dall'ambiente (`config/settings.py`). Con saldo insufficiente l'azione è rifiutata (409, o 402 per le chat). Il controllo di piano dell'import precede quello di quota/credito.

**Riserva e restituzione.** Ogni servizio esegue in una transazione `select_for_update` (sul Job per la guardia, sulla `DailyQuota` e, se serve, sull'`User`): se il contatore è sotto il massimale lo incrementa (modalità `"quota"`), altrimenti scala il prezzo dal saldo (modalità `"credit"`). La modalità è tenuta in memoria per la durata della richiesta; in caso di eccezione `_refund` decrementa il contatore o riaccredita il prezzo. La logica è replicata in ogni servizio (`manual_generation.py`, `cover_letter_manual_generation.py`, `referral_message_manual_generation.py`, `import_service.py`, `manual_job_service.py`, `tasks.py`, `draft_chat.py`, `cover_letter_draft_chat.py`); non esiste un registro delle operazioni di addebito.

### 4.7 `RunLog` (diario tecnico)

Campi: `user` (FK, null), `job` (FK, null), `task_type`, `status` (`success` | `failure`), `message`, `started_at`, `finished_at`. Non visibile all'utente; consultabile da Admin.

| `task_type` | Quando viene scritto |
|---|---|
| `collection` | SUCCESS a ogni ciclo per utente (notturno e manuale) con `raccolti=N scorati=M scartati_scoring=K`, anche con 0 ricerche; FAILURE se la raccolta di un utente fallisce |
| `scoring` | FAILURE per ogni job il cui scoring fallisce |
| `cv_generation` | FAILURE se la generazione manuale fallisce; SUCCESS **solo** se il CV resta multi-pagina dopo il ripiego |
| `cover_letter_generation` | solo FAILURE |
| `referral_message_generation` | solo FAILURE |
| `cv_draft_chat` | solo FAILURE (chiamata AI della chat) |
| `cover_letter_draft_chat` | solo FAILURE |

Le generazioni riuscite, le anteprime e le finalizzazioni non lasciano traccia nel `RunLog`; le offerte scartate dalla raccolta (campi mancanti o troppo lunghi, duplicati) neppure.

### 4.8 `PushSubscription` (`apps/notifications/models.py`)

`user`, `endpoint` (URL 1000), `p256dh_key`, `auth_key`, `created_at`; unicità su (`user`, `endpoint`). Un utente può avere più dispositivi, al massimo 10 sottoscrizioni (le più vecchie oltre il limite vengono eliminate alla registrazione di una nuova). Endpoint ammessi solo verso i push service noti (§3.8). Una sottoscrizione per cui il push service risponde 404/410 viene eliminata all'invio (Sprint 66).

### 4.9 `CVDraft` (bozza dell'editor CV, Sprint 51)

- `job` (**OneToOne**, `related_name="cv_draft"`): una sola bozza per job, nessuno storico;
- `user`;
- `content_json`: stessa struttura di §4.5, modificata dall'editor con `PATCH` dell'intero oggetto;
- `chat_history` (Sprint 59): lista di turni
  ```
  [{"role": "user", "message": str},
   {"role": "assistant", "message": str,
    "actions": [{"type": str, "profile_experience_id": int|null, "bullet_index": int|null,
                 "area_index": int|null, "education_index": int|null, "language_index": int|null,
                 "text": str|null, "name": str|null, "level": str|null,
                 "decision": "accepted"|"rejected"}]}]      # "decision" assente finché l'utente non sceglie
  ```
- `created_at`, `updated_at`.

La bozza non ha un PDF proprio. Il seme si crea dall'ultimo `CVDocument` con `content_json` non vuoto (§5.12). La docstring del modello dice che generare un nuovo CV sovrascrive la bozza: non è implementato (§11).

### 4.10 `CoverLetterDocument` (Sprint 42)

- `job` (FK, `related_name="cover_letter_documents"`), `user`, `html_source`;
- `pdf_file`: file nella cartella media `cover_letter_documents/`, nome casuale `<uuid4>.pdf` (Sprint 66); scaricabile solo con URL firmato (§4.15);
- `generated_at`;
- `instructions_used`: indicazioni dell'utente per questa generazione (alimenta lo storico delle indicazioni riusabili); vuoto per i documenti finalizzati dall'editor;
- `content_json` (Sprint 63): `{"content_language": str, "translated_city": str, "paragraphs": [str]}`; `{}` per le lettere precedenti, non riapribili nell'editor.

Ogni generazione o finalizzazione crea un nuovo record; in UI si usa l'ultimo. Non tocca mai `Job.status` né `is_archived`.

### 4.11 `CoverLetterDraft` (Sprint 63)

`job` (OneToOne, `related_name="cover_letter_draft"`), `user`, `content_json` (stessa struttura di §4.10), `chat_history`, `created_at`, `updated_at`. Ogni turno assistente ha `actions: [{"type": "update_paragraph"|"add_paragraph"|"remove_paragraph", "paragraph_index": int|null, "text": str|null, "decision"?: "accepted"|"rejected"}]`.

### 4.12 `ReferralMessageDocument` (Sprint 50)

- `job` (FK, `related_name="referral_message_documents"`), `user`;
- `channel`: `linkedin` | `email`;
- `recipient_name` (255, facoltativo), `recipient_linkedin_url` (URL 500, facoltativo, **salvato ma inerte**: non usato nel prompt né mostrato nello storico);
- `instructions_used`, `subject` (255, vuoto per LinkedIn), `content`, `generated_at`.

Nessun PDF. Più messaggi per job (storico, mai sostituiti, non modificabili né cancellabili dall'app).

### 4.13 `JobFilterPreset` (filtri preferiti, Sprint 64)

- `user` (FK, `related_name="job_filter_presets"`), `name` (100), `created_at`; ordinamento per `created_at`;
- `scores` (JSON lista di interi), `statuses` (JSON ⊆ `new`, `cv_generated`, `application_done`), `search_ids` (JSON lista di id `SavedSearch` come stringhe numeriche o `"none"`, **non FK**: un id di una ricerca eliminata non filtra nulla), `location` (255), `applicants_ranges` (JSON ⊆ `under_25`, `25_50`, `51_100`, `101_200`, `over_200`), `has_recruiter` (`""` | `"yes"` | `"no"`).
- Mai l'intervallo di date né la sezione. Massimo 50 per utente (`MAX_JOB_FILTER_PRESETS`, tetto tecnico non legato al piano). Validazione in `JobFilterPresetSerializer`.

### 4.14 Tabelle di terze parti

- `authtoken_token` (DRF): non più usata dallo Sprint 66 (app non installata, righe cancellate dalla migrazione `accounts/0008`); i token sono in `AuthToken` (§4.15).
- Tabelle di django-allauth (`account_emailaddress`, `socialaccount_*`) e `django_site`.
- Tabelle di `django_celery_beat` (`PeriodicTask`, `CrontabSchedule`, `IntervalSchedule`…): pianificazioni dei task (§3.2).
- Sessioni Django (login Google e Admin).

### 4.15 `AuthToken` e file degli utenti (Sprint 66)

**`AuthToken`** (`apps/accounts/models.py`): `user` (FK, `related_name="auth_tokens"`), `key_hash` (SHA-256 esadecimale del token, unico), `created_at`, `last_used_at` (default now; aggiornato al più una volta l'ora), `user_agent` (primi 200 caratteri, per riconoscere il dispositivo in Admin). Il token in chiaro esiste solo nella risposta di login/registrazione e nel `localStorage` del dispositivo. In Admin la lista è in sola lettura; eliminare una riga disconnette quel dispositivo.

**File degli utenti** (`apps/common/files.py`). CV, cover letter e foto profilo stanno in `MEDIA_ROOT` (volume `media_data`) con nomi casuali (`uuid4().hex`), assegnati dalle `upload_to` `cv_document_upload_to`, `cover_letter_document_upload_to`, `profile_photo_upload_to`. Non sono mai serviti da Caddy (`/media/*` → 404, volume non montato nel container `caddy`) né da Django (nessuna rotta `/media/` neanche in sviluppo). Si scaricano solo da URL firmati:

- firma `django.core.signing.TimestampSigner` con salt distinto per tipo (`cv`, `cover-letter`, `photo`) su `"<user_id>:<doc_id>"` (foto: `"<user_id>"`), validità `SIGNED_URL_MAX_AGE = 3600` s;
- URL generati dall'API per il proprietario: `JobSerializer.cv_pdf_url` / `cover_letter_pdf_url` (ultimo documento) e `ProfileSerializer.photo_url`;
- le view `/api/files/...` non richiedono l'header `Authorization` (funzionano come semplice `<a href>`, anche nella PWA iOS) ma verificano firma, scadenza, corrispondenza documento↔firma e che il documento appartenga all'utente della firma (attivo); ogni errore → **404**, mai 403;
- risposta `FileResponse` con `Cache-Control: private, no-store`; PDF come allegato con i nomi suggeriti di sempre (`cv_download_filename`, `cover_letter_download_filename` in `apps/jobs/serializers.py`), foto inline.

Il frontend ricarica il dettaglio del job ogni 20 minuti e quando la pagina torna visibile, così i link non scadono con la pagina aperta.

**Foto profilo.** Alla scrittura (`ProfileSerializer.validate_photo` → `sanitize_photo`) è riaperta con Pillow e ricodificata da zero: solo JPEG/PNG/WebP, max 5 MB e 4000×4000 pixel, orientamento applicato ai pixel (`ImageOps.exif_transpose`), nessun metadato EXIF/GPS/XMP (resta solo il profilo colore). L'API non espone più il campo `photo` in lettura: `has_photo` (bool) e `photo_url` (firmato, `null` se assente). Il rendering PDF continua a leggerla dal filesystem (`file://{profile.photo.path}`, `generation._build_photo_url`).

**File esistenti.** Il comando idempotente `manage.py secure_media_files [--dry-run] [--delete-orphans]` rinomina con nomi casuali i file con nomi del vecchio schema aggiornando il DB (le foto vengono anche ricodificate come sopra) e, con `--delete-orphans`, elimina i file in `MEDIA_ROOT` non più referenziati da nessun record (versioni vecchie di foto, file di record cancellati).

---

## 5. I flussi principali, tradotti in tecnica

### 5.1 Ciclo notturno (raccolta → scoring)

Task `apps.jobs.tasks.run_nightly_cycle`, eseguito dal worker alle **02:00 Europe/Rome** (crontab in DB). È un batch **globale**: un solo task che itera **in sequenza** su `User.objects.all()` e per ciascuno chiama `run_nightly_cycle_for_user(user)` (funzione normale, non un task Celery). Se un utente fallisce, si scrive un `RunLog` `collection`/FAILURE e si passa al successivo.

Per ogni utente:

1. **Raccolta** (`apps/jobs/collection.py`, `collect_jobs_for_user`): chiama la fonte (§5.3) con tutte le ricerche attive dell'utente; la fonte fa **una chiamata Apify per gruppo** (tipo × città × paese), finestra "ultime 24 ore" applicata dall'actor, al massimo 150 risultati per chiamata. **Nessun tetto per piano o per notte** e **nessun cap di intake** (rimossi nello Sprint 46). Ogni offerta:
   - è scartata se manca uno dei campi `REQUIRED_FIELDS` (`title`, `company`, `location`, `description`, `apply_url`);
   - è scartata se uno dei campi `title`, `company`, `location`, `apply_url`, `matched_search`, `salary`, `recruiter_name`, `recruiter_profile_url` supera il `max_length` del modello (Sprint 49; mai troncata);
   - è scartata se il suo `external_id` esiste già tra i job LinkedIn dell'utente (archiviati e importati compresi) o è già comparso nello stesso run;
   - altrimenti diventa un `Job` con `origin=collected`, `status=new`, creato con `Job.objects.create` uno per uno (senza transazione). Gli scarti non sono registrati.
2. **Scoring** (§5.9) di tutti i job appena creati, in parallelo (`SCORING_CONCURRENCY = 5` thread). Un job il cui scoring fallisce **resta in lista senza punteggio**.
3. **`RunLog`** `collection`/SUCCESS con `raccolti=N scorati=M scartati_scoring=K`. La funzione restituisce `{collected, scored, discarded_scoring, kept}`, dove oggi `kept = scored`.

**Nessuna generazione automatica di CV** (rimossa nello Sprint 45): tutti i documenti si generano solo su richiesta.

Se una chiamata di gruppo ad Apify fallisce dopo 2 tentativi, l'eccezione risale e si perde la raccolta **intera** dell'utente per quella notte (inclusi gli altri gruppi). Un errore imprevisto durante la creazione dei job interrompe la raccolta e lascia in DB, senza punteggio, i job già creati (lo scoring parte solo a raccolta conclusa). Per rilanciare il ciclo di un solo utente serve la shell Django (`DEPLOY.md` §7.4); su quel percorso non ci sono guardie né quote.

> **Freschezza per fusi lontani.** Con un unico batch alle 02:00 Europe/Rome, gli utenti europei trovano job freschi prima delle 10:00 locali; per fusi lontani i job possono essere di molte ore prima. Accettato per l'MVP.

### 5.2 Generazione su richiesta: schema comune

Tutte le azioni manuali che producono contenuti AI (CV, cover letter, messaggio di networking) seguono lo stesso schema, **sincrono nella richiesta HTTP**:

1. **Guardia di concorrenza + riserva** in un'unica transazione (`_guard_and_reserve`): `select_for_update` sul `Job`; se il flag `*_generation_in_progress` dell'artefatto è già attivo la richiesta è rifiutata (409, nessun consumo). Per il CV si verifica anche `Profile.is_complete` (409 "Completa il profilo…"). Poi si riserva quota o credito (§4.6; saldo insufficiente → 409) e si accende il flag.
2. **Esecuzione** (chiamata Bedrock, eventuale rendering PDF, salvataggio) fuori dalla transazione, nello stesso processo gunicorn.
3. **Successo**: flag spento; per il CV `status = cv_generated`, `date_cv_generated = now`, `is_archived = False` (il job esce dall'Archivio); cover letter e messaggi non toccano lo stato del job. Risposta 201.
4. **Fallimento** (qualsiasi `Exception`): restituzione della riserva (contatore decrementato o prezzo riaccreditato), `RunLog` FAILURE, flag spento; per il CV `status` torna a `new`. Risposta 502 con messaggio generico ("Impossibile creare il CV per questo job.").

I tre flag sono indipendenti: si può generare una cover letter mentre è in corso un CV sullo stesso job. Il pulsante della PWA si disabilita durante la richiesta e, per CV e cover letter, quando il flag è attivo nel job serializzato (il flag dei messaggi non è esposto dal serializer, §11).

| Azione | Servizio | Guardia | Contatore / prezzo | Stato del job |
|---|---|---|---|---|
| Genera / rigenera CV (con "colma i gap") | `apps/cv/manual_generation.py` | `cv_generation_in_progress` | `manual_cv_count` / `PRICE_MANUAL_CV_EXTRA` | → `cv_generated` (→ `new` se fallisce); esce dall'archivio |
| Genera cover letter | `apps/cv/cover_letter_manual_generation.py` | `cover_letter_generation_in_progress` | `cover_letter_count` / `PRICE_COVER_LETTER_EXTRA` | invariato |
| Genera messaggio di networking | `apps/cv/referral_message_manual_generation.py` | `referral_message_generation_in_progress` | `referral_message_count` / `PRICE_REFERRAL_MESSAGE_EXTRA` | invariato |
| Import da link | `apps/jobs/import_service.py` | nessuna (controllo duplicato prima della riserva) | `import_count` / `PRICE_IMPORT_EXTRA`, solo Pro | nuovo job `new` |
| Job manuale | `apps/jobs/manual_job_service.py` | nessuna | `manual_job_count` / `PRICE_MANUAL_JOB_EXTRA` | nuovo job `new` |
| Raccolta manuale | `apps/jobs/tasks.py` | `User.collection_in_progress` (stantia dopo 2 h) | `collection_count`, nessun credito | nuovi job `new` |
| Messaggio chat editor | `apps/cv/draft_chat.py`, `cover_letter_draft_chat.py` | nessuna | solo credito (`PRICE_*_DRAFT_CHAT_MESSAGE`) | invariato |

Il "riprova" dopo un fallimento è una normale nuova richiesta e consuma come tale. Il timeout gunicorn (`SystemExit`) è intercettato solo dalla raccolta manuale; per le generazioni un worker ucciso a metà lascia il flag acceso e la riserva non restituita (§11).

### 5.3 La "fonte offerte" come componente sostituibile

`apps/jobs/sources/__init__.py` espone `get_job_source()`, che oggi restituisce sempre `ApifyLinkedInSource` (`apps/jobs/sources/apify_linkedin.py`). L'interfaccia ha due metodi: `fetch(searches, …)` per la raccolta e `fetch_by_url(url)` per l'import. Raccolta, scoring e generazione non dipendono dalla fonte concreta.

**Raccolta via Apify.**
- Actor `cheap_scraper~linkedin-job-scraper`, endpoint `run-sync-get-dataset-items`, autenticazione `Authorization: Bearer <APIFY_API_TOKEN>` (token solo in env, mai nell'URL).
- Le ricerche attive sono **raggruppate per (`search_type`, `city`, `country`)**: una chiamata per gruppo. Un utente con tutte le ricerche sulla stessa città fa al massimo 2 chiamate (una per tipo).
- Payload per gruppo: `keyword` = lista delle keywords per i gruppi Job role, oppure `COMPANY_SEARCH_KEYWORDS = ["jobs", "hiring"]` per i gruppi Company; `location = "<città>, <paese>"`; `publishedAt = "r86400"` (ultime 24 h); `maxItems = MAX_ITEMS_PER_CALL = 150` (minimo fatturato per chiamata dall'actor, pay-per-result); `saveOnlyUniqueItems = true`; per le Company anche **`companyInclude`** con i nomi azienda (risoluzione per azienda LinkedIn invece che full-text).
- Timeout 180 s, `MAX_ATTEMPTS = 2`. Il parametro `limit` di `fetch()` è ignorato.
- `_normalize_item` mappa i nomi alternativi dei campi Apify; `matched_search` = `searchString` (sostituito dal nome azienda per le Company); `applicationsCount` → `applicants_count` o `applicants_bucket` ("first 25" → `under_25`, "Over 200" → `over_200`); `posterFullName` / `posterProfileUrl` → recruiter; `published_at` con `parse_datetime`.

**Import da URL via API guest di LinkedIn.** `fetch_by_url` estrae l'id dall'URL (`linkedin.com/jobs/view/…<id>`) e legge `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<id>` (nessuna chiave, User-Agent da browser, timeout 15 s); il parsing dell'HTML è fatto con espressioni regolari sulle classi `topcard__title`, `topcard__org-name-link`, `topcard__flavor--bullet`, `show-more-less-html__markup`. Nessun dato su data di pubblicazione, candidati o recruiter.

> **Nota di conformità.** Lo scraping di LinkedIn tramite terze parti e la lettura della pagina guest possono violare i termini di servizio di LinkedIn. Scelta consapevole del committente per l'MVP (§11).

### 5.4 Pre-popolamento del profilo da CV caricato (onboarding)

`POST /api/profile/import-cv/` (multipart, campo `file`), view `CVImportView`, modulo `apps/profiles/cv_import.py`:

1. **Estrazione del testo** lato server: `pdfplumber` per i PDF, `python-docx` per i `.docx`; il formato si decide dai primi byte del file (`%PDF-` / `PK\x03\x04`), non da nome o content-type (Sprint 66). File mancante, formato diverso, oltre 5 MB, PDF oltre 10 pagine o `.docx` oltre 30 MB decompresso → 400; file corrotto → 422. Il testo estratto è troncato a `MAX_TEXT_LENGTH = 30.000` caratteri.
2. **Soglia**: se il testo è sotto `MIN_TEXT_LENGTH = 40` caratteri (tipico dei PDF scannerizzati; niente OCR) → 422 "non siamo riusciti a leggere il CV, compila il profilo manualmente", senza chiamare Claude.
3. **Strutturazione** con `BEDROCK_CV_PARSING_MODEL` sul solo testo. Prompt: nessuna invenzione; date ISO (primo del mese se c'è solo mese/anno); telefono ed email solo se scritti letteralmente; lingue mappate su codice ISO e uno dei 4 livelli (A1/A2 → elementary, B1/B2 → intermediate, C1 → fluent, C2/nativo → mother_tongue), voce omessa se incerta.
4. Prima della chiamata AI si riserva `DailyQuota.cv_import_count` (5/giorno, nessun credito; oltre → 409); se Bedrock fallisce la quota viene restituita e la risposta è 502 (prima: 500 non gestito). Throttle `cv_import` 10/ora (§7.1).
5. **Risposta 200** con il JSON strutturato. **Nulla viene salvato**: è la PWA a pre-compilare il form, che l'utente salva poi con le API del profilo.

L'import non consuma credito. Lato frontend il pre-fill scarta date e `technologies` delle esperienze e date dell'istruzione; città e LinkedIn non sono estratti. L'import è disponibile solo in onboarding, non nella pagina Profilo.

### 5.5 Notifiche: meccanismo

Due task Beat ogni 15 minuti iterano su tutti gli utenti (`apps/notifications/tasks.py`):

- **Mattutina** (`send_morning_notifications`): se l'ora locale dell'utente (`User.timezone`) è **10** (qualunque minuto tra 10:00 e 10:59) ed esiste almeno un `Job` con `date_collected > last_notified_at`, invia a tutte le sue `PushSubscription` il payload fisso "Nuovi job pronti" / "Ci sono nuove offerte da valutare nella tua lista." e aggiorna `last_notified_at`. Il confronto col timestamp è la guardia anti doppio invio e gestisce i fusi a est (si annuncia il batch più recente non ancora annunciato). Contano tutti i job creati (raccolti, raccolta manuale, importati, manuali, anche senza punteggio).
- **Inattività** (`send_inactivity_notifications`): se sono passati 7 giorni (`INACTIVITY_THRESHOLD`) da `last_activity_reset` e non è già stato inviato un promemoria per questo periodo (`last_inactivity_notified_at >= last_activity_reset`), invia "Non ti candidi da un po'" / "Entra nell'app e valuta le offerte in attesa." e aggiorna `last_inactivity_notified_at`.

I testi sono solo in italiano. I timestamp vengono aggiornati anche se l'utente non ha sottoscrizioni o se gli invii falliscono. Dallo Sprint 66: `webpush(..., timeout=10)`; una risposta 404/410 del push service elimina la sottoscrizione; qualunque altro errore su una sottoscrizione viene registrato nel log (solo l'id, mai l'endpoint) e si prosegue con le altre; un errore su un utente non interrompe il giro degli utenti successivi.

### 5.6 Raccolta manuale "Collect now" (Home)

`POST /api/jobs/collect/` → `run_manual_collection_for_user(user)`, **sincrono nella richiesta**:

1. Transazione con `select_for_update` su `User` e `DailyQuota`: se `collection_in_progress` è vero e non stantio (impostato da meno di `COLLECTION_STALE_AFTER = 2 h`) → 409 "Raccolta già in corso per questo account."; se `collection_count >= COLLECTION_DAILY_LIMIT = 1` → 409 "Hai già usato la raccolta manuale per oggi. Massimo 1 al giorno.". Altrimenti incrementa il contatore e accende il lock con `collection_started_at`.
2. Esegue la stessa pipeline del ciclo notturno per il solo utente (§5.1: raccolta raggruppata + scoring parallelo).
3. Successo → 200 `{collected, scored, discarded_scoring, kept}`.
4. Fallimento, compreso `SystemExit` sollevato da gunicorn al timeout: restituzione del contatore, `RunLog` FAILURE, 502 "Raccolta non riuscita. Riprova più tardi.".
5. In `finally` il lock viene rilasciato (`collection_in_progress = False`, `collection_started_at = None`).

Limite uguale per tutti i piani, senza sblocco a credito (le chiamate Apify sono fatturate comunque). Non esiste una guardia condivisa con il batch notturno: le due raccolte possono sovrapporsi (la deduplica evita i doppioni, non le doppie chiamate). Per concedere una seconda raccolta lo stesso giorno l'amministratore azzera il contatore da shell (`DEPLOY.md` §7.3).

### 5.7 Import di un job da URL LinkedIn

`POST /api/jobs/import/` con `{url}` → `import_job_from_url(user, url)`, sincrono:

1. Piano non Pro → 403 (anche con credito).
2. URL non riconosciuto → 409 "Impossibile importare quel job.".
3. `external_id` già presente tra i job LinkedIn dell'utente (anche raccolti di notte) → 409 "Questo job è già nella tua lista.".
4. Riserva `import_count` (3/giorno) o credito `PRICE_IMPORT_EXTRA`; saldo insufficiente → 409.
5. Lettura dalla API guest (§5.3). Se fallisce o mancano campi obbligatori: restituzione della riserva e 409.
6. Creazione del `Job` (`source=linkedin`, `origin=imported`, `published_at` nullo) e **scoring sincrono** (`score_job`); un fallimento di scoring non fa fallire la richiesta (job senza punteggio).
7. 201 `{job_id, status, score}`.

Il controllo `max_length` dello Sprint 49 non è applicato all'import.

### 5.8 Creazione manuale di un job

`POST /api/jobs/manual/` → `create_manual_job(user, data)`, disponibile per **entrambi i piani**:

- validazione con `ManualJobCreateSerializer`: obbligatori `title`, `company`, `location`, `description`, `published_at` (data/ora interpretata in Europe/Rome), facoltativo `apply_url` → 400 con errori per campo;
- riserva `manual_job_count` (3/giorno) o credito `PRICE_MANUAL_JOB_EXTRA`; saldo insufficiente → 409;
- creazione con `source=manual`, `external_id = "manual-<uuid4>"`, `origin=imported` (sezione Importati), poi scoring sincrono;
- 201 `{job_id, status, score}`.

Non c'è un percorso di restituzione: il job viene creato subito e un errore di scoring non fa fallire la richiesta.

### 5.9 Scoring

Moduli `apps/jobs/ai_scoring.py` (prompt, schema, chiamata) e `apps/jobs/scoring.py` (applicazione, batch, fallimenti).

- **Input del modello**: profilo completo (sommario, esperienze con bullet, competenze, istruzione, certificazioni, lingue con livello tradotto) + titolo, azienda e descrizione dell'offerta. La località del job **non** è passata.
- **Scala 1–10** con **rubrica per fascia** (Sprint 47) basata sul conteggio dei requisiti "hard" soddisfatti o mancanti: 9–10 tutti soddisfatti; 7–8 manca al più un elemento secondario; 5–6 manca almeno un requisito hard o seniority non allineata; 3–4 più requisiti mancanti o forte disallineamento; 1–2 profilo non pertinente. Descrizione vuota o non valutabile → match e gap vuoti, punteggio ≤ 6.
- **Regole** nel prompt: ogni voce di match/gap legata a un requisito esplicito dell'offerta; nessuna competenza inventata; nessun gap su elementi già nel profilo; `score_reasoning` di al massimo 2 frasi (~40 parole); `label` brevissima e `reason` di una frase; una lingua assente dal profilo non va mai tra i match.
- **Schema** `SCORE_JSON_SCHEMA`: `score` (int), `score_match` / `score_gaps` (liste di `{label, reason}`), `score_reasoning`, `language_check {required, language, international_exception}`.
- **Cap deterministico sulla lingua** (Sprint 48, `_language_score_cap`): il modello dichiara solo se l'offerta richiede una lingua (esplicitamente, o perché scritta interamente in una lingua non inglese) e se c'è un'eccezione "ambiente internazionale / inglese". In Python, se `required` è vero, non c'è eccezione e nessuna parola intera del nome lingua restituito coincide con le etichette localizzate (it/en/fr/de/es) delle lingue del profilo, il punteggio è limitato a `LANGUAGE_MISMATCH_SCORE_CAP = 3` e `score_reasoning` riceve il prefisso "Punteggio limitato a 3/10: lingua richiesta (X) assente dal profilo.". Qualsiasi livello nel profilo evita il cap; il confronto è per parola intera (non per sottostringa) e non usa i codici ISO.
- **Applicazione** (`_apply_score_result`): clamp a 1–10, cap lingua, salvataggio di `score`, `score_match`, `score_gaps`, `score_reasoning`, `date_scored`.
- **Batch** (`score_jobs`, usato da raccolta notturna e manuale): `ThreadPoolExecutor` con `SCORING_CONCURRENCY = 5` thread **solo per le chiamate Bedrock**; il profilo è caricato una volta con `prefetch_related`; i salvataggi avvengono sul thread principale. **Singolo** (`score_job`): usato da import e job manuali.
- **Scarto campi oltre `max_length`**: avviene prima, nella raccolta (§5.1), per evitare che un `DataError` interrompa il batch.
- **Fallimenti**: errore Bedrock o output fuori schema dopo 3 tentativi → il job **resta in DB e in lista con `score = NULL`** (ordinato in fondo, senza badge), `RunLog` `scoring`/FAILURE. Nessun nuovo tentativo automatico.
- **Storico**: i punteggi precedenti allo Sprint 47 restano su 1–5 e quelli precedenti allo Sprint 48 non hanno il cap; nessun ri-scoring.

### 5.10 Cover letter

`POST /api/jobs/<id>/generate-cover-letter/` con `{instructions}` → `request_cover_letter_generation` (schema §5.2) → `generate_cover_letter(job, instructions)` (`apps/cv/cover_letter_generation.py`):

1. `generate_cover_letter_content` (`cover_letter_content.py`): contesto profilo uguale a quello del CV (sommario, città, esperienze, skill, certificazioni; **non** istruzione e lingue), titolo/azienda/descrizione dell'offerta, indicazioni, lingua. Il modello scrive solo i **paragrafi del corpo** (3–5: apertura, 1–2 di esperienze reali, uno dedicato alle indicazioni se presenti, chiusura), più `translated_city` e `content_language`. Le indicazioni possono orientare il tono o introdurre fatti reali non presenti nel profilo, sotto la responsabilità dell'utente.
2. Oggetto, saluto ("Dear Hiring Manager," e simili) e chiusura sono testi fissi per lingua (`COVER_LETTER_LABELS`, 5 lingue), mai generati.
3. Intestazione: nome e cognome; riga contatti "Città tradotta, PAESE | telefono | email del profilo", **senza LinkedIn**. Nessuna data, destinatario, foto o grassetto.
4. Rendering con `render_cover_letter` (3 livelli di compattamento, §3.6), salvataggio di `CoverLetterDocument` con `instructions_used` e `content_json`.

Indicazioni riusabili: `GET /api/cover-letter-instructions/` restituisce fino a 20 testi `instructions_used` distinti, su tutti i job dell'utente, dal più recente; la PWA li propone come checkbox e li concatena al testo nuovo separati da una riga vuota.

Nome file di download: `Cover letter {Nome Cognome} - {Titolo job}.pdf` (caratteri `\/:*?"<>|` rimossi; senza nome si usa l'email); per il CV `CV {Nome Cognome} - {Titolo job}.pdf`. Entrambi calcolati da `JobSerializer`.

### 5.11 Messaggi di networking

`POST /api/jobs/<id>/generate-referral-message/` con `{channel, recipient_name?, recipient_linkedin_url?, instructions?}` → `request_referral_message_generation` (schema §5.2) → `generate_referral_message`:

- canale non valido → 400;
- `generate_referral_message_content` (`referral_message_content.py`) passa profilo, nome reale del candidato (per la firma), offerta, canale, destinatario, indicazioni e lingua; schema `{subject, message}`;
- vincoli di canale solo nel prompt: LinkedIn al massimo 80–100 parole, nessun oggetto; email con oggetto di circa 60 caratteri e corpo di 150–180 parole in 2–3 paragrafi; saluto e firma nel testo; saluto generico se manca il nome; nessuna relazione pregressa inventata; nessun allegato menzionato; richiesta finale chiara;
- salvataggio di un nuovo `ReferralMessageDocument` (nessun rendering), 201 con il messaggio serializzato (`id, channel, recipient_name, recipient_linkedin_url, subject, content, generated_at`).

Storico per job: `GET /api/jobs/<id>/referral-messages/` (dal più recente). Indicazioni riusabili: `GET /api/referral-message-instructions/` (20 distinte, tutti i job). La copia negli appunti è fatta dalla PWA (`navigator.clipboard`, con "Oggetto: …" in testa per l'email).

### 5.12 Editor delle bozze (CV e cover letter)

Stesso schema per i due documenti (moduli `apps/cv/draft.py` e `apps/cv/cover_letter_draft.py`, view in `apps/jobs/views.py`):

| Passo | CV | Cover letter |
|---|---|---|
| **Apertura** | `GET …/cv-draft/` (200 `content_json`, 404 se manca); su 404 la PWA chiama `POST …/cv-draft/` | `GET` / `POST …/cover-letter-draft/` |
| **Seed** | `seed_draft_for_job`: `update_or_create` della bozza copiando `content_json` dall'ultimo `CVDocument`; 409 se non c'è un documento o se il suo `content_json` è vuoto | `seed_cover_letter_draft_for_job`, stessa logica sull'ultima `CoverLetterDocument` |
| **Modifica** | `PATCH …/cv-draft/` con l'intero `content_json` (400 se non supera la validazione, vedi sotto), dall'autosave della PWA (debounce 1,2 s) | `PATCH …/cover-letter-draft/` |
| **Anteprima** | `POST …/cv-draft/preview/` con il contenuto corrente nel body (o quello salvato): PDF binario + header `X-Page-Count`. Nessun taglio automatico: si renderizzano solo esperienze e bullet con `shown = true`, nell'ordine della bozza; codici lingua tradotti | `POST …/cover-letter-draft/preview/`: oggetto, saluto e chiusura fissi, paragrafi e città dalla bozza |
| **Finalizzazione** | `POST …/cv-draft/finalize/` → nuovo `CVDocument` (`generation_type=manual`, `content_json` = bozza) | `POST …/cover-letter-draft/finalize/` → nuova `CoverLetterDocument` |

Proprietà comuni:
- **validazione del `content_json`** (Sprint 66, `apps/cv/draft_validation.py`) in `PATCH` e anteprima: esattamente le chiavi prodotte dalla generazione (chiavi sconosciute o mancanti → 400), tipi attesi, numero massimo di elementi (CV: 20 aree, 30 esperienze con 30 bullet e 50 tecnologie ciascuna, 20 voci di istruzione, 100 skill, 50 certificazioni, 30 lingue; cover letter: 15 paragrafi), lunghezza massima di ogni testo (es. sommario 5.000, bullet 2.000, paragrafo 3.000) e dimensione totale (200.000 caratteri di JSON). Throttle `draft_preview` 60/min sull'anteprima;
- nessuna chiamata AI e **nessun consumo** di quota o credito in apertura, modifica, anteprima e finalizzazione;
- la finalizzazione non cambia `Job.status` né `date_cv_generated`; il nuovo PDF diventa quello scaricabile; la bozza resta;
- la finalizzazione usa la bozza **salvata sul server**: le modifiche degli ultimi ~1,2 s non ancora salvate dall'autosave possono restarne fuori;
- il backend risemina con `POST`, ma la PWA chiama `POST` solo su 404: una bozza esistente **non viene riseminata** dopo una nuova generazione AI (§11).

Cosa si modifica nella bozza CV: sommario, qualifica, aree (aggiungi/rimuovi/riordina), per ogni esperienza "mostra nel CV" e ruolo (azienda, luogo, date e tecnologie no), bullet (mostra/nascondi, testo con grassetto, aggiungi/rimuovi/riordina), istruzione (tutti i campi, solo nel CV), skill e certificazioni (solo selezione tra quelle del profilo), lingue (solo nel CV). Nella bozza della cover letter solo i paragrafi (modifica, riordino, aggiunta, eliminazione). Nessuna modifica della bozza viene scritta sul profilo master.

### 5.13 Chat AI degli editor

Endpoint `…/cv-draft/chat/` e `…/cover-letter-draft/chat/` (moduli `draft_chat.py`, `cover_letter_draft_chat.py`):

- `GET` → `{history}` (404 senza bozza).
- `POST {message[, focus_bullets]}`:
  1. messaggio vuoto o oltre 2.000 caratteri → 400 (al massimo 50 `focus_bullets`); bozza assente → 502; throttle `chat` 20/min sul solo `POST`;
  2. **riserva del credito** (`select_for_update` sull'`User`): saldo sotto `PRICE_CV_DRAFT_CHAT_MESSAGE` / `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE` → **402** "Saldo credito insufficiente…"; non c'è quota gratuita;
  3. chiamata Bedrock (`BEDROCK_CV_GENERATION_MODEL`, 2000 token) con: `content_json` salvato della bozza (con gli id interni), skill/certificazioni del profilo (CV), titolo/azienda/descrizione dell'offerta, cronologia (solo i testi degli ultimi 20 turni, `MAX_HISTORY_TURNS_IN_PROMPT`, senza azioni né decisioni; la cronologia completa resta salvata), nuovo messaggio; per il CV anche i **bullet puntati** dall'utente (`focus_bullets: [{profile_experience_id, bullet_index}]`, tenuti solo se esistono), presentati come aiuto per le frasi ambigue, non come vincolo;
  4. errore AI → riaccredito, `RunLog` FAILURE, 502;
  5. **filtro difensivo** sulle azioni (`_sanitize_actions`): per il CV scarta i toggle di skill/certificazioni con nomi non presenti nel profilo e i livelli lingua non validi; per la cover letter scarta gli indici di paragrafo fuori range;
  6. accoda turno utente e risposta in `chat_history`; risponde `{reply, actions}`. **Il backend non modifica mai `content_json`**.
- `PATCH {message_index, action_index, decision}` → scrive `decision` (`accepted` | `rejected`) dentro l'azione (Sprint 62); 204, oppure 400 per indici non interi o non validi.

**Azioni.** CV, 16 tipi (`CHAT_ACTION_TYPES`): `update_summary`, `update_qualification`, `update_role`, `update_bullet`, `add_bullet`, `hide_bullet`, `show_bullet`, `hide_experience`, `show_experience`, `update_area`, `add_area`, `remove_area`, `toggle_skill`, `toggle_certification`, `update_education_notes`, `update_language_level`. Cover letter, 3 tipi: `update_paragraph`, `add_paragraph` (in coda), `remove_paragraph`. Lo schema dell'azione è "piatto" (un oggetto con `type` e campi nullable, senza `oneOf`) per compatibilità con il tool-use forzato; i riferimenti sono **indici posizionali 0-based** sulla bozza inviata.

**Pattern proposta → conferma.** Ogni azione è mostrata come card "prima → dopo" con Accetta/Rifiuta; nulla è applicato in automatico. "Accetta" applica la modifica allo stato dell'editor con le stesse funzioni dell'editing manuale, e quindi passa dall'autosave; poi la PWA registra la decisione con `PATCH`. Alla riapertura le card già decise restano disabilitate.

**Grounding.** Il testo narrativo si può amplificare oltre il profilo solo su richiesta esplicita dell'utente nella conversazione, segnalandolo nella risposta; aziende, ruoli e risultati non si inventano mai; skill e certificazioni del CV solo con nomi esatti del profilo, senza eccezioni (vincolo garantito anche dal filtro server). Nella cover letter il modello non scrive mai oggetto, saluto o chiusura.

**Costi.** Un messaggio = un addebito, a prescindere dal numero di azioni proposte; nessun `RunLog` per i messaggi riusciti.

---

## 6. Generazione del CV in dettaglio

Le regole di contenuto (qualifica, sommario, Areas of Expertise, selezione e taglio, istruzione, lingue, ordine e aspetto delle sezioni) sono definite in `Docs/03-specifiche-funzionali-contenuto-cv-v5.md`; qui la sintesi tecnica della pipeline.

### 6.1 Perché il template del prototipo non era riusabile

Il template a placeholder e il prompt del workflow *03* del prototipo erano modellati sul CV di **una persona specifica**: dati personali e contatti scritti nel documento, esperienze cablate come slot nominali con un numero fisso di bullet, una frase personale imposta come chiusura del sommario, un numero fisso di placeholder e un nome file personale. Il numero di esperienze e di bullet dipende invece dal profilo di ciascun utente: per questo il CV è generato da un template HTML con cicli e dati per-utente.

### 6.2 La pipeline di generazione (as-is)

Punto d'ingresso: `request_manual_cv_generation(job, extra_instructions)` (§5.2) → `generate_cv(job, MANUAL, extra_instructions)` in `apps/cv/generation.py`.

0. **Gap filling** (prima della pipeline, `apps/cv/gap_filling.py`). `POST …/generate-cv/` accetta `{gaps: [str], gap_instructions: str}`; `build_extra_instructions` produce: stringa vuota se non c'è nulla; solo "INDICAZIONI DEL CANDIDATO PER QUESTA GENERAZIONE" se ci sono solo indicazioni; altrimenti l'elenco numerato "GAP DA COLMARE PER QUESTA OFFERTA" (testo "etichetta (motivo)" dei gap selezionati) più le indicazioni dell'utente o `DEFAULT_GAP_INSTRUCTION`. Il testo finisce in `CVDocument.extra_instructions_used`; nulla viene salvato sul profilo.
1. **Controllo profilo**: `profile.is_complete` (≥ 1 istruzione), altrimenti `ProfileIncomplete`.
2. **Contenuti AI** (`apps/cv/ai_content.py`, `generate_cv_content`): una sola chiamata `call_claude_structured` con `BEDROCK_CV_GENERATION_MODEL`, 4000 token, effort medium. Input: profilo (sommario, città, **tutte** le esperienze ordinate per `-end_date, -start_date` con company/role/bullets/technologies, skill, certificazioni; istruzione e lingue non passano dal modello), offerta, `extra_instructions`, istruzione di lingua, intervallo 4–6 delle Areas of Expertise. Schema `CONTENT_JSON_SCHEMA` (tutti i campi obbligatori, `additionalProperties: false`):
   `summary`, `qualification`, `translated_city`, `content_language` (enum 5 lingue), `areas_of_expertise[{label, grounding_reference}]`, `experiences[{company, role, highly_relevant, bullets[{text, relevance_rank}]}]` (una voce per esperienza, stesso ordine, mai più bullet di quelli forniti), `skills[]`, `certifications[]`.
   Regole principali del prompt: nessuna invenzione, con due eccezioni controllate (Areas of Expertise per astrazione da contenuto reale; amplificazione di esperienze reali solo per i gap selezionati, mai nuovi datori di lavoro, ruoli, periodi, skill o certificazioni); qualifica dal titolo del job ripulito, o dall'esperienza più recente se ambiguo; sommario riscrivibile sulle priorità dell'offerta; grassetto `**…**` su 1–2 espressioni per bullet (§6.6).
3. **Contesto e selezione** (`_build_render_context`, `apps/cv/selection.py`):
   - lingua HTML (`_resolve_html_lang`): `en` se la modalità è "english", altrimenti `content_language` se supportata, altrimenti `en`;
   - istruzione: **tutte** le voci del profilo, ordinate per data di fine decrescente (in corso = più recente), poi durata minore, poi casuale (`select_educations_to_show`), copiate senza riformulazione;
   - budget bullet totale da `BULLET_BUDGET_BY_EDU_COUNT = {1: 18, 2: 16, 3: 14}` (con 3 o più voci si usa 14; `EDU_MAX_SHOWN = 3` è solo la soglia della tabella);
   - `_attach_facts`: riattacca per indice ai contenuti AI i dati fattuali del profilo (`profile_experience_id`, località, date formattate solo come anno, "Present" tradotto per le esperienze in corso, tecnologie), mai riformulati;
   - `select_and_cut_experiences`: oltre `MAX_EXPERIENCES_SHOWN = 5` si tengono le 5 più recenti, con uno swap singolo (la più recente tra le escluse marcate `highly_relevant` sostituisce la meno recente); si tengono i B bullet globalmente più rilevanti (`relevance_rank`); un'esperienza `highly_relevant` rimasta senza bullet ne riceve `MIN_GUARANTEED_BULLETS_FOR_RELEVANT_EXPERIENCE = 2`;
   - skill e certificazioni filtrate sui nomi esatti del profilo (`_filter_grounded_skills`); lingue tradotte nella lingua del CV.
4. **Rendering e ripiego** (`_render_with_overflow_retry`): `render_cv` a dimensione fissa (§3.6); se il PDF supera una pagina si rimuove il bullet globalmente meno rilevante (`remove_least_relevant_bullet`) e si rirenderizza, fino a `MAX_OVERFLOW_ITERATIONS = 4`. Se resta multi-pagina si salva comunque, senza errore per l'utente, con un `RunLog` `cv_generation`/SUCCESS "CV generato multi-pagina…".
5. **Snapshot** (`build_draft_content_json`): `content_json` con il pool completo di esperienze e bullet e i flag `shown` (§4.5).
6. **Salvataggio**: `CVDocument` con `html_source`, `generation_type`, `extra_instructions_used`, `content_json`, `areas_of_expertise_grounding` e il file PDF. L'orchestratore aggiorna poi lo stato del job (§5.2).

### 6.3 Dove finiscono i dati personali

Nessun dato personale è nel template. Nome e cognome vengono da `User.first_name` / `last_name` (fallback: email di login); la riga contatti è composta da `_build_contact_parts`: "Città tradotta, PAESE | telefono | email del profilo | LinkedIn", con `Profile.city`, `country_code`, `phone`, `email`, `linkedin_url` (le parti vuote sono omesse). La foto (`Profile.photo`) è inclusa solo se `cv_include_photo` è attivo e la foto esiste.

### 6.4 Template

Un **unico template CV** (`cv_template.html`), non selezionabile: non esiste un'impostazione "template" nel modello (l'onboarding mostra solo un campo disabilitato "Standard"). Per aggiungerne altri basterebbero nuovi file e un campo di scelta. La cover letter ha un proprio template separato (`cover_letter_template.html`), con stile e compattamento diversi (§3.6).

Ordine delle sezioni del CV: intestazione (nome, qualifica, contatti, foto), sommario senza titolo, Areas of Expertise su due colonne, righe "Certified in" / "Skilled in", esperienze (azienda stampata una sola volta per ruoli consecutivi nella stessa azienda, riga ruolo | luogo | date, bullet, riga tecnologie), istruzione, lingue. Etichette in 5 lingue (`SECTION_LABELS`).

### 6.5 Foto: opzione on/off

La foto compare solo con `User.cv_include_photo = true` e `Profile.photo` presente; il template gestisce l'intestazione con e senza foto (allineamento al fondo, Sprint 41). La cover letter non ha mai la foto.

### 6.6 Grassetto sulle keyword (Sprint 58)

Il modello marca con `**…**` al massimo 1–2 brevi espressioni per bullet di esperienza, testo letterale del bullet. Il filtro di template `bold_markup` (`apps/cv/templatetags/cv_extras.py`) fa l'escape HTML del testo e trasforma solo le porzioni marcate in `<strong>` (marcatori non bilanciati restano letterali); è applicato **solo ai bullet delle esperienze**, nel PDF generato, nell'anteprima e nel PDF finalizzato. Nell'editor il componente `RichBulletInput` (contentEditable, pulsante B e Ctrl/Cmd+B) converte marcatori ↔ `<strong>` e salva sempre la stringa con i marcatori.

### 6.7 Aspetto del template (sintesi)

Valori in `rendering.py` (`COMPACT_LEVELS`) e in `cv_template.html`, fissati con il committente negli Sprint 52–57: corpo 9pt Caladea, nome 18pt, qualifica 14pt, contatti 9pt, titoli di sezione 11pt maiuscoli blu `#2f4a63` con filetto (unico colore; il resto è nero), letter-spacing 0.2pt, bullet "•" a 14pt con rientro 16pt/−12pt per esperienze e aree, testo giustificato per sommario, righe Certified/Skilled in e bullet, riga lingue distribuita (`space-between`). Il dettaglio è nel documento 03.

---

## 7. Fuso orario e multi-utenza

- Il database salva tutto in UTC; la conversione all'ora locale avviene solo dove serve.
- **Due riferimenti temporali:**
  - **Europe/Rome** (`TIME_ZONE`): orario del batch notturno (02:00) e del backup (03:30), giorno delle quote (`DailyQuota.date`), interpretazione della data/ora dei job manuali;
  - **`User.timezone`** (default Europe/Rome, nessuna UI per cambiarlo): ora 10 della notifica mattutina, "oggi" del filtro date della lista e delle statistiche Home ("oggi" = dalla mezzanotte locale; "ultima settimana" = ultimi 7 giorni mobili, non legati al fuso).
- La PWA usa la data del browser per il default "oggi–oggi" del filtro date e per formattare le date mostrate.
- Per fusi lontani da Roma restano piccole incoerenze accettate (reset quote in un'ora inattesa, freschezza del batch, spostamento DST).

**Isolamento.** Tutte le view richiedono autenticazione per default (`DEFAULT_PERMISSION_CLASSES = IsAuthenticated`, Sprint 66): gli endpoint pubblici (registrazione, login, download firmati) dichiarano `AllowAny` esplicitamente. Ogni record è legato a un `user`; ogni queryset delle view filtra per l'utente autenticato (`get_object_or_404(Job, pk=pk, user=request.user)`, `filter(profile__user=…)`, ecc.): un oggetto di un altro utente restituisce 404. Coperto da `apps/common/test_multi_user_isolation.py`. I file degli utenti seguono la stessa regola tramite gli URL firmati (§4.15).

### 7.1 Limiti di frequenza e di input (Sprint 66)

**Throttling DRF** (`REST_FRAMEWORK` in `config/settings.py`), contatori nella cache Redis condivisa dai worker (`CACHES` → `REDIS_CACHE_URL`, default `redis://redis:6379/2`; nei test una `DummyCache`). L'IP del client è l'ultimo indirizzo di `X-Forwarded-For` impostato da Caddy (`NUM_PROXIES = 1`). Oltre il limite → 429.

| Scope | Limite | Dove |
|---|---|---|
| `anon` | 60/min per IP | tutte le richieste non autenticate |
| `user` | 300/min per utente | tutte le richieste autenticate |
| `login` | 10/min per IP | `POST /api/accounts/login/` |
| `login_email` | 10/ora per email (hash) | `POST /api/accounts/login/` (`LoginEmailRateThrottle`) |
| `register` | 5/ora per IP | `POST /api/accounts/register/` |
| `cv_import` | 10/ora per utente | `POST /api/profile/import-cv/` (oltre alla quota di 5/giorno) |
| `chat` | 20/min per utente | `POST` delle due chat degli editor |
| `draft_preview` | 60/min per utente | anteprime PDF delle bozze |

**Django Admin.** La view di login è sostituita da `apps/accounts/admin_login.throttled_admin_login`: dopo 10 tentativi falliti dallo stesso IP in 15 minuti (finestra fissa dal primo errore, azzerata da un login riuscito) risponde 429. Path da `DJANGO_ADMIN_PATH` (con "/" finale, default `admin/`), da passare identico anche a Caddy.

**Limiti di input** (validazione lato server, 400 oltre il limite):

| Testo | Limite |
|---|---|
| Descrizione del job manuale | 20.000 |
| Indicazioni di cover letter e messaggi di networking, istruzione "colma i gap" | 2.000 |
| Gap selezionati | 30, da 500 caratteri |
| Messaggio di chat degli editor | 2.000 |
| Nome destinatario / URL LinkedIn del destinatario | 255 / 500 |
| `objective_statement`, sommario del profilo, note istruzione, bullet | 2.000 / 5.000 / 3.000 / 2.000 (max 30 bullet) |
| `content_json` delle bozze | struttura e dimensioni in §5.12 |
| Import CV | 5 MB, 10 pagine, 30.000 caratteri estratti (§5.4) |
| Foto profilo | 5 MB, 4000×4000, JPEG/PNG/WebP (§4.15) |

Upload: `DATA_UPLOAD_MAX_MEMORY_SIZE` 2,5 MB per il corpo non-file, `FILE_UPLOAD_MAX_MEMORY_SIZE` 5 MB (oltre, l'upload passa su file temporaneo); Caddy rifiuta corpi oltre 10 MB su `/api/*`.

**Altre impostazioni.** Renderer DRF solo JSON con `DEBUG=False` (la Browsable API solo in sviluppo). `DEBUG` è falso se `DJANGO_DEBUG` manca; con `DEBUG=False` l'avvio fallisce se `DJANGO_SECRET_KEY` è vuota o contiene "insecure" (quella di sviluppo). `PATCH /api/accounts/me/` salva solo i campi modificati (`save(update_fields=…)`), così non può riscrivere `extra_credit` con un valore letto prima di un addebito o di una ricarica concorrente.

---

## 8. Hosting e deploy

Questa sezione descrive l'infrastruttura in sintesi. Procedure (avvio, aggiornamento, test in container, backup manuale, runbook) e tabella completa delle variabili d'ambiente sono in `DEPLOY.md`.

### 8.1 VPS singolo

Un VPS Linux economico (1 vCPU, ~4 GB RAM) con Docker Engine e plugin Compose; aggiornamenti di sicurezza automatici (`unattended-upgrades`, script `docker/vps-setup.sh`). Sul server non devono girare altri stack che pubblicano le porte 80/443 (incidente del 17/10/2026, `DEPLOY.md` §2).

### 8.2 Docker Compose

In produzione si usa **solo** `docker-compose.prod.yml` (mai mescolato con `docker-compose.yml`, che è per lo sviluppo: incidente del 17/08/2026, vedi `CLAUDE.md`).

| Servizio | Immagine | Ruolo |
|---|---|---|
| `db` | `postgres:16-alpine` | Database, volume `postgres_data`, healthcheck `pg_isready` |
| `redis` | `redis:7-alpine` | Broker Celery (db 0/1) e cache Django (db 2: throttling) |
| `web` | `./backend` | All'avvio `migrate` + `collectstatic`, poi `gunicorn --workers 4 --timeout 1800`; volumi `static_data`, `media_data` |
| `worker` | `./backend` | `celery worker`; volume `media_data` |
| `beat` | `./backend` | `celery beat` (`DatabaseScheduler`) |
| `frontend-build` | `./frontend` | One-shot: `npm run build` nel volume `frontend_dist`, poi termina |
| `caddy` | `caddy:2-alpine` | Porte 80/443, monta in sola lettura `static_data` e `frontend_dist` (non `media_data`, Sprint 66); access log nel volume `caddy_logs` |

Tutti i servizi hanno la rotazione dei log Docker (`json-file`, 5 file da 10 MB per container, Sprint 66). `web`, `worker` e `beat` girano come utente non privilegiato `app` (uid 1000, `backend/Dockerfile`): il codice è di root e in sola lettura, scrivibili solo `/app/staticfiles` e `/app/mediafiles`; `pg_dump` del backup e WeasyPrint funzionano senza privilegi. I volumi `media_data`/`static_data` creati prima dello Sprint 66 vanno passati a uid 1000 una volta (`DEPLOY.md` §4.5).

`web`, `worker` e `beat` condividono la stessa immagine: dopo una modifica al backend vanno ricostruiti tutti e tre. Il timeout di 1800 s e i 4 worker gunicorn servono alle operazioni sincrone (raccolta manuale con decine di job da scorare, generazioni): con 4 worker al massimo 4 operazioni lunghe possono essere in corso contemporaneamente su tutto il sito.

### 8.3 Caddy per HTTPS

`docker/caddy/Caddyfile.prod`: certificato Let's Encrypt automatico per il dominio configurato (`DOMAIN`, `CADDY_EMAIL`), compressione gzip, `reverse_proxy web:8000` per `/api/*` (corpo massimo 10 MB), il path dell'admin (`DJANGO_ADMIN_PATH`) e `/accounts/*`; serve direttamente `/static/*`; **`/media/*` risponde 404** (i file degli utenti si scaricano solo dagli URL firmati, §4.15); PWA statica con fallback su `index.html` per le rotte client-side.

Dallo Sprint 66 Caddy aggiunge a tutte le risposte (sostituendo i valori equivalenti di Django, senza duplicati) `Strict-Transport-Security: max-age=31536000`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` (anche Django usa lo stesso valore), una `Permissions-Policy` che nega camera, microfono, geolocalizzazione, pagamenti e USB, toglie l'header `Server` e applica la `Content-Security-Policy`:

`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; manifest-src 'self'; frame-src blob:; object-src blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`

Motivazioni (verificate sul bundle di build): nessuno script inline in `index.html` né `eval`, nessuna risorsa esterna; `'unsafe-inline'` negli stili perché le primitive Radix inseriscono elementi `<style>` a runtime; l'anteprima PDF degli editor è un `<iframe>` su un URL `blob:` (i documenti blob ereditano la policy, quindi servono `frame-src blob:` e `object-src blob:` per il visualizzatore PDF del browser; `frame-ancestors` e `X-Frame-Options` non si applicano ai documenti blob). Il service worker è `/sw.js` (stessa origine).

**Access log** in JSON su file nel volume `caddy_logs` (`/var/log/caddy/access.log`), ruotato ogni 24 ore o a 10 MiB e cancellato dopo 14 giorni (`roll_keep_for 336h`); il parametro `s` dei download firmati è sostituito con `REDACTED`, gli header `Authorization`/`Cookie` e `Set-Cookie` sono rimossi. Log applicativo Django su stdout (`LOGGING`: errori 5xx di `django.request`, warning e log del package `apps`), mai token, header o query string.

### 8.4 Backup

- **Implementato**: task `apps.common.tasks.backup_database` (Beat, 03:30 Europe/Rome) che esegue `pg_dump -Fc` del database e un `tar.gz` di `MEDIA_ROOT` e li carica su un bucket S3-compatibile (`BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY`, `BACKUP_S3_REGION`) con boto3. Ripristino con il comando `restore_backup AAAA-MM-GG --confirm` (`pg_restore --clean --if-exists`).
- **Non configurato in produzione**: le variabili `BACKUP_S3_*` sono vuote, quindi il task registra solo un warning e **non esiste un backup automatico fuori dal VPS**. Esistono solo dump manuali locali nella cartella `backups/` (non versionata). Il ripristino end-to-end non è mai stato provato in produzione.
- I PDF sono rigenerabili dall'HTML salvato, ma i file media (anche le foto) sono inclusi nel backup previsto.

### 8.5 Configurazione e segreti

Solo variabili d'ambiente, lette in `config/settings.py`; `.env.example` alla radice documenta le chiavi, `.env` non è mai committato. Gruppi: Django (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_ADMIN_PATH`, `REGISTRATION_INVITE_CODE`), database (`POSTGRES_*`), Celery e cache (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_CACHE_URL`), AI (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BEDROCK_REGION`, `BEDROCK_*_MODEL`), Apify (`APIFY_API_TOKEN`, l'unica letta dal codice), Google OAuth (vuote in produzione), Web Push (`VAPID_*`), prezzi (`PRICE_*`, §4.6), deploy (`DOMAIN`, `CADDY_EMAIL`), backup (`BACKUP_S3_*`, vuote in produzione). Dopo una modifica a `.env` i container vanno ricreati, non solo riavviati. I massimali giornalieri e i parametri della pipeline CV sono invece costanti nel codice.

### 8.6 Aggiornamenti di sicurezza

Aggiornamenti automatici del sistema operativo; dipendenze applicative con intervalli di versione bloccati in `requirements.txt` e `package-lock.json`, da aggiornare periodicamente a mano (Sprint 66: Django 5.2 LTS, DRF 3.16, Celery 5.5, Pillow 12). Il controllo periodico delle vulnerabilità note (`pip-audit`, `npm audit`) è nel runbook di `DEPLOY.md`.

---

## 9. Amministrazione (piani e credito)

L'amministratore gestisce piani e credito **solo dal Django Admin** (`/admin/`), oppure dalla shell Django per le operazioni non coperte (`DEPLOY.md` §7). Non esistono checkout self-service, voucher né codici sconto. Da API `plan` ed `extra_credit` sono in sola lettura.

**Modelli registrati in Admin:**

| Modello | Configurazione |
|---|---|
| `User` | `UserAdmin` di Django con un fieldset "App di ricerca lavoro": `plan`, `timezone`, `interface_language`, `cv_language_mode`, `cv_include_photo`, `objective_statement`, `extra_credit`, `last_activity_reset`, `last_notified_at`; in lista anche `plan` ed `extra_credit`. Non sono esposti `last_inactivity_notified_at`, `collection_in_progress`, `collection_started_at` |
| `Profile` | Con inline di `Experience`, `Education`, `Skill`, `Certification`, `Language` |
| `SavedSearch` | Lista con keywords, città, paese, utente, attiva |
| `Job` | Lista con titolo, azienda, utente, source, origin, status, score, archiviato, `discarded_by_cap`; filtri e ricerca |
| `DailyQuota` | In lista solo `manual_cv_count` e `import_count`; gli altri 5 contatori solo nel dettaglio |
| `RunLog` | Lista con tipo, esito, utente, job, date; filtri per tipo ed esito |
| `CVDocument` | Lista con job, utente, tipo, data |
| `PushSubscription` | Lista con utente, endpoint, data |
| `AuthToken` | Sprint 66: lista in sola lettura con utente, creazione, ultimo uso, user agent; nessuna aggiunta; eliminare una riga disconnette quel dispositivo |

Registrati automaticamente dalle librerie: sito e account social di allauth, PeriodicTask e pianificazioni di `django_celery_beat` (da qui si modificano gli orari dei task).

**Non registrati**: `CVDraft`, `CoverLetterDocument`, `CoverLetterDraft`, `ReferralMessageDocument`, `JobFilterPreset`. Per consultarli serve la shell.

Comandi di gestione: `set_e2e_account` e `seed_e2e_jobs` (solo con `DEBUG=True`, per i test e2e), `restore_backup`.

---

## 10. Cosa cambia rispetto al prototipo n8n (storico)

Riepilogo, utile a chi conosceva il prototipo, di cosa è stato **riusato** e cosa **sostituito**.

**Riusato (con adattamenti):**
- l'**actor Apify** e la modalità `run-sync-get-dataset-items`, oggi con chiamate raggruppate per tipo × città × paese e `companyInclude` per le ricerche Company;
- l'**impianto del prompt di scoring** (criteri prioritizzati, JSON match/gap), poi riscritto: scala 1–10 con rubrica, voci `{label, reason}`, cap lingua deterministico;
- l'**impianto del prompt CV** (grounding, niente invenzioni, traduzione, lunghezze), ripulito dalle parti personali e poi esteso (qualifica, Areas of Expertise, rilevanza dei bullet, gap filling, grassetto);
- il **layout visivo** del CV come punto di partenza del template HTML, poi ritoccato negli Sprint 52–57.

**Sostituito:**
- **Google Sheets → PostgreSQL**;
- **Google Drive + Google Doc "trova e sostituisci" → template HTML + WeasyPrint**;
- **OpenAI → Claude** (il prototipo, pur citando Claude, chiamava modelli OpenAI), oggi via AWS Bedrock;
- **n8n (schedulazione e orchestrazione) → Celery Beat + Django** dentro il monolite;
- **template modellato su una persona → template generico** con dati dal profilo di ciascun utente;
- **token e segreti nel workflow → variabili d'ambiente**.

Rispetto al prototipo e alle prime versioni di questo documento sono venuti meno i CV generati automaticamente di notte: oggi ogni documento è generato su richiesta.

---

## 11. Punti aperti e limiti tecnici noti

Elenco descrittivo dei difetti e dei limiti osservati nel codice al 2026-11-14 (aggiornato allo Sprint 66, che ha chiuso i punti su import CV, token senza scadenza e invio push non protetto). Non sono decisioni: sono lo stato attuale, da valutare in sprint futuri. I punti aperti delle versioni precedenti già chiusi o superati (supporto multi-filtro dell'actor, distribuzione tra ricerche con tetto unico, compattamento del CV, prezzi e modelli "da fissare", formato di `Education`, overflow estremo) sono stati tolti. La numerazione è rifatta.

**Rischi di prodotto e conformità**

1. **Conformità scraping LinkedIn.** Apify e la pagina guest di LinkedIn possono violare i termini di servizio di LinkedIn: rischio di blocco della fonte o legale, da rivalutare prima di un pubblico reale.
2. **Dipendenza dal credito Apify.** Con il credito dell'account Apify esaurito ogni chiamata risponde 403 e nessun utente riceve offerte finché il token non viene cambiato (già successo; `DEPLOY.md` §7.1). Non c'è un avviso automatico.
3. **Notifiche push su iPhone** solo con la PWA aggiunta alla Home: canale fragile proprio dove passa il valore principale del prodotto.
4. **Privacy (GDPR).** Mancano cancellazione dell'account ed export dei dati (la cancellazione a cascata dall'`User` sarebbe semplice), recupero e cambio password.

**Infrastruttura e operatività**

5. **Backup non operativo.** Il backup su storage esterno è implementato ma non configurato; nessun ripristino è mai stato provato (§8.4).
6. **Login Google non attivo** in produzione (credenziali vuote), `LOGIN_REDIRECT_URL` non impostato, ritorno da Google mai verificato. Dallo Sprint 66 l'API accetta solo token: per attivarlo serve un passaggio sessione → token dopo il ritorno da Google (§3.7).
7. **Operazioni lunghe sincrone in gunicorn.** Raccolta manuale e generazioni occupano un worker gunicorn per tutta la durata; con 4 worker, poche operazioni contemporanee bastano a rallentare tutto il sito. Un deploy o riavvio durante un'operazione la interrompe.
8. **Flag transitori senza timeout.** `cv_generation_in_progress`, `cover_letter_generation_in_progress` e `referral_message_generation_in_progress` vengono spenti solo dal codice della richiesta; se il processo muore (timeout gunicorn → `SystemExit`, non intercettato da `except Exception`; riavvio) il flag resta acceso e il job resta bloccato per quel tipo di generazione, con la riserva di quota/credito non restituita. Solo la guardia della raccolta manuale ha uno sblocco automatico (2 ore).
9. **Raccolta notturna fragile.** Un errore su un solo gruppo Apify fa perdere tutta la raccolta dell'utente; un errore durante la creazione dei job lascia job senza punteggio; i job senza punteggio non vengono mai ritentati. Il ciclo è sequenziale su tutti gli utenti in un unico task.
10. **Nessuna guardia condivisa** tra raccolta manuale e notturna (doppie chiamate Apify possibili). Lo sblocco di una seconda raccolta manuale nello stesso giorno richiede la shell.
11. **Notifiche.** Non esiste un modo per disattivare le notifiche dall'app né per annullare la sottoscrizione di un dispositivo al logout.
12. **Osservabilità limitata.** `RunLog` registra solo i fallimenti per CV, cover letter, messaggi e chat (più il caso multi-pagina del CV); le generazioni riuscite, le offerte scartate dalla raccolta (campi mancanti, troppo lunghi, duplicati) e i consumi di quota/credito non lasciano traccia. Non esiste un registro contabile del credito.
13. **Modelli non in Admin.** `CVDraft`, `CoverLetterDocument`, `CoverLetterDraft`, `ReferralMessageDocument` e `JobFilterPreset` non sono registrati; la lista `DailyQuota` mostra 2 contatori su 6; `User` in Admin non espone i campi della raccolta manuale e dell'inattività.
14. **Costi AI e Apify non stimati.** Senza tetto per notte il costo della raccolta cresce con il numero di gruppi (ogni chiamata fattura almeno 150 risultati) e quello dello scoring con il numero di offerte raccolte; nessuna soglia o monitoraggio è definito.

**Backend: difetti puntuali**

15. **Stato del job sovrascritto dalla generazione CV.** Il successo imposta sempre `status = cv_generated` e il fallimento sempre `new`, anche per un job già in `application_done` (la PWA permette di rigenerare il CV su questi job).
16. **`JobSerializer` non espone `referral_message_generation_in_progress`**: il frontend lo legge ma il valore è sempre indefinito, quindi il pulsante "Genera messaggio" si disabilita solo durante la richiesta locale (la guardia server resta attiva).
17. **`discarded_by_cap` non filtrato.** I job storici marcati dal vecchio cap compaiono in lista e nelle statistiche Home.
18. **Import da URL.** Non applica il controllo `max_length` della raccolta; il controllo duplicati avviene prima della riserva senza lock, quindi due import simultanei dello stesso URL possono arrivare al vincolo di unicità con un errore non gestito (non verificato).
19. **Job manuale senza restituzione**: se qualcosa fallisce dopo la riserva la quota resta consumata (lo scoring fallito non fa fallire la richiesta).
20. **Scoring.** Il cap lingua dipende dal fatto che il modello segnali la lingua richiesta; il prefisso del cap è sempre in italiano; la località del job non è passata al modello; i punteggi storici su 1–5 si mescolano a quelli su 1–10 in ordinamento, filtro e colori.
21. **Ricerche salvate.** La `PATCH` che cambia il tipo di una ricerca attiva non ricontrolla i limiti di piano; su Free la disattivazione automatica della ricerca precedente non è segnalata dalla UI.
22. **Profilo.** `Education.end_date` facoltativa; completezza verificata solo alla generazione; `technologies` non modificabile da UI; foto non rimovibile dalla pagina Profilo; le foto e le versioni precedenti dei documenti restano su disco finché non si esegue `secure_media_files --delete-orphans`.
23. **Messaggi e testi del backend solo in italiano** (errori API, notifiche, prefisso del cap lingua), anche con interfaccia in inglese.
24. **Commenti e docstring superati** nel codice: "3 livelli di compattamento" in `generation.py` e `draft.py`; docstring di `CVDraft` ("generare un nuovo CV sovrascrive il draft") e di `CoverLetterDraft`; nome del PeriodicTask notturno con "cap di intake"; riferimenti a `02-specifiche-tecniche-v3.md`.

**Editor e chat**

25. **Bozza non riseminata.** Dopo "Rigenera CV" o una nuova cover letter, "Modifica" riapre la bozza precedente (con la sua chat), perché la PWA chiama il seed solo su 404 e nessun codice aggiorna la bozza alla generazione.
26. **Finalizzazione e autosave.** "Genera PDF finale" usa la bozza salvata: le modifiche degli ultimi ~1,2 s possono restare fuori.
27. **Indici posizionali nelle azioni chat.** Le azioni e il puntamento dei bullet usano indici sulla bozza al momento dell'invio: dopo un riordino, o accettando più azioni `add`/`remove` dello stesso turno, gli indici successivi possono puntare all'elemento sbagliato. Il filtro server del CV non valida indici e id; quello della cover letter controlla solo il range.
28. **Contesto della chat.** Al modello arriva la cronologia senza le azioni proposte né le decisioni; lo stato reale arriva solo dal `content_json` salvato. Una decisione la cui registrazione fallisce non viene ritentata.
29. **Documenti precedenti non riapribili.** CV precedenti allo Sprint 51 e cover letter precedenti allo Sprint 63 hanno `content_json` vuoto: il pulsante "Modifica" compare ma l'apertura fallisce (409) finché non si rigenera.
30. **Grassetto** interpretato solo nei bullet delle esperienze: marcatori `**` in altri campi (es. sommario modificato a mano o dalla chat) escono come asterischi.
31. **Gap filling.** La numerazione dei gap in UI (sull'elenco completo) non coincide con quella del prompt (solo i selezionati, in ordine di clic): un'indicazione "per il gap 2" può riferirsi a un gap diverso.
32. **Cover letter.** Template non allineato allo stile del CV (font sans-serif di fallback, nessun giustificato); il pannello chat riusa testi che parlano di "CV" e "sommario"; le combinazioni di indicazioni riusate diventano nuove voci nello storico.

**Frontend**

33. **Bundle vecchio nelle tab aperte**: dopo un deploy una tab già aperta può usare la versione precedente finché non viene ricaricata (osservato nello Sprint 58); nessun ricaricamento automatico.
34. **Filtri preferiti.** Un preset creato dalla sezione Importati salva anche il filtro "Ricerca" (lì nascosto), che torna attivo applicandolo altrove; l'eliminazione è ottimistica e non gestisce l'errore dell'API.
35. **Test e2e obsoleto**: `job-list.spec.js` contiene ancora il test dell'arricchimento con "salva anche nel profilo", funzione rimossa nello Sprint 44 (§13).

**Calibrazione**

36. **Parametri della pipeline CV** (budget 18/16/14, minimo 2 bullet garantiti, 4 iterazioni di ripiego, 5 esperienze) e prezzi del listino sono valori da tarare con l'uso reale; sono costanti nel codice o variabili d'ambiente, senza impatto architetturale.

---

## 12. API REST

Tutti gli endpoint sono sotto il dominio dell'app; salvo dove indicato richiedono autenticazione (header `Authorization: Token …`, §3.7; la sessione Django non è accettata dall'API) e restituiscono 401 senza credenziali o con token scaduto/revocato. Oltre i limiti di frequenza (§7.1) rispondono 429. Ogni oggetto è filtrato sull'utente autenticato: un id di un altro utente dà **404**. Le risposte d'errore hanno la forma `{"detail": "…"}` (o gli errori per campo di DRF per i 400 di validazione). Prefissi da `backend/config/urls.py`; route in `apps/*/urls.py`.

### 12.1 Account, profilo, ricerche, notifiche

| Metodo | Path | Scopo | Risposte rilevanti |
|---|---|---|---|
| POST | `/api/accounts/register/` | Registrazione `{email, password, invite_code?}` (pubblico; `invite_code` obbligatorio se `REGISTRATION_INVITE_CODE` è valorizzato) | 201 `{token}`; 400 validazione o codice di invito errato; 429 |
| POST | `/api/accounts/login/` | Login (pubblico); crea un nuovo token per questo dispositivo | 200 `{token}`; 400 credenziali errate (messaggio generico); 429 |
| POST | `/api/accounts/logout/` | Revoca il token della richiesta (Sprint 66) | 204; 401 |
| GET, PATCH | `/api/accounts/me/` | Dati utente e preferenze: `id, email, first_name, last_name, plan, extra_credit, timezone, interface_language, cv_language_mode, cv_include_photo, objective_statement` (read-only: id, email, plan, extra_credit) | 200; 400 |
| GET, PATCH | `/api/profiles/me/` | Profilo dell'utente (creato se manca); PATCH JSON o multipart per la foto (`photo` solo in scrittura; in lettura `has_photo` e `photo_url` firmato, §4.15) | 200; 400 (anche foto non ammessa) |
| GET, PUT, PATCH | `/api/profiles/<id>/` | Stesso profilo per id (solo il proprio) | 200; 404 |
| GET, POST | `/api/experiences/`, `/api/educations/`, `/api/skills/`, `/api/certifications/`, `/api/languages/` | Elenco e creazione delle voci del profilo | 200; 201; 400 (es. lingua/livello fuori lista) |
| GET, PUT, PATCH, DELETE | `/api/<sezione>/<id>/` | Lettura, modifica, eliminazione di una voce | 200; 204; 404 |
| POST | `/api/profile/import-cv/` | Estrazione e strutturazione di un CV PDF/.docx (multipart `file`), senza salvataggio | 200 JSON strutturato; 400 file mancante, formato non supportato, oltre 5 MB o 10 pagine; 409 quota giornaliera esaurita; 422 illeggibile o testo < 40 caratteri; 502 se l'AI fallisce |
| GET, POST | `/api/searches/` | Ricerche salvate (`search_type, keywords, city, country`; `is_active` read-only) | 200; 201; 400 oltre il limite di piano |
| GET, PUT, PATCH, DELETE | `/api/searches/<id>/` | Singola ricerca | 200; 204; 404 |
| POST | `/api/searches/<id>/activate/` | Attiva; su Free disattiva la precedente dello stesso tipo | 200 (con `deactivated_previous` se applicabile); 400 limite attive Pro |
| POST | `/api/searches/<id>/deactivate/` | Disattiva | 200 |
| GET | `/api/searches-city-autocomplete/?q=` | Proxy Nominatim (min 2 caratteri, max 8 risultati, cache 1 h) | 200 lista `{city, country…}`, `[]` anche su errore di rete |
| GET | `/api/notifications/vapid-public-key/` | Chiave pubblica VAPID | 200 `{public_key}` |
| POST | `/api/notifications/push-subscriptions/` | Registra/aggiorna la sottoscrizione `{endpoint, keys:{p256dh, auth}}`; endpoint solo verso push service noti (§3.8), max 10 per utente | 201; 400 |
| GET | `/api/` | Radice del router DRF (autenticata; navigabile solo con `DEBUG=True`) | 200; 401 |
| GET | `/api/files/cv/<doc_id>/?s=…`, `/api/files/cover-letter/<doc_id>/?s=…` | Download del PDF con URL firmato (Sprint 66, §4.15); **nessun header di autenticazione richiesto** | 200 PDF allegato, `Cache-Control: private, no-store`; 404 firma assente/manomessa/scaduta o documento non dell'utente della firma |
| GET | `/api/files/photo/?s=…` | Foto profilo con URL firmato | 200 immagine inline; 404 come sopra |

### 12.2 Job: lista, azioni, raccolta, import

| Metodo | Path | Scopo | Risposte rilevanti |
|---|---|---|---|
| GET | `/api/jobs/` | Lista job (senza paginazione), ordinata per `score` decrescente (nulli in fondo) poi `date_collected` decrescente. Query: `section` (`main` default \| `imported` \| `favorites` \| `archived`), `q` (sottostringa su titolo/azienda/località; se presente ignora gli altri filtri), `date_from`, `date_to` (`YYYY-MM-DD`, fuso utente, estremi inclusi), `location`, `score` (CSV interi), `status` (CSV), `search` (CSV di id `SavedSearch` e/o `none`, in OR), `applicants` (CSV di fasce), `recruiter` (`yes` \| `no` \| `all`) | 200 lista `JobSerializer`; 400 parametro non valido |
| GET | `/api/jobs/<id>/` | Dettaglio | 200; 404 |
| GET | `/api/jobs/stats/` | Statistiche Home `{jobs:{today, week, total, manual:{…}}, cvs:{…}, applications:{…}}` | 200 |
| POST | `/api/jobs/collect/` | Raccolta manuale sincrona (§5.6) | 200 `{collected, scored, discarded_scoring, kept}`; 409 in corso o già usata oggi; 502 fallita |
| POST | `/api/jobs/import/` | Import da link LinkedIn `{url}` (§5.7) | 201 `{job_id, status, score}`; 403 non Pro; 409 URL non valido, offerta non recuperabile, duplicato, quota/credito esauriti |
| POST | `/api/jobs/manual/` | Creazione manuale (§5.8) | 201 `{job_id, status, score}`; 400 validazione; 409 quota/credito esauriti |
| POST | `/api/jobs/<id>/archive/`, `/unarchive/` | Archivia / ripristina (non cambia lo stato) | 200 job serializzato; 404 |
| POST | `/api/jobs/<id>/favorite/`, `/unfavorite/` | Preferito sì/no | 200 job serializzato; 404 |
| POST | `/api/jobs/<id>/mark-application-done/` | Candidatura fatta (anche senza CV); aggiorna `last_activity_reset` | 200 job serializzato; 409 già fatta |
| GET, POST | `/api/job-filter-presets/` | Elenco e creazione dei filtri preferiti | 200; 201; 400 validazione; 409 oltre 50 |
| DELETE | `/api/job-filter-presets/<id>/` | Eliminazione | 204; 404 |

Campi di `JobSerializer`: `id, title, company, location, description, apply_url, published_at, salary, matched_search, applicants_count, applicants_bucket, recruiter_name, recruiter_profile_url, origin, is_archived, is_favorite, status, cv_generation_in_progress, cover_letter_generation_in_progress, score, score_match, score_gaps, score_reasoning, date_collected, date_scored, date_cv_generated, date_application_done, cv_pdf_url, cv_download_filename, cover_letter_pdf_url, cover_letter_download_filename`. Dallo Sprint 66 `cv_pdf_url` e `cover_letter_pdf_url` sono URL firmati validi un'ora (`/api/files/…?s=…`, §4.15), non più il path media.

### 12.3 CV, cover letter, messaggi, editor e chat

| Metodo | Path | Scopo | Risposte rilevanti |
|---|---|---|---|
| POST | `/api/jobs/<id>/generate-cv/` | Genera/rigenera CV `{gaps?: [str], gap_instructions?: str}` (§5.2, §6.2) | 201 `{cv_document_id}`; 400 oltre i limiti di §7.1; 409 già in corso, profilo incompleto, quota/credito esauriti; 502 generazione fallita |
| GET | `/api/jobs/<id>/cv-draft/` | Bozza CV | 200 `content_json`; 404 |
| POST | `/api/jobs/<id>/cv-draft/` | Crea o risemina la bozza dall'ultimo CV | 201 `content_json`; 409 nessun CV riapribile |
| PATCH | `/api/jobs/<id>/cv-draft/` | Sostituisce l'intero `content_json` | 200; 400 struttura o dimensioni non valide (§5.12); 404 |
| POST | `/api/jobs/<id>/cv-draft/preview/` | Anteprima PDF (body facoltativo con il contenuto) | 200 `application/pdf` + `X-Page-Count`; 400 come sopra; 404; 429 |
| POST | `/api/jobs/<id>/cv-draft/finalize/` | Nuovo `CVDocument` dalla bozza, gratuito | 201 `{cv_document_id}`; 409 nessuna bozza |
| GET | `/api/jobs/<id>/cv-draft/chat/` | Cronologia chat CV | 200 `{history}`; 404 |
| POST | `/api/jobs/<id>/cv-draft/chat/` | Messaggio `{message, focus_bullets?: [{profile_experience_id, bullet_index}]}` | 200 `{reply, actions}`; 400 vuoto o oltre 2.000 caratteri; 402 credito insufficiente; 429; 502 AI fallita o bozza assente |
| PATCH | `/api/jobs/<id>/cv-draft/chat/` | Decisione `{message_index, action_index, decision}` | 204; 400 |
| POST | `/api/jobs/<id>/generate-cover-letter/` | Genera cover letter `{instructions?}` (§5.10) | 201 `{cover_letter_document_id}`; 400 indicazioni oltre 2.000 caratteri; 409; 502 |
| GET | `/api/cover-letter-instructions/` | Ultime 20 indicazioni distinte | 200 `{instructions}` |
| GET, POST, PATCH | `/api/jobs/<id>/cover-letter-draft/` | Bozza cover letter (come per il CV) | 200 / 201; 400; 404; 409 |
| POST | `/api/jobs/<id>/cover-letter-draft/preview/` | Anteprima PDF | 200 `application/pdf` + `X-Page-Count`; 404 |
| POST | `/api/jobs/<id>/cover-letter-draft/finalize/` | Nuova `CoverLetterDocument` dalla bozza, gratuita | 201 `{cover_letter_document_id}`; 409 |
| GET, POST, PATCH | `/api/jobs/<id>/cover-letter-draft/chat/` | Chat cover letter (`POST {message}`, senza `focus_bullets`) | come la chat CV: 200 / 204; 400; 402; 404; 502 |
| POST | `/api/jobs/<id>/generate-referral-message/` | Messaggio di networking `{channel, recipient_name?, recipient_linkedin_url?, instructions?}` (§5.11) | 201 messaggio; 400 canale non valido o testi oltre i limiti; 409; 502 |
| GET | `/api/jobs/<id>/referral-messages/` | Storico messaggi del job, dal più recente | 200 lista |
| GET | `/api/referral-message-instructions/` | Ultime 20 indicazioni distinte | 200 `{instructions}` |

### 12.4 Altri URL serviti dal backend

| Path | Scopo |
|---|---|
| `/admin/` (o `DJANGO_ADMIN_PATH`) | Django Admin (sessione, utenti staff); login limitato a 10 errori per IP in 15 minuti (429) |
| `/accounts/…` | django-allauth (login Google: `/accounts/google/login/`, callback) |
| `/static/…` | Servito direttamente da Caddy in produzione |
| `/media/…` | **Mai servito** (404 da Caddy; nessuna rotta Django): i file si scaricano da `/api/files/…` |

---

## 13. Test

### 13.1 Suite backend

299 test Django (`python manage.py test`), **tutti verdi il 2026-11-14 (Sprint 66)** se lanciati con `DJANGO_DEBUG=true` (con la configurazione di produzione `DEBUG=false` il redirect HTTPS fa rispondere 301 al test client e ~60 test falliscono senza regressioni reali: procedura in `DEPLOY.md` §4.4). Il database di test è separato. Le chiamate esterne (Bedrock, Apify, LinkedIn, Nominatim, Web Push, S3) sono sempre simulate con mock.

| File | Test | Cosa copre |
|---|---|---|
| `apps/jobs/tests.py` | 105 | Raccolta per utente (campi obbligatori, dedup, scarto oltre `max_length`, assenza di cap), scoring singolo e parallelo (concorrenza, fallimenti, cap lingua e regressione sottostringa), ciclo notturno per utente e orchestratore, assenza di CV automatici, raccolta manuale (guardia, guardia stantia, quota, rimborso, `SystemExit`) e relativa API, schedulazione del ciclo notturno, import da link (servizio e API), job manuale (servizio e API), lista e filtri (sezioni, date nel fuso utente, location, candidati, recruiter, ricerca multipla, ricerca testuale), archivio, preferiti, dettaglio, candidatura fatta (anche senza CV), API dei messaggi di networking, filtri preferiti, comando `seed_e2e_jobs` |
| `apps/jobs/sources/tests.py` | 26 | Fonte Apify (payload raggruppato, Company con `companyInclude`, normalizzazione, candidati e recruiter, retry) e import via API guest |
| `apps/cv/tests.py` | 31 | Generazione CV (un blocco per esperienza, 1 pagina su profilo standard, foto on/off, istruzione copiata dal profilo, CV congelato dopo modifiche al profilo, modalità lingua, ripiego per overflow e `RunLog` multi-pagina), generazione manuale (quota nel giorno Europe/Rome, credito, concorrenza, rimborso, ritorno a `new`, uscita dall'archivio), messaggi di networking (8 test: quota, più messaggi per job, concorrenza, credito, rimborso, indicazioni) |
| `apps/cv/test_selection.py` | 19 | Selezione dell'istruzione, budget bullet, cap esperienze con swap, taglio per rilevanza, rimozione del bullet meno rilevante |
| `apps/notifications/tests.py` | 18 | Notifica mattutina (ora locale, `last_notified_at`), promemoria di inattività, API sottoscrizione e chiave VAPID; Sprint 66: allowlist degli endpoint, massimo 10 sottoscrizioni, `timeout=10`, 410 → sottoscrizione eliminata, un errore non interrompe il giro (né sulle altre sottoscrizioni né sugli altri utenti) |
| `apps/common/test_multi_user_isolation.py` | 11 | Isolamento dei dati tra utenti sulle API |
| `apps/searches/tests.py` | 10 | Limiti di piano delle ricerche, attivazione per tipo su Free, downgrade, modifica |
| `apps/profiles/tests.py` | 7 | API del profilo (foto: `has_photo` e `photo_url` firmato); import CV (4 test, di cui 2 con `call_claude_structured` simulato) |
| `apps/common/tests.py` | 5 | Schedulazione e task di backup, comando `restore_backup` |
| `apps/accounts/tests.py` | 7 | `/me` (plan e credito esposti e read-only, nome modificabile, nessun lost update di `extra_credit`, fuso orario validato), comando `set_e2e_account` |
| `apps/accounts/test_security.py` | 21 | Sprint 66: token (solo hash nel DB, un token per login/dispositivo, logout revoca solo il corrente, scadenza a 30 giorni di inattività con scorrimento, `last_used_at` al più ogni ora, `revoke_all_tokens`), errore di login generico, permessi di default e sessione non accettata dall'API, codice di invito (errato, mancante, corretto, vuoto = aperta, nessuna rivelazione dell'email), throttling di login per IP e per email e della registrazione, limite dei login falliti all'admin |
| `apps/common/test_files.py` | 19 | Sprint 66: download firmati (proprietario senza header, altro utente, firma assente/manomessa/scaduta/di un altro tipo o documento → 404, `/media/` non servito, header di risposta), URL firmati nel `JobSerializer`, nomi casuali, foto (EXIF/GPS rimossi e orientamento applicato, formato/dimensioni/peso, URL firmato), comando `secure_media_files` (dry-run, rinomina idempotente con ricodifica delle foto, orfani) |
| `apps/jobs/test_input_limits.py` | 16 | Sprint 66: limiti di lunghezza (descrizione job manuale, messaggi di chat, indicazioni cover letter, gap, destinatario), validazione del `content_json` delle bozze CV e cover letter in PATCH e anteprima, import CV (5 MB, formato dai primi byte, 10 pagine, troncamento del testo, quota giornaliera, errore AI → 502 con quota restituita), limiti dei bullet del profilo |
| `apps/searches/test_geo.py` | 4 | Proxy di autocomplete città (con una LocMemCache: nei test la cache di default è una DummyCache) |

Prima di chiudere uno sprint che tocca i modelli va eseguito anche `makemigrations --check`; dallo Sprint 66 anche `check --deploy` con `DEBUG=false` (nessun problema segnalato: i warning su HSTS `includeSubDomains`/`preload` sono silenziati per scelta).

### 13.2 Test end-to-end (Playwright)

In `frontend/e2e/` (`npm run test:e2e`, configurazione `playwright.config.js`, base URL da `E2E_BASE_URL`), con account e job preparati dai comandi `set_e2e_account` e `seed_e2e_jobs` (richiedono `DEBUG=True`):

- `auth-onboarding.spec.js`: registrazione e onboarding manuale, raggruppamento esperienze per azienda, login errato, lingua dell'interfaccia (browser it/en, switcher);
- `account.spec.js`: piano e saldo, ciclo di vita di una ricerca salvata, limite di piano, persistenza delle impostazioni, istruzione iOS per le push;
- `job-list.spec.js`: sezioni, filtri (punteggio, stato, location, ricerca multi-selezione, candidati, recruiter), ricerca testuale, archivio con annulla e swipe, generazione CV (pulsante disabilitato), link annuncio e candidatura senza CV, espandi motivazioni, badge candidati e icona recruiter, preferiti, filtri preferiti;
- `push-subscription.spec.js`: sottoscrizione push verificata lato backend (endpoint finto su `fcm.googleapis.com`, per passare l'allowlist dello Sprint 66).

L'esecuzione degli e2e non è documentata negli ultimi sprint. `job-list.spec.js` contiene ancora il test "arricchimento con 'salva anche nel profilo'", relativo a una funzione rimossa nello Sprint 44: con il codice attuale non può passare.

### 13.3 Cosa non è coperto

- `apps/common/ai.py`: tool-use forzato, validazione `jsonschema`, retry, `StructuredOutputError`;
- **cover letter**: generazione, quota e credito, endpoint, nomi file, bozza, chat (nessun test);
- **editor CV** (`draft.py`: seed, anteprima, finalizzazione) e **chat** (`draft_chat.py`: azioni, filtro difensivo, `focus_bullets`, credito, `record_action_decision`), e i relativi endpoint;
- filtro `bold_markup` e componente `RichBulletInput`;
- statistiche Home (`stats.py`, `/api/jobs/stats/`);
- gap filling (`gap_filling.py`) e il suo passaggio nel prompt;
- filtro di grounding su skill/certificazioni del CV (`_filter_grounded_skills`), etichette nelle 5 lingue, grassetto nel PDF;
- normalizzazione delle lingue (`profiles/0007`), validazione delle choices di `Language`, `Profile.email`;
- login Google;
- renderer solo JSON con `DEBUG=False` (i test girano con `DEBUG=True`), header di Caddy e CSP (verificati solo con `caddy validate` e una prova manuale);
- frontend senza test unitari: editor, chat, Home e dialog di cover letter e messaggi non hanno test e2e.

---

*Fine del documento.*
