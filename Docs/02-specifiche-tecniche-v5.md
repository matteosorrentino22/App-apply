# Specifiche Tecniche — App di ricerca lavoro e generazione CV

> **Documento:** 02 — Specifiche tecniche
> **Versione:** 5 — descrizione **as-is al 2026-11-14** (Sprint 66 sicurezza, Sprint 67 privacy e GDPR, Sprint 68 lista job, scoring e raccolta, Sprint 69 generazione, editor e chat, Sprint 70 account, profilo, notifiche e frontend, Sprint 71 testi del backend in it/en, Sprint 72 fondamenta, Sprint 73 navigazione, Sprint 74 lista Jobs, Sprint 75 dettaglio job e Sprint 76 editor, Sprint 79 accesso e onboarding, Sprint 80 rifinitura, Sprint 81 correzioni dopo la prova su iPhone, Sprint 82 anteprima PDF su mobile, attività come chip, stipendio e contratto e Sprint 78 profilo e impostazioni del redesign UI, Sprint 77 raccolta automatica Pro)
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
> **Numerazione.** La numerazione dei paragrafi §1–§11 delle versioni precedenti è mantenuta, perché il codice la cita nei commenti (es. §3.5, §3.8, §5.1, §5.2, §5.3, §5.5, §6.3, §8.4). Le parti nuove sono aggiunte in coda ai paragrafi esistenti (§4.9–§4.16, §5.6–§5.21, §6.6–§6.7) o come nuove sezioni (§12 API REST, §13 Test). I commenti nel codice citano ancora `02-specifiche-tecniche-v3.md`: vanno letti come riferimenti a questo documento.

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
| 67 | Privacy e GDPR: consensi in registrazione e gate delle accettazioni (`LegalAcceptance`), verifica email, recupero e cambio password, email di servizio via Celery, export ZIP e cancellazione dell'account, preferenza notifiche, Bedrock in UE, backup locale ruotato, access log senza token | §3.5, §3.7, §4.1, §4.16, §5.14–§5.18, §7.1, §8, §12, §13 |
| 71 | Testi del backend rivolti all'utente tradotti con gettext (msgid italiani, `locale/en/LC_MESSAGES/django.po` con `.mo` committato): lingua da `Accept-Language` nelle richieste API (`ApiLocaleMiddleware`), da `User.interface_language` in notifiche e scoring; email di servizio sullo stesso meccanismo; messaggio proprio per il 429 | §3.1, §3.3, §5.21, §13 |
| 68 | `Job.matched_saved_search` (FK) per il filtro "Ricerca"; eliminazione dei job del vecchio cap e rimozione di `discarded_by_cap`; punteggi 1–5 riscalati ×2; retry dello scoring (`scoring_failures`); raccolta isolata per gruppo Apify con scarti ed esiti nel `RunLog`; guardia condivisa manuale/notturna; limiti di piano sulla `PATCH` del tipo; import e job manuale robusti; località nel prompt di scoring; azioni Admin sui contatori | §4.4, §4.7, §5.1, §5.3, §5.6–§5.9, §9 |

Decisioni delle versioni precedenti **superate dal codice** e quindi tolte da questo documento: limite di raccolta 50/100 job per utente per notte; cap di intake di 15 job/giorno con tie-break; generazione automatica dei CV per i job 4–5; una sola chiamata Apify per utente; scoring fallito = offerta scartata; scala 1–5; "riserva all'accodamento" con task Celery per le generazioni manuali; 3 livelli di compattamento del CV; selezione delle 3 voci di istruzione più recenti; budget bullet 12/10/9 distribuito per peso; arricchimento del profilo salvabile; `Education.end_date` obbligatoria; voucher.

### Storico versioni (condensato)

- **v1–v2** (luglio 2026): architettura monolitica Django + Celery, modello dati, flussi del ciclo notturno, deploy su VPS con Docker Compose. Batch alle 02:00 Europe/Rome, riserva della quota con restituzione su fallimento, foto on/off, pipeline di parsing del CV caricato.
- **v3** (luglio 2026, revisione criticità): credito come saldo in euro con listino; niente Word; una chiamata Apify per utente con limite 50/100; reset quote a mezzanotte Europe/Rome; notifica basata su `last_notified_at`; guardia di concorrenza. Aggiornata poi in place con gli sprint 39 e 47.
- **v4** (01/08/2026): recepisce il documento 03 v3 (pipeline CV con budget deterministico e loop di ripiego, `Education.start_date/end_date`, rimozione di `key_achievements`).
- **v5** (14/11/2026): fusione di v3 e v4, allineamento all'as-is degli sprint 40–64, aggiunte le sezioni API REST (§12) e Test (§13). Aggiornata in place con lo Sprint 66 (sicurezza), lo Sprint 67 (privacy e GDPR), gli Sprint 68–70 e lo Sprint 71 (testi del backend in it/en).

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
| Motore AI | Claude via **AWS Bedrock** (`AnthropicBedrock`), helper unico `apps/common/ai.py` | Output strutturato con tool-use forzato e validazione `jsonschema`, modelli per uso configurabili da env; default in UE (Sprint 67). |
| Usi dell'AI | Scoring, parsing del CV caricato, contenuti del CV, cover letter, messaggi di networking, chat degli editor | Sette punti di chiamata, tutti dallo stesso helper. |
| Documenti | Template HTML/CSS → PDF con WeasyPrint (CV in Caladea a dimensione fissa; cover letter a 3 livelli di compattamento) | Solo PDF; editor in-app con bozza e chat AI. |
| Credito | Saldo in € (`Decimal`) + listino prezzi unitari da env | Oltre il massimale giornaliero si paga a credito; le chat sono sempre a credito. |
| Autenticazione | Email/password con token propri (`AuthToken`, scadenza dopo 30 giorni di inattività) + login Google (django-allauth) | Google è implementato ma **non configurato in produzione** (pulsante nascosto); registrazione su invito opzionale; consensi obbligatori, verifica email e recupero password (Sprint 67). |
| Notifiche | Web Push (VAPID, `pywebpush`); email di servizio via SMTP (Gmail) | Notifica a fine raccolta automatica (Pro, se ci sono job nuovi; Sprint 77, prima alle 10 locali) e promemoria di inattività a 7 giorni, disattivabili; email solo di servizio (verifica, recupero password, cancellazione). |
| Hosting | VPS singolo economico | Tutto lo stack su un server con Docker. |
| Deploy | Docker Compose (`docker-compose.prod.yml`) + Caddy | HTTPS automatico; un solo file compose in produzione. |
| Backup | Task Celery `pg_dump` + media: su storage S3-compatibile se configurato, altrimenti in un volume locale con rotazione a 7 giorni | In produzione è attivo il backup **locale** (Sprint 67), sullo stesso VPS (§8.4). |
| Amministrazione | Django Admin | Piani e credito si gestiscono solo da Admin; non esistono voucher né checkout. |

L'app deriva dal **prototipo n8n** del committente (workflow *01 Job Collection*, *02 Job Scoring*, *03 CV Generation*), da cui sono stati recuperati l'actor Apify, l'impianto dei prompt e il layout del CV; Google Sheets e Google Drive sono stati sostituiti da PostgreSQL e dalla generazione PDF sul server (§10).

---

## 2. Architettura generale

### 2.1 Il principio: un monolite

L'applicazione è un **unico progetto Django** che espone:

- un'**API REST** (`/api/...`) consumata dalla PWA (§12);
- il **Django Admin** (path da `DJANGO_ADMIN_PATH`, default `/admin/`) per l'amministrazione (§9);
- gli URL di **django-allauth** (`/accounts/...`) per il login Google;
- alcuni **lavori programmati** eseguiti dal worker Celery (raccolte automatiche Pro, promemoria, backup) e l'invio delle **email di servizio** (Sprint 67).

La PWA React è un progetto separato (`frontend/`) compilato in file statici serviti da Caddy; parla solo con l'API.

### 2.2 I processi a runtime

| Processo | Comando | Cosa fa |
|---|---|---|
| `web` | `gunicorn config.wsgi:application --workers 4 --timeout 1800` | Risponde a tutte le richieste della PWA. **Esegue in modo sincrono** anche le operazioni lente richieste dall'utente: generazione di CV, cover letter e messaggi di networking, messaggi delle chat degli editor, import da link e creazione manuale (con scoring), raccolta manuale "Collect now" (raccolta + scoring di tutte le ricerche attive), parsing del CV caricato. |
| `worker` | `celery -A config worker` | Esegue i task schedulati da Beat (raccolte automatiche Pro, promemoria di inattività, backup) e, dallo Sprint 67, l'invio delle email di servizio accodate dal `web`. Concorrenza = numero di CPU (oggi 1). |
| `beat` | `celery -A config beat` con `DatabaseScheduler` | Fa partire i task alle ore previste; le pianificazioni stanno nel DB e sono modificabili da Admin (§5.1, §5.5, §8.4). |

L'unico lavoro accodato su Celery da una richiesta dell'utente è l'**invio delle email di servizio** (`send_service_email.delay`, Sprint 67, §5.14): un invio SMTP lento o fallito non deve bloccare né far fallire la richiesta. Nessun'altra azione dell'utente usa `.delay()` / `apply_async()`. Redis serve da broker/result backend per questi task e, dallo Sprint 66, da cache per il throttling (§7.1). Il timeout di 30 minuti di gunicorn esiste proprio perché raccolta manuale e generazioni girano dentro la richiesta (Sprint 44–45, §8.2); la PWA mostra un indicatore di caricamento e attende la risposta.

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
                    │  • ogni 15': raccolte automatiche │   │
                    │    Pro (raccolta + scoring)       │   │
                    │  • ogni 15': promemoria           │   │
                    │    inattività                     │   │
                    │  • 03:30 backup (locale o S3)     │   │
                    │  • email di servizio (Gmail SMTP) │   │
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
                                                        (backup, facoltativo, non
                                                        configurato) · Gmail SMTP
                                                        (email di servizio)
```

Apify e Bedrock sono chiamati sia dal `web` (azioni manuali) sia dal `worker` (raccolte automatiche Pro). Web Push e l'SMTP delle email di servizio sono usati solo dal worker. LinkedIn guest API e Nominatim solo dal `web`.

Tutti i container girano sullo **stesso VPS**, orchestrati da `docker-compose.prod.yml` (§8).

### 2.4 Organizzazione del codice

App Django in `backend/apps/` (una per dominio):

| App | Contenuto principale |
|---|---|
| `accounts` | `User` custom, `AuthToken` e autenticazione a token con scadenza, registrazione (su invito)/login/logout, throttle del login, limite dei login all'admin, `/me`, comando `set_e2e_account`; dallo Sprint 67 `LegalAcceptance` e versioni dei testi (`legal.py`), gate delle accettazioni (`permissions.py`), verifica email e recupero/cambio password, email di servizio (`emails.py`, `tasks.py`), export e cancellazione dell'account (`account_data.py`, `signals.py`) |
| `common` | `ai.py` (helper Bedrock), `files.py` (nomi casuali, URL firmati, ricodifica foto) e view `/api/files/…`, task di backup (S3 o locale ruotato), comandi `restore_backup` e `secure_media_files`, test di isolamento multi-utente |
| `profiles` | `Profile` e sezioni, opzioni lingua/livello (`language_options.py`), import CV (`cv_import.py`) |
| `searches` | `SavedSearch`, limiti di piano (`services.py`), downgrade (`signals.py`), proxy Nominatim (`geo.py`) |
| `jobs` | `Job`, `DailyQuota`, `RunLog`, `JobFilterPreset`; fonte offerte (`sources/`), raccolta, scoring, import, job manuale, lista/filtri, statistiche, raccolta manuale e automatica (`tasks.py`); **tutte** le view dei job, incluse quelle di CV, cover letter, messaggi ed editor |
| `cv` | `CVDocument`, `CVDraft`, `CoverLetterDocument`, `CoverLetterDraft`, `ReferralMessageDocument`; pipeline CV (`ai_content`, `selection`, `generation`, `rendering`), gap filling, cover letter, messaggi, editor (`draft*`, `cover_letter_draft*`), template HTML |
| `notifications` | `PushSubscription`, invio push, task notifiche |

Frontend in `frontend/src/`: `pages/` (Login, Register, Onboarding, JobList, JobDetail, CvDraftEditor, CoverLetterDraftEditor, Profile, `settings/` (dallo Sprint 78: Settings, Searches, Limits, Privacy; prima un'unica AccountPage); dallo Sprint 67 Legal, LegalAcceptance, VerifyEmail, ForgotPassword, ResetPassword), `components/`, `api/` (client fetch e funzioni per endpoint), `legal/` (testi di informativa e termini in JSX, it/en, Sprint 67), `i18n/` (traduzioni it/en), `sw.js` (service worker).

---

## 3. Stack tecnologico in dettaglio

### 3.1 Backend — Python + Django

Django 5.1 + Django REST Framework 3.15 (`backend/requirements.txt`). Settings unico in `config/settings.py`, configurato solo da variabili d'ambiente; dev e prod differiscono per `.env` e per il file compose. `DJANGO_DEBUG` vale `true` se non impostato; con `DEBUG=false` sono attivi `SECURE_SSL_REDIRECT`, cookie sicuri e `SECURE_PROXY_SSL_HEADER` (Caddy davanti). `TIME_ZONE = "Europe/Rome"`, `USE_TZ = True`. **i18n** (Sprint 71): `LANGUAGE_CODE = "it"`, `LANGUAGES = [it, en]`, `LOCALE_PATHS = [backend/locale]`, `USE_I18N = True`, middleware `apps.common.middleware.ApiLocaleMiddleware` dopo le sessioni; dettaglio in §5.21. Nessuna cache configurata: vale la `LocMemCache` di default, per processo (usata solo dal proxy Nominatim).

Dipendenze principali: `celery`, `redis`, `psycopg2-binary`, `Pillow`, `django-allauth`, `django-celery-beat`, `anthropic` (+ `boto3`), `jsonschema`, `pdfplumber`, `python-docx`, `weasyprint`, `pywebpush`, `requests`, `gunicorn`.

### 3.2 Task in background — Celery + Redis

Celery con broker e result backend Redis (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`), serializzazione JSON, fuso `Europe/Rome`, scheduler `django_celery_beat.schedulers:DatabaseScheduler`. I task esistenti sono:

| Task | Pianificazione (creata da migrazione dati) |
|---|---|
| `apps.jobs.tasks.run_automatic_collections` | ogni 15 minuti (`jobs/0022_replace_nightly_cycle_schedule`, PeriodicTask "Raccolte automiche Pro (ogni 15 minuti)"); avvia `apps.jobs.tasks.run_automatic_collection(user_id)` per ogni Pro dovuto (§5.1). Fino allo Sprint 76 c'era `run_nightly_cycle` alle 02:00 (`jobs/0003`), rimosso dalla stessa migrazione |
| `apps.notifications.tasks.send_inactivity_notifications` | ogni 15 minuti (`notifications/0002_schedule_notification_tasks`). La notifica mattutina `send_morning_notifications` (stessa migrazione) è stata rimossa nello Sprint 77 (`notifications/0003_remove_morning_notification`) |
| `apps.common.tasks.backup_database` | crontab 03:30 Europe/Rome (`common/0001_schedule_backup`) |
| `apps.common.tasks.add` | nessuna; task di prova |
| `apps.accounts.tasks.send_service_email` | nessuna; accodato dalle view dell'account (Sprint 67, §5.14) |

Le pianificazioni sono righe di `django_celery_beat` modificabili da Admin. Le azioni dell'utente **non** passano da Celery, salvo l'invio delle email di servizio (§2.2). Nei test `CELERY_TASK_ALWAYS_EAGER = True`: i task girano in linea, senza Redis.

### 3.3 Frontend — React come PWA

React 19 + React Router 7, build con Vite 7, Tailwind CSS 4, componenti in stile shadcn/ui su primitive Radix (checkbox, dialog, label, radio-group, select, slot), icone `lucide-react`. Lint con `oxlint`, test e2e con Playwright (§13).

**PWA.** `vite-plugin-pwa` in modalità `injectManifest` con service worker proprio (`src/sw.js`): precache con Workbox dei soli asset di build (installabilità), `skipWaiting` + `clients.claim`, gestione di `push` e `notificationclick` (apre `/`). **Aggiornamenti** (Sprint 70, `src/lib/appUpdate.js`): il service worker è registrato direttamente (`navigator.serviceWorker.register('/sw.js')`, `injectRegister: false`, `registerType: 'prompt'` in `vite.config.js`) e non con `virtual:pwa-register`, che anche in modalità `prompt` ricarica la pagina quando prende il controllo un service worker trovato da un controllo successivo o da un'altra scheda. La PWA chiama `registration.update()` ogni 30 minuti e quando la scheda torna visibile; al `controllerchange` di una pagina già controllata (cioè un aggiornamento, non la prima installazione) mostra "Nuova versione disponibile — Aggiorna" (`AppUpdateBanner`), che ricarica solo su richiesta. **Nessuna runtime cache per `/api`**: le chiamate API vanno sempre in rete. "Apertura lista immediata" resta un requisito di reattività dell'API, non di cache locale.

**Client API** (`src/api/client.js`): `fetch` su percorsi relativi `/api/...`, header `Authorization: Token <token>` se presente nel `localStorage` (chiave `app_apply_token`) e, dallo Sprint 71, `Accept-Language` con la lingua dell'interfaccia (`currentLanguage()` di `src/i18n/language.js`: scelta salvata in `app_apply_lang`, altrimenti lingua del dispositivo; anche nei due `fetch` diretti delle anteprime). Gli errori diventano `ApiError` con `status` e `detail`; un 401 con token presente (sessione scaduta o revocata) cancella il token locale ed emette l'evento `app-apply:auth-expired`, che `AuthContext` usa per tornare al login (Sprint 66); un 403 con `code = legal_acceptance_required` emette `app-apply:legal-required` (`LEGAL_REQUIRED_EVENT`), che fa ricaricare l'utente e quindi mostrare la schermata di accettazione (Sprint 67, §5.17). Le anteprime PDF degli editor usano un `fetch` diretto per leggere blob e header `X-Page-Count`.

**i18n.** Dizionario proprio in `src/i18n/translations.js`, lingue `it` ed `en`; lingua iniziale da `localStorage` o dal dispositivo, poi `User.interface_language` dopo il login. Dallo Sprint 71 anche i testi del backend arrivano nella lingua dell'interfaccia (§5.21): la PWA mostra così com'è il `detail` delle risposte d'errore (toast e messaggi delle pagine) e gli errori per campo (`formatApiErrorDetail`), mentre per gli errori con un `code` stabile (import del CV, verifica email, gate) usa i propri testi it/en; non esiste alcuna mappatura dei testi italiani del server. Le notifiche push e le email di servizio seguono `User.interface_language`. I testi di informativa e termini sono componenti JSX in `src/legal/` (it/en), con versione, data e dati del titolare letti da `GET /api/legal/`.

**Design system** (Sprint 72, redesign UI in `Docs/design/`): token in `src/index.css` (`:root` + `@theme inline`, Tailwind v4, nessun `tailwind.config.js`) con i valori di `DESIGN.md §3` — sfondo `#fdfbf7`, card bianche, testo secondario `#6f6350`, nuovi colori `tint`, `note`, `chip`, `destructive-text`, bordi di `note`/`success`/`destructive`, `overlay`; colori del punteggio a fasce ridefiniti per il contrasto (la logica di `utils/scoreStyle.js` non cambia); raggi per ruolo (`rounded-card` 16, `-button` 14, `-field` 12, `-modal` 20, `-sheet` 24) e ombre (`shadow-card`, `-popover`, `-modal`, `-toast`), accanto alla scala storica `rounded-sm…xl` ancora usata dalle pagine non ridisegnate. Il tema scuro (`prefers-color-scheme`) resta quello esistente, con un equivalente scuro dei token nuovi (non ridisegnato: `SPEC-DELTA.md` B8). Solo font di sistema. Componenti in `src/components/ui/`: restyling di `button` (altezza minima invece che fissa, varianti `primary`/`secondary`/`ghost`/`text`/`destructive`, taglie `default` 44 px, `sm`, `lg` 52 px, `icon` 44 px), `card`, `badge` (varianti `primary`, `neutral`, `success`, `destructive`), `input`/`textarea`/`select` (48 px, raggio 12, testo 16 px che evita lo zoom automatico di iOS), `checkbox` (24 px), `radio-group`, `label`, `dialog` (stessa API, aspetto della finestra centrale); nuovi `modal` (finestra centrale con azioni impilate), `sheet` (pannello dal basso con maniglia, ✕, corpo scorrevole e piede con area sicura iOS; da 1024 px finestra centrale di 480 px), `banner` (`info`, `note`, `error` con `role="alert"`, `success`), `field` (etichetta + controllo + suggerimento/errore con `aria-describedby`/`aria-invalid`), `score-chip` (44 px o 56 px, etichetta accessibile), `empty-state`, `spinner`. Finestre e pannelli si animano con keyframe CSS in `index.css` (nessun plugin), disattivate con `prefers-reduced-motion`. I nuovi componenti sono a disposizione degli sprint 73–80; le pagine esistenti mantengono struttura e flussi.

**Icone e logo** (Sprint 72): `public/favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` (180 px, `<link rel="apple-touch-icon">` in `index.html`), `pwa-192x192.png`, `pwa-512x512.png` e `pwa-maskable-512x512.png` (`purpose: maskable` nel manifest di `vite.config.js`, `background_color` `#fdfbf7`), dal logo "Incontro" di `Docs/design/logo/`.

**Navigazione** (Sprint 73, `components/AppShell.jsx`, al posto della `Topbar` di `App.jsx`): tre voci Jobs (`/list`, attiva anche su `/jobs/*`), Profilo (`/profile`), Impostazioni (`/settings`), con `aria-current="page"` sulla voce attiva. Sotto i 1024 px barra di tab fissa in basso (icona + etichetta, `padding-bottom: max(8px, env(safe-area-inset-bottom))`); da 1024 px barra in alto `sticky` con `BrandLogo` (marchio SVG da `src/assets/brand/`, variante chiara con il tema scuro, + wordmark con font di sistema), voci a pillola e `LanguageSwitcher` compatto. Senza navigazione (non autenticato o accettazioni mancanti) una testata con logo e lingua. `index.html` usa `viewport-fit=cover`; `#root` ha altezza minima `100dvh`; la variabile CSS `--app-bottom-bar` (classe `has-tabbar` su `<html>`, impostata da `AppShell`) vale l'altezza della barra di tab più l'area sicura sotto i 1024 px e 0 altrove: la usano il contenuto (padding inferiore) e gli elementi fissi in basso (`ToastProvider`, `AppUpdateBanner`, pulsante chat degli editor). Dallo Sprint 75 `ui/action-bar.jsx` (`ActionBar`), mentre è montata, aggiunge `has-actionbar` a `<html>`: `index.css` nasconde la barra di tab (classe `app-tabbar`) e porta `--app-bottom-bar` all'altezza della barra azione (65 px + `max(28px, 12px + safe-area)`) a ogni larghezza. La rotta `/home` reindirizza a `/list`; `HomePage` è stata rimossa. Dallo Sprint 74 le statistiche sono in `components/StatsSummary.jsx` (riepilogo espandibile nella lista, `GET /api/jobs/stats/`, ricaricato dopo una raccolta) e la raccolta manuale in `components/CollectJobsSheet.jsx` (`Sheet` controllato dalla lista, `POST /api/jobs/collect/`). "Esci" è `components/LogoutButton.jsx` in fondo ad `AccountPage` (`Modal` di conferma, stesso `logout()` di `AuthContext`).

**Lista job** (Sprint 74, `pages/JobListPage.jsx`): testata con `CollectButton`, ricerca testuale e pulsante Filtri con il numero di gruppi attivi; `StatsSummary` in Raccolti; sezioni come `FilterPill`; riga "N filtri attivi · Cancella". I filtri sono in `components/JobFiltersSheet.jsx` (`Sheet`: filtri salvati, date, località, stato, ricerca di provenienza, punteggio, candidati, recruiter con `ui/segmented.jsx`); restano nella query string con `updateParams`, che dallo Sprint 74 accetta anche **funzioni** sul valore corrente nell'URL (i toggle delle pillole non si annullano a vicenda con clic ravvicinati); i valori ammessi sono in `utils/jobFilters.js`. `components/JobCard.jsx` è la scheda ridotta: link "stirato" sul titolo (`data-card-link`), `RecruiterIcon`, `ScoreChip`, 2 gap, cuoricino; niente pulsanti di dettaglio/archivio/generazione. `components/SwipeToArchive.jsx` accetta l'avvio del gesto anche dal link della scheda, prende la pointer capture solo quando il movimento è orizzontale e annulla il click successivo a uno swipe. `components/ManualJobSheet.jsx` contiene il form del job manuale. `components/CostConfirmDialog.jsx` (`useCostConfirm`: `confirmCost(usage, azione)` restituisce una promessa) sostituisce `window.confirm` nella lista e, dallo Sprint 75, nel dettaglio; `confirmCreditCharge` (lib/usage.js) è stata rimossa nello Sprint 76 perché non più usata (gli editor non la usavano). Avvisi di sistema: `components/SystemBanner.jsx` mostra in cima alla colonna `AppUpdateBanner` (stato da `useAppUpdateAvailable` di `lib/appUpdate.js`) oppure `ProfileCompletionBanner`, entrambi `ui/banner`. `ToastProvider` usa un toast scuro con azione. Nuovi componenti `ui/pill.jsx` (`FilterPill`) e `ui/segmented.jsx` (`SegmentedControl`, radio nativi).

**Dettaglio job** (Sprint 75, `pages/JobDetailPage.jsx`, stesse API di prima): la pagina tiene stato e chiamate; la presentazione è divisa in `components/job-detail/` — `ScoreSection.jsx` (`ScoreSection`: motivazione con `ui/expandable-text.jsx`, contatori `ui/counter-toggle.jsx`, un elenco aperto per volta; `DescriptionSection` a fisarmonica), `DocumentsSection.jsx` (righe `ui/document-row.jsx` per CV, cover letter, messaggi; avvisi `ui/banner` variante `note`; link di download = URL firmati del job, come prima), `GapSheet.jsx`, `CoverLetterSheet.jsx`, `ReferralSheet.jsx` (pannelli `ui/sheet` con `GenerationSheetParts.jsx`: contatore caratteri, pillole delle indicazioni passate, piede con `ActionCostHint` dell'azione giusta, motivo del blocco, pulsante disattivato con `next_charge = blocked`). Limiti dei campi in `utils/generationLimits.js`, uguali ai `max_length` del server (indicazioni 2.000, nome destinatario 255, link 500; `joinInstructions` unisce le indicazioni riusate e quelle nuove con una riga vuota, come prima). Menu senza dipendenze `ui/menu.jsx` (pattern WAI-ARIA menu button: `aria-haspopup`/`aria-expanded`, fuoco sulla prima voce, ↑ ↓ Home Fine, Esc riporta il fuoco al pulsante, Tab e clic fuori chiudono), usato dal ⋯ della testata (archivia / riporta dall'archivio con `POST /api/jobs/<id>/archive|unarchive/`, "Segna candidatura fatta" senza CV), dal ⋯ delle righe documento (rigenera) e da `ui/split-button.jsx` (`SplitButton` "Genera CV ▾" nella `ActionBar`). Le generazioni restano sincrone: lo stato `generating` (`cv` | `cover_letter` | `referral_message`) apre una `Modal` non chiudibile con `Spinner`; i flag `*_generation_in_progress` del server continuano a disattivare i pulsanti (nessun cambio alla guardia di concorrenza, §5.2). Conferma del costo con `useCostConfirm` prima di ogni generazione. Archivia e preferito rispondono con `JobSerializer` (senza i campi del dettaglio): la pagina aggiorna solo `is_archived` / `is_favorite` — fino allo Sprint 74 il preferito sostituiva l'intero job e spariva fino al ricaricamento ciò che dipende da `cv_editable`, `cv_page_count` e simili.

**Editor di CV e cover letter** (Sprint 76, `pages/CvDraftEditorPage.jsx`, `pages/CoverLetterDraftEditorPage.jsx`, stesse API e stessa logica di bozza, autosave + anteprima con un solo debounce, `flushPendingSave` prima di chat e finalizzazione): impianto comune `components/editor/EditorShell.jsx` (testata, `SegmentedControl` Modifica / Anteprima, `Banner` multipagina, `ActionBar` larga 1112 px con "Assistente" sotto i 1024 px e "Genera PDF finale"; colonna della chat da 1024 px con griglia `minmax(0,1fr) 400px`, gap 24, altezza calcolata fino alla barra azione; sotto, la chat in `Sheet` con `useKeyboardInset` di `lib/useMediaQuery.js`, che con `visualViewport` scrive `--keyboard-inset` e `--visual-height` per restare sopra la tastiera dell'iPhone). `editor/EditorPreview.jsx` mostra il PDF come prima (blob URL in un iframe, ora in proporzione A4); `editor/OutdatedDraftModal.jsx` è la "bozza superata" in `Modal`; `editor/CvSections.jsx` contiene le sezioni del CV in `ui/accordion.jsx` (`AccordionSection`, pulsante con `aria-expanded`), l'interruttore `ui/switch.jsx` (`role="switch"`) per "Mostra nel CV" e i pulsanti "Aggiungi" con i limiti del server di `utils/draftLimits.js` (stessi valori di `apps/cv/draft_validation.py`). La chat è **una sola istanza di codice**: lo stato (cronologia, prezzo/saldo, testo in scrittura, decisioni, avvisi) è nell'hook `lib/useDraftChat.js` chiamato dalla pagina (sempre montata), con le chiamate di `lib/draftChatApi.js`; `components/DraftChatPanel.jsx` è la presentazione comune (bolle, schede proposta Rifiuta / Accetta, avvisi nel flusso, chip del contesto con ✕, campo con `maxLength` 2000 e invio), usata da `CvDraftChatPanel` e `CoverLetterChatPanel`, che forniscono solo le etichette delle proposte e il contesto dei bullet. `RichBulletInput` (condiviso con il Profilo) ha solo un ritocco di stile: testo a 16 px (niente zoom dell'iPhone), pulsante del grassetto da 32 px; props e comportamento invariati. `ExperienceGroupEditor` (Profilo) non è usato dagli editor e non è toccato. *Sprint 82:* in `components/editor/EditorPreview.jsx` l'iframe del PDF (blob URL) ha di nuovo un'altezza esplicita `h-[70vh] min-h-[420px]` come nello Sprint 69; `aspect-[210/297]` solo da `lg`. Con la sola proporzione, dentro un contenitore flex centrato, su Safari iOS e Chrome Android l'anteprima risultava bianca (segnalazione del committente; non riproducibile in Playwright, che non visualizza PDF).

**Profilo e Impostazioni** (Sprint 78, stesse API di prima). `pages/ProfilePage.jsx`: stessa logica di caricamento e salvataggio sezione per sezione; presentazione in `ui/accordion.jsx` (`AccordionSection` con `keepMounted`: il contenuto chiuso resta nel DOM nascosto, così la validazione nativa dei campi obbligatori continua a valere e, con un campo non valido, la sezione si apre e il browser mostra il messaggio), `ActionBar` con "Salva modifiche" (`form="profile-form"`), `Modal` per la rimozione della foto (prima `window.confirm`), `Banner` per esito e avviso oltre 5 esperienze. `ExperienceGroupEditor`, `EducationListEditor`, `ListSectionEditor` e `RichBulletInput` con le stesse props e lo stesso comportamento; il loro titolo interno (`legend`) è nascosto alla vista con il CSS del contenitore (resta per gli screen reader); in `ExperienceGroupEditor` solo stile (larghezze minime dei campi). Impostazioni: `pages/AccountPage.jsx` (680 righe) sostituita da `pages/settings/` — `SettingsPage.jsx` (elenco a gruppi con `components/settings/SettingsList.jsx`: `SettingsGroup`, `SettingsRow` link/pulsante/con interruttore, `SettingsSubpageHeader`; pannelli per lingua del CV, email con `EmailChangeForm`, fuso con `TimezoneSelect`, lingua; raccolta automatica con `Switch` e orario; `NotificationsRow.jsx` con preferenza e attivazione sul dispositivo e pannello iOS), `SearchesPage.jsx` (`/settings/searches`: card con `Switch`, pannello nuova/modifica, `Modal` di eliminazione, `ActionBar` "Nuova ricerca"), `LimitsPage.jsx` (`/settings/limits`, `UsageLimitsCard` a righe con barra), `PrivacyPage.jsx` (`/settings/privacy`: pannello del cambio password, documenti legali con l'accettazione dell'età, export con `lib/dataExport.js` `useDataExport`, `DeleteAccountButton` in `Modal`). Route in `App.jsx` (`/settings/*` sconosciute → `/settings`); `AppShell` tiene "Impostazioni" attiva su tutte le sottopagine.

**Accesso, onboarding e pagine legali** (Sprint 79, stesse API e stessa logica di prima). `components/auth/AuthPage.jsx` (`AuthPage`: colonna `max-w-sm`, titolo, descrizione, `footer`; variante `centered` con icona in un cerchio, tono `neutral`/`success`/`error`) è l'impianto di `LoginPage`, `RegisterPage`, `VerifyEmailPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `ConfirmEmailChangePage` e `LegalAcceptancePage`; campi con `ui/field.jsx`, esiti ed errori con `ui/banner.jsx`. `RegisterPage` distribuisce gli errori del server per chiave (`email`, `password`, `invite_code` sotto il campo; `accept_privacy`/`accept_terms`/`confirm_age` sotto `LegalConsents`; il resto in un `Banner`). Il pulsante Google resta condizionato a `google_login_enabled` di `/api/legal/` (non configurato: non compare). `ForgotPasswordPage` mostra il modulo solo con `email_enabled` (come prima). `pages/onboarding/OnboardingPage.jsx`: indicatore a barre (`<ol>` con `aria-current="step"`), un `<form id="onboarding-step">` per passo e il pulsante in `ActionBar` (`form="onboarding-step"`); nel passo 2 l'input del CV è nascosto dentro un `<label>` a forma di pulsante e il suo valore viene svuotato a ogni scelta (per poter riscegliere lo stesso file dopo un errore); `handle*Submit`, `cvImportErrorKey`, il limite di 5 MB e `isCreatedRow` sono invariati. `legal/shared.jsx`: `Section` diventa `<details>`/`<summary>` (prop `defaultOpen`, usata dalla prima sezione di `PrivacyContent`/`TermsContent`; testi invariati). Rimosso `ExportDataButton` (sostituito da `useDataExport`).

**Rifinitura** (Sprint 80, nessuna API nuova). *Errore di rete:* `apiFetch` (`api/client.js`) trasforma il `TypeError` di `fetch` in `ApiError` con `status` 0 e `data = { code: 'network_error', detail }` (testo it/en da `translations`) ed emette `app-apply:network-error`; `components/NetworkErrorNotice.jsx` (in `App.jsx`) lo mostra come toast, al massimo uno ogni 5 s. `AuthContext` espone `connectionError` e `retryConnection`: se il primo `/me` fallisce per un motivo diverso da 401/403 il token resta e `ProtectedRoute`, con un token salvato, mostra "Nessuna connessione" con "Riprova" invece del redirect a `/login`. `LegalPage` carica `/api/legal/` da sé con stato d'errore e nuovo tentativo (prima `useLegalInfo` ignorava l'errore e la pagina restava in caricamento). *404:* `pages/NotFoundPage.jsx` sulla route `*`. *Notifiche disattivate:* `Banner` nel `CollectJobsSheet` per i Pro con `auto_collection_enabled` e `notifications_enabled` falso. *Bersagli di tocco:* `FilterPill`, `Switch`, grassetto di `RichBulletInput` e `RecruiterIcon` hanno un `::after` trasparente che porta l'area a 44 px senza cambiare l'aspetto; selettore di lingua, pulsanti di spostamento degli editor e link isolati (accesso, piè di pagina legale) a 44 px. *Pulizia:* rimossi `MultiSelectFilter.jsx`, le parti non usate di `ui/dialog.jsx` e `ui/card.jsx` e 29 chiavi di traduzione non usate (verificate con uno script: tutte le chiavi usate esistono in it ed en; le 40 rimaste "non citate" sono nomi e livelli delle lingue letti in blocco da `utils/languageOptions.js`). Segnaposto della ricerca della lista accorciato, con nome accessibile completo (`jobs.searchLabel`).

**Correzioni dopo la prova su iPhone** (Sprint 81, nessuna API nuova). *Barre in basso:* `ui/action-bar.jsx` ha la variante `stacked` (Profilo, Ricerche): sta sopra la barra di tab, che resta visibile (`html.has-actionbar-stacked`); la predefinita (dettaglio job, editor, onboarding) la sostituisce come prima. L'altezza reale della barra è misurata (`ResizeObserver`) e scritta in `--app-actionbar-h`; `--app-tabbar` è l'altezza della barra di tab; `--app-bottom-bar` (spazio in fondo, toast) somma le due. In Profilo la barra "Salva modifiche" compare solo se il contenuto (istantanea JSON senza le `_key`) differisce da quello dell'ultimo caricamento o salvataggio, durante il salvataggio o con un errore. *Area sicura superiore:* striscia fissa `h-[env(safe-area-inset-top)]` con lo sfondo in `AppShell`; `theme-color` uguale allo sfondo (chiaro e scuro) in `index.html` e nel manifest. *Date:* `ui/date-range.jsx` (`DateRangeFields`, griglia `minmax(0,1fr)` impilata sotto i 20rem di contenitore con una container query) in esperienze, istruzione e filtri della lista; in `index.css` gli `input[type=date|datetime-local|month|time]` hanno `appearance: none`, larghezza 100 %, `min-width: 0` e altezza 48 px. *Editor del profilo:* `ExperienceGroupEditor`, `EducationListEditor`, `ListSectionEditor` con nuovo markup (stesse props e logica): campi a tutta larghezza, riquadro `bg-tint` per ruolo e riga, azioni come pulsanti di testo da 44 px; `CityAutocomplete` impila città e paese sotto i 20rem; `ChipInput` alto 48 px, testo a 16 px (niente zoom di iOS), nome del ✕ tradotto (`common.removeItem`). *Raccolta automatica:* `accounts/0012` non attiva più nulla.

**Componenti trasversali** (Sprint 70): banner del profilo incompleto (`ProfileCompletionBanner`, da `profile_status` di `/me`); costi delle azioni a massimale (`lib/usage.js`: `useUsage`, `actionCostText`, `confirmCreditCharge`; componente `ActionCostHint`; riquadro `UsageLimitsCard` in Impostazioni); `TimezoneSelect` (select nativo con `Intl.supportedValuesOf('timeZone')`).

**iPhone.** Le push via web funzionano su iOS solo con la PWA aggiunta alla schermata Home; l'app lo segnala in Impostazioni quando rileva iOS fuori dalla modalità standalone. Dallo Sprint 78 (`components/settings/NotificationsRow.jsx`) il controllo `isIOS() && !isStandalone()` viene **prima** di `isPushSupported()`: Safari fuori dalla Home non espone `PushManager` e prima l'utente vedeva "non supportate" invece delle istruzioni.

### 3.4 Database — PostgreSQL

PostgreSQL 16 (`postgres:16-alpine`), volume `postgres_data`. Tutti i dati applicativi sono legati a un `user` (§7). Migrazioni sempre committate; alcune migrazioni sono **migrazioni dati** che creano i PeriodicTask (§3.2) o normalizzano dati (`profiles/0007_normalize_language_data`).

### 3.5 Motore AI — Claude via AWS Bedrock

**Client.** Tutte le chiamate passano dall'unica funzione `call_claude_structured(model, system, user_content, schema, max_tokens, effort=None)` in `apps/common/ai.py` (Sprint 40). Usa `AnthropicBedrock(aws_region=settings.AWS_BEDROCK_REGION)` dell'SDK `anthropic`, creato a ogni chiamata; le credenziali `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` sono lette da boto3 dall'ambiente. L'API Anthropic diretta non è più usata (dal 18/08/2026, credito esaurito sulla chiave).

**Output strutturato via tool-use forzato.** Bedrock rifiuta il parametro nativo `output_config.format` (json_schema). Ogni chiamata dichiara quindi un solo tool `output` con `input_schema = schema` e `tool_choice = {"type": "tool", "name": "output"}`; la descrizione del tool vieta chiavi contenitore (es. `jsonPayload`) e campi extra. Sempre `thinking = {"type": "disabled"}`; `output_config = {"effort": …}` solo se `effort` è indicato.

**Validazione e retry.** L'input del blocco `tool_use` è validato con `jsonschema.validate`. Se non è conforme si ritenta, fino a `_MAX_ATTEMPTS = 3`, poi si solleva `StructuredOutputError`. Gli errori di rete o API di Bedrock **non** sono ritentati e si propagano al chiamante, che decide (rimborso, `RunLog`, 502…). Gli schemi non usano `minItems` / `maxItems`: i vincoli di quantità (es. 4–6 Areas of Expertise) stanno solo nei prompt.

**Modelli per uso** (variabili d'ambiente, default in `settings.py`):

| Variabile | Default | Usata da |
|---|---|---|
| `AWS_BEDROCK_REGION` | `eu-central-1` | client |
| `BEDROCK_SCORING_MODEL` | `eu.anthropic.claude-haiku-4-5-20251001-v1:0` | scoring |
| `BEDROCK_CV_GENERATION_MODEL` | `eu.anthropic.claude-opus-5` | contenuti CV, cover letter, messaggi di networking, chat editor CV e cover letter |
| `BEDROCK_CV_PARSING_MODEL` | `eu.anthropic.claude-opus-5` | import CV in onboarding |

**Elaborazione in UE (Sprint 67).** I default sono la regione di Francoforte (`eu-central-1`) e i profili di inferenza cross-region `eu.`, che instradano le richieste solo verso regioni AWS dell'Unione Europea (non necessariamente Francoforte), come dichiarato nell'informativa privacy; prima dello Sprint 67 erano `us-east-1` e i profili `us.`. I valori effettivi sono quelli del `.env` (aggiornato a mano dal committente) e i profili `eu.` vanno abilitati nella console Bedrock della regione. L'accesso ai profili `eu.` dall'account AWS non è stato verificato nello sprint.

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

- **Email + password.** `User` custom (`AbstractUser`, `email` unica; `username` = email alla registrazione). `POST /api/accounts/login/` e `/register/` (quest'ultima solo con l'invio email non configurato, vedi sotto) creano ogni volta un **nuovo token** (`AuthToken`, §4.15: uno per login/dispositivo, 256 bit casuali da `secrets.token_urlsafe(32)`), che la PWA salva nel `localStorage` e invia come `Authorization: Token …`. Nel DB c'è solo lo SHA-256 del token.
- **Scadenza per inattività (Sprint 66).** L'autenticazione DRF è solo `apps.accounts.authentication.ExpiringTokenAuthentication` (niente `TokenAuthentication` né `SessionAuthentication` di DRF): un token non usato da più di `AUTH_TOKEN_IDLE_DAYS = 30` giorni viene cancellato e la richiesta riceve 401; a ogni uso `last_used_at` viene aggiornato, al massimo una volta l'ora. `POST /api/accounts/logout/` cancella il solo token della richiesta (gli altri dispositivi restano collegati); `apps.accounts.tokens.revoke_all_tokens(user)` li cancella tutti (usato da recupero e cambio password dello Sprint 67; la cancellazione dell'account li elimina a cascata). I token DRF esistenti sono stati cancellati dalla migrazione `accounts/0008` (tutti gli utenti hanno rifatto il login); l'app `rest_framework.authtoken` non è più installata (la sua tabella resta, vuota).
- **Registrazione su invito.** Se `REGISTRATION_INVITE_CODE` è valorizzato, la registrazione richiede `invite_code` uguale (confronto a tempo costante con `hmac.compare_digest`); il controllo precede quello sull'email già registrata, quindi senza codice valido non si scopre se un'email esiste. Vuoto = registrazione aperta.
- **Consensi in registrazione (Sprint 67).** `RegisterSerializer` (via `LegalConsentFields`) richiede `accept_privacy`, `accept_terms`, `confirm_age` tutti `true` (400 per campo altrimenti) e accetta `interface_language` (lingua delle email). Dopo la creazione `record_acceptances(user)` scrive le tre righe `LegalAcceptance` con le versioni correnti (§4.16). La PWA non pre-seleziona mai le caselle.
- **Verifica dell'email (Sprint 67).** Attiva solo se l'invio email è configurato (`apps.accounts.emails.email_enabled()`: `EMAIL_HOST_USER` e `EMAIL_HOST_PASSWORD` valorizzati).
  - Token: `TimestampSigner(salt="apps.accounts.verify-email")` su `"<user_id>:<email in minuscolo>"`, validità `EMAIL_VERIFICATION_MAX_AGE` = 3 giorni; nessuna tabella. Link `PUBLIC_BASE_URL/verify-email?t=<token>`, aperto dalla PWA che chiama `POST /api/accounts/verify-email/`: firma scaduta → 400 `code: expired`, firma manomessa, payload non valido o utente/email non corrispondenti (o non attivo) → 400 `code: invalid`; altrimenti `email_verified = True`. La verifica non crea un token: l'utente fa poi il login.
  - Registrazione con email attiva: risposta sempre `201 {"verification_required": true}`, senza token. Se l'email è nuova crea l'utente con `email_verified = False` e invia il link; se è già registrata non crea nulla e invia al titolare dell'indirizzo l'email "tentativo di registrazione" (non enumerazione). Senza email: comportamento precedente, utente creato con `email_verified = True`, risposta `201 {token, verification_required: false}`, email duplicata → 400 "Un utente con questa email esiste già.".
  - Login con email attiva e `email_verified = False`: **403** `{code: "email_not_verified"}`, restituito solo **dopo** la verifica della password (credenziali errate → sempre il 400 generico).
  - Reinvio: `POST /api/accounts/verify-email/resend/ {email}` risponde sempre `200 {"status": "sent_if_registered"}` e invia solo se l'account esiste, è attivo e non è verificato.
  - La migrazione `accounts/0010` ha marcato verificati tutti gli utenti esistenti.
- **Recupero della password (Sprint 67).** `POST /api/accounts/password-reset/ {email}`: senza email configurata 503 `code: email_unavailable`; altrimenti sempre `200 {"status": "sent_if_registered"}`, con invio solo per un account attivo con password utilizzabile. Link `PUBLIC_BASE_URL/reset-password?uid=<id base64>&token=<token>` con il `default_token_generator` di Django: monouso (il token dipende dall'hash della password e da `last_login`), validità `PASSWORD_RESET_TIMEOUT` = 3 giorni. `POST /api/accounts/password-reset/confirm/ {uid, token, new_password}`: link non valido o scaduto → 400 `code: invalid_link`; password che non supera i validatori → 400 `new_password`; altrimenti nuova password, `email_verified = True` (il link è arrivato all'indirizzo) e `revoke_all_tokens` (logout ovunque). Non restituisce un token.
- **Cambio della password (Sprint 67).** `POST /api/accounts/password/change/ {old_password, new_password}`, autenticato: password attuale errata o nuova non valida → 400; altrimenti `revoke_all_tokens` e **nuovo token** per il dispositivo corrente nella risposta (la PWA lo salva subito).
- **Login.** Messaggio d'errore unico ("Credenziali non valide.") per email inesistente e password errata; anche con email inesistente si passa da `authenticate()` (che calcola comunque un hash), così i tempi non rivelano se l'account esiste. Con email attiva e indirizzo non verificato: 403 `email_not_verified` (vedi sopra). Limiti di frequenza in §7.1.
- **Gate delle accettazioni legali (Sprint 67).** `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated, apps.accounts.permissions.LegalAcceptanceRequired]`: per un utente autenticato a cui manca l'accettazione della versione corrente di almeno un documento (`missing_acceptances`, una query per richiesta) ogni view che usa i permessi di default risponde **403** `{"code": "legal_acceptance_required", "detail": …}`. **Regola: una view che dichiara `permission_classes` esplicitamente è esente dal gate**; per questo nello Sprint 67 sono state tolte le `permission_classes = [IsAuthenticated]` ridondanti da job, profilo, ricerche e notifiche. Le uniche view esenti sono: `me`, `logout`, `legal-acceptance`, `export`, `delete`, `password/change` (con `IsAuthenticated`) e gli endpoint pubblici con `AllowAny` (`register`, `login`, `verify-email`, `verify-email/resend`, `password-reset`, `password-reset/confirm`, `export/download`, `GET /api/legal/`, download firmati `/api/files/…`). Le richieste non autenticate ricevono sempre 401 prima del gate. `LEGAL_GATE_ENABLED = not TESTING`: spento nei test (quasi tutti gli utenti dei test non hanno accettazioni), riacceso con `override_settings` in quelli dedicati. Flusso completo in §5.17.
- **Django Admin.** Usa la propria sessione Django (non l'API). Path configurabile con `DJANGO_ADMIN_PATH`; i tentativi di login falliti sono limitati per IP (§7.1).
- **Login Google.** django-allauth (`allauth.account`, `allauth.socialaccount`, provider Google, `SITE_ID = 1`), URL sotto `/accounts/` proxati da Caddy; la PWA apre `/accounts/google/login/?process=login` a piena pagina. Dallo Sprint 67 il pulsante compare solo se `GET /api/legal/` riporta `google_login_enabled` (vero se `GOOGLE_OAUTH_CLIENT_ID` è valorizzato). Dallo Sprint 66 l'API non accetta più la sessione Django: al ritorno da Google l'utente avrebbe una sessione ma nessun token, quindi il percorso va completato (sessione → token) prima di attivare il login Google. Login solo via email, verifica email disattivata (`ACCOUNT_EMAIL_VERIFICATION = "none"`). Credenziali da `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`: **oggi vuote in produzione**, quindi il login Google non è attivo. `LOGIN_REDIRECT_URL` non è impostato (vale il default Django) e il ritorno da Google non è stato verificato. Il percorso allauth salta anche le spunte dei consensi e il codice di invito. Le URL di allauth (`/accounts/*`, compresa la registrazione di allauth) restano comunque raggiungibili: un account creato da lì non ottiene un token per l'API ed è soggetto al gate.
- Password solo come hash (default Django), validatori standard; lunghezza massima 128 caratteri in registrazione/login.
- **Cancellazione dell'account ed export dei dati** (Sprint 67): §5.15 e §5.16. **Non esiste** il cambio dell'indirizzo email (in `me` è in sola lettura).

### 3.8 Notifiche — Web Push

Standard Web Push con chiavi VAPID (`VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL`), invio con `pywebpush.webpush` (`apps/notifications/services.py`). La PWA legge la chiave pubblica da `GET /api/notifications/vapid-public-key/`, fa `PushManager.subscribe` e registra la sottoscrizione con `POST /api/notifications/push-subscriptions/` (`update_or_create` per utente + endpoint). Nessun servizio esterno a pagamento. Meccanismo di invio in §5.5. Dallo Sprint 70 il logout annulla la sottoscrizione del dispositivo corrente: la PWA manda `push_endpoint` a `POST /api/accounts/logout/` (il server elimina la `PushSubscription` dell'utente con quell'endpoint) e poi chiama `PushSubscription.unsubscribe()` nel browser. Dallo Sprint 67 `PATCH /api/accounts/me/ {notifications_enabled: false}` elimina **tutte** le `PushSubscription` dell'utente (e la PWA annulla quella del browser corrente con `PushSubscription.unsubscribe()`), mentre la registrazione di una nuova sottoscrizione rimette `notifications_enabled = True`. Dallo Sprint 66 l'endpoint della sottoscrizione è accettato solo se `https`, senza porta esplicita né credenziali, con host di un push service noto (`fcm.googleapis.com`, `updates.push.services.mozilla.com`, `*.push.apple.com`, `*.notify.windows.com`); al massimo 10 sottoscrizioni per utente (oltre si eliminano le più vecchie).

---

## 4. Modello dati

Modelli Django reali, con i campi rilevanti. Tutti i timestamp sono salvati in UTC (`USE_TZ`). Salvo dove indicato, ogni record è legato direttamente o indirettamente a un `User`, con cancellazione a cascata.

### 4.1 `User` (`apps/accounts/models.py`)

Estende `AbstractUser` (quindi anche `username`, `password`, `first_name`, `last_name`, `is_staff`, `is_superuser`, `date_joined`…).

| Campo | Tipo | Significato |
|---|---|---|
| `email` | Email, unica | Identificativo di login (lo `username` è valorizzato uguale); dallo Sprint 70 modificabile solo con il flusso di conferma di §5.19, che aggiorna anche `username` |
| `first_name`, `last_name` | testo | Nome mostrato su CV, cover letter, firma dei messaggi e nei nomi file; se mancano si usa l'email di login |
| `plan` | `free` \| `pro` (default `free`) | Piano; modificabile solo da Admin. Il passaggio Pro→Free disattiva tutte le ricerche (segnale in `apps/searches/signals.py`) |
| `timezone` | testo, default `Europe/Rome` | Fuso dell'orario della raccolta automatica (Sprint 77; prima della notifica delle 10:00), di "oggi" della lista e delle statistiche. Dallo Sprint 70 impostabile in Impostazioni e in onboarding (`PATCH /api/accounts/me/`, solo con un nome IANA valido) e inizializzato in registrazione con il fuso del browser (un nome non valido è ignorato e resta il default) |
| `interface_language` | `it` \| `en` (default `it`) | Lingua dell'interfaccia; dal backend usata solo per la lingua delle email di servizio (Sprint 67; in registrazione arriva dalla PWA) |
| `cv_language_mode` | `english` \| `job_language` (default `job_language`) | Lingua di CV, cover letter e messaggi |
| `cv_include_photo` | bool (default false) | Foto nel CV on/off |
| `objective_statement` | testo (max 2.000 via API) | Situazione/obiettivo raccolto in onboarding, modificabile anche dalla pagina Profilo (Sprint 70); **inerte** (non usato da nessun prompt) |
| `created_at` | datetime | Creazione; valore iniziale dei due timestamp sotto |
| `last_activity_reset` | datetime | Inizio del periodo di inattività: inizializzato a `created_at` in `save()`, aggiornato a ogni "candidatura fatta"; l'annullamento della candidatura (Sprint 69) non lo modifica |
| `last_notified_at` | datetime | Ultima notifica dei job nuovi inviata (fino allo Sprint 76 la mattutina, che lo usava per decidere; dallo Sprint 77 solo informativo, aggiornato dalla notifica di fine raccolta automatica). Dallo Sprint 70 riportato a "adesso" quando le notifiche vengono riaccese (§5.5) |
| `last_inactivity_notified_at` | datetime, null | Ultimo promemoria di inattività; impedisce di rinviarlo a ogni giro finché `last_activity_reset` non cambia |
| `extra_credit` | `Decimal(8,2)`, default 0 | Saldo del credito in euro; caricato da Admin, scalato e riaccreditato in modo atomico |
| `collection_in_progress` | bool | Guardia di concorrenza della raccolta per utente, condivisa da raccolta manuale e automatica (Sprint 68, 77) |
| `auto_collection_enabled` | bool, default false | Raccolta automatica attiva (Sprint 77, solo Pro; validato in `PATCH /api/accounts/me/`). Dallo Sprint 81 la migrazione `accounts/0012_enable_auto_collection_for_pro` non fa nulla (prima attivava i Pro esistenti alle 07:00): nessuna attivazione preimpostata |
| `auto_collection_time` | ora, default 07:00 | Orario della raccolta automatica, a quarti d'ora, nel fuso `timezone` |
| `auto_collection_last_local_date` | data, null | Data locale dell'ultima raccolta automatica avviata: il task ogni 15 minuti non la ripete nello stesso giorno locale; impostata a oggi quando si attiva o si cambia l'orario dopo l'orario di oggi |
| `collection_started_at` | datetime, null | Inizio della raccolta in corso; la guardia è considerata stantia dopo 2 ore o se il timestamp manca |
| `email_verified` | bool (default false) | Sprint 67: indirizzo confermato dal link di verifica (o da un recupero password). Con l'invio email non configurato i nuovi account nascono già verificati; la migrazione dati `accounts/0010` ha marcato verificati tutti gli utenti esistenti. In sola lettura via API |
| `notifications_enabled` | bool (default true) | Sprint 67: preferenza notifiche. Con false i task di notifica saltano l'utente; impostarla a false via `PATCH /me` elimina tutte le sue `PushSubscription`; registrare una sottoscrizione la rimette a true |

Migrazioni dello Sprint 67: `accounts/0009_user_email_verified_legalacceptance` (i due campi sopra e il modello `LegalAcceptance`, §4.16) e `accounts/0010_mark_existing_users_verified` (migrazione dati).

### 4.2 `Profile` e sezioni (`apps/profiles/models.py`)

Un solo profilo master per utente. Non esiste un campo `key_achievements`: le Areas of Expertise sono calcolate dal modello a ogni generazione.

- **`Profile`**: `user` (OneToOne, `related_name="profile"`), `summary` (max 5.000 via API), `photo` (ImageField in `profile_photos/`, nome casuale `<uuid4>.<ext>`; vedi §4.15 per la ricodifica e il download; dallo Sprint 70 rimovibile con `DELETE /api/profiles/me/photo/`, che azzera il campo e cancella il file a commit avvenuto), contatti per l'intestazione dei documenti: `phone`, `email` (email da mostrare sul CV, separata da quella di login; se vuota nessuna email sul CV — Sprint 41), `city`, `country_code` (ISO 3166-1 alpha-2), `linkedin_url`. La property `is_complete` è vera se esiste **almeno una voce di istruzione**; è verificata solo al momento della generazione del CV, non al salvataggio. Dallo Sprint 70 `/api/accounts/me/` espone `profile_status`: `complete` (`is_complete`), `incomplete` (esperienze o sommario presenti ma nessuna istruzione) o `empty` (profilo assente o vuoto), usato dal banner della PWA.
- **`Experience`**: `profile`, `company`, `role`, `location`, `location_country_code`, `start_date` (null), `end_date` (null = in corso), `bullets` (JSON, lista di stringhe), `technologies` (JSON, lista; modificabile da onboarding e pagina Profilo dallo Sprint 70). Via API: dallo Sprint 70 al massimo **15 bullet da 400 caratteri** (prima 30 × 2.000, Sprint 66) e 50 tecnologie da 200. I limiti valgono per le modifiche: `_validate_string_list` in `apps/profiles/serializers.py` accetta, su un'esperienza esistente, un numero di elementi fino al massimo tra il limite e quello attuale e i testi oltre la lunghezza massima già presenti nell'esperienza, così un profilo salvato prima resta salvabile senza toccare i bullet in eccesso ma non può crescere.
- **Numero di voci per sezione** (Sprint 70, `ProfileSectionViewSet.max_items`, controllato solo in creazione): 30 esperienze, 15 istruzioni, 100 competenze, 50 certificazioni, 36 lingue; oltre → 400 `{detail}`.
- **`Education`**: `profile`, `institution`, `title`, `location`, `location_country_code`, `start_date` (null), `end_date` (**null ammesso** = in corso, Sprint 34), `notes` (max 3.000 via API). Mai riscritta dall'AI.
- **`Skill`**, **`Certification`**: solo `name`.
- **`Language`**: `language` (choices `LANGUAGE_CHOICES`: 36 codici ISO a 2 lettere), `level` (choices `LANGUAGE_LEVEL_CHOICES`: `elementary`, `intermediate`, `fluent`, `mother_tongue`; può essere vuoto). Le etichette tradotte in it/en/fr/de/es (`LANGUAGE_NAME_LABELS`, `LANGUAGE_LEVEL_LABELS` in `language_options.py`) servono al rendering del CV e al cap lingua dello scoring. I dati preesistenti sono stati normalizzati da `profiles/0007_normalize_language_data` (best-effort, i valori non riconosciuti restano).

### 4.3 `SavedSearch` (`apps/searches/models.py`)

- `user`, `search_type` (`job_role` "Job role keyword" | `company` "Company", default `job_role`), `keywords`, `city`, `country`, `is_active` (default **false**: una ricerca nuova nasce disattivata e si attiva con l'endpoint dedicato), `created_at`.
- Non ci sono `name` né un campo `location` unico; città e paese arrivano dall'autocomplete Nominatim.
- Limiti di piano (`apps/searches/services.py`): Free max 10 salvate e **1 attiva per tipo** (attivandone un'altra dello stesso tipo la precedente si disattiva, l'API la restituisce in `deactivated_previous`); Pro max 100 salvate e 50 attive in totale. Oltre → 400. Dallo Sprint 68 la `PATCH` che cambia `search_type` di una ricerca **attiva** ripassa da `activate_search` (stessa regola dell'attivazione, in transazione): su Free spegne l'altra attiva del nuovo tipo e la restituisce in `deactivated_previous`; su Pro il pool è unico e non cambia nulla.

### 4.4 `Job` (`apps/jobs/models.py`)

Un record per offerta e per utente.

| Gruppo | Campi | Note |
|---|---|---|
| Identità | `user`, `source` (`linkedin` \| `manual`), `external_id` (255) | Unicità su (`user`, `source`, `external_id`): è la deduplica. Job manuali: `external_id = "manual-<uuid4>"` |
| Annuncio | `title`, `company`, `location` (255), `description`, `apply_url` (URL 1000, facoltativo), `published_at` (null), `salary` (255), `contract_type` (Sprint 82: `""` \| `full_time` \| `part_time` \| `temporary` \| `contract` \| `internship` \| `volunteer` \| `other`) | `published_at` è nullo per gli import da link; `salary` e `contract_type` si valorizzano solo dalla raccolta Apify (dallo Sprint 82; prima `salary` restava sempre vuoto perché si leggeva `salary` invece di `salaryInfo`) |
| Provenienza | `matched_search` (255), `matched_saved_search` (FK `SavedSearch`, null, `SET_NULL`, `related_name="jobs"`) | `matched_search` è l'etichetta del badge, uno storico mai riscritto: per le ricerche Job role `"<keywords> - <città>, <paese>"` (dal `searchString` Apify), per le Company il nome azienda; vuoto per import e job manuali. La FK (Sprint 68) è valorizzata in raccolta con la ricerca del gruppo che ha prodotto l'offerta (§5.3) ed è il criterio del filtro "Ricerca"; per i job precedenti l'ha valorizzata la migrazione `jobs/0018` dai valori attuali delle ricerche, solo se la corrispondenza era univoca (sul dump del 2026-11-14: 13.568 job su 14.486 con etichetta). Null anche per i job di ricerche poi eliminate |
| Dati LinkedIn | `applicants_count` (int, null), `applicants_bucket` (`under_25` \| `over_200` \| vuoto), `recruiter_name` (255), `recruiter_profile_url` (URL 500) | Valorizzati solo dalla raccolta Apify; count e bucket mai insieme |
| Sezione | `origin` (`collected` \| `imported`), `is_archived`, `is_favorite` | Sezioni: Raccolti (`collected`, non archiviati), Importati (`imported`, non archiviati: import da link **e** job manuali), Preferiti (`is_favorite`, non archiviati), Archiviati |
| Stato | `status` (`new` \| `cv_generated` \| `application_done`, default `new`) | Tre stati stabili. Tutti i job nascono `new`. Transizioni: generazione CV riuscita → `cv_generated` (un `application_done` resta tale); fallita → invariato; "candidatura fatta" → `application_done`; annullamento → `cv_generated` se esiste un `CVDocument`, altrimenti `new` (Sprint 69) |
| Guardie | `cv_generation_in_progress`, `cover_letter_generation_in_progress`, `referral_message_generation_in_progress` + `cv_generation_started_at`, `cover_letter_generation_started_at`, `referral_message_generation_started_at` (Sprint 69) | Flag transitori indipendenti, guardie di concorrenza (§5.2), con il momento di accensione. Solo il primo corrisponde allo stato visibile "CV in generazione". Un flag acceso da oltre `GENERATION_STALE_AFTER` (35 minuti, oltre il `--timeout 1800` di gunicorn) o senza timestamp è **stantio**: non blocca la guardia e il serializer lo espone spento (`is_generation_active`, property `*_generation_active`) |
| Scoring | `score` (1–10, null), `score_match`, `score_gaps` (JSON), `score_reasoning`, `score_rescaled_from_legacy` (bool), `scoring_failures` (int, default 0) | `score` nullo = scoring fallito o mai eseguito: ritentato dal ciclo notturno finché `scoring_failures` < `MAX_SCORING_FAILURES = 3` (Sprint 68). Match/gap sono liste di `{label, reason}`; i job scorati prima del 09/09/2026 hanno stringhe semplici. I punteggi dati su scala 1–5 (prima del 2026-09-24 21:00 UTC) sono riscalati ×2 dal comando `rescale_legacy_scores` e marcati con `score_rescaled_from_legacy` |
| Date | `date_collected` (auto all'inserimento), `date_scored`, `date_cv_generated`, `date_application_done` | `date_collected` è la base del filtro date, della riga "Importato:", delle statistiche e della notifica mattutina |

Il campo storico `discarded_by_cap` (marcatore del cap di intake rimosso nello Sprint 46) è stato tolto nello Sprint 68: i job marcati si eliminano con `delete_discarded_by_cap_jobs` (dry-run di default, `--confirm`; documenti e bozze in cascata, PDF cancellati dal disco) e la migrazione `jobs/0019` che rimuove la colonna si rifiuta di partire finché ne restano (`DEPLOY.md` §4.7). La `jobs/0017` dà alla colonna un default lato database, così gli INSERT del codice nuovo funzionano anche prima della rimozione.

### 4.5 `CVDocument` (`apps/cv/models.py`)

Un record per ogni PDF di CV prodotto (generazione AI o finalizzazione dall'editor); mai cancellato. In UI si usa l'ultimo per `-generated_at, -id`.

- `job` (FK, `related_name="cv_documents"`), `user`;
- `html_source`: HTML usato per il PDF;
- `pdf_file`: file nella cartella media `cv_documents/`, nome casuale `<uuid4>.pdf` (Sprint 66, `apps.common.files.cv_document_upload_to`; prima `cv_<job>_<doc>.pdf`); scaricabile solo con URL firmato (§4.15);
- `generated_at`;
- `generation_type`: `automatic` | `manual`. Oggi si scrive sempre `manual`; `automatic` resta solo per i record storici;
- `extra_instructions_used`: testo "gap da colmare + indicazioni" usato nella generazione (Sprint 44, ex `enrichment_used`); vuoto per i documenti finalizzati dall'editor;
- `areas_of_expertise_grounding`: lista `[{label, grounding_reference}]` restituita dal modello, solo per diagnosi; vuota per i documenti finalizzati dall'editor;
- `content_json`: snapshot strutturato (Sprint 51), `{}` per i CV precedenti, che quindi non sono riapribili nell'editor (la PWA non mostra "Modifica CV", §12.2 `cv_editable`);
- `page_count` (Sprint 69, null per i documenti precedenti): pagine del PDF; oltre 1 la PWA lo segnala.

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
     "bullets": [{"id": str, "text": str, "shown": bool}]}  # pool completo prodotto dall'AI, testo con **grassetto**; id stabile (Sprint 69)
  ],
  "educations": [{"institution", "title", "location", "dates", "notes"}],  # stringhe già formattate
  "skills": [str], "certifications": [str],          # selezione corrente, sottoinsieme del profilo
  "languages": [{"language": codice, "level": codice}]
}
```

`shown` di un bullet indica se è sopravvissuto al taglio al budget e al loop di ripiego. `id` (Sprint 69, 12 caratteri esadecimali, `apps/cv/draft_ids.py`) identifica il bullet per chat e puntamento ✦ indipendentemente dalla posizione: assegnato alla generazione, dalla PWA per i bullet nuovi e in modo pigro dal server per i contenuti precedenti (lettura della bozza, seed, PATCH, anteprima, finalizzazione). Un CV già prodotto **non** cambia se il profilo viene modificato dopo.

### 4.6 `DailyQuota` (contatori giornalieri) e listino prezzi

Un record per (`user`, `date`), unico; `date` è il giorno **Europe/Rome** (`timezone.localtime(now).date()` con `TIME_ZONE = Europe/Rome`), quindi i contatori ripartono da zero alla mezzanotte di Roma. Sette contatori indipendenti:

| Contatore | Azione | Free | Pro | Oltre il massimale | Prezzo (env, default) |
|---|---|---|---|---|---|
| `manual_cv_count` | Generazione CV (anche rigenerazione, con o senza gap) | 1/g | 10/g | credito | `PRICE_MANUAL_CV_EXTRA` = 1,50 € |
| `cover_letter_count` | Generazione cover letter | 1/g | 10/g | credito | `PRICE_COVER_LETTER_EXTRA` = 1,50 € |
| `referral_message_count` | Messaggio di networking | 1/g | 10/g | credito | `PRICE_REFERRAL_MESSAGE_EXTRA` = 1,00 € |
| `import_count` | Import job da link LinkedIn | **non consentito** | 3/g | credito | `PRICE_IMPORT_EXTRA` = 0,50 € |
| `manual_job_count` | Creazione manuale di un job | 3/g | 3/g | credito | `PRICE_MANUAL_JOB_EXTRA` = 0,50 € |
| `collection_count` | Raccolta del giorno, automatica o manuale (Sprint 77); `collection_done_at` = inizio della raccolta di oggi | 1/g | 1/g | **nessuna estensione** | — |
| `cv_import_count` | Import/parsing del CV caricato (Sprint 66) | 5/g | 5/g | **nessuna estensione** (409) | — |

Azioni **sempre a credito**, senza contatore né massimale:

| Azione | Prezzo (env, default) |
|---|---|
| Messaggio nella chat dell'editor CV | `PRICE_CV_DRAFT_CHAT_MESSAGE` = 0,20 € |
| Messaggio nella chat dell'editor cover letter | `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE` = 0,20 € |

Gratuite: import/parsing del CV in onboarding (entro `CV_IMPORT_DAILY_LIMIT = 5` al giorno, senza credito; restituito se la chiamata AI fallisce), raccolta (una al giorno, senza credito), anteprime e finalizzazione delle bozze, archivio/preferiti/candidatura, filtri preferiti.

**Esposizione all'utente** (Sprint 70): `GET /api/accounts/usage/` (`apps/accounts/usage.py`, sola lettura) restituisce `date` e `resets_at` (mezzanotte Europe/Rome successiva), `plan`, `extra_credit`, `actions` con, per `cv`, `cover_letter`, `referral_message`, `import`, `manual_job`, `collection`, `cv_import`: `used` (contatore di oggi), `limit` (massimale del piano; 0 per l'import sul Free), `remaining`, `price` (stringa decimale, `null` se non c'è estensione a credito) e `next_charge` (`included` \| `credit` \| `blocked` \| `unavailable`: cosa succederebbe alla prossima richiesta con il saldo attuale); `chat_prices` con i prezzi a messaggio delle due chat. Legge le stesse costanti e gli stessi prezzi dei servizi, non riserva nulla: la decisione resta ai servizi (una richiesta concorrente può cambiare l'esito tra lettura e azione).

I massimali sono costanti nel codice (`MANUAL_CV_PLAN_LIMITS`, `COVER_LETTER_PLAN_LIMITS`, `REFERRAL_MESSAGE_PLAN_LIMITS`, `IMPORT_DAILY_LIMIT`, `MANUAL_JOB_DAILY_LIMIT`, `COLLECTION_DAILY_LIMIT`, `CV_IMPORT_DAILY_LIMIT`); i prezzi sono `Decimal` letti dall'ambiente (`config/settings.py`). Con saldo insufficiente l'azione è rifiutata (409, o 402 per le chat). Il controllo di piano dell'import precede quello di quota/credito.

**Riserva e restituzione.** Ogni servizio esegue in una transazione `select_for_update` (sul Job per la guardia, sulla `DailyQuota` e, se serve, sull'`User`): se il contatore è sotto il massimale lo incrementa (modalità `"quota"`), altrimenti scala il prezzo dal saldo (modalità `"credit"`). La modalità è tenuta in memoria per la durata della richiesta; in caso di eccezione `_refund` decrementa il contatore o riaccredita il prezzo (dallo Sprint 68 anche per il job manuale e per l'import che arriva al vincolo di unicità). In Django Admin le azioni "Azzera la quota di raccolta manuale di oggi" e "Azzera tutti i contatori giornalieri di oggi" (lista utenti) e "Azzera tutti i contatori delle righe selezionate" (lista `DailyQuota`) sostituiscono la shell (`apps/jobs/admin_actions.py`). La logica è replicata in ogni servizio (`manual_generation.py`, `cover_letter_manual_generation.py`, `referral_message_manual_generation.py`, `import_service.py`, `manual_job_service.py`, `tasks.py`, `draft_chat.py`, `cover_letter_draft_chat.py`); non esiste un registro delle operazioni di addebito.

### 4.7 `RunLog` (diario tecnico)

Campi: `user` (FK, null), `job` (FK, null), `task_type`, `status` (`success` | `failure` | `skipped`, quest'ultimo dallo Sprint 68), `message`, `started_at`, `finished_at`. Non visibile all'utente; consultabile da Admin. Alla cancellazione di un utente (Sprint 67) i suoi `RunLog` e quelli dei suoi job restano, con `user`/`job` a NULL (`SET_NULL`) e `message` svuotato (§5.15). Nessuna pulizia automatica dei `RunLog`.

| `task_type` | Quando viene scritto |
|---|---|
| `collection` | A ogni raccolta per utente (automatica e manuale), anche con 0 ricerche (manuale); SKIPPED per un'automatica saltata (raccolta in corso, nessuna ricerca attiva, raccolta di oggi già fatta); FAILURE con prefisso "automatica:" per un'automatica fallita: prima riga `raccolti=N scorati=M scartati_scoring=K ritentati=R ritentati_scorati=S scartati_campi_mancanti=A scartati_troppo_lunghi=B scartati_duplicati=C gruppi=G gruppi_falliti=F`, poi una riga per gruppo (`gruppo <tipo> · <città>, <paese>: ok, offerte=N` o `ERRORE <eccezione>`). SUCCESS se nessun gruppo è fallito, FAILURE se almeno uno è fallito (gli altri sono comunque raccolti) o se la raccolta fallisce del tutto (messaggio dell'eccezione); SKIPPED se il ciclo notturno salta l'utente per una raccolta manuale in corso (Sprint 68) |
| `scoring` | FAILURE per ogni job il cui scoring fallisce |
| `cv_generation` | FAILURE se la generazione manuale fallisce (anche per `SystemExit`, Sprint 69); SUCCESS **solo** se il CV resta multi-pagina dopo il ripiego |
| `cover_letter_generation` | solo FAILURE |
| `referral_message_generation` | solo FAILURE |
| `cv_draft_chat` | solo FAILURE (chiamata AI della chat) |
| `cover_letter_draft_chat` | solo FAILURE |

Le generazioni riuscite, le anteprime e le finalizzazioni non lasciano traccia nel `RunLog`. Le offerte scartate dalla raccolta sono contate (non elencate) nel `RunLog` `collection` dallo Sprint 68.

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
    "actions": [{"type": str, "profile_experience_id": int|null, "bullet_id": str|null,
                 "area_index": int|null, "education_index": int|null, "language_index": int|null,
                 "text": str|null, "name": str|null, "level": str|null,
                 "area_text"?: str,                      # solo update_area/remove_area (Sprint 69)
                 "decision": "accepted"|"rejected"}]}]      # "decision" assente finché l'utente non sceglie
  ```
- `source_document` (Sprint 69, FK nullable a `CVDocument`, `SET_NULL`): documento di riferimento — quello del seed, poi quello prodotto dalla finalizzazione della bozza o quello scelto con "continua la bozza". La bozza è **superata** se l'ultimo `CVDocument` del job (con `content_json`) è un altro. Le bozze esistenti l'hanno ricevuto dalla migrazione `cv/0011` (ultimo documento generato prima della creazione della bozza);
- `created_at`, `updated_at`.

La bozza non ha un PDF proprio. Il seme si crea dall'ultimo `CVDocument` con `content_json` non vuoto (§5.12). Una nuova generazione non tocca la bozza: è l'editor a chiedere se riseminarla (§5.12). Le azioni salvate prima dello Sprint 69 (`bullet_index`) ricevono alla prima lettura il `bullet_id` del bullet che occupa quella posizione.

### 4.10 `CoverLetterDocument` (Sprint 42)

- `job` (FK, `related_name="cover_letter_documents"`), `user`, `html_source`;
- `pdf_file`: file nella cartella media `cover_letter_documents/`, nome casuale `<uuid4>.pdf` (Sprint 66); scaricabile solo con URL firmato (§4.15);
- `generated_at`;
- `instructions_used`: indicazioni dell'utente per questa generazione (alimenta lo storico delle indicazioni riusabili); vuoto per i documenti finalizzati dall'editor;
- `content_json` (Sprint 63): `{"content_language": str, "translated_city": str, "paragraphs": [{"id": str, "text": str}]}` (paragrafi con id stabile dallo Sprint 69; quelli salvati come semplici stringhe sono convertiti in modo pigro); `{}` per le lettere precedenti, non riapribili nell'editor;
- `page_count` (Sprint 69): pagine del PDF, come per il CV.

Ogni generazione o finalizzazione crea un nuovo record; in UI si usa l'ultimo. Non tocca mai `Job.status` né `is_archived`.

### 4.11 `CoverLetterDraft` (Sprint 63)

`job` (OneToOne, `related_name="cover_letter_draft"`), `user`, `content_json` (stessa struttura di §4.10), `chat_history`, `source_document` (Sprint 69, come in §4.9), `created_at`, `updated_at`. Ogni turno assistente ha `actions: [{"type": "update_paragraph"|"add_paragraph"|"remove_paragraph", "paragraph_id": str|null, "text": str|null, "decision"?: "accepted"|"rejected"}]` (`paragraph_index` fino allo Sprint 68, convertito in modo pigro).

### 4.12 `ReferralMessageDocument` (Sprint 50)

- `job` (FK, `related_name="referral_message_documents"`), `user`;
- `channel`: `linkedin` | `email`;
- `recipient_name` (255, facoltativo), `recipient_linkedin_url` (URL 500, facoltativo, **salvato ma inerte**: non usato nel prompt, nemmeno come contesto; dallo Sprint 69 la PWA lo mostra nello storico come link e spiega che è solo un riferimento);
- `instructions_used`, `subject` (255, vuoto per LinkedIn), `content`, `generated_at`.

Nessun PDF. Più messaggi per job (storico, mai sostituiti, non modificabili né cancellabili dall'app).

### 4.13 `JobFilterPreset` (filtri preferiti, Sprint 64)

- `user` (FK, `related_name="job_filter_presets"`), `name` (100), `created_at`; ordinamento per `created_at`;
- `scores` (JSON lista di interi), `statuses` (JSON ⊆ `new`, `cv_generated`, `application_done`), `search_ids` (JSON lista di id `SavedSearch` come stringhe numeriche o `"none"`, **non FK**: un id di una ricerca eliminata non filtra nulla), `location` (255), `applicants_ranges` (JSON ⊆ `under_25`, `25_50`, `51_100`, `101_200`, `over_200`), `has_recruiter` (`""` | `"yes"` | `"no"`); dallo Sprint 82 `contract_types` (JSON ⊆ codici di `Job.ContractType`) e `has_salary` (`""` | `"yes"` | `"no"`), vuoti nei preset salvati prima (migrazione `jobs/0023`).
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

**Cancellazione dei file (Sprint 67).** I segnali di `apps/accounts/signals.py` eliminano il file su disco dopo il commit (`transaction.on_commit`) quando si cancella una riga `CVDocument`, `CoverLetterDocument` o `Profile` (`post_delete`), qualunque sia la strada (cancellazione dell'account, Django Admin, shell, cascata). `ProfileSerializer.update` cancella la foto precedente quando ne viene caricata una nuova: era l'unica fonte di file orfani, perché CV e cover letter creano sempre una riga nuova.

**File esistenti.** Il comando idempotente `manage.py secure_media_files [--dry-run] [--delete-orphans]` rinomina con nomi casuali i file con nomi del vecchio schema aggiornando il DB (le foto vengono anche ricodificate come sopra) e, con `--delete-orphans`, elimina i file in `MEDIA_ROOT` non più referenziati da nessun record (versioni vecchie di foto, file di record cancellati).

### 4.16 `LegalAcceptance` (Sprint 67)

Registro delle accettazioni (`apps/accounts/models.py`): `user` (FK, `related_name="legal_acceptances"`, cascata), `document` (`privacy` | `terms` | `age`), `version` (20), `accepted_at` (default now); ordinamento per `accepted_at, id`.

- **Solo inserimenti**: `save()` solleva `ValueError` su una riga già esistente; una nuova versione aggiunge righe e quelle vecchie restano come storico (si cancellano solo con l'account). In Admin è in sola lettura, senza aggiunta né modifica.
- **Versioni correnti** come costanti in `apps/accounts/legal.py`: `PRIVACY_VERSION = "1.1"` e `PRIVACY_DATE = "2026-11-15"` (Sprint 77: raccolta automatica e notifica di fine raccolta), `TERMS_VERSION = "1.0"` e `TERMS_DATE = "2026-11-14"` (data di entrata in vigore mostrata nelle pagine), `MIN_AGE = 16`; la versione della dichiarazione d'età è l'età minima stessa (`AGE_VERSION = "16"`), così un cambio del requisito richiede una nuova dichiarazione.
- `missing_acceptances(user)`: documenti di cui manca la coppia (documento, versione corrente), calcolato con una query e memorizzato sull'oggetto `user` per la durata della richiesta. `record_acceptances(user, documents=None)`: `bulk_create` delle versioni correnti (tutte o solo quelle indicate). `public_legal_info()`: versioni, date, età minima e dati del titolare (`LEGAL_CONTROLLER_NAME`, `_ADDRESS`, `_EMAIL`, con `complete` vero se ci sono nome ed email).
- Cambiare un testo in modo sostanziale = nuovo numero di versione e data in `legal.py` (e nei testi in `frontend/src/legal/` e `Docs/legal/`): tutti gli utenti rivedono la schermata di accettazione al primo accesso.

---

## 5. I flussi principali, tradotti in tecnica

### 5.1 Raccolta automatica Pro (raccolta → scoring; dallo Sprint 77 al posto del ciclo notturno)

Fino allo Sprint 76 il task `run_nightly_cycle` girava alle 02:00 Europe/Rome per tutti gli utenti. Dallo Sprint 77 (SPEC-DELTA A4/A5, B1–B4) c'è **una raccolta al giorno per utente**, automatica (solo Pro) o manuale (§5.6), che consuma la stessa quota `DailyQuota.collection_count` (`COLLECTION_DAILY_LIMIT = 1`, giorno Europe/Rome).

- **Dispatcher** `run_automatic_collections` (Beat, ogni 15 minuti): per ogni utente attivo con `plan = pro` e `auto_collection_enabled`, `automatic_collection_due(user)` confronta l'ora locale nel fuso `User.timezone` (fuso non valido → Europe/Rome) con `auto_collection_time`: dovuta se l'ora "da orologio" è ≥ dell'orario e `auto_collection_last_local_date` non è oggi (data locale). Prima di avviare segna la data locale (il giro successivo non la ripete mentre è in coda) e chiama `run_automatic_collection.delay(user_id)`; un errore su un utente non ferma gli altri. Ora legale: un orario inesistente il giorno del passaggio all'ora legale parte al primo giro dopo (es. 02:30 → 03:00); uno ripetuto al ritorno all'ora solare non riparte (data locale già segnata). Un orario a ridosso della mezzanotte può partire dopo la mezzanotte e consumare la quota del nuovo giorno.
- **Task per utente** `run_automatic_collection(user_id)` (worker): ricontrolla piano e attivazione, poi `run_automatic_collection_for_user(user)`.

`run_automatic_collection_for_user(user)` (funzione normale):

0. **Guardia e quota**, in una transazione con `select_for_update` su `User` e `DailyQuota`: se `collection_in_progress` è attivo e non stantio (< 2 h, §5.6) → `RunLog` `collection`/SKIPPED; senza ricerche attive → SKIPPED senza consumare la quota; se la raccolta di oggi è già fatta (`collection_count >= 1`, per esempio a mano prima dell'orario) → SKIPPED. Altrimenti riserva la quota (`collection_count += 1`, `collection_done_at = now`) e accende la guardia, spenta in `finally`.
1. **Raccolta** (`apps/jobs/collection.py`, `collect_jobs_for_user`): chiama `fetch_groups` della fonte (§5.3) con tutte le ricerche attive dell'utente; la fonte fa **una chiamata Apify per gruppo** (tipo × città × paese), finestra "ultime 24 ore" applicata dall'actor, al massimo 150 risultati per chiamata. Un gruppo che fallisce (dopo i 2 tentativi) non fa perdere gli altri: le sue offerte mancano e l'errore finisce nel `RunLog`; se falliscono **tutti** i gruppi si solleva `CollectionFailed` (raccolta fallita). **Nessun tetto per piano o per notte** e **nessun cap di intake** (rimossi nello Sprint 46). Ogni offerta:
   - è scartata se manca uno dei campi `REQUIRED_FIELDS` (`title`, `company`, `location`, `description`, `apply_url`);
   - è scartata se uno dei campi `title`, `company`, `location`, `apply_url`, `matched_search`, `salary`, `recruiter_name`, `recruiter_profile_url` supera il `max_length` del modello (Sprint 49; mai troncata);
   - è scartata se il suo `external_id` esiste già tra i job LinkedIn dell'utente (archiviati e importati compresi) o è già comparso nello stesso run;
   - altrimenti diventa un `Job` con `origin=collected`, `status=new`, `matched_saved_search` = ricerca attribuita dalla fonte (se è tra le ricerche attive dell'utente), creato con `Job.objects.create` uno per uno (senza transazione). Gli scarti sono contati per motivo (`CollectionResult.discarded_missing`, `discarded_too_long`, `discarded_duplicate`).
2. **Scoring** (§5.9) in parallelo (`SCORING_CONCURRENCY = 5` thread) dei job appena creati **più** i job dell'utente rimasti senza punteggio con `scoring_failures < 3` (Sprint 68: scoring fallito in passato o raccolta interrotta prima dello scoring). Un job il cui scoring fallisce **resta in lista senza punteggio** e incrementa `scoring_failures`.
3. **`RunLog`** `collection` con conteggi, scarti ed esito per gruppo (§4.7). La funzione restituisce `{collected, scored, discarded_scoring, kept, retried, retried_scored, groups_failed}`, dove `kept = scored`.
4. **Fallimento** (eccezione, compreso `SystemExit`; in pratica tutti i gruppi falliti o un errore imprevisto): la quota torna **sulla riga riservata** (`_refund_collection_quota(quota_pk)`, Sprint 77: prima si restituiva sul giorno corrente, sbagliando giorno a cavallo della mezzanotte), `RunLog` FAILURE con prefisso "automatica:"; non si ritenta lo stesso giorno. Se falliscono solo alcuni gruppi la raccolta è riuscita e la quota resta consumata (le chiamate sono già pagate).
5. **Notifica** (§5.5): se `collected > 0`, `send_new_jobs_notification(user)`.

**Nessuna generazione automatica di CV** (rimossa nello Sprint 45): tutti i documenti si generano solo su richiesta.

Un errore imprevisto durante la creazione dei job interrompe ancora la raccolta dell'utente, ma i job già creati senza punteggio vengono ripresi dallo scoring della raccolta successiva (automatica o manuale; chi non raccoglie non ha ritenti). Il limite per lingua dello Sprint 48 non è stato riapplicato ai job valutati prima (servirebbe una nuova chiamata AI per job). Per rilanciare la raccolta di un solo utente serve la shell Django (`DEPLOY.md` §7.4), con la stessa guardia e la stessa quota; per ritentare subito lo scoring dei job senza punteggio c'è `manage.py retry_unscored_jobs [--dry-run] [--user-id N] [--ignore-limit]`.

> **Worker con 1 CPU.** Le raccolte automatiche girano nel worker Celery (concorrenza = numero di CPU, 1 sul VPS): con più Pro allo stesso orario partono una dopo l'altra. La raccolta manuale gira nel `web` e non ne risente.

### 5.2 Generazione su richiesta: schema comune

Tutte le azioni manuali che producono contenuti AI (CV, cover letter, messaggio di networking) seguono lo stesso schema, **sincrono nella richiesta HTTP**:

1. **Guardia di concorrenza + riserva** in un'unica transazione (`_guard_and_reserve`): `select_for_update` sul `Job`; se il flag `*_generation_in_progress` dell'artefatto è già attivo **e non stantio** (§4.4, Sprint 69) la richiesta è rifiutata (409, nessun consumo). Per il CV si verifica anche `Profile.is_complete` (409 "Completa il profilo…"). Poi si riserva quota o credito (§4.6; saldo insufficiente → 409) e si accende il flag con `*_generation_started_at = now`.
2. **Esecuzione** (chiamata Bedrock, eventuale rendering PDF, salvataggio) fuori dalla transazione, nello stesso processo gunicorn.
3. **Successo**: flag e timestamp spenti; per il CV `status = cv_generated` salvo per un job già `application_done`, che resta tale (Sprint 69), `date_cv_generated = now`, `is_archived = False` (il job esce dall'Archivio); cover letter e messaggi non toccano lo stato del job. Risposta 201 (CV e cover letter con `page_count`, §12.3).
4. **Fallimento** (qualsiasi `Exception` e, dallo Sprint 69, anche `SystemExit`, cioè il timeout di gunicorn): restituzione della riserva (contatore decrementato o prezzo riaccreditato), `RunLog` FAILURE, flag spento; lo stato del job **non cambia** (Sprint 69, prima tornava a `new`). Risposta 502 con messaggio generico ("Impossibile creare il CV per questo job."); con `SystemExit` l'eccezione viene rilanciata dopo la pulizia e il worker termina.

I tre flag sono indipendenti: si può generare una cover letter mentre è in corso un CV sullo stesso job. Il pulsante della PWA si disabilita durante la richiesta e quando il flag (non stantio) è attivo nel job serializzato, per tutti e tre gli artefatti (`referral_message_generation_in_progress` esposto dallo Sprint 69).

| Azione | Servizio | Guardia | Contatore / prezzo | Stato del job |
|---|---|---|---|---|
| Genera / rigenera CV (con "colma i gap") | `apps/cv/manual_generation.py` | `cv_generation_in_progress` (stantio dopo 35 min) | `manual_cv_count` / `PRICE_MANUAL_CV_EXTRA` | → `cv_generated` (`application_done` resta; invariato se fallisce); esce dall'archivio |
| Genera cover letter | `apps/cv/cover_letter_manual_generation.py` | `cover_letter_generation_in_progress` | `cover_letter_count` / `PRICE_COVER_LETTER_EXTRA` | invariato |
| Genera messaggio di networking | `apps/cv/referral_message_manual_generation.py` | `referral_message_generation_in_progress` | `referral_message_count` / `PRICE_REFERRAL_MESSAGE_EXTRA` | invariato |
| Import da link | `apps/jobs/import_service.py` | nessuna (controllo duplicato prima della riserva; `IntegrityError` sul vincolo di unicità → "già importato" con restituzione) | `import_count` / `PRICE_IMPORT_EXTRA`, solo Pro | nuovo job `new` |
| Job manuale | `apps/jobs/manual_job_service.py` | nessuna (restituzione se la creazione fallisce) | `manual_job_count` / `PRICE_MANUAL_JOB_EXTRA` | nuovo job `new` |
| Raccolta manuale e automatica | `apps/jobs/tasks.py` | `User.collection_in_progress` (stantia dopo 2 h, condivisa tra le due) | `collection_count` (una al giorno in totale, solo con ricerche attive; restituita sulla riga riservata), nessun credito | nuovi job `new` |
| Messaggio chat editor | `apps/cv/draft_chat.py`, `cover_letter_draft_chat.py` | nessuna | solo credito (`PRICE_*_DRAFT_CHAT_MESSAGE`) | invariato |

Il "riprova" dopo un fallimento è una normale nuova richiesta e consuma come tale. Il timeout gunicorn (`SystemExit`) è intercettato dalla raccolta manuale e, dallo Sprint 69, dalle tre generazioni. Un processo ucciso senza eccezione (SIGKILL, OOM, riavvio oltre il tempo di grazia) lascia invece la riserva consumata; il flag scade da solo dopo 35 minuti (§11).

### 5.3 La "fonte offerte" come componente sostituibile

`apps/jobs/sources/__init__.py` espone `get_job_source()`, che oggi restituisce sempre `ApifyLinkedInSource` (`apps/jobs/sources/apify_linkedin.py`). L'interfaccia ha due metodi: `fetch(searches, …)` per la raccolta e `fetch_by_url(url)` per l'import. Raccolta, scoring e generazione non dipendono dalla fonte concreta.

**Raccolta via Apify.**
- Actor `cheap_scraper~linkedin-job-scraper`, endpoint `run-sync-get-dataset-items`, autenticazione `Authorization: Bearer <APIFY_API_TOKEN>` (token solo in env, mai nell'URL).
- Le ricerche attive sono **raggruppate per (`search_type`, `city`, `country`)**: una chiamata per gruppo. Un utente con tutte le ricerche sulla stessa città fa al massimo 2 chiamate (una per tipo).
- Payload per gruppo: `keyword` = lista delle keywords per i gruppi Job role, oppure `COMPANY_SEARCH_KEYWORDS = ["jobs", "hiring"]` per i gruppi Company; `location = "<città>, <paese>"`; `publishedAt = "r86400"` (ultime 24 h); `maxItems = MAX_ITEMS_PER_CALL = 150` (minimo fatturato per chiamata dall'actor, pay-per-result); `saveOnlyUniqueItems = true`; per le Company anche **`companyInclude`** con i nomi azienda (risoluzione per azienda LinkedIn invece che full-text).
- Timeout 180 s, `MAX_ATTEMPTS = 2`. Il parametro `limit` di `fetch()` è ignorato.
- **Esito per gruppo** (Sprint 68): `fetch_groups(searches, window_hours)` restituisce un elemento per gruppo `{label, offers, error}` (`label` = `"<tipo> · <città>, <paese>"`) e intercetta l'eccezione di ogni gruppo invece di farla risalire; `fetch()` resta come appiattimento che solleva il primo errore. Ogni offerta porta `saved_search_id`: la ricerca del gruppo la cui etichetta coincide (senza maiuscole) con quella dell'actor (Company: nome azienda = keywords; Job role: `"<keywords> - <città>, <paese>"` = `searchString`), oppure l'unica ricerca del gruppo, altrimenti `None`.
- `_normalize_item` mappa i nomi alternativi dei campi Apify; dallo Sprint 82 `salaryInfo` (lista di 1–2 stringhe, es. `["$91000.00", "$136500.00"]`) → `salary` = `"$91.000 – $136.500"` (`_format_salary`: simbolo della fonte, `.00` tolti, migliaia con il punto, decimali con la virgola, stringhe non riconosciute invariate, massimo 255) e `contractType` → `contract_type` (`_normalize_contract_type`, valore ignoto = vuoto); `matched_search` = `searchString` (sostituito dal nome azienda per le Company); `applicationsCount` → `applicants_count` o `applicants_bucket` ("first 25" → `under_25`, "Over 200" → `over_200`); `posterFullName` / `posterProfileUrl` → recruiter; `published_at` con `parse_datetime`.

**Import da URL via API guest di LinkedIn.** `fetch_by_url` estrae l'id dall'URL (`linkedin.com/jobs/view/…<id>`) e legge `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<id>` (nessuna chiave, User-Agent da browser, timeout 15 s); il parsing dell'HTML è fatto con espressioni regolari sulle classi `topcard__title`, `topcard__org-name-link`, `topcard__flavor--bullet`, `show-more-less-html__markup`. Nessun dato su data di pubblicazione, candidati o recruiter.

> **Nota di conformità.** Lo scraping di LinkedIn tramite terze parti e la lettura della pagina guest possono violare i termini di servizio di LinkedIn. Scelta consapevole del committente per l'MVP (§11).

### 5.4 Pre-popolamento del profilo da CV caricato (onboarding)

`POST /api/profile/import-cv/` (multipart, campo `file`), view `CVImportView`, modulo `apps/profiles/cv_import.py`:

1. **Estrazione del testo** lato server: `pdfplumber` per i PDF, `python-docx` per i `.docx`; il formato si decide dai primi byte del file (`%PDF-` / `PK\x03\x04`), non da nome o content-type (Sprint 66). File mancante, formato diverso, oltre 5 MB, PDF oltre 10 pagine o `.docx` oltre 30 MB decompresso → 400; file corrotto → 422. Dallo Sprint 70 ogni errore ha un `code` (`file_missing`, `file_too_large`, `unsupported_type`, `too_many_pages`, `unreadable`, `quota_exceeded`, `ai_unavailable`; eccezione `CVFileRejected(code, message)`, sottoclasse di `ValueError`) da cui la PWA sceglie il messaggio nella lingua dell'interfaccia; la PWA controlla i 5 MB anche prima dell'invio e tratta un 413 di Caddy come file troppo grande. Il testo estratto è troncato a `MAX_TEXT_LENGTH = 30.000` caratteri.
2. **Soglia**: se il testo è sotto `MIN_TEXT_LENGTH = 40` caratteri (tipico dei PDF scannerizzati; niente OCR) → 422 "non siamo riusciti a leggere il CV, compila il profilo manualmente", senza chiamare Claude.
3. **Strutturazione** con `BEDROCK_CV_PARSING_MODEL` sul solo testo. Prompt: nessuna invenzione; date ISO (primo del mese se c'è solo mese/anno); telefono ed email solo se scritti letteralmente; lingue mappate su codice ISO e uno dei 4 livelli (A1/A2 → elementary, B1/B2 → intermediate, C1 → fluent, C2/nativo → mother_tongue), voce omessa se incerta.
4. Prima della chiamata AI si riserva `DailyQuota.cv_import_count` (5/giorno, nessun credito; oltre → 409); se Bedrock fallisce la quota viene restituita e la risposta è 502 `ai_unavailable` (prima: 500 non gestito). Throttle `cv_import` 10/ora (§7.1).
5. **Risposta 200** con il JSON strutturato. **Nulla viene salvato**: è la PWA a pre-compilare il form, che l'utente salva poi con le API del profilo.

L'import non consuma credito. Lato frontend il pre-fill scarta le date di esperienze e istruzione (dallo Sprint 70 tiene le `technologies`; i bullet oltre 400 caratteri sono evidenziati, perché il salvataggio li rifiuterebbe); città e LinkedIn non sono estratti. L'import è disponibile solo in onboarding, non nella pagina Profilo.

### 5.5 Notifiche: meccanismo

Un task Beat ogni 15 minuti itera sugli utenti attivi con `notifications_enabled = True` (`apps/notifications/tasks.py`; filtro aggiunto nello Sprint 67, ricontrollato anche nella funzione per singolo utente) per il promemoria di inattività; la notifica dei job nuovi parte invece dalla raccolta automatica:

- **Fine raccolta automatica** (`send_new_jobs_notification(user)`, Sprint 77, al posto della notifica mattutina delle 10:00 rimossa): chiamata da `run_automatic_collection_for_user` quando la raccolta ha creato job; se le notifiche sono attive invia a tutte le `PushSubscription` "Nuovi job pronti" / "Ci sono nuove offerte da valutare nella tua lista." e aggiorna `last_notified_at`. Nessuna notifica dopo la raccolta manuale, l'import o il job manuale.
- **Inattività** (`send_inactivity_notifications`): se sono passati 7 giorni (`INACTIVITY_THRESHOLD`) da `last_activity_reset` e non è già stato inviato un promemoria per questo periodo (`last_inactivity_notified_at >= last_activity_reset`), invia "Non ti candidi da un po'" / "Entra nell'app e valuta le offerte in attesa." e aggiorna `last_inactivity_notified_at`.

I testi sono in italiano o in inglese secondo `User.interface_language` al momento dell'invio (Sprint 71, `notification_payload` con `translation.override`). I timestamp vengono aggiornati anche se l'utente non ha sottoscrizioni o se gli invii falliscono; per un utente con le notifiche disattivate invece non vengono toccati. Dallo Sprint 70, quando la preferenza torna attiva (`PATCH /me` da `false` a `true`, oppure registrazione di una sottoscrizione con la preferenza spenta) `last_notified_at` è riportato a "adesso" (dallo Sprint 77 è solo informativo: nessuna notifica lo legge più). `last_inactivity_notified_at` non cambia. Il logout elimina la sottoscrizione del dispositivo (§3.8). Dallo Sprint 66: `webpush(..., timeout=10)`; una risposta 404/410 del push service elimina la sottoscrizione; qualunque altro errore su una sottoscrizione viene registrato nel log (solo l'id, mai l'endpoint) e si prosegue con le altre; un errore su un utente non interrompe il giro degli utenti successivi.

### 5.6 Raccolta manuale "Raccogli ora" (pannello della lista job)

`POST /api/jobs/collect/` → `run_manual_collection_for_user(user)`, **sincrono nella richiesta**:

1. Transazione con `select_for_update` su `User` e `DailyQuota`: se `collection_in_progress` è vero e non stantio (impostato da meno di `COLLECTION_STALE_AFTER = 2 h`, anche dalla raccolta automatica) → 409 "Raccolta già in corso per questo account."; se l'utente ha ricerche attive e `collection_count >= COLLECTION_DAILY_LIMIT = 1` (raccolta di oggi già fatta, automatica o manuale) → 409 "Raccolta di oggi già eseguita alle HH:MM. Massimo 1 al giorno." (ora di `collection_done_at` nel fuso dell'utente; con la data se il suo "oggi" non coincide con quello di Roma). Altrimenti, **solo con ricerche attive**, incrementa il contatore e scrive `collection_done_at` (Sprint 77: senza ricerche attive non si chiama la fonte e la quota non si consuma, ma si ritentano i job senza punteggio); accende il lock con `collection_started_at`.
2. Esegue la stessa pipeline dell'automatica per il solo utente (§5.1: raccolta raggruppata + scoring parallelo).
3. Successo → 200 `{collected, scored, discarded_scoring, kept, retried, retried_scored, groups_failed}` (ritenta anche i job dell'utente senza punteggio). Nessuna notifica push.
4. Fallimento, compreso `SystemExit` sollevato da gunicorn al timeout: restituzione della quota **sulla riga riservata**, `RunLog` FAILURE, 502 "Raccolta non riuscita. Riprova più tardi.".
5. In `finally` il lock viene rilasciato (`collection_in_progress = False`, `collection_started_at = None`).

Limite uguale per tutti i piani, senza sblocco a credito (le chiamate Apify sono fatturate comunque), **condiviso con la raccolta automatica** dei Pro: una raccolta manuale prima dell'orario fa saltare l'automatica di quel giorno (`RunLog` SKIPPED). Se falliscono solo alcuni gruppi la raccolta manuale riesce (200) con le offerte degli altri; se falliscono tutti è un fallimento (502, quota restituita). Per concedere una seconda raccolta lo stesso giorno l'amministratore usa l'azione Admin "Azzera la quota di raccolta manuale di oggi" (`DEPLOY.md` §7.3), che vale anche per l'automatica.

### 5.7 Import di un job da URL LinkedIn

`POST /api/jobs/import/` con `{url}` → `import_job_from_url(user, url)`, sincrono:

1. Piano non Pro → 403 (anche con credito).
2. URL non riconosciuto → 409 "Impossibile importare quel job.".
3. `external_id` già presente tra i job LinkedIn dell'utente (anche raccolti di notte) → 409 "Questo job è già nella tua lista.".
4. Riserva `import_count` (3/giorno) o credito `PRICE_IMPORT_EXTRA`; saldo insufficiente → 409.
5. Lettura dalla API guest (§5.3). Se fallisce, mancano campi obbligatori o un campo supera il `max_length` del modello (stessi controlli della raccolta, `offer_rejection_reason`, Sprint 68): restituzione della riserva e 409.
6. Creazione del `Job` (`source=linkedin`, `origin=imported`, `published_at` nullo) in un savepoint: se due import simultanei dello stesso link arrivano entrambi qui, il secondo riceve `IntegrityError` dal vincolo di unicità → riserva restituita e 409 "Questo job è già nella tua lista." (Sprint 68). Poi **scoring sincrono** (`score_job`); un fallimento di scoring non fa fallire la richiesta (job senza punteggio, ritentato di notte).
7. 201 `{job_id, status, score}`.


### 5.8 Creazione manuale di un job

`POST /api/jobs/manual/` → `create_manual_job(user, data)`, disponibile per **entrambi i piani**:

- validazione con `ManualJobCreateSerializer`: obbligatori `title`, `company`, `location`, `description`, `published_at` (data/ora interpretata in Europe/Rome), facoltativo `apply_url` → 400 con errori per campo;
- riserva `manual_job_count` (3/giorno) o credito `PRICE_MANUAL_JOB_EXTRA`; saldo insufficiente → 409;
- creazione con `source=manual`, `external_id = "manual-<uuid4>"`, `origin=imported` (sezione Importati), poi scoring sincrono;
- 201 `{job_id, status, score}`.

Se la creazione fallisce dopo la riserva, contatore o credito vengono restituiti e la risposta è 502 "Impossibile creare il job. Riprova più tardi." (Sprint 68). Un errore di scoring invece non fa fallire la richiesta e non restituisce nulla: il job esiste (è ciò che la quota paga) e lo scoring viene ritentato dal ciclo notturno come per i job raccolti. Scelta più semplice della restituzione condizionata, che avrebbe reso gratuito un job rimasto in lista e richiesto un percorso di addebito in più.

### 5.9 Scoring

Moduli `apps/jobs/ai_scoring.py` (prompt, schema, chiamata) e `apps/jobs/scoring.py` (applicazione, batch, fallimenti).

- **Input del modello**: profilo completo (sommario, esperienze con bullet, competenze, istruzione, certificazioni, lingue con livello tradotto) + titolo, azienda, **località** (dallo Sprint 68, `Località: …` o "non indicata") e descrizione dell'offerta.
- **Scala 1–10** con **rubrica per fascia** (Sprint 47) basata sul conteggio dei requisiti "hard" soddisfatti o mancanti: 9–10 tutti soddisfatti; 7–8 manca al più un elemento secondario; 5–6 manca almeno un requisito hard o seniority non allineata; 3–4 più requisiti mancanti o forte disallineamento; 1–2 profilo non pertinente. Descrizione vuota o non valutabile → match e gap vuoti, punteggio ≤ 6.
- **Regole** nel prompt: ogni voce di match/gap legata a un requisito esplicito dell'offerta; nessuna competenza inventata; nessun gap su elementi già nel profilo; `score_reasoning` di al massimo 2 frasi (~40 parole); `label` brevissima e `reason` di una frase; una lingua assente dal profilo non va mai tra i match.
- **Schema** `SCORE_JSON_SCHEMA`: `score` (int), `score_match` / `score_gaps` (liste di `{label, reason}`), `score_reasoning`, `language_check {required, language, international_exception}`.
- **Cap deterministico sulla lingua** (Sprint 48, `_language_score_cap`): il modello dichiara solo se l'offerta richiede una lingua (esplicitamente, o perché scritta interamente in una lingua non inglese) e se c'è un'eccezione "ambiente internazionale / inglese". In Python, se `required` è vero, non c'è eccezione e nessuna parola intera del nome lingua restituito coincide con le etichette localizzate (it/en/fr/de/es) delle lingue del profilo, il punteggio è limitato a `LANGUAGE_MISMATCH_SCORE_CAP = 3` e `score_reasoning` riceve il prefisso "Punteggio limitato a 3/10: lingua richiesta (X) assente dal profilo." (in inglese "Score capped at 3/10: required language (X) missing from the profile."): il prefisso è salvato nel DB, quindi è nella lingua dell'interfaccia del proprietario del job **al momento dello scoring** (`translation.override(job.user.interface_language)`, Sprint 71) e non cambia se l'utente cambia lingua dopo. Qualsiasi livello nel profilo evita il cap; il confronto è per parola intera (non per sottostringa) e non usa i codici ISO.
- **Applicazione** (`_apply_score_result`): clamp a 1–10, cap lingua, salvataggio di `score`, `score_match`, `score_gaps`, `score_reasoning`, `date_scored`.
- **Batch** (`score_jobs`, usato da raccolta notturna e manuale): `ThreadPoolExecutor` con `SCORING_CONCURRENCY = 5` thread **solo per le chiamate Bedrock**; il profilo è caricato una volta con `prefetch_related`; i salvataggi avvengono sul thread principale. **Singolo** (`score_job`): usato da import e job manuali.
- **Scarto campi oltre `max_length`**: avviene prima, nella raccolta (§5.1), per evitare che un `DataError` interrompa il batch.
- **Fallimenti**: errore Bedrock o output fuori schema dopo 3 tentativi → il job **resta in DB e in lista con `score = NULL`** (ordinato in fondo, senza badge), `RunLog` `scoring`/FAILURE e `scoring_failures` +1. Il ciclo notturno (e la raccolta manuale) ritenta i job dell'utente con `score` nullo e `scoring_failures < MAX_SCORING_FAILURES = 3` (`scoring.unscored_jobs_to_retry`); oltre resta senza punteggio, ritentabile solo con `retry_unscored_jobs --ignore-limit`.
- **Storico**: i punteggi dati su scala 1–5 sono riscalati ×2 da `rescale_legacy_scores` (dry-run di default, `--confirm`, `--before <ISO>`; idempotente grazie a `score_rescaled_from_legacy`; i valori > 5 prima del taglio sono segnalati e lasciati). Taglio di default **2026-09-24 21:00 UTC**, non la data del commit dello Sprint 47 (2026-09-28 14:39 UTC): sui dati l'ultimo punteggio 1–5 è delle 08:37 UTC del 24/09 e il primo su 1–10 delle 21:07 UTC dello stesso giorno. Sul dump del 2026-11-14 i punteggi da riscalare erano 3.898, di cui 988 sui job del vecchio cap (eliminati) → 2.910. I punteggi precedenti allo Sprint 48 non hanno il cap lingua e non sono stati rivalutati. Frontend senza logica speciale: colori a fasce (`scoreStyle.js`, `ceil(score/2)`), filtro 1–10 e ordinamento lavorano già sulla sola scala 1–10.

### 5.10 Cover letter

`POST /api/jobs/<id>/generate-cover-letter/` con `{instructions}` → `request_cover_letter_generation` (schema §5.2) → `generate_cover_letter(job, instructions)` (`apps/cv/cover_letter_generation.py`):

1. `generate_cover_letter_content` (`cover_letter_content.py`): contesto profilo uguale a quello del CV (sommario, città, esperienze, skill, certificazioni; **non** istruzione e lingue), titolo/azienda/descrizione dell'offerta, indicazioni, lingua. Il modello scrive solo i **paragrafi del corpo** (3–5: apertura, 1–2 di esperienze reali, uno dedicato alle indicazioni se presenti, chiusura), più `translated_city` e `content_language`. Le indicazioni possono orientare il tono o introdurre fatti reali non presenti nel profilo, sotto la responsabilità dell'utente.
2. Oggetto, saluto ("Dear Hiring Manager," e simili) e chiusura sono testi fissi per lingua (`COVER_LETTER_LABELS`, 5 lingue), mai generati.
3. Intestazione: nome e cognome; riga contatti "Città tradotta, PAESE | telefono | email del profilo", **senza LinkedIn**. Nessuna data, destinatario, foto o grassetto.
4. Rendering con `render_cover_letter` (3 livelli di compattamento, §3.6), salvataggio di `CoverLetterDocument` con `instructions_used`, `content_json` (paragrafi con id) e `page_count`.

Indicazioni riusabili: `GET /api/cover-letter-instructions/` restituisce fino a 20 **voci** distinte, su tutti i job dell'utente, dalla più recente; la PWA le propone come checkbox e le concatena al testo nuovo separate da una riga vuota. Dallo Sprint 69 (`apps/cv/instructions_history.py`) ogni `instructions_used` è scomposto nei blocchi separati da righe vuote e i blocchi sono deduplicati ignorando spazi e maiuscole: una combinazione di voci già note non produce una voce nuova (vale anche per lo storico esistente); un'indicazione scritta su più paragrafi compare come più voci. `instructions_used` resta il testo completo passato al modello.

Nome file di download: `Cover letter {Nome Cognome} - {Titolo job}.pdf` (caratteri `\/:*?"<>|` rimossi; senza nome si usa l'email); per il CV `CV {Nome Cognome} - {Titolo job}.pdf`. Entrambi calcolati da `JobSerializer`.

### 5.11 Messaggi di networking

`POST /api/jobs/<id>/generate-referral-message/` con `{channel, recipient_name?, recipient_linkedin_url?, instructions?}` → `request_referral_message_generation` (schema §5.2) → `generate_referral_message`:

- canale non valido → 400;
- `generate_referral_message_content` (`referral_message_content.py`) passa profilo, nome reale del candidato (per la firma), offerta, canale, destinatario, indicazioni e lingua; schema `{subject, message}`;
- vincoli di canale solo nel prompt: LinkedIn al massimo 80–100 parole, nessun oggetto; email con oggetto di circa 60 caratteri e corpo di 150–180 parole in 2–3 paragrafi; saluto e firma nel testo; saluto generico se manca il nome; nessuna relazione pregressa inventata; nessun allegato menzionato; richiesta finale chiara;
- salvataggio di un nuovo `ReferralMessageDocument` (nessun rendering), 201 con il messaggio serializzato (`id, channel, recipient_name, recipient_linkedin_url, subject, content, generated_at`).

Storico per job: `GET /api/jobs/<id>/referral-messages/` (dal più recente). Indicazioni riusabili: `GET /api/referral-message-instructions/` (20 voci distinte, tutti i job, stesse regole di scomposizione e deduplica della cover letter). `recipient_linkedin_url` non entra nel prompt (nemmeno come contesto: nessun fetch del profilo). La copia negli appunti è fatta dalla PWA (`navigator.clipboard`, con "Oggetto: …" in testa per l'email).

### 5.12 Editor delle bozze (CV e cover letter)

Stesso schema per i due documenti (moduli `apps/cv/draft.py` e `apps/cv/cover_letter_draft.py`, view in `apps/jobs/views.py`):

| Passo | CV | Cover letter |
|---|---|---|
| **Apertura** | La PWA legge prima il job (`cv_draft_outdated`, §12.2): se vero chiede "riparti dal nuovo documento / continua la bozza" (Sprint 69); altrimenti `GET …/cv-draft/` (200 `content_json`, 404 se manca) e su 404 `POST …/cv-draft/` | `GET` / `POST …/cover-letter-draft/`, `cover_letter_draft_outdated` |
| **Seed / risemina** | `POST …/cv-draft/` → `seed_draft_for_job`: `update_or_create` della bozza copiando `content_json` dall'ultimo `CVDocument` (id dei bullet assegnati se mancano), **chat azzerata**, `source_document` = quel documento; 409 se non c'è un documento o se il suo `content_json` è vuoto | `seed_cover_letter_draft_for_job`, stessa logica sull'ultima `CoverLetterDocument` |
| **Continua la bozza** | `POST …/cv-draft/` con `{"mode": "keep"}` (Sprint 69) → `keep_cv_draft`: contenuto e chat invariati, `source_document` = ultimo documento; 200. Senza bozza equivale al seed | `keep_cover_letter_draft` |
| **Lettura** | `load_cv_draft`: normalizzazione pigra (id dei bullet, azioni della chat con `bullet_index` → `bullet_id`), salvata se cambia qualcosa | `load_cover_letter_draft` (paragrafi stringa → `{id, text}`, `paragraph_index` → `paragraph_id`) |
| **Modifica** | `PATCH …/cv-draft/` con l'intero `content_json`, ripulito da `clean_cv_draft_content` (id mancanti assegnati su una copia, poi validazione; 400 se non la supera), dall'autosave della PWA (debounce 1,2 s); risponde con il contenuto salvato | `PATCH …/cover-letter-draft/` |
| **Anteprima** | `POST …/cv-draft/preview/` con il contenuto corrente nel body (o quello salvato): PDF binario + header `X-Page-Count`. Nessun taglio automatico: si renderizzano solo esperienze e bullet con `shown = true`, nell'ordine della bozza; codici lingua tradotti | `POST …/cover-letter-draft/preview/`: oggetto, saluto e chiusura fissi, paragrafi e città dalla bozza |
| **Finalizzazione** | `POST …/cv-draft/finalize/` con `{"content": …}` facoltativo (Sprint 69: il contenuto a schermo, ripulito e salvato nella bozza prima del rendering; 400 se non valido) → nuovo `CVDocument` (`generation_type=manual`, `content_json` = bozza, `page_count`), che diventa il `source_document` della bozza | `POST …/cover-letter-draft/finalize/`, stesso schema → nuova `CoverLetterDocument` |

Proprietà comuni:
- **validazione del `content_json`** (Sprint 66, `apps/cv/draft_validation.py`) in `PATCH` e anteprima: esattamente le chiavi prodotte dalla generazione (chiavi sconosciute o mancanti → 400), tipi attesi, numero massimo di elementi (CV: 20 aree, 30 esperienze con 30 bullet e 50 tecnologie ciascuna, 20 voci di istruzione, 100 skill, 50 certificazioni, 30 lingue; cover letter: 15 paragrafi), lunghezza massima di ogni testo (es. sommario 5.000, bullet 2.000, paragrafo 3.000) e dimensione totale (200.000 caratteri di JSON). Throttle `draft_preview` 60/min sull'anteprima;
- nessuna chiamata AI e **nessun consumo** di quota o credito in apertura, modifica, anteprima e finalizzazione;
- la finalizzazione non cambia `Job.status` né `date_cv_generated`; il nuovo PDF diventa quello scaricabile; la bozza resta;
- la PWA invia alla finalizzazione il contenuto a schermo (annullando l'autosave in attesa) e, prima di un messaggio in chat, salva subito l'eventuale modifica in attesa: nessuna modifica resta fuori dal PDF o dal contesto del modello (Sprint 69);
- una nuova generazione AI non tocca la bozza: alla riapertura dell'editor l'utente sceglie se riseminare o continuare (Sprint 69).

Cosa si modifica nella bozza CV: sommario e qualifica (con grassetto, Sprint 69), aree (aggiungi/rimuovi/riordina, con grassetto), per ogni esperienza "mostra nel CV" e ruolo (con grassetto; azienda, luogo, date e tecnologie no), bullet (mostra/nascondi, testo con grassetto, aggiungi/rimuovi/riordina), istruzione (tutti i campi, note con grassetto, solo nel CV), skill e certificazioni (solo selezione tra quelle del profilo), lingue (solo nel CV). Nella bozza della cover letter solo i paragrafi (modifica, riordino, aggiunta, eliminazione). Nessuna modifica della bozza viene scritta sul profilo master.

### 5.13 Chat AI degli editor

Endpoint `…/cv-draft/chat/` e `…/cover-letter-draft/chat/` (moduli `draft_chat.py`, `cover_letter_draft_chat.py`):

- `GET` → `{history, price, balance}` (404 senza bozza): `price` è `PRICE_CV_DRAFT_CHAT_MESSAGE` / `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE`, `balance` il saldo dell'utente, entrambi stringhe decimali, mostrati dalla PWA sopra il campo di testo (Sprint 69).
- `POST {message[, focus_bullets]}`:
  1. messaggio vuoto o oltre 2.000 caratteri → 400 (al massimo 50 `focus_bullets`); bozza assente → 502; throttle `chat` 20/min sul solo `POST`;
  2. **riserva del credito** (`select_for_update` sull'`User`): saldo sotto `PRICE_CV_DRAFT_CHAT_MESSAGE` / `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE` → **402** "Saldo credito insufficiente…"; non c'è quota gratuita;
  3. chiamata Bedrock (`BEDROCK_CV_GENERATION_MODEL`, 2000 token) con: `content_json` salvato della bozza (con gli id di esperienze, bullet e paragrafi), skill/certificazioni del profilo (CV), titolo/azienda/descrizione dell'offerta, cronologia degli ultimi 20 turni (`MAX_HISTORY_TURNS_IN_PROMPT`; la cronologia completa resta salvata) in cui ogni turno dell'assistente porta anche le **azioni proposte in forma compatta** con la decisione `accepted`/`rejected`/`pending` (Sprint 69, `history_for_prompt`; testo troncato a 200 caratteri), nuovo messaggio; per il CV anche i **bullet puntati** dall'utente (`focus_bullets: [{profile_experience_id, bullet_id}]`, Sprint 69; `bullet_index` ancora accettato dalle schede vecchie; tenuti solo se esistono), presentati come aiuto per le frasi ambigue, non come vincolo;
  4. errore AI → riaccredito, `RunLog` FAILURE, 502;
  5. **filtro difensivo** sulle azioni (`_sanitize_actions`, sulla bozza salvata): per il CV scarta i toggle di skill/certificazioni con nomi non presenti nel profilo, i livelli lingua non validi e — dallo Sprint 69 — le azioni su esperienze o `bullet_id` inesistenti, con `area_index`/`education_index`/`language_index` fuori range o senza il testo richiesto; normalizza `profile_experience_id` sul proprietario del bullet e allega `area_text` alle azioni sulle aree; per la cover letter scarta le azioni con `paragraph_id` inesistente o senza testo;
  6. accoda turno utente e risposta in `chat_history`; risponde `{reply, actions, balance}`. **Il backend non modifica mai `content_json`**.
- `PATCH {message_index, action_index, decision}` → scrive `decision` (`accepted` | `rejected`) dentro l'azione (Sprint 62); 204, oppure 400 per indici non interi o non validi. Gli indici sono posizioni nella cronologia, che cresce solo in coda. Dallo Sprint 69 la PWA ritenta la registrazione (3 tentativi) e segnala se non riesce.

**Azioni.** CV, 16 tipi (`CHAT_ACTION_TYPES`): `update_summary`, `update_qualification`, `update_role`, `update_bullet`, `add_bullet`, `hide_bullet`, `show_bullet`, `hide_experience`, `show_experience`, `update_area`, `add_area`, `remove_area`, `toggle_skill`, `toggle_certification`, `update_education_notes`, `update_language_level`. Cover letter, 3 tipi: `update_paragraph`, `add_paragraph` (in coda), `remove_paragraph`. Lo schema dell'azione è "piatto" (un oggetto con `type` e campi nullable, senza `oneOf`) per compatibilità con il tool-use forzato. Riferimenti (Sprint 69): bullet per **`bullet_id`** e paragrafi per **`paragraph_id`** (id stabili, §4.5), esperienze per `profile_experience_id`; aree, istruzione e lingue restano **indici 0-based** sulla bozza inviata, con `area_text` come riferimento di sicurezza per le aree.

**Pattern proposta → conferma.** Ogni azione è mostrata come card "prima → dopo" con Accetta/Rifiuta; nulla è applicato in automatico. "Accetta" applica la modifica allo stato dell'editor con le stesse funzioni dell'editing manuale, ritrovando l'elemento per id (o, per le aree, per `area_text`), e quindi passa dall'autosave; se l'elemento non c'è più la modifica non viene applicata, il pannello lo segnala e la decisione registrata è `rejected`. Poi la PWA registra la decisione con `PATCH`. Alla riapertura le card già decise restano disabilitate.

**Grounding.** Il testo narrativo si può amplificare oltre il profilo solo su richiesta esplicita dell'utente nella conversazione, segnalandolo nella risposta; aziende, ruoli e risultati non si inventano mai; skill e certificazioni del CV solo con nomi esatti del profilo, senza eccezioni (vincolo garantito anche dal filtro server). Nella cover letter il modello non scrive mai oggetto, saluto o chiusura.

**Costi.** Un messaggio = un addebito, a prescindere dal numero di azioni proposte; nessun `RunLog` per i messaggi riusciti.

### 5.14 Email di servizio (Sprint 67)

Testo semplice, in italiano o in inglese secondo `User.interface_language` (`apps/accounts/emails.py`; dallo Sprint 71 i testi sono msgid gettext in italiano tradotti nel `.po` come il resto del backend, composti dentro `translation.override`, §5.21), oggetto con prefisso "App-apply — " e firma "email automatica: non rispondere". Mai dati del profilo nel corpo: solo il link o la conferma dell'operazione. Sei tipi:

| Tipo | Quando | Contenuto |
|---|---|---|
| `verify` | Registrazione con email attiva; reinvio | Link `/verify-email?t=…` (3 giorni) |
| `already_registered` | Registrazione con un'email già registrata (email attiva) | Avviso del tentativo, link a `/login` e `/forgot-password` |
| `password_reset` | Richiesta di recupero | Link `/reset-password?uid=…&token=…` (3 giorni, monouso) |
| `account_deleted` | Dopo la cancellazione dell'account | Conferma, backup cancellati entro 7 giorni |
| `email_change_confirm` | Sprint 70: richiesta di cambio email, al **nuovo** indirizzo | Link `/confirm-email-change?t=…` (3 giorni) |
| `email_change_notice` | Sprint 70: stessa richiesta, all'indirizzo **attuale** | Avviso (senza il nuovo indirizzo), invito a cambiare la password se non è stato l'utente, link a `/settings` |

I link sono costruiti da `PUBLIC_BASE_URL` (default `https://$DOMAIN`, in sviluppo `http://localhost:5173`).

**Invio.** `send_templated_email` compone destinatario, oggetto e corpo e accoda il task `apps.accounts.tasks.send_service_email(to, subject, body)` con `.delay()`. Il task non legge il database, quindi funziona anche per un utente appena cancellato e non dipende dal commit della transazione che lo accoda; ritenta fino a 3 volte con backoff (`autoretry_for=OSError`, che comprende gli errori SMTP). Se il broker non risponde l'eccezione è registrata nel log (solo il tipo di email, mai l'indirizzo) e l'operazione dell'utente prosegue senza email.

**Configurazione.** SMTP di Django pensato per Gmail con una password per le app: `EMAIL_HOST` (default `smtp.gmail.com`), `EMAIL_PORT` (587), `EMAIL_USE_TLS` (true), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (gli spazi con cui Google mostra la password sono ignorati), `DEFAULT_FROM_EMAIL` (default `EMAIL_HOST_USER`), `EMAIL_TIMEOUT = 20` s; `EMAIL_BACKEND` sovrascrivibile da env.

**Senza credenziali** (`email_enabled()` falso): il task registra un warning e non invia; registrazione senza verifica (utenti già verificati, token subito), login senza controllo dell'indirizzo, reinvio della verifica e recupero password rispondono 503 `email_unavailable` (la PWA lo sa in anticipo da `GET /api/legal/` → `email_enabled` e mostra "non disponibile"). Nei test `EMAIL_BACKEND` locmem e credenziali azzerate (`TESTING`), così la suite lanciata nel container di produzione non legge le credenziali reali del `.env`.

**Non enumerazione.** Con l'email attiva registrazione, reinvio e recupero rispondono allo stesso modo che l'indirizzo esista o no (§3.7); i limiti per indirizzo usano l'hash dell'email nella chiave di cache (§7.1).

### 5.15 Cancellazione dell'account (Sprint 67)

`POST /api/accounts/delete/ {password, confirm: true}` (`DeleteAccountView`, esente dal gate, throttle `password_check`):

1. `DeleteAccountSerializer` verifica la password (400 `password` se errata) e `confirm is True` (400 altrimenti).
2. Si salvano email e lingua dell'utente, che servono per l'email di conferma dopo la cancellazione.
3. `delete_account(user)` (`apps/accounts/account_data.py`): `user.delete()` in una transazione. La cascata elimina profilo e sezioni, ricerche, job, CV, cover letter, bozze e chat, messaggi di networking, filtri preferiti, `DailyQuota`, `AuthToken` (tutti i dispositivi disconnessi), `PushSubscription` e `LegalAcceptance`.
4. I segnali di `apps/accounts/signals.py` fanno la pulizia che la cascata non fa: `pre_delete` di `User` svuota `message` dei `RunLog` dell'utente e dei suoi job (le righe restano, con `user`/`job` a NULL per `SET_NULL`, come statistiche tecniche: il messaggio è il testo di un'eccezione e può contenere testo derivato dalle richieste); `post_delete` di `CVDocument`, `CoverLetterDocument` e `Profile` registra con `transaction.on_commit` la cancellazione del PDF o della foto su disco (un errore di file è solo registrato nel log). Valgono anche per una cancellazione da Django Admin o dalla shell.
5. Email `account_deleted` all'indirizzo salvato (solo con l'endpoint dell'utente, non dall'Admin); risposta **204**.

I dati restano nei backup locali fino alla loro rotazione (7 giorni, §5.18). Le copie delle email inviate restano nella cartella "Posta inviata" dell'account Gmail mittente (§11).

### 5.16 Export dei dati (Sprint 67)

Due passi, come per i PDF dello Sprint 66, perché un semplice link funziona anche nella PWA iOS (che non può aggiungere l'header `Authorization` a un download):

1. `POST /api/accounts/export/` (autenticato, esente dal gate, throttle `data_export` **3 al giorno** per utente) → `200 {"url": "/api/accounts/export/download/?s=…"}`, firma `TimestampSigner(salt="apps.accounts.export")` sull'id utente, validità `EXPORT_URL_MAX_AGE` = 10 minuti. Il limite si applica qui, non al download.
2. `GET /api/accounts/export/download/?s=…` (nessuna autenticazione): firma assente, manomessa o scaduta, o utente non attivo → 404; altrimenti `build_export(user)` genera lo ZIP **in modo sincrono** (`SpooledTemporaryFile`, in memoria fino a 20 MB, poi su disco) e lo restituisce come allegato `app-apply-dati-<id>.zip`, `Cache-Control: private, no-store`.

Contenuto dello ZIP:
- `README.txt`: spiegazione in italiano e in inglese;
- `dati.json`: `exported_at`, `account` (campi dell'`User` rilevanti per l'utente, comprese preferenze, credito, timestamp di attività e notifica), `legal_acceptances` (storico completo), `profile` (con `experiences`, `educations`, `skills`, `certifications`, `languages` e `photo_file`), `saved_searches`, `jobs`, `cv_documents`, `cv_drafts`, `cover_letter_documents`, `cover_letter_drafts`, `referral_messages`, `job_filter_presets`, `daily_quotas`, `sessions` (`AuthToken`), `push_subscriptions`, `run_logs`; ogni documento ha un campo `file` con il percorso nell'archivio;
- `files/`: `foto.<ext>`, `cv/cv_job<job>_<id>.pdf`, `cover_letter/cover_letter_job<job>_<id>.pdf` (un file mancante su disco è saltato con un warning).

Esclusi: hash della password (non è tra i campi esportati), `key_hash` dei token, chiavi `p256dh`/`auth` delle sottoscrizioni push, `html_source` dei documenti (il PDF è già incluso), dati di altri utenti.

### 5.17 Gate delle accettazioni legali (Sprint 67)

1. **Registrazione**: le tre accettazioni si registrano con l'account (§3.7).
2. **Utenti senza le versioni correnti** (registrati prima dello Sprint 67, o dopo un cambio di versione in `legal.py`): `GET /api/accounts/me/` (esente) riporta `legal_acceptance_required: true` e `legal_missing` (elenco dei documenti); `ProtectedRoute` mostra allora `LegalAcceptancePage` al posto di qualunque pagina protetta, senza barra di navigazione. Qualunque altra chiamata riceve 403 `legal_acceptance_required` e il client emette `LEGAL_REQUIRED_EVENT`, che fa ricaricare l'utente (§3.3).
3. **Accettazione**: `POST /api/accounts/legal-acceptance/ {accept_privacy, accept_terms, confirm_age}` (tutti `true`, altrimenti 400) registra solo i documenti mancanti e restituisce l'utente aggiornato (`UserOnboardingSerializer`), con cui la PWA esce dalla schermata.
4. **Alternative** dalla stessa schermata, tutte esenti dal gate: export dei dati, cancellazione dell'account, logout.

Le pagine pubbliche `/privacy` e `/terms` (`LegalPage`, testi in `frontend/src/legal/PrivacyContent.jsx` e `TermsContent.jsx`) leggono da `GET /api/legal/` versioni, date, età minima e titolare; se `controller.complete` è falso mostrano l'avviso "dati del titolare da completare". Il footer `LegalFooter` con i due link è in tutte le pagine. Copia di riferimento dei testi, con i segnaposto, in `Docs/legal/` (it/en).

### 5.18 Backup giornaliero (Sprint 21, rivisto nello Sprint 67)

Task `apps.common.tasks.backup_database` (Beat, 03:30 Europe/Rome, eseguito dal `worker`), data del nome file = data del giorno (`AAAA-MM-GG`):

1. **Dump**: `pg_dump -Fc` → `db-AAAA-MM-GG.dump` e `tar.gz` di `MEDIA_ROOT` (cartella `media/` nell'archivio) → `media-AAAA-MM-GG.tar.gz`.
2. **Con `BACKUP_S3_BUCKET` valorizzato**: i due file, scritti in una cartella temporanea, sono caricati sul bucket S3-compatibile con boto3 (nessuna rotazione lato app).
3. **Senza bucket (situazione di produzione)**: backup **locale** in `BACKUP_LOCAL_DIR` (default `<BASE_DIR>/backups`, cioè `/app/backups`, volume `local_backups`). I dump si scrivono in una cartella temporanea `.tmp-*` dentro il volume e poi si spostano con `os.replace` (un dump fallito non tocca quelli buoni né quello del giorno), con permessi `0600`; la cartella è `0700` (creata così dal `Dockerfile`).
4. **Rotazione**: `rotate_local_backups` cancella i file `db-*`/`media-*` con data **nel nome** (non `mtime`) anteriore agli ultimi `BACKUP_LOCAL_KEEP_DAYS = 7` giorni, oggi compreso; i file con altri nomi (per esempio dump manuali) sono ignorati.

Ripristino e stato in produzione in §8.4.

### 5.19 Cambio dell'email di accesso (Sprint 70)

`POST /api/accounts/email/change/ {password, new_email}` (permessi di default, quindi dietro il gate; throttle `password_check`):
1. senza invio email configurato → 503 `email_unavailable`;
2. password errata o nuovo indirizzo uguale a quello attuale → 400;
3. se il nuovo indirizzo non appartiene a nessun account: `email_change_confirm` al nuovo indirizzo e `email_change_notice` a quello attuale; altrimenti nessuna email. In entrambi i casi 200 `{status: "confirmation_sent"}` (non rivela quali indirizzi sono registrati).

Il link contiene un token `TimestampSigner` (salt `apps.accounts.change-email`, `sign_object` di `{id, old, new}`, validità `EMAIL_VERIFICATION_MAX_AGE` = 3 giorni), stesso schema della verifica dello Sprint 67 e nessuna tabella in più. `POST /api/accounts/email/change/confirm/ {token}` è pubblico (il link può essere aperto su un dispositivo non collegato; throttle `email_request`): verifica firma e scadenza, cerca l'utente attivo con quell'id **e** l'email attuale uguale a `old` (dopo il cambio lo stesso link non vale più), rifiuta con `email_taken` se nel frattempo un altro account ha preso il nuovo indirizzo, poi imposta `email` e `username` al nuovo indirizzo (minuscolo) e `email_verified = True`. Le sessioni restano valide. Nessun dato nuovo è conservato: informativa ed export non cambiano (l'export contiene già l'email di accesso).

### 5.20 Contatori e prezzi visibili (Sprint 70)

Dati da `GET /api/accounts/usage/` (§4.6). Nella PWA: "I tuoi limiti di oggi" in Impostazioni (`UsageLimitsCard`, dallo Sprint 78 nella sottopagina `/settings/limits`); `ActionCostHint` sotto import da link, "Aggiungi manualmente" (pulsante e popup), "Raccogli ora" e, nella pagina del job, nei pannelli di generazione di CV, cover letter e messaggi (azioni `cv`, `cover_letter`, `referral_message`; fino allo Sprint 74 i pannelli di cover letter e messaggi avevano le due azioni scambiate); conferma quando `next_charge = credit` prima di import, job manuale e generazioni del dettaglio, con `useCostConfirm` (`components/CostConfirmDialog.jsx`, finestra dell'app: lista dallo Sprint 74, dettaglio dallo Sprint 75) Dopo ogni azione i dati si ricaricano. Le chat degli editor mostrano prezzo e saldo del `GET` della chat (`price`, `balance`) e non chiedono conferma; da Sprint 76 il pannello disattiva campo e invio quando `balance < price`.

### 5.21 Lingua dei testi del backend (Sprint 71)

Ogni testo che il backend restituisce all'utente esiste in italiano e in inglese, con il meccanismo standard di Django:

- **Sorgenti in italiano** marcati con `gettext` (`from django.utils.translation import gettext as _`) nel punto in cui il messaggio viene prodotto (view, serializer, servizi, moduli `*_manual_generation.py`, raccolta/import/job manuale, chat, file, account, notifiche, scoring), `gettext_lazy` per le costanti di modulo (`INVALID_INVITE_MESSAGE`, `UNREADABLE_CV_MESSAGE`, payload delle notifiche, testi delle email). Segnaposto sempre con nome (`%(max)s`, `{link}` per le email), mai f-string: `makemessages` non le estrae e il traduttore deve poter spostare i valori.
- **Traduzione inglese** in `backend/locale/en/LC_MESSAGES/django.po` (msgid italiani, ~120 voci) e **`django.mo` compilato e committato**: nessun passo di build in più, funziona allo stesso modo nell'immagine di produzione, nei test e nello stack di sviluppo, che monta `./backend` su `/app` e nasconderebbe un `.mo` compilato nell'immagine. Il rischio di un `.mo` non ricompilato è coperto da un test (sotto). Rigenerazione: comandi in `DEPLOY.md` §4.9 (`makemessages -l en --add-location=file --no-obsolete`, poi `compilemessages`), in un container usa e getta con `gettext`, che l'immagine non contiene.
- **Lingua attiva.** Nelle richieste `/api/*` la decide `apps.common.middleware.ApiLocaleMiddleware`, una `LocaleMiddleware` di Django limitata all'API, dall'header `Accept-Language` che la PWA invia a ogni chiamata (§3.3); una lingua diversa da it/en, o nessun header, ricade sull'italiano (`LANGUAGE_CODE`). Fuori dall'API (Django Admin, pagine di allauth) resta l'italiano qualunque sia la lingua del browser; a fine richiesta la lingua torna quella di default sul thread. Nei task, dove non c'è una richiesta, vale `User.interface_language` con `translation.override`: notifiche push (`apps/notifications/tasks.py`) e prefisso del cap lingua (`apps/jobs/scoring.py`, salvato nel DB: lingua del proprietario al momento dello scoring). Le email di servizio sono composte nella richiesta ma con la lingua del destinatario (`User.interface_language`), non con quella della richiesta.
- **Messaggi standard di Django e DRF** (campo obbligatorio, lunghezza massima, scelta non valida, password troppo simile o comune, credenziali mancanti, non trovato) usano le traduzioni incluse nei due pacchetti: in italiano e in inglese senza voci nel nostro `.po`. Fa eccezione il 429, il cui testo italiano di DRF è tradotto a metà ("La richiesta è stata limitata (throttled). Expected available in N seconds."): `apps.common.exceptions.api_exception_handler` (`EXCEPTION_HANDLER`) lo sostituisce con "Troppe richieste: riprova tra N secondi/minuti/ore." / "Too many requests: please try again in N seconds/minutes/hours." (header `Retry-After` invariato).
- **Non tradotti, per scelta:** prompt e istruzioni inviati al modello AI, testi generati dall'AI (motivazioni, CV, cover letter, messaggi, risposte della chat), log tecnici, messaggi dei `RunLog`, Django Admin (etichette, azioni, messaggi), comandi di gestione, nomi dei file scaricati, chiavi del JSON dell'export (il `README.txt` dell'export è già bilingue), etichette fisse dei documenti (seguono la lingua del documento, §6.2).
- **Testi già salvati.** Le motivazioni con il prefisso del cap salvate prima dello Sprint 71 restano in italiano.

---

## 6. Generazione del CV in dettaglio

Le regole di contenuto (qualifica, sommario, Areas of Expertise, selezione e taglio, istruzione, lingue, ordine e aspetto delle sezioni) sono definite in `Docs/03-specifiche-funzionali-contenuto-cv-v5.md`; qui la sintesi tecnica della pipeline.

### 6.1 Perché il template del prototipo non era riusabile

Il template a placeholder e il prompt del workflow *03* del prototipo erano modellati sul CV di **una persona specifica**: dati personali e contatti scritti nel documento, esperienze cablate come slot nominali con un numero fisso di bullet, una frase personale imposta come chiusura del sommario, un numero fisso di placeholder e un nome file personale. Il numero di esperienze e di bullet dipende invece dal profilo di ciascun utente: per questo il CV è generato da un template HTML con cicli e dati per-utente.

### 6.2 La pipeline di generazione (as-is)

Punto d'ingresso: `request_manual_cv_generation(job, extra_instructions)` (§5.2) → `generate_cv(job, MANUAL, extra_instructions)` in `apps/cv/generation.py`.

0. **Gap filling** (prima della pipeline, `apps/cv/gap_filling.py`). `POST …/generate-cv/` accetta `{gap_numbers: [int], gap_instructions: str}` (Sprint 69; `gaps: [str]` ancora accettato per le schede vecchie). `resolve_selected_gaps` ricava dai numeri le righe "N. etichetta (motivo: …)" con **lo stesso numero e testo del pannello** (posizione 1-based nell'elenco completo `score_gaps`, ordine dell'elenco; numeri fuori range ignorati; dei testi legacy riconosciuti si recupera il numero, gli altri restano senza numero). `build_extra_instructions` produce: stringa vuota se non c'è nulla; solo "INDICAZIONI DEL CANDIDATO PER QUESTA GENERAZIONE" se ci sono solo indicazioni; altrimenti l'elenco "GAP DA COLMARE PER QUESTA OFFERTA" (con la nota che i numeri sono quelli visti dal candidato) più le indicazioni dell'utente o `DEFAULT_GAP_INSTRUCTION`. Il testo finisce in `CVDocument.extra_instructions_used`; nulla viene salvato sul profilo.
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
4. **Rendering e ripiego** (`_render_with_overflow_retry`): `render_cv` a dimensione fissa (§3.6); se il PDF supera una pagina si rimuove il bullet globalmente meno rilevante (`remove_least_relevant_bullet`) e si rirenderizza, fino a `MAX_OVERFLOW_ITERATIONS = 4`. Se resta multi-pagina si salva comunque, senza errore, con un `RunLog` `cv_generation`/SUCCESS "CV generato multi-pagina…"; dallo Sprint 69 il numero di pagine è salvato in `page_count` e la PWA avvisa l'utente.
5. **Snapshot** (`build_draft_content_json`): `content_json` con il pool completo di esperienze e bullet, i flag `shown` e l'`id` di ogni bullet (§4.5).
6. **Salvataggio**: `CVDocument` con `html_source`, `generation_type`, `extra_instructions_used`, `content_json`, `page_count`, `areas_of_expertise_grounding` e il file PDF. L'orchestratore aggiorna poi lo stato del job (§5.2).

### 6.3 Dove finiscono i dati personali

Nessun dato personale è nel template. Nome e cognome vengono da `User.first_name` / `last_name` (fallback: email di login); la riga contatti è composta da `_build_contact_parts`: "Città tradotta, PAESE | telefono | email del profilo | LinkedIn", con `Profile.city`, `country_code`, `phone`, `email`, `linkedin_url` (le parti vuote sono omesse). La foto (`Profile.photo`) è inclusa solo se `cv_include_photo` è attivo e la foto esiste.

### 6.4 Template

Un **unico template CV** (`cv_template.html`), non selezionabile: non esiste un'impostazione "template" nel modello (l'onboarding mostra solo un campo disabilitato "Standard"). Per aggiungerne altri basterebbero nuovi file e un campo di scelta. La cover letter ha un proprio template separato (`cover_letter_template.html`), con stile e compattamento diversi (§3.6).

Ordine delle sezioni del CV: intestazione (nome, qualifica, contatti, foto), sommario senza titolo, Areas of Expertise su due colonne, righe "Certified in" / "Skilled in", esperienze (azienda stampata una sola volta per ruoli consecutivi nella stessa azienda, riga ruolo | luogo | date, bullet, riga tecnologie), istruzione, lingue. Etichette in 5 lingue (`SECTION_LABELS`).

### 6.5 Foto: opzione on/off

La foto compare solo con `User.cv_include_photo = true` e `Profile.photo` presente; il template gestisce l'intestazione con e senza foto (allineamento al fondo, Sprint 41). La cover letter non ha mai la foto.

### 6.6 Grassetto sulle keyword (Sprint 58)

Il modello marca con `**…**` al massimo 1–2 brevi espressioni per bullet di esperienza, testo letterale del bullet. Il filtro di template `bold_markup` (`apps/cv/templatetags/cv_extras.py`) fa l'escape HTML del testo e trasforma solo le porzioni marcate in `<strong>` (marcatori non bilanciati restano letterali); è applicato ai bullet delle esperienze e, dallo Sprint 69, anche a qualifica, sommario, aree, ruolo e note dell'istruzione (i campi di testo libero che utente e chat possono modificare), nel PDF generato, nell'anteprima e nel PDF finalizzato; restano letterali solo i campi presi così come sono dal profilo. Nell'editor il componente `RichBulletInput` (contentEditable, pulsante B e Ctrl/Cmd+B), usato per tutti questi campi, converte marcatori ↔ `<strong>` e salva sempre la stringa con i marcatori. La cover letter non ha grassetti.

### 6.7 Aspetto del template (sintesi)

Valori in `rendering.py` (`COMPACT_LEVELS`) e in `cv_template.html`, fissati con il committente negli Sprint 52–57: corpo 9pt Caladea, nome 18pt, qualifica 14pt, contatti 9pt, titoli di sezione 11pt maiuscoli blu `#2f4a63` con filetto (unico colore; il resto è nero), letter-spacing 0.2pt, bullet "•" a 14pt con rientro 16pt/−12pt per esperienze e aree, testo giustificato per sommario, righe Certified/Skilled in e bullet, riga lingue distribuita (`space-between`). Il dettaglio è nel documento 03.

---

## 7. Fuso orario e multi-utenza

- Il database salva tutto in UTC; la conversione all'ora locale avviene solo dove serve.
- **Due riferimenti temporali:**
  - **Europe/Rome** (`TIME_ZONE`): orario del backup (03:30), giorno delle quote (`DailyQuota.date`, anche la raccolta del giorno), interpretazione della data/ora dei job manuali;
  - **`User.timezone`** (default Europe/Rome; dallo Sprint 70 impostabile in Impostazioni e in onboarding, e preso dal browser in registrazione): orario della raccolta automatica (Sprint 77; prima l'ora 10 della notifica mattutina), "oggi" del filtro date della lista e delle statistiche Home ("oggi" = dalla mezzanotte locale; "ultima settimana" = ultimi 7 giorni mobili, non legati al fuso).
- Dallo Sprint 70 la PWA calcola il default "oggi–oggi" del filtro date nel fuso dell'utente (`todayInputValue(user.timezone)` con `Intl.DateTimeFormat`, ripiego sulla data del dispositivo se il browser non conosce il fuso); le date mostrate restano formattate nel fuso del dispositivo.
- Per fusi lontani da Roma restano piccole incoerenze accettate (reset quote in un'ora inattesa, freschezza del batch, spostamento DST).

**Isolamento.** Tutte le view richiedono autenticazione per default (`DEFAULT_PERMISSION_CLASSES = IsAuthenticated`, Sprint 66; dallo Sprint 67 insieme al gate `LegalAcceptanceRequired`, §3.7): gli endpoint pubblici (registrazione, login, verifica email, recupero password, `GET /api/legal/`, download firmati) dichiarano `AllowAny` esplicitamente. Ogni record è legato a un `user`; ogni queryset delle view filtra per l'utente autenticato (`get_object_or_404(Job, pk=pk, user=request.user)`, `filter(profile__user=…)`, ecc.): un oggetto di un altro utente restituisce 404. Coperto da `apps/common/test_multi_user_isolation.py`. I file degli utenti seguono la stessa regola tramite gli URL firmati (§4.15).

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
| `email_request` | 10/ora per IP | Sprint 67: `POST` di `verify-email/resend/`, `password-reset/` e `password-reset/confirm/` (contatore condiviso tra i tre endpoint, stesso scope) |
| `email_address` | 3/ora per email (hash) | Sprint 67: `verify-email/resend/` e `password-reset/` (`EmailAddressRateThrottle`): nessuno può usare l'app per inondare di email una casella altrui |
| `password_check` | 10/ora per utente | Sprint 67: `password/change/` e `delete/` (tentativi di password) |
| `data_export` | 3/giorno per utente | Sprint 67: `POST /api/accounts/export/` (non il download) |

I contatori stanno nella cache Redis con la durata della propria finestra: il più lungo (`data_export`) dura 24 ore, il limite di conservazione dichiarato nell'informativa.

**Django Admin.** La view di login è sostituita da `apps/accounts/admin_login.throttled_admin_login`: dopo 10 tentativi falliti dallo stesso IP in 15 minuti (finestra fissa dal primo errore, azzerata da un login riuscito) risponde 429. Path da `DJANGO_ADMIN_PATH` (con "/" finale, default `admin/`), da passare identico anche a Caddy.

**Limiti di input** (validazione lato server, 400 oltre il limite):

| Testo | Limite |
|---|---|
| Descrizione del job manuale | 20.000 |
| Indicazioni di cover letter e messaggi di networking, istruzione "colma i gap" | 2.000 |
| Gap selezionati | 30, da 500 caratteri |
| Messaggio di chat degli editor | 2.000 |
| Nome destinatario / URL LinkedIn del destinatario | 255 / 500 |
| `objective_statement`, sommario del profilo, note istruzione, bullet | 2.000 / 5.000 / 3.000 / 400 (max 15 bullet per esperienza; Sprint 70, non retroattivo, §4.2) |
| Voci del profilo | 30 esperienze, 15 istruzioni, 100 competenze, 50 certificazioni, 36 lingue (Sprint 70, solo in creazione) |
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
| `web` | `./backend` | All'avvio `migrate` + `collectstatic`, poi `gunicorn --workers 4 --timeout 1800`; volumi `static_data`, `media_data`, `local_backups` (Sprint 67, letto da `restore_backup`) |
| `worker` | `./backend` | `celery worker` (task di Beat ed email di servizio); volumi `media_data`, `local_backups` (Sprint 67, scritto dal backup) |
| `beat` | `./backend` | `celery beat` (`DatabaseScheduler`) |
| `frontend-build` | `./frontend` | One-shot: `npm run build` nel volume `frontend_dist`, poi termina |
| `caddy` | `caddy:2-alpine` | Porte 80/443, monta in sola lettura `static_data` e `frontend_dist` (non `media_data`, Sprint 66); access log nel volume `caddy_logs` |

Tutti i servizi hanno la rotazione dei log Docker (`json-file`, 5 file da 10 MB per container, Sprint 66). `web`, `worker` e `beat` girano come utente non privilegiato `app` (uid 1000, `backend/Dockerfile`): il codice è di root e in sola lettura, scrivibili solo `/app/staticfiles`, `/app/mediafiles` e (Sprint 67) `/app/backups` (`0700`; un'eventuale cartella `backups/` locale non entra nell'immagine, esclusa da `.dockerignore`); il volume `local_backups` non è montato da `caddy`, quindi i backup non sono mai serviti; `pg_dump` del backup e WeasyPrint funzionano senza privilegi. I volumi `media_data`/`static_data` creati prima dello Sprint 66 vanno passati a uid 1000 una volta (`DEPLOY.md` §4.5).

`web`, `worker` e `beat` condividono la stessa immagine: dopo una modifica al backend vanno ricostruiti tutti e tre. Il timeout di 1800 s e i 4 worker gunicorn servono alle operazioni sincrone (raccolta manuale con decine di job da scorare, generazioni): con 4 worker al massimo 4 operazioni lunghe possono essere in corso contemporaneamente su tutto il sito.

### 8.3 Caddy per HTTPS

`docker/caddy/Caddyfile.prod`: certificato Let's Encrypt automatico per il dominio configurato (`DOMAIN`, `CADDY_EMAIL`), compressione gzip, `reverse_proxy web:8000` per `/api/*` (corpo massimo 10 MB), il path dell'admin (`DJANGO_ADMIN_PATH`) e `/accounts/*`; serve direttamente `/static/*`; **`/media/*` risponde 404** (i file degli utenti si scaricano solo dagli URL firmati, §4.15); PWA statica con fallback su `index.html` per le rotte client-side.

Dallo Sprint 66 Caddy aggiunge a tutte le risposte (sostituendo i valori equivalenti di Django, senza duplicati) `Strict-Transport-Security: max-age=31536000`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` (anche Django usa lo stesso valore), una `Permissions-Policy` che nega camera, microfono, geolocalizzazione, pagamenti e USB, toglie l'header `Server` e applica la `Content-Security-Policy`:

`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; worker-src 'self'; manifest-src 'self'; frame-src blob:; object-src blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`

Motivazioni (verificate sul bundle di build): nessuno script inline in `index.html` né `eval`, nessuna risorsa esterna; `'unsafe-inline'` negli stili perché le primitive Radix inseriscono elementi `<style>` a runtime; l'anteprima PDF degli editor è un `<iframe>` su un URL `blob:` (i documenti blob ereditano la policy, quindi servono `frame-src blob:` e `object-src blob:` per il visualizzatore PDF del browser; `frame-ancestors` e `X-Frame-Options` non si applicano ai documenti blob). Il service worker è `/sw.js` (stessa origine).

Lo Sprint 67 **non ha cambiato la CSP**: le nuove pagine (`/privacy`, `/terms`, verifica email, recupero password, schermata di accettazione) usano solo risorse della stessa origine; il link al sito del Garante e i `mailto:` del titolare sono navigazioni, non risorse caricate; il download dell'export è una navigazione verso `/api/...` (stessa origine).

**Access log** in JSON su file nel volume `caddy_logs` (`/var/log/caddy/access.log`), ruotato ogni 24 ore o a 10 MiB e cancellato dopo 14 giorni (`roll_keep_for 336h`); i parametri `s` (download firmati ed export) e, dallo Sprint 67, `t` e `token` (link di verifica email e di recupero password, che aprono la PWA con il token nella query) sono sostituiti con `REDACTED`; gli header `Authorization`/`Cookie` e `Set-Cookie` sono rimossi e, dallo Sprint 67, anche `Referer`, che riporterebbe gli stessi token sulle chiamate API successive della pagina. Log applicativo Django su stdout (`LOGGING`: errori 5xx di `django.request`, warning e log del package `apps`), mai token, header o query string.

### 8.4 Backup

- **Task** `apps.common.tasks.backup_database` (Beat, 03:30 Europe/Rome): `pg_dump -Fc` del database e `tar.gz` di `MEDIA_ROOT`, caricati su un bucket S3-compatibile (`BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY`, `BACKUP_S3_REGION`, boto3) se `BACKUP_S3_BUCKET` è valorizzato, altrimenti (Sprint 67) scritti nel volume locale `local_backups` (`BACKUP_LOCAL_DIR`, default `/app/backups`) come `db-AAAA-MM-GG.dump` e `media-AAAA-MM-GG.tar.gz`, file `0600`, cartella `0700`, scrittura in una cartella temporanea e poi spostamento, rotazione per data nel nome con conservazione degli ultimi `BACKUP_LOCAL_KEEP_DAYS = 7` giorni (costante nel codice). Flusso in §5.18.
- **Ripristino**: `restore_backup AAAA-MM-GG --confirm` oppure `restore_backup --file <path> --confirm` (`pg_restore --clean --if-exists`; pensato per un ambiente di test separato). Con la data il dump si cerca sul bucket S3 se `BACKUP_S3_BUCKET` è valorizzato, altrimenti in `BACKUP_LOCAL_DIR`; senza `--confirm` o senza data/`--file` il comando rifiuta. Ripristina solo il database: l'archivio dei media va estratto a mano.
- **In produzione** `BACKUP_S3_*` sono vuote, quindi è attivo il **backup locale**: i backup restano sullo stesso VPS dei dati (un guasto del disco li perde insieme), non sono cifrati e la copia fuori dal VPS è manuale (`DEPLOY.md` §6). Il ripristino end-to-end non è mai stato provato in produzione. I dump fatti a mano nella cartella `backups/` sul VPS (non versionata, fuori dal volume) non rientrano nella rotazione e vanno eliminati a mano.
- I 7 giorni sono anche il termine, dichiarato nell'informativa, entro cui i dati di un account cancellato spariscono dai backup. I PDF sono rigenerabili dall'HTML salvato, ma i file media (anche le foto) sono inclusi nel backup.

### 8.5 Configurazione e segreti

Solo variabili d'ambiente, lette in `config/settings.py`; `.env.example` alla radice documenta le chiavi, `.env` non è mai committato. Gruppi: Django (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_ADMIN_PATH`, `REGISTRATION_INVITE_CODE`), titolare del trattamento (Sprint 67: `LEGAL_CONTROLLER_NAME`, `LEGAL_CONTROLLER_EMAIL`, `LEGAL_CONTROLLER_ADDRESS` facoltativo; mai nel repository, che è pubblico), email di servizio (Sprint 67: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `PUBLIC_BASE_URL` per i link, default `https://$DOMAIN`), database (`POSTGRES_*`), Celery e cache (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `REDIS_CACHE_URL`), AI (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BEDROCK_REGION`, `BEDROCK_*_MODEL`), Apify (`APIFY_API_TOKEN`, l'unica letta dal codice), Google OAuth (vuote in produzione; `GOOGLE_OAUTH_CLIENT_ID` decide anche se il pulsante compare), Web Push (`VAPID_*`), prezzi (`PRICE_*`, §4.6), deploy (`DOMAIN`, `CADDY_EMAIL`), backup (`BACKUP_S3_*`, vuote in produzione; `BACKUP_LOCAL_DIR`, Sprint 67). Dopo una modifica a `.env` i container vanno ricreati, non solo riavviati. I massimali giornalieri e i parametri della pipeline CV sono invece costanti nel codice.

### 8.6 Aggiornamenti di sicurezza

Aggiornamenti automatici del sistema operativo; dipendenze applicative con intervalli di versione bloccati in `requirements.txt` e `package-lock.json`, da aggiornare periodicamente a mano (Sprint 66: Django 5.2 LTS, DRF 3.16, Celery 5.5, Pillow 12). Il controllo periodico delle vulnerabilità note (`pip-audit`, `npm audit`) è nel runbook di `DEPLOY.md`.

---

## 9. Amministrazione (piani e credito)

L'amministratore gestisce piani e credito **solo dal Django Admin** (`/admin/`), oppure dalla shell Django per le operazioni non coperte (`DEPLOY.md` §7). Non esistono checkout self-service, voucher né codici sconto. Da API `plan` ed `extra_credit` sono in sola lettura.

**Modelli registrati in Admin:**

| Modello | Configurazione |
|---|---|
| `User` | `UserAdmin` di Django con un fieldset "App di ricerca lavoro": `plan`, `timezone`, `interface_language`, `cv_language_mode`, `cv_include_photo`, `objective_statement`, `extra_credit`, `last_activity_reset`, `last_notified_at`, e (Sprint 68) un fieldset "Raccolta e inattività": `collection_in_progress`, `collection_started_at`, `last_inactivity_notified_at`; dallo Sprint 67 `email_verified`, `notifications_enabled`; in lista anche `plan` ed `extra_credit`. Azioni (Sprint 68): "Azzera la quota di raccolta manuale di oggi", "Azzera tutti i contatori giornalieri di oggi" |
| `Profile` | Con inline di `Experience`, `Education`, `Skill`, `Certification`, `Language` |
| `SavedSearch` | Lista con keywords, città, paese, utente, attiva |
| `Job` | Lista con titolo, azienda, utente, source, origin, status, score, archiviato, `score_rescaled_from_legacy`, `scoring_failures`; filtri e ricerca; `user` e `matched_saved_search` come id |
| `DailyQuota` | In lista tutti e 7 i contatori (Sprint 68), ricerca per email; azione "Azzera tutti i contatori delle righe selezionate" |
| `JobFilterPreset` | Sprint 68: sola lettura (nome, utente, data; dettaglio con i filtri), nessuna aggiunta |
| `CVDraft`, `CoverLetterDocument`, `CoverLetterDraft`, `ReferralMessageDocument` | Sprint 68: sola lettura, eliminabili; `html_source` non mostrato; in lista solo job, utente, date (canale e destinatario per i messaggi) |
| `RunLog` | Lista con tipo, esito, utente, job, date; filtri per tipo ed esito |
| `CVDocument` | Lista con job, utente, tipo, data |
| `PushSubscription` | Lista con utente, endpoint, data |
| `AuthToken` | Sprint 66: lista in sola lettura con utente, creazione, ultimo uso, user agent; nessuna aggiunta; eliminare una riga disconnette quel dispositivo |
| `LegalAcceptance` | Sprint 67: registro in sola lettura (utente, documento, versione, data); nessuna aggiunta né modifica |

Registrati automaticamente dalle librerie: sito e account social di allauth, PeriodicTask e pianificazioni di `django_celery_beat` (da qui si modificano gli orari dei task).

Comandi di gestione: `set_e2e_account` e `seed_e2e_jobs` (solo con `DEBUG=True`, per i test e2e), `restore_backup` (S3 o cartella locale, oppure `--file`), `secure_media_files`; dallo Sprint 68 `delete_discarded_by_cap_jobs`, `rescale_legacy_scores` (entrambi dry-run di default, `--confirm` per eseguire) e `retry_unscored_jobs`.

Un utente eliminato da Admin perde, grazie ai segnali di §5.15, anche i file su disco e il testo dei `RunLog`; non riceve però l'email di conferma, che parte solo dall'endpoint dell'utente.

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

Elenco descrittivo dei difetti e dei limiti osservati nel codice al 2026-11-14 (aggiornato allo Sprint 66, che ha chiuso i punti su import CV, token senza scadenza e invio push non protetto, e allo Sprint 67, che ha chiuso quelli su cancellazione ed export dei dati, recupero e cambio password, backup assente e notifiche non disattivabili: i punti 4, 5, 6, 11 e 22 sono stati riscritti con quello che resta aperto, i nuovi sono in coda dal 37; lo Sprint 70 ha chiuso o ridotto i punti 11, 22, 33, 35 e 40 e aggiunto i punti 44–46; lo Sprint 71 ha chiuso il punto 23 e ridotto il 20). Non sono decisioni: sono lo stato attuale, da valutare in sprint futuri. I punti aperti delle versioni precedenti già chiusi o superati (supporto multi-filtro dell'actor, distribuzione tra ricerche con tetto unico, compattamento del CV, prezzi e modelli "da fissare", formato di `Education`, overflow estremo) sono stati tolti. La numerazione è rifatta.

**Rischi di prodotto e conformità**

1. **Conformità scraping LinkedIn.** Apify e la pagina guest di LinkedIn possono violare i termini di servizio di LinkedIn: rischio di blocco della fonte o legale, da rivalutare prima di un pubblico reale.
2. **Dipendenza dal credito Apify.** Con il credito dell'account Apify esaurito ogni chiamata risponde 403 e nessun utente riceve offerte finché il token non viene cambiato (già successo; `DEPLOY.md` §7.1). Non c'è un avviso automatico.
3. **Notifiche push su iPhone** solo con la PWA aggiunta alla Home: canale fragile proprio dove passa il valore principale del prodotto.
4. **Privacy (GDPR): residui dello Sprint 67.** Le funzioni di base esistono (§3.7, §5.14–§5.17). Restano: le **copie delle email** inviate via Gmail (indirizzo del destinatario e testo, mai dati del profilo) nella cartella "Posta inviata" dell'account mittente, anche dopo la cancellazione dell'account: vanno cancellate periodicamente a mano o la conservazione va dichiarata nell'informativa (decisione del committente); i `RunLog` degli utenti cancellati restano senza messaggio e non c'è una pulizia automatica dei `RunLog` in generale. Il cambio dell'indirizzo email esiste dallo Sprint 70 (§5.19).

**Infrastruttura e operatività**

5. **Backup solo sul VPS.** Senza storage S3 configurato il backup è locale (Sprint 67): un guasto del disco perde dati e backup insieme, la copia fuori dal VPS è manuale, i file non sono cifrati. `restore_backup` ripristina solo il database (i media vanno estratti a mano); nessun ripristino è mai stato provato in produzione (§8.4).
6. **Login Google non attivo** in produzione (credenziali vuote; dallo Sprint 67 il pulsante è nascosto), `LOGIN_REDIRECT_URL` non impostato, ritorno da Google mai verificato. Dallo Sprint 66 l'API accetta solo token: per attivarlo servono un passaggio sessione → token dopo il ritorno da Google e la raccolta delle accettazioni e del codice di invito, che il flusso allauth salta (§3.7). Le URL di allauth (`/accounts/*`, compresa la sua registrazione) restano raggiungibili: un account creato da lì non ottiene un token ed è soggetto al gate (superficie di allauth: vedi anche il punto 41).
7. **Operazioni lunghe sincrone in gunicorn.** Raccolta manuale e generazioni occupano un worker gunicorn per tutta la durata; con 4 worker, poche operazioni contemporanee bastano a rallentare tutto il sito. Un deploy o riavvio durante un'operazione la interrompe.
8. **Flag transitori: riserva persa se il processo viene ucciso.** *Risolto in parte nello Sprint 69:* i tre flag hanno un timestamp e diventano stantii dopo 35 minuti (non bloccano più), e il timeout di gunicorn (`SystemExit`) è intercettato con restituzione della riserva. Resta che un processo ucciso senza eccezione (SIGKILL, OOM, riavvio oltre il tempo di grazia) non restituisce quota/credito: servirebbe un registro delle riserve.
9. **Raccolta automatica** (fino allo Sprint 76 notturna). *(Sprint 68: errori isolati per gruppo Apify, job senza punteggio ritentati fino a 3 volte.)* Resta: le raccolte automatiche girano una alla volta nel worker (1 CPU); un errore imprevisto durante la creazione dei job interrompe la raccolta dell'utente (i job già creati vengono poi scorati dal retry).
10. *(Risolto nello Sprint 68: guardia `collection_in_progress` condivisa tra raccolta manuale e notturna; sblocco della seconda raccolta manuale con un'azione Admin.)*
11. **Notifiche.** *(Sprint 70: il logout elimina la sottoscrizione del dispositivo, `last_notified_at` riallineato alla riattivazione.)* Resta: la preferenza dello Sprint 67 vale per tutto l'account (non per singolo dispositivo); un dispositivo da cui si esce senza rete (logout fallito lato server) resta registrato finché il push service non risponde 404/410.
12. **Osservabilità limitata.** `RunLog` registra solo i fallimenti per CV, cover letter, messaggi e chat (più il caso multi-pagina del CV); le generazioni riuscite e i consumi di quota/credito non lasciano traccia. Non esiste un registro contabile del credito. Le offerte scartate dalla raccolta sono contate nel `RunLog` `collection` dallo Sprint 68.
13. *(Risolto nello Sprint 68: modelli registrati in Admin, `DailyQuota` con tutti i contatori, campi di raccolta e inattività nella scheda `User`, §9.)*
14. **Costi AI e Apify non stimati.** Senza tetto per notte il costo della raccolta cresce con il numero di gruppi (ogni chiamata fattura almeno 150 risultati) e quello dello scoring con il numero di offerte raccolte; nessuna soglia o monitoraggio è definito.

**Backend: difetti puntuali**

15. **Stato del job sovrascritto dalla generazione CV.** *Risolto nello Sprint 69:* `application_done` resta dopo una rigenerazione, il fallimento non cambia lo stato; "candidatura fatta" è annullabile.
16. **`JobSerializer` non espone `referral_message_generation_in_progress`.** *Risolto nello Sprint 69.*
17. *(Risolto nello Sprint 68: job del vecchio cap eliminati, campo `discarded_by_cap` rimosso, §4.4.)*
18. *(Risolto nello Sprint 68: controlli di lunghezza della raccolta e `IntegrityError` gestito come "già importato" con restituzione, §5.7.)*
19. *(Risolto nello Sprint 68: restituzione se la creazione fallisce; lo scoring fallito viene ritentato di notte, §5.8.)*
20. **Scoring.** Il cap lingua dipende dal fatto che il modello segnali la lingua richiesta e non è stato riapplicato ai job valutati prima dello Sprint 48. *(Sprint 71: il prefisso del cap è nella lingua dell'interfaccia del proprietario al momento dello scoring; quelli salvati prima restano in italiano.)* *(Sprint 68: località passata al modello, punteggi storici riscalati su 1–10.)*
21. *(Risolto nello Sprint 68: la `PATCH` del tipo di una ricerca attiva ripassa dai limiti di piano; la PWA segnala con un avviso la ricerca disattivata.)* Resta: nessun lock sulle attivazioni concorrenti (B4 dell'audit di sicurezza).
22. **Profilo.** `Education.end_date` facoltativa; completezza verificata solo alla generazione (dallo Sprint 70 la PWA mostra un banner finché manca); *(Sprint 70: `technologies` modificabile da UI, foto rimovibile, limiti su bullet e numero di voci.)* Dallo Sprint 67 la foto sostituita e i file dei record cancellati vengono eliminati (§4.15); eventuali orfani precedenti restano finché non si esegue `secure_media_files --delete-orphans`.
23. **Messaggi e testi del backend solo in italiano.** *Risolto nello Sprint 71* (§5.21): errori e validazioni dell'API, notifiche push, prefisso del cap lingua ed email di servizio in it/en con gettext. Resta: un testo nuovo rivolto all'utente va marcato con `gettext` e tradotto nel `.po` a mano (regola in `CLAUDE.md`, protetta dal test del catalogo solo per le voci già marcate: un testo non marcato resta in italiano senza errori); prompt, `RunLog` e Admin restano in italiano per scelta.
24. **Commenti e docstring superati** nel codice: "3 livelli di compattamento" in `generation.py` e `draft.py`; docstring di `CVDraft` ("generare un nuovo CV sovrascrive il draft") e di `CoverLetterDraft`; nome del PeriodicTask notturno con "cap di intake"; riferimenti a `02-specifiche-tecniche-v3.md`.

**Editor e chat**

25. **Bozza non riseminata.** *Risolto nello Sprint 69:* `source_document` e dialogo "riparti / continua" (§5.12).
26. **Finalizzazione e autosave.** *Risolto nello Sprint 69:* il contenuto a schermo viaggia con la finalizzazione.
27. **Indici posizionali nelle azioni chat.** *Risolto nello Sprint 69 per bullet e paragrafi* (id stabili, filtro server sui riferimenti). Restano per indice aree (protette da `area_text`), istruzione e lingue: la chat non aggiunge né rimuove voci di istruzione o lingue, ma una rimozione manuale tra la proposta e l'accettazione può spostare l'indice.
28. **Contesto della chat.** *Risolto nello Sprint 69:* azioni e decisioni nella cronologia del prompt, retry della registrazione delle decisioni.
29. **Documenti precedenti non riapribili.** CV precedenti allo Sprint 51 e cover letter precedenti allo Sprint 63 hanno `content_json` vuoto e restano non modificabili; *dallo Sprint 69* il pulsante "Modifica" non compare e il dettaglio spiega di rigenerarli (`cv_editable`/`cover_letter_editable`).
30. **Grassetto.** *Risolto nello Sprint 69:* `bold_markup` anche su qualifica, sommario, aree, ruolo e note dell'istruzione, con lo stesso campo a grassetto nell'editor.
31. **Gap filling.** *Risolto nello Sprint 69:* `gap_numbers` e righe del prompt con lo stesso numero e testo del pannello.
32. **Cover letter.** Template non allineato allo stile del CV (font sans-serif di fallback, nessun giustificato): **lasciato così per scelta** (Sprint 63, confermato nello Sprint 69). *Risolti nello Sprint 69:* testi propri del pannello chat, combinazioni di indicazioni nello storico.

**Frontend**

33. *(Risolto nello Sprint 70: controllo periodico del service worker e avviso "Nuova versione disponibile — Aggiorna", senza ricaricamenti automatici, §3.3.)* Resta: le schede aperte con un bundle precedente allo Sprint 70 non mostrano l'avviso e vanno ricaricate a mano una volta.
34. *(Risolto nello Sprint 68: un preset salvato da Importati non contiene il filtro "Ricerca"; se l'eliminazione fallisce la pillola viene ripristinata con un messaggio. Sezione e filtri della lista sono nella query string `/list?section=…&from=…&to=…&score=…&status=…&search=…&location=…&applicants=…&recruiter=…&q=…`, con l'ultima query anche in `sessionStorage` per il link "Torna alla lista".)*
35. *(Risolto nello Sprint 70: test dell'arricchimento rimosso, e2e allineati a codice di invito e filtri nell'URL, §13.2.)*

**Calibrazione**

36. **Parametri della pipeline CV** (budget 18/16/14, minimo 2 bullet garantiti, 4 iterazioni di ripiego, 5 esperienze) e prezzi del listino sono valori da tarare con l'uso reale; sono costanti nel codice o variabili d'ambiente, senza impatto architetturale.

**Privacy, account ed email (Sprint 67)**

37. **Gate legato a una convenzione.** Una view che dichiara `permission_classes` è esente dal gate delle accettazioni: una view futura che ripete `permission_classes = [IsAuthenticated]` lo aggira senza errori. La regola va rispettata a mano: `test_privacy.py` verifica il 403 solo su un campione di endpoint (lista job, ricerche, profilo, chiave VAPID), non su tutte le view.
38. **Email via Celery.** Se il `worker` è fermo le email restano in coda; se il broker non risponde l'email è persa (solo un log). Nessun avviso all'utente; consegna e antispam di Gmail non sono stati verificati.
39. **Export sincrono** nella richiesta, senza limite di dimensione: per account con moltissimi PDF occupa un worker gunicorn per qualche secondo.
40. **Onboarding dopo la verifica email.** *(Sprint 70: banner con il link all'onboarding, se il profilo è vuoto, o al Profilo, se manca l'istruzione, su tutte le pagine.)* Il login continua a portare alla lista (`/list`) salvo `next=/onboarding`.
41. **Fuori perimetro dall'audit dello Sprint 66**, non affrontati: restrizione dell'admin per IP e superficie di allauth (M5), race condition minori sulle ricerche (B4), delimitazione dei contenuti di terzi nei prompt (B6).
42. **Testi legali con data fissa.** `PRIVACY_DATE`/`TERMS_DATE` sono costanti in `legal.py`; i testi della PWA (`frontend/src/legal/`) e la copia in `Docs/legal/` vanno tenuti allineati a mano, senza controllo automatico.
43. *(Risolto nello Sprint 67: il dialogo della PWA annuncia l'email di conferma solo con `email_enabled` di `GET /api/legal/`.)*

**Sprint 70**

44. *(Risolto al merge degli Sprint 69–70: la pagina del job mostra `ActionCostHint` e chiede conferma con `confirmCreditCharge` per generazione di CV, cover letter e messaggi; il prezzo e il saldo delle chat sono nei pannelli dello Sprint 69.)* Resta: la conferma esiste solo nella PWA, non nell'API.
45. **Fuso proposto in onboarding.** Non esiste un flag "fuso scelto dall'utente": l'onboarding propone il fuso del dispositivo quando quello salvato è ancora il default Europe/Rome, anche se l'utente l'avesse scelto di proposito (basta riselezionarlo).
46. **Cambio email senza stato lato server.** La richiesta non lascia traccia nel database: una seconda richiesta non annulla il link della prima (entrambi validi fino alla scadenza o al primo cambio riuscito), e l'app non mostra un "cambio in attesa".

---

## 12. API REST

Tutti gli endpoint sono sotto il dominio dell'app; salvo dove indicato richiedono autenticazione (header `Authorization: Token …`, §3.7; la sessione Django non è accettata dall'API) e restituiscono 401 senza credenziali o con token scaduto/revocato. Dallo Sprint 67 gli endpoint autenticati sono anche soggetti al **gate delle accettazioni** (§3.7, §5.17): 403 `{"code": "legal_acceptance_required"}` finché l'utente non ha accettato le versioni correnti; nelle tabelle sono indicati gli endpoint **esenti** e quelli **pubblici** (senza autenticazione, quindi fuori dal gate). Oltre i limiti di frequenza (§7.1) rispondono 429. Ogni oggetto è filtrato sull'utente autenticato: un id di un altro utente dà **404**. Le risposte d'errore hanno la forma `{"detail": "…"}` (o gli errori per campo di DRF per i 400 di validazione). Dallo Sprint 71 i testi sono in italiano o in inglese secondo l'header `Accept-Language` della richiesta (default italiano, §5.21); i `code` restano invariati. Prefissi da `backend/config/urls.py`; route in `apps/*/urls.py`.

### 12.1 Account, profilo, ricerche, notifiche

| Metodo | Path | Scopo | Risposte rilevanti |
|---|---|---|---|
| POST | `/api/accounts/register/` | Registrazione `{email, password, invite_code?, interface_language?, timezone?, accept_privacy, accept_terms, confirm_age}` (`timezone` dal browser, Sprint 70: un nome non valido è ignorato) (pubblico; `invite_code` obbligatorio se `REGISTRATION_INVITE_CODE` è valorizzato; le tre accettazioni devono essere `true`, Sprint 67) | Email non configurata: 201 `{token, verification_required: false}`, 400 anche per email già registrata. Email configurata: sempre 201 `{verification_required: true}` senza token, anche per un'email già registrata (non enumerazione, §3.7). 400 validazione, consensi mancanti o codice di invito errato; 429 |
| POST | `/api/accounts/login/` | Login (pubblico); crea un nuovo token per questo dispositivo | 200 `{token}`; 400 credenziali errate (messaggio generico); 403 `{code: "email_not_verified"}` con email configurata e indirizzo non confermato, solo dopo una password corretta (Sprint 67); 429 |
| POST | `/api/accounts/logout/` | Revoca il token della richiesta (Sprint 66); dallo Sprint 70 `{push_endpoint?}` elimina anche la `PushSubscription` dell'utente con quell'endpoint (il dispositivo corrente). **Esente** dal gate | 204; 401 |
| GET, PATCH | `/api/accounts/me/` | Dati utente e preferenze: `id, email, first_name, last_name, plan, extra_credit, timezone, interface_language, cv_language_mode, cv_include_photo, objective_statement`; dallo Sprint 67 `email_verified`, `notifications_enabled`, dallo Sprint 77 `auto_collection_enabled` (attivabile solo dai Pro, altrimenti 400) e `auto_collection_time` ("HH:MM" a quarti d'ora, altrimenti 400) (scrivibile: `false` elimina tutte le `PushSubscription`), `legal_acceptance_required`, `legal_missing` (documenti mancanti), `legal_acceptances` (per documento: ultima `version` e `accepted_at`); dallo Sprint 70 `profile_status` (`complete` \| `incomplete` \| `empty`, §4.2) e, se `notifications_enabled` passa da `false` a `true`, riallineamento di `last_notified_at`. Read-only: id, email, plan, extra_credit, email_verified e i tre campi `legal_*`. **Esente** dal gate | 200; 400 |
| GET | `/api/accounts/usage/` | Sprint 70: contatori di oggi, massimali del piano, prezzi extra, `next_charge` per azione e prezzi delle chat (§4.6); dallo Sprint 77 `actions.collection.done_at` (ora della raccolta di oggi o null). Dietro il gate | 200; 401; 403 |
| POST | `/api/accounts/email/change/` | Sprint 70: `{password, new_email}` → link di conferma al nuovo indirizzo e avviso all'attuale (§5.19) | 200 `{status: "confirmation_sent"}` anche se il nuovo indirizzo è già registrato (nessuna email); 400 password errata o stesso indirizzo; 429 (`password_check`); 503 `email_unavailable` |
| POST | `/api/accounts/email/change/confirm/` | Sprint 70, **pubblico**: `{token}` dal link | 200 `{status: "email_changed", email}`; 400 `{code: "expired" \| "invalid" \| "email_taken"}`; 429 (`email_request`) |
| GET | `/api/legal/` | Sprint 67, **pubblico** (nessuna autenticazione): `{privacy: {version, date}, terms: {version, date}, min_age, controller: {name, address, email, complete}, google_login_enabled, email_enabled}` | 200 |
| POST | `/api/accounts/legal-acceptance/` | Sprint 67: accettazione delle versioni correnti `{accept_privacy, accept_terms, confirm_age}` (tutti `true`); registra solo i documenti mancanti. **Esente** dal gate | 200 utente come `me`; 400 |
| POST | `/api/accounts/verify-email/` | Sprint 67, **pubblico**: conferma dell'indirizzo `{token}` (§3.7) | 200 `{status: "verified"}`; 400 `{code: "expired" \| "invalid"}` |
| POST | `/api/accounts/verify-email/resend/` | Sprint 67, **pubblico**: nuovo link `{email}`, inviato solo a un account attivo non verificato | 200 `{status: "sent_if_registered"}` in ogni caso; 400 email non valida; 429 (`email_request`, `email_address`); 503 `{code: "email_unavailable"}` senza email configurata |
| POST | `/api/accounts/password-reset/` | Sprint 67, **pubblico**: richiesta di recupero `{email}` | Come il reinvio: 200 `{status: "sent_if_registered"}`; 400; 429; 503 |
| POST | `/api/accounts/password-reset/confirm/` | Sprint 67, **pubblico**: `{uid, token, new_password}`; revoca tutti i token | 200 `{status: "password_reset"}`; 400 `{code: "invalid_link"}` o errori su `new_password`; 429 (`email_request`) |
| POST | `/api/accounts/password/change/` | Sprint 67: `{old_password, new_password}`; revoca tutti i token. **Esente** dal gate | 200 `{token}` (nuovo token per questo dispositivo); 400 password attuale errata o nuova non valida; 429 (`password_check`) |
| POST | `/api/accounts/delete/` | Sprint 67: cancellazione immediata `{password, confirm: true}` (§5.15). **Esente** dal gate | 204; 400 password errata o conferma mancante; 429 (`password_check`) |
| POST | `/api/accounts/export/` | Sprint 67: URL firmato dell'export (§5.16). **Esente** dal gate | 200 `{url}` (valido 10 minuti); 429 oltre 3 al giorno (`data_export`) |
| GET | `/api/accounts/export/download/?s=…` | Sprint 67, **pubblico** (URL firmato, nessun header di autenticazione): ZIP generato al momento | 200 `application/zip` allegato `app-apply-dati-<id>.zip`, `Cache-Control: private, no-store`; 404 firma assente/manomessa/scaduta o utente non attivo |
| GET, PATCH | `/api/profiles/me/` | Profilo dell'utente (creato se manca); PATCH JSON o multipart per la foto (`photo` solo in scrittura; in lettura `has_photo` e `photo_url` firmato, §4.15) | 200; 400 (anche foto non ammessa) |
| DELETE | `/api/profiles/me/photo/` | Sprint 70: rimuove la foto e cancella il file (a commit avvenuto) | 204 (anche senza foto) |
| GET, PUT, PATCH | `/api/profiles/<id>/` | Stesso profilo per id (solo il proprio) | 200; 404 |
| GET, POST | `/api/experiences/`, `/api/educations/`, `/api/skills/`, `/api/certifications/`, `/api/languages/` | Elenco e creazione delle voci del profilo | 200; 201; 400 (es. lingua/livello fuori lista, bullet oltre 15 × 400, numero massimo di voci della sezione, Sprint 70) |
| GET, PUT, PATCH, DELETE | `/api/<sezione>/<id>/` | Lettura, modifica, eliminazione di una voce | 200; 204; 404 |
| POST | `/api/profile/import-cv/` | Estrazione e strutturazione di un CV PDF/.docx (multipart `file`), senza salvataggio | 200 JSON strutturato; errori con `code` (Sprint 70): 400 `file_missing` \| `unsupported_type` \| `file_too_large` \| `too_many_pages`; 409 `quota_exceeded` (con `limit`); 422 `unreadable` (illeggibile o testo < 40 caratteri); 502 `ai_unavailable` |
| GET, POST | `/api/searches/` | Ricerche salvate (`search_type, keywords, city, country`; `is_active` read-only) | 200; 201; 400 oltre il limite di piano |
| GET, PUT, PATCH, DELETE | `/api/searches/<id>/` | Singola ricerca; cambiare `search_type` di una ricerca attiva applica i limiti di piano dell'attivazione (Sprint 68) | 200 (con `deactivated_previous` se su Free è stata spenta l'altra ricerca attiva del nuovo tipo); 204; 400; 404 |
| POST | `/api/searches/<id>/activate/` | Attiva; su Free disattiva la precedente dello stesso tipo | 200 (con `deactivated_previous` se applicabile); 400 limite attive Pro |
| POST | `/api/searches/<id>/deactivate/` | Disattiva | 200 |
| GET | `/api/searches-city-autocomplete/?q=` | Proxy Nominatim (min 2 caratteri, max 8 risultati, cache 1 h) | 200 lista `{city, country…}`, `[]` anche su errore di rete |
| GET | `/api/notifications/vapid-public-key/` | Chiave pubblica VAPID | 200 `{public_key}` |
| POST | `/api/notifications/push-subscriptions/` | Registra/aggiorna la sottoscrizione `{endpoint, keys:{p256dh, auth}}`; endpoint solo verso push service noti (§3.8), max 10 per utente; dallo Sprint 67 rimette `notifications_enabled = true` | 201; 400 |
| GET | `/api/` | Radice del router DRF (autenticata; navigabile solo con `DEBUG=True`) | 200; 401 |
| GET | `/api/files/cv/<doc_id>/?s=…`, `/api/files/cover-letter/<doc_id>/?s=…` | Download del PDF con URL firmato (Sprint 66, §4.15); **nessun header di autenticazione richiesto** (pubblico, fuori dal gate) | 200 PDF allegato, `Cache-Control: private, no-store`; 404 firma assente/manomessa/scaduta o documento non dell'utente della firma |
| GET | `/api/files/photo/?s=…` | Foto profilo con URL firmato | 200 immagine inline; 404 come sopra |

### 12.2 Job: lista, azioni, raccolta, import

| Metodo | Path | Scopo | Risposte rilevanti |
|---|---|---|---|
| GET | `/api/jobs/` | Lista job (senza paginazione), ordinata per `score` decrescente (nulli in fondo) poi `date_collected` decrescente. Query: `section` (`main` default \| `imported` \| `favorites` \| `archived`), `q` (sottostringa su titolo/azienda/località; se presente ignora gli altri filtri), `date_from`, `date_to` (`YYYY-MM-DD`, fuso utente, estremi inclusi), `location`, `score` (CSV interi), `status` (CSV), `search` (CSV di id `SavedSearch` e/o `none`, in OR; dallo Sprint 68 per FK `matched_saved_search`, con ripiego sull'etichetta per i job senza FK), `applicants` (CSV di fasce), `recruiter` (`yes` \| `no` \| `all`), dallo Sprint 82 `contract` (CSV di codici di contratto, in OR; esclude i job senza contratto) e `salary` (`yes` \| `no` \| `all`, su `salary` non vuoto) | 200 lista `JobSerializer`; 400 parametro non valido |
| GET | `/api/jobs/<id>/` | Dettaglio (`JobDetailSerializer`) | 200; 404 |
| GET | `/api/jobs/stats/` | Statistiche (pannello "Raccogli nuovi job" della lista; Home fino allo Sprint 72) `{jobs:{today, week, total, manual:{…}}, cvs:{…}, applications:{…}}` | 200 |
| POST | `/api/jobs/collect/` | Raccolta manuale sincrona (§5.6) | 200 `{collected, scored, discarded_scoring, kept, retried, retried_scored, groups_failed}`; 409 in corso (anche l'automatica) o raccolta di oggi già fatta ("già eseguita alle HH:MM"); senza ricerche attive non consuma la quota; 502 fallita su tutti i gruppi |
| POST | `/api/jobs/import/` | Import da link LinkedIn `{url}` (§5.7) | 201 `{job_id, status, score}`; 403 non Pro; 409 URL non valido, offerta non recuperabile, duplicato, quota/credito esauriti |
| POST | `/api/jobs/manual/` | Creazione manuale (§5.8) | 201 `{job_id, status, score}`; 400 validazione; 409 quota/credito esauriti; 502 creazione fallita (quota/credito restituiti) |
| POST | `/api/jobs/<id>/archive/`, `/unarchive/` | Archivia / ripristina (non cambia lo stato) | 200 job serializzato; 404 |
| POST | `/api/jobs/<id>/favorite/`, `/unfavorite/` | Preferito sì/no | 200 job serializzato; 404 |
| POST | `/api/jobs/<id>/mark-application-done/` | Candidatura fatta (anche senza CV); aggiorna `last_activity_reset` | 200 job serializzato (dettaglio); 409 già fatta |
| POST | `/api/jobs/<id>/undo-application-done/` | Annulla la candidatura (Sprint 69): `cv_generated` se c'è un CV, altrimenti `new`; `date_application_done` azzerata; `last_activity_reset` invariato | 200 job serializzato (dettaglio); 409 se il job non è `application_done` |
| GET, POST | `/api/job-filter-presets/` | Elenco e creazione dei filtri preferiti | 200; 201; 400 validazione; 409 oltre 50 |
| DELETE | `/api/job-filter-presets/<id>/` | Eliminazione | 204; 404 |

Campi di `JobSerializer`: `id, title, company, location, description, apply_url, published_at, salary, contract_type, matched_search, applicants_count, applicants_bucket, recruiter_name, recruiter_profile_url, origin, is_archived, is_favorite, status, cv_generation_in_progress, cover_letter_generation_in_progress, referral_message_generation_in_progress, score, score_match, score_gaps, score_reasoning, date_collected, date_scored, date_cv_generated, date_application_done, cv_pdf_url, cv_download_filename, cover_letter_pdf_url, cover_letter_download_filename`. Dallo Sprint 66 `cv_pdf_url` e `cover_letter_pdf_url` sono URL firmati validi un'ora (`/api/files/…?s=…`, §4.15), non più il path media. Dallo Sprint 69 i tre `*_generation_in_progress` sono falsi se il flag è stantio (§4.4).

`JobDetailSerializer` (Sprint 69; dettaglio, candidatura e annullamento) aggiunge `cv_page_count`, `cv_editable` (ultimo CV con `content_json` non vuoto), `cv_draft_outdated` (esiste una bozza e l'ultimo CV non è il suo `source_document`), `cover_letter_page_count`, `cover_letter_editable`, `cover_letter_draft_outdated`. Non sono nella lista per non aggiungere query per ogni job.

### 12.3 CV, cover letter, messaggi, editor e chat

| Metodo | Path | Scopo | Risposte rilevanti |
|---|---|---|---|
| POST | `/api/jobs/<id>/generate-cv/` | Genera/rigenera CV `{gap_numbers?: [int], gap_instructions?: str}` (Sprint 69: numeri 1-based dei gap in `score_gaps`; `gaps?: [str]` ancora accettato) (§5.2, §6.2) | 201 `{cv_document_id, page_count}`; 400 oltre i limiti di §7.1; 409 già in corso, profilo incompleto, quota/credito esauriti; 502 generazione fallita |
| GET | `/api/jobs/<id>/cv-draft/` | Bozza CV (normalizzata, §5.12) | 200 `content_json`; 404 |
| POST | `/api/jobs/<id>/cv-draft/` | Crea o risemina la bozza dall'ultimo CV (chat azzerata); con `{"mode": "keep"}` conserva la bozza e prende l'ultimo CV come riferimento (Sprint 69) | 201 `content_json` (seed); 200 (keep); 409 nessun CV riapribile |
| PATCH | `/api/jobs/<id>/cv-draft/` | Sostituisce l'intero `content_json` (id mancanti assegnati) | 200 contenuto salvato; 400 struttura o dimensioni non valide (§5.12); 404 |
| POST | `/api/jobs/<id>/cv-draft/preview/` | Anteprima PDF (body facoltativo con il contenuto) | 200 `application/pdf` + `X-Page-Count`; 400 come sopra; 404; 429 |
| POST | `/api/jobs/<id>/cv-draft/finalize/` | Nuovo `CVDocument` dalla bozza, gratuito; `{"content": …}` facoltativo salvato prima del rendering (Sprint 69) | 201 `{cv_document_id, page_count}`; 400 contenuto non valido; 409 nessuna bozza |
| GET | `/api/jobs/<id>/cv-draft/chat/` | Cronologia chat CV, prezzo del messaggio e saldo | 200 `{history, price, balance}`; 404 |
| POST | `/api/jobs/<id>/cv-draft/chat/` | Messaggio `{message, focus_bullets?: [{profile_experience_id, bullet_id}]}` | 200 `{reply, actions, balance}`; 400 vuoto o oltre 2.000 caratteri; 402 credito insufficiente; 429; 502 AI fallita o bozza assente |
| PATCH | `/api/jobs/<id>/cv-draft/chat/` | Decisione `{message_index, action_index, decision}` | 204; 400 |
| POST | `/api/jobs/<id>/generate-cover-letter/` | Genera cover letter `{instructions?}` (§5.10) | 201 `{cover_letter_document_id, page_count}`; 400 indicazioni oltre 2.000 caratteri; 409; 502 |
| GET | `/api/cover-letter-instructions/` | Ultime 20 voci distinte (scomposte e deduplicate, §5.10) | 200 `{instructions}` |
| GET, POST, PATCH | `/api/jobs/<id>/cover-letter-draft/` | Bozza cover letter (come per il CV, anche `{"mode": "keep"}`) | 200 / 201; 400; 404; 409 |
| POST | `/api/jobs/<id>/cover-letter-draft/preview/` | Anteprima PDF | 200 `application/pdf` + `X-Page-Count`; 404 |
| POST | `/api/jobs/<id>/cover-letter-draft/finalize/` | Nuova `CoverLetterDocument` dalla bozza, gratuita; `{"content": …}` facoltativo | 201 `{cover_letter_document_id, page_count}`; 400; 409 |
| GET, POST, PATCH | `/api/jobs/<id>/cover-letter-draft/chat/` | Chat cover letter (`POST {message}`, senza `focus_bullets`; azioni per `paragraph_id`) | come la chat CV: 200 / 204; 400; 402; 404; 502 |
| POST | `/api/jobs/<id>/generate-referral-message/` | Messaggio di networking `{channel, recipient_name?, recipient_linkedin_url?, instructions?}` (§5.11) | 201 messaggio; 400 canale non valido o testi oltre i limiti; 409; 502 |
| GET | `/api/jobs/<id>/referral-messages/` | Storico messaggi del job, dal più recente | 200 lista |
| GET | `/api/referral-message-instructions/` | Ultime 20 voci distinte (scomposte e deduplicate, §5.10) | 200 `{instructions}` |

### 12.4 Altri URL serviti dal backend

| Path | Scopo |
|---|---|
| `/admin/` (o `DJANGO_ADMIN_PATH`) | Django Admin (sessione, utenti staff); login limitato a 10 errori per IP in 15 minuti (429) |
| `/accounts/…` | django-allauth (login Google: `/accounts/google/login/`, callback); raggiungibile anche se il pulsante è nascosto (§3.7) |
| `/static/…` | Servito direttamente da Caddy in produzione |
| `/media/…` | **Mai servito** (404 da Caddy; nessuna rotta Django): i file si scaricano da `/api/files/…` |

---

## 13. Test

### 13.1 Suite backend

488 test Django (`python manage.py test`; 299 allo Sprint 66, 345 con lo Sprint 67, 386 con lo Sprint 68, 415 con lo Sprint 69, 448 con lo Sprint 70, 465 con lo Sprint 71), **tutti verdi il 2026-11-15 (Sprint 77)** se lanciati con `DJANGO_DEBUG=true` (con la configurazione di produzione `DEBUG=false` il redirect HTTPS fa rispondere 301 al test client e ~60 test falliscono senza regressioni reali: procedura in `DEPLOY.md` §4.4). Il database di test è separato. Le chiamate esterne (Bedrock, Apify, LinkedIn, Nominatim, Web Push, S3, `pg_dump`/`pg_restore`) sono sempre simulate con mock; le email usano il backend locmem e i task Celery girano in linea (`CELERY_TASK_ALWAYS_EAGER`). Nei test sono spenti il gate delle accettazioni (`LEGAL_GATE_ENABLED`), l'invio email e il codice di invito del `.env`, riaccesi con `override_settings` nei test dedicati (§3.7, §5.14).

| File | Test | Cosa copre |
|---|---|---|
| `apps/jobs/tests.py` | 104 | Raccolta per utente (campi obbligatori, dedup, scarto oltre `max_length`, assenza di cap), scoring singolo e parallelo (concorrenza, fallimenti, cap lingua e regressione sottostringa), ciclo notturno per utente e orchestratore, assenza di CV automatici, raccolta manuale (guardia, guardia stantia, quota, rimborso, `SystemExit`) e relativa API, schedulazione del ciclo notturno, import da link (servizio e API), job manuale (servizio e API), lista e filtri (sezioni, date nel fuso utente, location, candidati, recruiter, ricerca multipla, ricerca testuale), archivio, preferiti, dettaglio, candidatura fatta (anche senza CV), API dei messaggi di networking, filtri preferiti, comando `seed_e2e_jobs` |
| `apps/jobs/test_sprint68.py` | 41 | Sprint 68: `delete_discarded_by_cap_jobs` (dry-run con conteggi, `--confirm` con documenti, bozze e file, colonna già rimossa) e rifiuto della migrazione `jobs/0019` con righe marcate; `rescale_legacy_scores` (dry-run, idempotenza, valori anomali, taglio personalizzato); contatore `scoring_failures`, retry notturno con limite, `retry_unscored_jobs`; FK `matched_saved_search` in raccolta, filtro dopo la modifica della ricerca, ripiego testuale, backfill `jobs/0018` solo univoco, ricerca eliminata; isolamento degli errori per gruppo Apify e attribuzione della ricerca, `RunLog` per gruppo, tutti i gruppi falliti; scarti contati; guardia condivisa manuale/notturna; azioni Admin sui contatori e pagine Admin nuove; import con `IntegrityError` e campi troppo lunghi; restituzione della quota/credito del job manuale e retry dello scoring; località nel prompt; `PATCH` del tipo di ricerca (Free/Pro, inattiva) |
| `apps/jobs/sources/tests.py` | 26 | Fonte Apify (payload raggruppato, Company con `companyInclude`, normalizzazione, candidati e recruiter, retry) e import via API guest |
| `apps/cv/tests.py` | 31 | Generazione CV (un blocco per esperienza, 1 pagina su profilo standard, foto on/off, istruzione copiata dal profilo, CV congelato dopo modifiche al profilo, modalità lingua, ripiego per overflow e `RunLog` multi-pagina), generazione manuale (quota nel giorno Europe/Rome, credito, concorrenza, rimborso, stato invariato se fallisce, uscita dall'archivio), messaggi di networking (8 test: quota, più messaggi per job, concorrenza, credito, rimborso, indicazioni) |
| `apps/cv/test_sprint69.py` | 29 | Sprint 69: stato del job dopo generazione riuscita/fallita, `SystemExit` con restituzione, flag stantii (guardia e serializer), `referral_message_generation_in_progress`, `page_count` in risposta e nel dettaglio; annullamento della candidatura (stato, `last_activity_reset` invariato, 409); numerazione dei gap nel prompt (anche testi legacy) e via API; bozza superata, risemina con chat azzerata e "continua"; finalizzazione con il contenuto corrente (CV e cover letter) e contenuto non valido; `cv_editable`/`cover_letter_editable`; id stabili (seed da documento legacy, normalizzazione pigra con mappatura delle azioni legacy, PATCH, paragrafi stringa); filtro delle azioni chat su id inesistenti e `area_text`, due rimozioni dello stesso turno; cronologia del prompt con decisioni; `focus_bullets` per id; prezzo e saldo della chat; storico delle indicazioni deduplicato; grassetto in sommario, aree, ruolo e note |
| `apps/cv/test_selection.py` | 19 | Selezione dell'istruzione, budget bullet, cap esperienze con swap, taglio per rilevanza, rimozione del bullet meno rilevante |
| `apps/jobs/test_sprint77.py` | 26 | Sprint 77: finestra oraria della raccolta automatica nel fuso dell'utente (fuso non valido, ora legale: orario inesistente e ripetuto), dispatcher solo Pro con l'opzione attiva e una volta al giorno, isolamento degli errori per utente, task che ricontrolla il piano; quota unica automatica/manuale (409 con l'ora, SKIPPED), nessuna quota senza ricerche attive, restituzione sulla riga riservata anche dopo mezzanotte, quota tenuta con fallimento parziale; push solo a fine automatica con job nuovi; API delle impostazioni (solo Pro, quarti d'ora, orario già passato → domani), `done_at` in usage, 409 in inglese, export; migrazione dati dei Pro esistenti |
| `apps/jobs/test_sprint82.py` | 19 | Sprint 82: `salaryInfo` → stringa leggibile (intervallo, decimali, simbolo con spazio e suffisso, migliaia della fonte, testo non riconosciuto, vuoto, 255 caratteri), `contractType` normalizzato, raccolta che salva stipendio e contratto, filtri `contract` (OR, job senza dato esclusi) e `salary` (con / senza, AND), ricerca testuale che li ignora, parametri API e 400, preset con `contract_types` e `has_salary` (default vuoti, valori non validi) |
| `apps/notifications/tests.py` | 16 | Notifica di fine raccolta (Sprint 77, al posto della mattutina: invio e `last_notified_at`, preferenza spenta, schedule delle 10:00 rimossa), promemoria di inattività, API sottoscrizione e chiave VAPID; Sprint 66: allowlist degli endpoint, massimo 10 sottoscrizioni, `timeout=10`, 410 → sottoscrizione eliminata, un errore non interrompe il giro (né sulle altre sottoscrizioni né sugli altri utenti) |
| `apps/common/test_multi_user_isolation.py` | 11 | Isolamento dei dati tra utenti sulle API |
| `apps/searches/tests.py` | 10 | Limiti di piano delle ricerche, attivazione per tipo su Free, downgrade, modifica |
| `apps/profiles/tests.py` | 7 | API del profilo (foto: `has_photo` e `photo_url` firmato); import CV (4 test, di cui 2 con `call_claude_structured` simulato) |
| `apps/common/tests.py` | 8 | Schedulazione del backup alle 03:30, backup su S3 simulato; Sprint 67: backup locale con `pg_dump` simulato e rotazione a 7 giorni, file con altri nomi ignorati dalla rotazione, dump fallito che non tocca i backup esistenti; `restore_backup` (rifiuto senza `--confirm`, backup locale mancante, ripristino dalla cartella locale e da `--file`) |
| `apps/accounts/tests.py` | 7 | `/me` (plan e credito esposti e read-only, nome modificabile, nessun lost update di `extra_credit`, fuso orario validato), comando `set_e2e_account` |
| `apps/accounts/test_privacy.py` | 43 | Sprint 67: spunte obbligatorie in registrazione e versioni registrate, `LegalAcceptance` append-only; gate (403 con codice su un campione di endpoint, endpoint esenti, accettazione che riapre l'app, nuova versione che richiude il gate, 401 prima del gate); `/api/legal/` (versioni, titolare incompleto, flag Google); verifica email (link valido, scaduto, manomesso, lingua dell'email, login bloccato solo dopo la password corretta, reinvio generico e limitato per indirizzo, non enumerazione in registrazione); migrazione `0010`; flusso senza email configurata (registrazione come prima, login non bloccato, duplicati segnalati, reset e reinvio 503, task che non invia); recupero password (risposta identica per indirizzi noti e sconosciuti, reset che cambia la password e revoca tutti i token, link non valido, password debole); cambio password (errori, revoca e nuovo token); cancellazione (password/conferma mancanti, nessuna riga residua su **tutte** le FK verso `User` e nessun file su disco, cancellazione fuori dall'endpoint pulita dai segnali, token non più valido); export (contenuto completo, niente hash/chiavi/dati di altri utenti, firma, 3 al giorno, funzionante senza accettazioni); foto sostituita cancellata; preferenza notifiche (sottoscrizioni eliminate, task che saltano l'utente, riattivazione con una nuova sottoscrizione) |
| `apps/accounts/test_sprint70.py` | 33 | Sprint 70: `/api/accounts/usage/` (Free senza attività, contatori usati, credito sufficiente/insufficiente, Pro, giorni precedenti esclusi, 401 e gate); fuso orario in registrazione (valido, non valido ignorato) e `PATCH /me`; `profile_status` (empty/incomplete/complete); `objective_statement` modificabile; logout con `push_endpoint` (solo il dispositivo corrente, mai di altri utenti, nessun effetto senza endpoint); riallineamento di `last_notified_at` da `PATCH /me` e da una nuova sottoscrizione, senza notifica per i job del periodo di silenzio; rimozione della foto con file cancellato dal disco; `technologies` modificabili; bullet 15 × 400 sulle nuove modifiche e profili esistenti oltre il limite ancora salvabili ma non estendibili; numero massimo di voci; codici d'errore dell'import CV; cambio email (email al nuovo e al vecchio indirizzo, email invariata fino alla conferma, conferma con login col nuovo indirizzo e link non riusabile, password errata/stesso indirizzo, indirizzo già registrato senza email, indirizzo preso prima della conferma, link manomesso/scaduto, non disponibile senza email) |
| `apps/accounts/test_security.py` | 21 | Sprint 66: token (solo hash nel DB, un token per login/dispositivo, logout revoca solo il corrente, scadenza a 30 giorni di inattività con scorrimento, `last_used_at` al più ogni ora, `revoke_all_tokens`), errore di login generico, permessi di default e sessione non accettata dall'API, codice di invito (errato, mancante, corretto, vuoto = aperta, nessuna rivelazione dell'email), throttling di login per IP e per email e della registrazione, limite dei login falliti all'admin. Dallo Sprint 67 le registrazioni dei test inviano le tre spunte |
| `apps/common/test_files.py` | 19 | Sprint 66: download firmati (proprietario senza header, altro utente, firma assente/manomessa/scaduta/di un altro tipo o documento → 404, `/media/` non servito, header di risposta), URL firmati nel `JobSerializer`, nomi casuali, foto (EXIF/GPS rimossi e orientamento applicato, formato/dimensioni/peso, URL firmato), comando `secure_media_files` (dry-run, rinomina idempotente con ricodifica delle foto, orfani) |
| `apps/jobs/test_input_limits.py` | 16 | Sprint 66: limiti di lunghezza (descrizione job manuale, messaggi di chat, indicazioni cover letter, gap, destinatario), validazione del `content_json` delle bozze CV e cover letter in PATCH e anteprima, import CV (5 MB, formato dai primi byte, 10 pagine, troncamento del testo, quota giornaliera, errore AI → 502 con quota restituita), limiti dei bullet del profilo |
| `apps/common/test_i18n.py` | 17 | Sprint 71: catalogo inglese senza voci `fuzzy` né `msgstr` vuoti e `.mo` committato identico al `.po` (confronto voce per voce, anche i plurali); testi in it/en secondo `Accept-Language` (assente o non supportato → italiano, `en-GB` → inglese) per login errato, codice di invito errato, quota di generazione CV esaurita, import non consentito al Free, raccolta manuale già usata, lunghezza massima (messaggio di DRF), parametro non valido con segnaposto, gate legale, 429; Admin in italiano con browser inglese; lingua non lasciata attiva dopo la richiesta; payload delle notifiche mattutina e di inattività e prefisso del cap lingua secondo `interface_language` anche con un'altra lingua attiva; email di servizio con gli stessi testi dello Sprint 67 |
| `apps/searches/test_geo.py` | 4 | Proxy di autocomplete città (con una LocMemCache: nei test la cache di default è una DummyCache) |

Prima di chiudere uno sprint che tocca i modelli va eseguito anche `makemigrations --check`; dallo Sprint 66 anche `check --deploy` con `DEBUG=false` (nessun problema segnalato: i warning su HSTS `includeSubDomains`/`preload` sono silenziati per scelta).

### 13.2 Test end-to-end (Playwright)

In `frontend/e2e/` (`npm run test:e2e`, configurazione `playwright.config.js`, base URL da `E2E_BASE_URL`), con account e job preparati dai comandi `set_e2e_account` e `seed_e2e_jobs` (richiedono `DEBUG=True`):

- `auth-onboarding.spec.js`: registrazione (con le tre spunte dei consensi, Sprint 67) e onboarding manuale, raggruppamento esperienze per azienda, login errato, lingua dell'interfaccia (browser it/en, switcher); dallo Sprint 79 anche passi e fuso orario dell'onboarding, import del CV con errore e riprova (risposta finta 422, poi 200), errori della registrazione sotto i campi e consensi mancanti, schermata "controlla la tua email", login con email non confermata e reinvio, verifica email riuscita/scaduta/mancante, recupero password non disponibile, inviato, link non valido e reset riuscito, pagine legali a fisarmonica (12 e 11 sezioni), schermata di accettazione. Gli stati legati alle email sono simulati con `page.route` (risposte finte di `/api/accounts/...` e `email_enabled` di `/api/legal/`), perché nello stack di prova le email non partono. Dallo Sprint 80: pagina non trovata, errore di rete all'avvio ("Nessuna connessione", Riprova, nessun redirect al login), nelle pagine legali (Riprova) e in un modulo (avviso di connessione), con `page.route(...).abort()`;
- `account.spec.js`: piano e saldo, ciclo di vita di una ricerca salvata, limite di piano, persistenza delle impostazioni, istruzione iOS per le push; dallo Sprint 70 titolo "Impostazioni" e riquadro "I tuoi limiti di oggi"; Dallo Sprint 77 la riga "Raccolta giornaliera" (0 / 1) nei limiti di oggi. Dallo Sprint 78: ricerche nella sottopagina (`addSearchFromSheet`: "Nuova ricerca" → pannello con l'avviso "nasce disattivata" → "Aggiungi ricerca"; interruttore "Usa la ricerca «…»"; eliminazione con conferma; indietro del browser verso l'elenco), limite del piano mostrato nel pannello, lingua del CV dal pannello e foto con interruttore (persistenza dopo il reload), limiti dalla sottopagina; nuovi: privacy e sicurezza da link diretto (documenti con versione, età minima, pannello password con password diverse, finestra di eliminazione con pulsante attivo solo con password e spunta), raccolta automatica nell'elenco (Free bloccata, Pro con orario 07:00), profilo (fisarmoniche, campo obbligatorio in una sezione chiusa che la riapre, "Salva modifiche" e "Profilo aggiornato.").
- `collection.spec.js` (Sprint 77): pannello di raccolta per un Free (automatica bloccata, "Scopri il piano Pro", regola "1 raccolta al giorno, automatica o manuale"), per un Pro (attivazione, orario 07:00 → 08:15 conservato dopo il ricaricamento) e con la raccolta di oggi già fatta (`DailyQuota` preparata con `manage.py shell`: "Raccogli ora" disattivato e "Raccolta di oggi già eseguita alle HH:MM."). Dallo Sprint 80 l'avviso "notifiche disattivate" per un Pro con l'automatica attiva.
- `job-list.spec.js`: sezioni, filtri (punteggio, stato, location, ricerca multi-selezione, candidati, recruiter), ricerca testuale, archivio con annulla e swipe, generazione CV (pulsante disabilitato), link annuncio e candidatura senza CV, espandi motivazioni, badge candidati e icona recruiter, preferiti, filtri preferiti; dallo Sprint 70 filtri nell'URL conservati tornando dal dettaglio e "Esci" dalla barra in alto (tolto il test dell'arricchimento, funzione rimossa nello Sprint 44); Dallo Sprint 73 anche: "Esci" da Impostazioni con finestra di conferma (al posto del test sull'"Esci" della barra in alto), navigazione a 3 voci con voce attiva e redirect di `/home`, barra di tab a 390 px con apertura del pannello di raccolta e nessuna pagina più larga dello schermo. Dallo Sprint 74 gli helper `inFilters` (apre il pannello Filtri, agisce, chiude con "Mostra risultati"), `toggleScore`, `openCard` (clic sul titolo della scheda) e `swipeCard`; generazione del CV dal dettaglio; ricerche di provenienza come pillole con `aria-pressed`; recruiter come segmento. Dallo Sprint 75 gli helper `actionBar` e `fromMoreMenu` (menu ⋯ del dettaglio): "Genera CV" apre il pannello "Colma i gap" e l'attesa è una finestra non chiudibile ("Generazione del CV…", resiste a Esc); "Segna candidatura fatta" senza CV dal menu ⋯; "Annulla candidatura" con la finestra di conferma (No / Sì); contatori corrispondenze/gap (al posto di "Espandi motivazioni"); menu ⋯ da tastiera per archiviare e riportare dall'archivio; ▾ di "Genera CV" con cover letter e messaggio e il costo dell'azione giusta (`action-cost-cover_letter`, `action-cost-referral_message`), `maxlength` 2000; a 390 px la barra azione sostituisce la barra di tab, senza larghezza in eccesso.
- Dallo Sprint 82: `job-list.spec.js` filtri Contratto (multi, OR) e Stipendio, combinati, nel conteggio, in un filtro salvato e riapplicato; dettaglio con stipendio e contratto, solo contratto, nessuna riga per un job importato (seed `seed_e2e_jobs` con stipendio e contratto su quattro job); `account.spec.js` attività come chip (aggiunta, modifica con contatore, oltre 400 caratteri "Fatto" disattivato, Annulla, ✕, blocco a 15).
- `layout.spec.js` (Sprint 81, helper `e2e/helpers/layout.js`): con dati lunghi (azienda e ruolo lunghi, 10 punti elenco, date) percorre accesso, lista, filtri, raccolta, job manuale, dettaglio, editor, Profilo con tutte le sezioni aperte, Impostazioni e sottopagine, nuova ricerca, onboarding; segnala pagina più larga dello schermo, elementi che escono dal contenitore visibile (primo antenato con bordo o sfondo), controlli sovrapposti nello stesso strato (escluso il contenuto che scorre sotto barre fisse o sticky) e spazio in fondo minore delle barre fisse. Gira nel progetto `chromium` a 360/390/1280 px e nei progetti `iphone-13` e `iphone-se` (WebKit con l'emulazione del dispositivo, `playwright.config.js`); `LAYOUT_SHOTS=<cartella>` salva gli screenshot. Sul VPS va lanciato con un solo worker e un limite di memoria (vedi `sprints/sprint-81.md`).
- `push-subscription.spec.js`: sottoscrizione push verificata lato backend (endpoint finto su `fcm.googleapis.com`, per passare l'allowlist dello Sprint 66).
- `editor.spec.js` (Sprint 76): crea nel DB di prova, con `manage.py shell` (stesso `.venv/bin/python` del seed), un job con un CV e una cover letter modificabili (`content_json`), competenze del profilo e, dove serve, una cronologia della chat con una proposta o un CV più recente. Verifica: a 390 px barra azione al posto della barra di tab, fisarmoniche con riassunto, interruttore "Mostra nel CV", "Aggiungi punto", salvataggio, anteprima (iframe o avviso), nessuna larghezza in eccesso; assistente in pannello dal basso con prezzo e saldo dell'API, avviso AI, chip del contesto, proposta accettata applicata al sommario e decisione conservata riaprendo; credito insufficiente con campo e invio disattivati; "bozza superata" con Riparti / Continua; a 1280 px cover letter con la chat in colonna larga 400 px, titoli dei paragrafi, `maxlength` 3000, aggiunta e rimozione di un paragrafo. La generazione AI e l'invio reale di un messaggio non sono provati (nessuna chiave AI nell'ambiente).

Dallo Sprint 67 le registrazioni via API degli spec inviano `accept_privacy`, `accept_terms`, `confirm_age` e usano il token della risposta: presuppongono quindi un backend **senza invio email configurato** (con l'email attiva la registrazione non restituisce token). Dallo Sprint 70 le registrazioni (via API e dal modulo) inviano il codice di invito letto da `E2E_INVITE_CODE` (vuoto = registrazione aperta). Gli e2e non sono stati rilanciati negli Sprint 67–70.

L'esecuzione degli e2e non è documentata negli ultimi sprint. Dallo Sprint 73 i comandi per lanciarli su un computer di sviluppo (backend con `.venv`, Postgres locale, variabili d'ambiente) sono in `sprints/sprint-73.md`, insieme alla procedura usata sul VPS con uno stack Docker usa e getta. Ultima esecuzione: 2026-11-14, **35/35** (dopo l'allineamento degli spec rimasti indietro dagli sprint 32–67). Dopo lo Sprint 74: **35/35**. Dopo lo Sprint 79: **58/58**. Dopo lo Sprint 81 vedi `sprints/sprint-81.md`. Dopo lo Sprint 80: **63/63** (al primo giro 62/63, un'instabilità di tempi non ripetuta: `sprints/sprint-80.md`). Requisiti dell'ambiente: limiti di frequenza alzati (`e2e_settings_local.py`), nessun codice di invito né email, app servita su `localhost` (contesto sicuro per service worker e push).

### 13.3 Cosa non è coperto

- `apps/common/ai.py`: tool-use forzato, validazione `jsonschema`, retry, `StructuredOutputError`;
- **cover letter**: generazione con il modello reale del contenuto, nomi file (bozza, chat, finalizzazione e storico delle indicazioni coperti in parte da `test_sprint69.py`);
- **editor CV** e **chat**: anteprima, credito insufficiente (402), `record_action_decision` (seed, finalizzazione, filtro, contesto e prezzo coperti da `test_sprint69.py`);
- componente `RichBulletInput` e dialogo "bozza superata" (solo frontend);
- statistiche Home (`stats.py`, `/api/jobs/stats/`);
- filtro di grounding su skill/certificazioni del CV (`_filter_grounded_skills`), etichette nelle 5 lingue;
- normalizzazione delle lingue (`profiles/0007`), validazione delle choices di `Language`, `Profile.email`;
- login Google;
- invio reale delle email via Gmail (consegna, antispam) e i flussi completi nella PWA in un browser: registrazione → email → verifica, recupero password dal link, export su iOS, schermata di accettazione, pagine legali, preferenza notifiche (Sprint 67; i backend sono coperti da `test_privacy.py`, il frontend no);
- accesso ai profili Bedrock `eu.` dall'account AWS (non verificato);
- access log di Caddy con i nuovi parametri oscurati (verificato solo con `caddy validate`);
- renderer solo JSON con `DEBUG=False` (i test girano con `DEBUG=True`), header di Caddy e CSP (verificati solo con `caddy validate` e una prova manuale);
- frontend senza test unitari: editor, chat, Home e dialog di cover letter e messaggi non hanno test e2e;
- Sprint 70, solo lato frontend e non provati in un browser: avviso di nuova versione (service worker reale), annullamento della sottoscrizione push nel browser al logout, banner del profilo, selettore del fuso orario, conferma prima dell'addebito, pagina `/confirm-email-change`.

---

*Fine del documento.*
