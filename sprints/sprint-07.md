# Sprint 07 — Fonte offerte (raccolta)

## Input
- Sprint 06 completato (ricerche attive disponibili); modello `Job` (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.3, §4.4; `02-specifiche-tecniche-v3.md` §5.1, §5.3, §11 punto 1.

## Obiettivo
Modulo interno con interfaccia unica ("offerte per queste ricerche, entro questa finestra, fino a questo limite") dietro cui gira l'integrazione Apify (actor LinkedIn), con limite 50 (Free)/100 (Pro) job/notte per utente, finestra 24h, filtro sui campi obbligatori, deduplica per `(user, source, external_id)`.

## Risultato atteso
Dato un utente con ricerche attive, un task/comando di raccolta popola `Job` con le offerte valide, rispettando il limite di piano e senza duplicati rispetto a job già mostrati.

## Criteri di verifica
- Con mock della risposta Apify che restituisce N offerte (N > limite di piano), l'esecuzione per un utente Free salva al massimo 50 `Job`, per un utente Pro al massimo 100.
- Un'offerta priva di uno tra `title`/`company`/`location`/`description`/`apply_url` non viene salvata (conteggio Job salvati < item del mock).
- Un'offerta senza `published_at` viene comunque salvata (`published_at` NULL in DB).
- Rieseguendo il task con lo stesso `external_id` già presente per l'utente, il conteggio Job resta invariato (nessun duplicato).
- Il token Apify è letto da variabile d'ambiente, non hardcoded nel codice (verifica statica).
- L'interfaccia pubblica del modulo non espone dettagli specifici di Apify al chiamante.

## Output per lo sprint successivo
Job raccolti e salvati per utente, pronti per lo scoring (Sprint 08).

---

## Esito (2026-07-26)

**Stato: completato**, con una riserva sulla mappatura esatta dei campi Apify (vedi Criticità).

### Cosa è stato fatto
- `apps.jobs.sources` — interfaccia unica sostituibile: `get_job_source()` ritorna l'istanza della fonte configurata (oggi `ApifyLinkedInSource`). Cambiare fonte in futuro significa sostituire questa funzione, senza toccare `collection.py`/scoring/CV.
- `apps.jobs.sources.apify_linkedin.ApifyLinkedInSource` — chiama l'actor Apify `cheap_scraper~linkedin-job-scraper` in modalità `run-sync-get-dataset-items` (`02-specifiche-tecniche-v3.md §5.3`), token letto da `settings.APIFY_API_TOKEN` (env, mai in query string) e passato come header `Authorization: Bearer`. Normalizza l'output grezzo dell'actor in dict con le chiavi attese da `collection.py` (`external_id`, `title`, `company`, `location`, `description`, `apply_url`, `published_at`, `salary`).
- `apps.jobs.collection.collect_jobs_for_user(user)` — interfaccia pubblica del modulo, **non** espone alcun dettaglio Apify: prende le ricerche attive dell'utente (`apps.searches.services.get_active_searches`, Sprint 06), applica nell'ordine il limite di piano job/notte (Free 50 / Pro 100 — enforcement lato nostro, non affidato al solo parametro passato alla fonte), il filtro sui 5 campi obbligatori (`title`, `company`, `location`, `description`, `apply_url`), e la deduplica per `(user, source, external_id)` (sia contro `Job` già in DB sia contro duplicati nello stesso batch). Ritorna la lista dei `Job` creati.
- Aggiunta `APIFY_API_TOKEN` a `config/settings.py` e `.env.example` (vuota in dev).
- Suite di test automatici (`apps/jobs/tests.py`, 6 test) con `get_job_source` mockato — disaccoppia i test dalla forma esatta della risposta Apify (vedi Criticità) e verifica solo la logica di raccolta/filtro/dedup/limite, che è ciò che lo sprint richiede.

### Criticità riscontrate
1. **Mappatura esatta dei campi della risposta Apify non verificabile in questo ambiente.** `_normalize_item` in `apify_linkedin.py` è una mappatura "best effort" sui nomi di campo più comuni per un job scraper (`title`, `company`/`companyName`, `applyUrl`/`jobUrl`/`link`, ecc.), scritta senza accesso alla documentazione live dell'actor `cheap_scraper~linkedin-job-scraper` né a un `APIFY_API_TOKEN` reale per un test end-to-end. **Da verificare e correggere con una vera chiamata di prova** non appena si dispone di credenziali Apify reali, prima di affidarsi alla raccolta in produzione. Non incide sui criteri di verifica dello sprint, che riguardano la logica di raccolta a valle della normalizzazione (testata mockando `get_job_source`, non l'HTTP reale verso Apify).
2. Nessun task Celery collegato ancora: lo sprint non lo richiede esplicitamente (`collect_jobs_for_user` è una funzione invocabile direttamente, come i criteri di verifica presuppongono con "un task/comando di raccolta"); l'orchestrazione schedulata arriva con Sprint 09.

### Verifica eseguita
`python manage.py test apps.jobs` (6/6) e `python manage.py test` sull'intero progetto (18/18, nessuna regressione); `makemigrations --check` pulito (nessun modello nuovo); verifica statica (`grep`) che nessun token Apify sia scritto nel codice.

| Criterio | Esito |
|---|---|
| Mock con N offerte > limite di piano → salvati al massimo 50 (Free) / 100 (Pro) | ✅ |
| Offerta priva di un campo obbligatorio non salvata | ✅ |
| Offerta senza `published_at` salvata comunque (`NULL`) | ✅ |
| Rieseguendo con lo stesso `external_id`, conteggio invariato (nessun duplicato) | ✅ |
| Token Apify da variabile d'ambiente, non hardcoded | ✅ (verifica statica) |
| Interfaccia pubblica non espone dettagli Apify | ✅ (per costruzione: `collect_jobs_for_user(user)` non ha parametri/ritorni specifici di Apify) |

### Cosa manca
- Verifica end-to-end reale contro l'API Apify (richiede token reale — vedi Criticità §1).
- Collegamento a un task Celery Beat schedulato: Sprint 09.
