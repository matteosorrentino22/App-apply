# Sprint 24 — Import job: richiesta diretta a LinkedIn invece di Apify

## Input
L'import manuale di job (Sprint 14, collegato all'UI nel fix del 2026-07-29)
usa `fetch_by_url` su `ApifyLinkedInSource`, che passa dall'actor Apify anche
per un singolo link: stesso problema di tempi variabili/timeout appena
affrontato per la raccolta notturna (§5.2 tecniche), e consumo di credito
Apify per un'operazione che riguarda un solo job già identificato dal link.

Verificato con richieste HTTP dirette (curl, User-Agent browser) che
l'endpoint pubblico `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}`
risponde senza autenticazione né rate-limiting apprezzabile, con titolo,
azienda, location e descrizione nel markup, e 404 pulito per job non
esistenti/rimossi.

## Obiettivo
Sostituire la fonte usata da `fetch_by_url` (solo per l'import manuale) con
una chiamata diretta a LinkedIn, lasciando **inalterata** `fetch()` (raccolta
notturna via Apify, §5.1/§5.3 tecniche) e l'interfaccia `get_job_source()`.
Nessuna nuova dipendenza esterna.

## Esito (2026-07-29)

### Implementazione
`ApifyLinkedInSource.fetch_by_url` (usato solo dall'import manuale, §4.9
funzionali) non passa più dall'actor Apify: estrae l'ID dal link, chiama
direttamente `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}`
(endpoint pubblico, nessuna chiave) e ne fa il parsing con regex (titolo,
azienda, location, descrizione — convertita da HTML a testo semplice per il
campo `Job.description`). `apply_url` è il link incollato dall'utente
(l'endpoint guest non lo restituisce e non serve altro: è già il link a cui
l'utente si candida). `published_at` resta `None` (non usato nel flusso di
import). La raccolta notturna (`fetch()`, via Apify) **non è stata toccata**.

Nessuna nuova dipendenza: parsing con `re`/`html` della libreria standard.

### Cosa cambia rispetto a prima
- Tempo di risposta: da 10–180s (chiamata sincrona Apify) a ~1s.
- Nessun consumo di credito Apify per un singolo import.
- Se LinkedIn cambia il markup del fragment `jobs-guest`, il parsing va
  aggiornato (nessuna dipendenza da Apify per assorbire il cambiamento, a
  differenza della raccolta notturna) — unico compromesso della scelta,
  segnalato esplicitamente perché tocca l'assunzione "un'unica fonte offerte,
  sostituibile" delle tecniche (§5.3): **solo per il path di import**, `fetch()`
  resta su Apify.
- Un job non più esistente o un link non riconoscibile restituiscono `None`,
  che il servizio di import (`import_service.py`, non modificato) già gestiva
  con il messaggio "impossibile importare quel job" e il refund di
  quota/credito.

### Verifica eseguita
- Prototipazione con richieste HTTP dirette reali (non mock) verso più ID
  di job LinkedIn reali: verificato titolo/azienda/location/descrizione
  estratti correttamente, 404 pulito su ID inesistenti, nessun
  rate-limiting/blocco su richieste ripetute.
- Test automatici: 6 nuovi test su `ApifyLinkedInSourceFetchByUrlTests`
  (parsing completo, verifica che non venga più chiamato `requests.post`/Apify,
  404 → `None`, errore di rete → `None`, URL non LinkedIn → `None` senza
  fare la richiesta, HTML senza titolo → `None`).
- `python manage.py test`: **139/139 passati** (128 pre-esistenti + 11 sulla
  fonte, di cui 6 nuovi di questo sprint). Eseguiti nel container di
  produzione con `DJANGO_DEBUG=true` per bypassare `SECURE_SSL_REDIRECT`
  (causa nota e preesistente di falsi fallimenti nei test in produzione,
  non legata a questo sprint — vedi nota simile in Sprint 23).
- `makemigrations --check --dry-run`: nessuna modifica ai modelli, nessuna
  differenza.

### Deploy
Rebuild dell'immagine `web`/`worker`/`beat` e riavvio in produzione (il
codice era stato copiato temporaneamente nel container solo per eseguire i
test prima del rebuild).

### Cosa manca
- Nessun elemento noto in sospeso per questo sprint. Bug 2 (selettività
  raccolta Apify) e suite e2e Playwright restano aperti dallo Sprint 23,
  volutamente fuori scope qui.
