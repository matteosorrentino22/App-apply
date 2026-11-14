# Sprint 45 — Scoring più accurato e parallelo, fix della raccolta manuale

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 23/08/2026 – 08/09/2026 · **Commit:** `d0c536f` (08/09, "Sprint 45: statistiche Home, scoring più accurato e più veloce, fix raccolta manuale"). Commit **cumulativo e di recupero**: riunisce lavoro di più sessioni rimasto fuori da git, perso per un `git reset` e ripristinato da uno stash orfano. Le statistiche Home e la navigazione dello stesso commit sono numerate **Sprint 44** nei commenti del codice e sono descritte in `sprint-44.md`; qui resta il resto del commit. Tabella di riconciliazione completa in `sprint-44.md`.

## Input
Fonte: riassunto dei messaggi utente della sessione principale del periodo (cancellata).
- **23/08**: migliorare scoring, match/gap e spiegazione. Su tre opzioni proposte, l'utente ha scelto di fare le prime due; poi ha chiesto di rifare lo scoring dei job dell'ultima settimana.
- **07–08/09**: dopo una raccolta manuale non tutti i job ricevevano il punteggio. Richiesto: timeout a 30 minuti, più worker, scoring in parallelo anche per lo stesso utente.

## Decisioni prese
- Lo scoring deve agganciare match e gap a requisiti **espliciti** nel testo dell'offerta; con descrizione vuota o segnaposto, liste vuote e punteggio prudenziale.
- Il modello deve ricevere il profilo **completo** (prima mancavano istruzione, certificazioni e lingue, causa nota di falsi gap su competenze già presenti).
- Le opzioni 1 e 2 su 3 corrispondono, per quanto ricostruibile, alle due modifiche sopra; la terza opzione scartata non è ricostruibile.
- Parallelismo con un pool di thread **solo sulle chiamate di rete** a Bedrock: nessun accesso ORM dai thread, il salvataggio resta sul thread principale.
- Gunicorn: `--timeout 1800` (30 minuti, come richiesto) e `--workers 4` (prima 3).

## Implementazione

### Backend
- `apps/jobs/ai_scoring.py`:
  - `SCORING_SYSTEM_PROMPT` con "Regole vincolanti" 1–4: ogni voce riferita a un requisito esplicito; descrizione non valutabile ⇒ `score_match`/`score_gaps` vuoti e punteggio prudenziale (allora "non superiore a 3" su scala 1–5, oggi "non superiore a 6" su 1–10); nessuna competenza inventata; nessun gap su elementi già presenti nel profilo.
  - `_build_profile_summary` aggiunge istruzione, certificazioni e lingue (etichette da `apps.profiles.language_options`).
- `apps/jobs/scoring.py`:
  - `SCORING_CONCURRENCY = 5`, `ThreadPoolExecutor` in `score_jobs`; `_score_call` (solo chiamata Bedrock), `_apply_score_result`, `_log_scoring_failure`;
  - profilo caricato una sola volta per utente con `prefetch_related` su `_PROFILE_PREFETCH = ("experiences", "skills", "educations", "certifications", "languages")`;
  - un fallimento su un job non blocca gli altri (`RunLog` di tipo `scoring`, `failure`).
- `apps/jobs/tasks.py`:
  - `run_manual_collection_for_user` cattura `(Exception, SystemExit)`: `SystemExit` è ciò che gunicorn solleva al timeout del worker; senza catturarlo la richiesta moriva senza `RunLog` né restituzione della quota, e i job restanti restavano senza punteggio;
  - in caso di fallimento: `_refund_collection_quota`, `RunLog` di fallimento, `ManualCollectionFailed`; il `finally` rilascia `collection_in_progress`.
  - **Rimossa la generazione automatica dei CV nel ciclo notturno** (`AUTO_GENERATION_SCORE_THRESHOLD`, `_generate_automatic_cv`): `run_nightly_cycle_for_user` fa ora raccolta → scoring → cap; il messaggio del commit non lo cita, vedi Note.

### Infrastruttura
- `docker-compose.prod.yml`, servizio `web`: `gunicorn ... --workers 4 --timeout 1800` (prima `--workers 3`, senza `--timeout`), con commento esplicativo.

### Altro contenuto del commit (fuori area, per completezza)
- `apps/cv/cv_parameters.py`: `BULLET_BUDGET_BY_EDU_COUNT` da `{1: 12, 2: 10, 3: 9}` a `{1: 18, 2: 16, 3: 14}`, con commento "Sprint 43". Fatto il 23/08 nella sessione `49768ee2` su un CV troppo corto.
- `cv_template.html`: `{% ifchanged exp.company %}`, così il nome dell'azienda non si ripete per due ruoli consecutivi nella stessa azienda.
- Raccolta manuale dalla Home (endpoint, guardia, quota): vedi `sprint-44.md`.

## Verifica
- Test aggiunti in `apps/jobs/tests.py`:
  - `test_batch_scoring_runs_calls_concurrently` (blocca un ritorno allo scoring sequenziale: commento "Sprint 45");
  - `NoAutomaticCvGenerationInNightlyCycleTests`;
  - `RunManualCollectionForUserTests`: guardia, quota, refund, fallimento della fonte;
  - `CollectJobsApiTests`: 200, 409 per raccolta in corso, 409 per secondo tentativo nello stesso giorno.
- Esito dell'esecuzione della suite al momento del commit: non documentato, la sessione è cancellata.
- Il ri-scoring dei job dell'ultima settimana (23/08) è un'operazione sui dati senza traccia nel repository: non verificabile.
- La sessione `49768ee2` riporta per la modifica al budget bullet: 50/50 test `apps.cv`, rigenerazione di prova, verifica via Caddy.

## Note / cosa manca
- La **rimozione della generazione automatica del CV** è un cambio funzionale rilevante: contraddice §4.7/§4.6 di `01-specifiche-funzionali-v4.md` e §5.1 punto 4 di `02-specifiche-tecniche-v3.md`, e anche `CLAUDE.md` ("genera automaticamente un CV"). Non è citata nel messaggio del commit, non ha un numero di sprint e non c'è la richiesta utente originale. Data e motivazione non ricostruibili.
- Il commento di `docker-compose.prod.yml` cita un timeout di 120 s "osservato in produzione", ma la versione precedente su git non aveva `--timeout`: probabile valore intermedio mai committato.
- Il commento su `score_jobs` citava `apply_intake_cap`, poi rimosso nello Sprint 46: commento aggiornato più tardi.
- I timeout molto alti (30 minuti) restano necessari perché la raccolta manuale scora **in sincrono dentro la richiesta HTTP**, non in un task Celery. Rischio residuo noto: un deploy o riavvio durante la raccolta lascia bloccato `collection_in_progress`. È stato corretto nello Sprint 46 con un timeout di 2 ore sulla guardia.
