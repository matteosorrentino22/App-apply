# Sprint 43 — Creazione manuale di un job nella sezione Importati

## Input
Richiesta del committente: nella sezione "Importati", oltre all'import da
link LinkedIn, poter inserire manualmente i dati di una job position (come
già possibile da Django Admin, ma con scoring automatico incluso). Campi
obbligatori: titolo, località (stessa logica di autocomplete degli altri
campi località), azienda, descrizione, data/ora di riferimento (→
`published_at`); facoltativo: link di candidatura. Nessun limite di piano,
a meno che l'import da LinkedIn non ne abbia già uno (in quel caso stesso
massimale ma contatore separato).

## Nota preliminare: lavoro pregresso non commitato
Prima di iniziare, trovate ~56 file modificati/nuovi nella working
directory di `main`, mai commitati: lo Sprint 39 (ricerche Company) più,
a giudicare dai commenti nel codice, gli Sprint 40-42 (migrazione del
motore AI da Anthropic diretto a Claude via AWS Bedrock, lettere di
presentazione, normalizzazione lingue profilo ed email profilo separata) —
già completati e distribuiti in produzione in una sessione precedente, ma
mai salvati su git. Verificato con la suite di test (186/186 dopo una
correzione, vedi sotto) e commitato come lavoro di recupero prima di
iniziare questo sprint, per non perderlo e per non mischiarlo con le
modifiche nuove. Corretto anche `apps/profiles/tests.py`, non aggiornato
durante la migrazione a Bedrock: due test mockavano ancora una classe
`Anthropic` rimossa da `cv_import.py`, causando un errore ad ogni
esecuzione della suite completa.

Sprint 40, 41 e 42 non hanno un proprio file `sprints/sprint-NN.md`
(il lavoro risulta solo da `sprint-39.md`, parziale, e dai commenti nel
codice): documentazione retroattiva non fatta in questa sessione — se
serve in futuro va ricostruita a parte.

## Esito (2026-08-22)

### Modello
- `Job.Source`: aggiunto `MANUAL` (oltre a `LINKEDIN`).
- `Job.apply_url`: reso opzionale (`blank=True, default=""`) — un job
  inserito a mano può non avere ancora un link di candidatura (es.
  candidatura di persona/via email); per LinkedIn/raccolta notturna resta
  sempre popolato.
- `DailyQuota.manual_job_count`: nuovo contatore giornaliero, separato da
  `import_count` (import da LinkedIn) — stesso massimale (3/giorno) e
  stesso meccanismo di sblocco a credito, ma budget indipendente: creare
  un job a mano e importarlo da un link non si consumano a vicenda.
  Migrazione `0007_dailyquota_manual_job_count_alter_job_apply_url_and_more`.

### Servizio
Nuovo `apps/jobs/manual_job_service.py` (stessa convenzione di
`manual_generation.py`/`import_service.py`): `create_manual_job(user, data)`
riserva quota/credito (`MANUAL_JOB_DAILY_LIMIT = 3`,
`PRICE_MANUAL_JOB_EXTRA` — nuova variabile d'ambiente, default 0.50 come
l'import), crea il `Job` con `source=MANUAL`, `origin=IMPORTED` (compare
quindi nella sezione Importati, stesso filtro già esistente), poi chiama
`score_job(job)` — stesso trattamento post-creazione dell'import da
LinkedIn: scoring subito, **nessuna generazione automatica di CV** anche
con punteggio alto (sempre manuale, come per l'import).

`external_id`: nessun link/offerta esterna da cui derivarlo come per
LinkedIn — generato come `manual-<uuid4>`, sufficiente a soddisfare il
vincolo di unicità `(user, source, external_id)`.

**Nessuna verifica di piano**: a differenza dell'import da LinkedIn
(riservato al piano Pro), la creazione manuale è disponibile sia su Free
sia su Pro, come richiesto esplicitamente.

### API
Nuovo `ManualJobCreateSerializer` (`serializers.py`): valida i campi
obbligatori (titolo, azienda, località, descrizione, `published_at`) e
quello opzionale (`apply_url`), con messaggi di errore per campo già
parlanti di default (DRF). Nuova `CreateManualJobView` su
`POST /api/jobs/manual/`: 201 con `{job_id, status, score}` se creato,
409 con `{detail}` se il massimale/credito è esaurito, 400 con gli errori
di validazione DRF se un campo obbligatorio manca.

### Frontend
- `CityOnlyAutocomplete` riusato per il campo località (stessa logica di
  autocomplete già usata per esperienze/istruzione del profilo, Sprint
  34) — un solo campo, il paese non è un campo separato sul modello Job.
- Nuovo pulsante "Aggiungi manualmente" nella sezione Importati
  (`JobListPage.jsx`), visibile su entrambi i piani, indipendente dal
  form di import da LinkedIn (che resta Pro-only). Apre un `Dialog` con
  titolo, azienda, località (autocomplete), descrizione (textarea),
  data/ora di riferimento (`<input type="datetime-local">` → inviato come
  stringa ISO, interpretata dal backend nel timezone di progetto
  `Europe/Rome`), link di candidatura opzionale.
- Errori di validazione mostrati con il dettaglio per campo
  (`formatApiErrorDetail`, già introdotto Sprint 36), non un messaggio
  generico.
- Nuove chiavi di traduzione `jobs.addManualJob*`/`jobs.manualJob*` (it/en).

### Verifica eseguita
- `python manage.py test`: 194/194 passati (10 nuovi test in
  `apps/jobs/tests.py`: creazione su piano Free, `apply_url` opzionale,
  unicità `external_id`, massimale giornaliero con e senza credito,
  contatori separati da `import_count`, endpoint API con successo e con
  campo obbligatorio mancante).
- `makemigrations --check --dry-run`: pulito.
- `npm run build`: pulito.
- Verifica end-to-end reale (Django test client contro il container di
  produzione, non solo unit test): `POST /api/jobs/manual/` → `201`, job
  creato con punteggio, visibile correttamente in
  `GET /api/jobs/?section=imported` con `published_at` nel timezone
  corretto. Utente di test creato per la verifica, eliminato subito dopo.

### Cosa manca
- Nessun punto aperto sulla richiesta. Resta valida la nota sulla
  documentazione retroattiva mancante per gli Sprint 40-42 (sopra).
