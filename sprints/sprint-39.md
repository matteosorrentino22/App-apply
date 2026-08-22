# Sprint 39 — Ricerche divise Job Role / Company, chiamate Apify raggruppate e filtrate

## Input
Richiesta del committente: le ricerche salvate mischiano oggi ruoli
("Business analyst") e nomi di azienda/agenzia ("Robert Half", "UBS") nello
stesso campo `keywords`, cercati come testo libero. Vanno introdotti due tipi
di ricerca espliciti — **Job role keyword** e **Company** — e sfruttati due
campi dell'actor Apify (`cheap_scraper~linkedin-job-scraper`) oggi non usati:

1. `keyword` accetta un array: oggi si fa **una chiamata per ogni ricerca
   attiva** (fino a 50/utente su piano PRO); va fatta invece una chiamata per
   gruppo di ricerche omogenee, risparmiando sul costo Apify.
2. Per le ricerche di tipo Company, oltre a metterle in `keyword`, vanno
   messe anche in `companyInclude` (campo actor che risolve il nome in un ID
   azienda LinkedIn e filtra solo quelle aziende).
3. `maxItems=150` e `saveOnlyUniqueItems=true` su ogni chiamata, per
   limitare la spesa (verificato: 150 è il minimo fatturabile in pay-per-result
   per questo actor, quindi è il valore più economico possibile).

### Collegamento a un bug noto (sprint-23, "Bug 2")
Sprint 23 aveva già diagnosticato e lasciato aperto un problema di
selettività: cercando "UBS" come `keyword` testuale, l'actor tornava anche
offerte non pertinenti (es. "Fielmann Group", ottici) — mai risolto,
segnalato come "da investigare separatamente". Il campo `companyInclude`
(risoluzione per ID azienda, non full-text) è di fatto il fix di quel bug per
le ricerche di tipo Company.

## Nota sulla deviazione dalla specifica
CLAUDE.md, sezione "Cosa NON fare": *"Non introdurre filtri di ricerca oltre
keywords e location"*. Questo sprint introduce un nuovo filtro (tipo
ricerca + `companyInclude`), quindi è una deviazione esplicita rispetto
all'architettura decisa nelle specifiche tecniche — segnalata qui su
richiesta diretta del committente (2026-08-15). CLAUDE.md e
`01-specifiche-funzionali-v4.md` §4.4 vanno aggiornati a fine sprint per
riflettere la nuova architettura, non prima (per non documentare qualcosa
che potrebbe ancora cambiare in corso d'opera).

## Decisioni prese in fase di analisi (discusse col committente il 2026-08-15)
- **Raggruppamento chiamate**: niente prodotto cartesiano lato Apify (l'actor
  avrebbe un campo `locations` array che incrocia ogni keyword con ogni
  location, ma cambierebbe la semantica rispetto a oggi). Si raggruppano
  invece le ricerche attive per `(search_type, city, country)` e si fa **una
  chiamata per gruppo**. Nei dati reali osservati oggi (tutte le ricerche di
  un utente condividono la stessa città) questo significa 2 chiamate/utente/
  notte; se in futuro lo stesso utente avrà ricerche dello stesso tipo su
  città diverse, si avranno più di 2 chiamate per quell'utente — comunque
  sempre ≤ al numero di ricerche attive, mai peggio di oggi.
- **Limite piano FREE**: cambia da "1 ricerca attiva totale" a **1 job-role
  attiva + 1 company attiva** (fino a 2 attive contemporaneamente). È un
  cambio di quota, non solo tecnico — va riflesso in
  `01-specifiche-funzionali-v4.md` §4.4.
- **Limite piano PRO**: resta **50 attive in totale**, ma ora liberamente
  divisibili tra i due tipi (non 50+50).
- **Migrazione dati esistenti**: tutte le `SavedSearch` esistenti diventano
  `search_type='job_role'` di default in migrazione; le righe che sono in
  realtà aziende vengono corrette a mano dopo il deploy. Per l'utente 3
  (piano PRO, dati reali ispezionati il 2026-08-15) sono già identificate
  come Company: Darwin Recruitment, Robert Half, Approach People
  Recruitment, Experis, Nicoll Curtin, Helvetica Partners, Robert Walters,
  Hays, Michael Page, Swisslinx, Deloitte, UBS, Randstad, LHH. Restano
  Job role: "IT Project manager", "Business analyst".

## Scoperta durante l'implementazione: `companyInclude` da solo non basta
Il punto 2b della richiesta originale ("le company vanno messe sia in
`keyword` sia in `companyInclude`") è stato **verificato sperimentalmente e
smentito** con chiamate reali all'actor il 2026-08-15, prima di scrivere il
codice definitivo:

- `keyword=["UBS"]` + `companyInclude=["UBS"]` (stessa finestra, stessa
  location): 140 risultati totali, solo **35 davvero UBS** (il resto Julius
  Baer, Deloitte, EY, ecc.) — lo stesso identico problema di selettività di
  sprint-23 "Bug 2", non risolto.
- `keyword=["jobs"]` (termine neutro) + `companyInclude=["UBS"]`, stessa
  finestra: 37 risultati, **tutti e 37 davvero UBS**.

Causa: mettere il nome azienda anche in `keyword` fa scattare la ricerca
semantica di LinkedIn, che aggira il filtro `companyInclude`. Con un
`keyword` neutro, `companyInclude` filtra al 100%. Ulteriori test hanno
anche escluso una perdita di recall: a parità di finestra il neutro trova
*più* posizioni vere (37 contro 35), non meno — il numero più alto
dell'approccio "sporco" era quasi tutto rumore. Confermato anche con più
aziende insieme (`companyInclude=["UBS","Deloitte","Robert Half"]` +
`keyword=["jobs"]` → 66/66 risultati corretti).

**Decisione presa (confermata col committente)**: per le chiamate di tipo
Company, `keyword` usa un termine neutro fisso — `["jobs", "hiring"]`
(testato: unione dei due dà il miglior recall tra le combinazioni provate,
sempre al 100% di pertinenza) — mai i nomi azienda, che restano solo in
`companyInclude`. Effetto collaterale gestito: `searchString` (usato per
`Job.matched_search`, sprint-23 fix 4) varrebbe qui "jobs"/"hiring" invece
del nome azienda — sovrascritto con `companyName` dell'item prima della
normalizzazione, così il badge "ricerca di provenienza" resta corretto.

## Piano tecnico

### Backend — modello e piano
- `apps/searches/models.py`: nuovo campo `SavedSearch.search_type`
  (`CharField` con `choices`: `job_role`, `company`), migrazione con default
  `job_role` per le righe esistenti.
- `apps/searches/services.py`: `PLAN_LIMITS` ristrutturato — FREE:
  `max_saved=10`, limite attive **per tipo** (`job_role: 1`, `company: 1`);
  PRO: `max_saved=100`, limite attive **totale** `50` (nessun vincolo per
  tipo). `activate_search` applica la regola giusta in base al piano.
- `apps/searches/serializers.py`: aggiunto `search_type` ai `fields`.
- `apps/searches/views.py`: verificare in corso d'opera se
  `check_can_create`/`activate_search` richiedono modifiche di firma per
  ricevere `search_type`.

### Backend — raccolta Apify
- `apps/jobs/sources/apify_linkedin.py` (`ApifyLinkedInSource.fetch`):
  raggruppa le `searches` per `(search_type, city, country)`; per ogni
  gruppo costruisce un payload:
  - `keyword`: lista delle keyword del gruppo (job-role) — per i gruppi
    Company, un termine neutro fisso invece dei nomi azienda (vedi
    "Scoperta durante l'implementazione" più sotto)
  - `location`: stringa singola del gruppo (campo legacy, non serve
    l'array `locations` visto che ogni chiamata ha già una sola location)
  - se `search_type == 'company'`: `companyInclude` = lista delle aziende
    del gruppo
  - `publishedAt`: come oggi
  - `maxItems: 150`, `saveOnlyUniqueItems: true` — su **ogni** chiamata,
    entrambi i tipi
- Verifica empirica da fare prima di chiudere lo sprint: una chiamata reale
  con array multi-keyword deve confermare che `searchString` (già usato per
  `matched_search`, fix 4 sprint-23) continua a taggare ogni job con la
  keyword specifica che ha fatto match, anche con array più grandi — non
  documentato esplicitamente dallo schema dell'actor.
- `apps/jobs/collection.py`: nessun cambio di interfaccia
  (`source.fetch(searches, window_hours, limit)` resta uguale), il
  raggruppamento resta interno alla fonte.

### Frontend
- `frontend/src/pages/AccountPage.jsx`: selettore tipo ricerca ("Job role
  keyword" / "Company") nel form di creazione/edit; indicatori di quota
  separati per tipo per il piano FREE (dove il limite è per tipo, non
  condiviso).
- `frontend/src/api/searches.js`: `createSearch`/`updateSearch` passano
  anche `search_type`.

### Verifica
- Test esistenti su `ApifyLinkedInSourceTests` e `services.py` (piani) da
  aggiornare; nuovi test per: raggruppamento per (tipo, location), payload
  `companyInclude` presente solo su tipo company, `maxItems`/
  `saveOnlyUniqueItems` sempre presenti, limite FREE per tipo, limite PRO
  condiviso tra i due tipi.
- `makemigrations --check` pulito a fine sprint.
- Verifica manuale sull'utente 3 (dati reali già ispezionati) dopo il
  backfill manuale dei tipi.

## Esito (2026-08-15)
Implementato secondo il piano, con una correzione rispetto al punto 2b
originale emersa durante l'implementazione (vedi sezione dedicata sopra:
`keyword` neutro `["jobs", "hiring"]` per le chiamate Company, non i nomi
azienda, che restano solo in `companyInclude`).

- **Modello**: `SavedSearch.search_type` (`job_role`/`company`, default
  `job_role`), migrazione `0003_savedsearch_search_type` applicata.
- **Piani**: `services.PLAN_LIMITS` ristrutturato come pianificato — FREE
  con `max_active_per_type` (1+1), PRO con `max_active_total` (50
  condiviso). `activate_search` aggiornato di conseguenza; `views.py` non
  ha richiesto modifiche.
- **Apify**: `ApifyLinkedInSource.fetch` raggruppa per `(search_type, city,
  country)`; `maxItems: 150` e `saveOnlyUniqueItems: true` su ogni
  chiamata; `companyInclude` solo sulle chiamate Company con `keyword`
  neutro fisso; `matched_search` per i job Company ricostruito dal
  `companyName` reale dell'item (non da `searchString`, che varrebbe
  "jobs"/"hiring").
- **Frontend**: selettore Job role/Company (RadioGroup) nel form di
  creazione e in quello di edit inline di `AccountPage.jsx`; badge tipo
  sulla card di ogni ricerca; `api/searches.js` passa `search_type`;
  `OnboardingPage.jsx` crea sempre la prima ricerca come `job_role`
  (nessun selettore in onboarding, per non appesantire il flusso — scelta
  esplicita, non un'omissione).
- **Dati esistenti**: backfill manuale per l'utente 3 (PRO) — le 14 righe
  già identificate come azienda impostate a `search_type='company'`, le 2
  restanti (`IT Project manager`, `Business analyst`) restano `job_role`
  di default. Nessun'altra ricerca attiva superava i nuovi limiti dopo il
  backfill (12 company + 2 job_role attive, ben sotto il tetto Pro di 50
  condiviso).

### Verifica eseguita
- **Chiamate reali ad Apify** (non solo unit test, dato il rischio
  identificato nel piano):
  - `searchString` tagga correttamente ogni item con la keyword specifica
    anche con array multi-keyword (2 keyword, 150 risultati, distinti
    correttamente 18 vs 132 per le due keyword).
  - Selettività `companyInclude`: **confermato il problema del punto 2b**
    (35/140 pertinenti con nome azienda anche in `keyword`) e **confermata
    la correzione** (37/37, poi 66/66 con 3 aziende insieme, usando
    `keyword` neutro). Vedi sezione "Scoperta durante l'implementazione".
- **Test automatici**: 15 test nuovi/aggiornati su
  `apps.jobs.sources.tests` e `apps.searches.tests`, tutti verdi
  individualmente (verificato con `-v 2`). Suite completa del progetto
  (179 test): stessi 46 fallimenti + 3 errori preesistenti su **tutta**
  la suite (accounts, jobs, notifications, profiles, common, searches),
  tutti dello stesso tipo — redirect 301 lato `SecurityMiddleware`
  (`SECURE_SSL_REDIRECT=True` perché questo container gira con
  `DJANGO_DEBUG=false`, configurazione di produzione) su ogni test che usa
  `APIClient` per fare richieste HTTP reali, indipendentemente dall'app
  testata. Non è una regressione di questo sprint (riprodotto identico
  anche su `apps.accounts`, mai toccato) — non corretto qui, fuori scope:
  richiederebbe eseguire i test in un ambiente con `DJANGO_DEBUG=true` o
  un container di test separato, non allestito in questa sessione.
- `makemigrations --check --dry-run`: pulito.
- `npx vite build` sul frontend: pulito.
- `web`/`worker`/`beat` riavviati (worker/beat non hanno autoreload) per
  caricare il nuovo codice.

### Cosa manca
- I 46 fallimenti + 3 errori preesistenti (redirect 301, vedi sopra) non
  sono stati indagati a fondo né corretti: pre-esistono a questo sprint e
  non riguardano la raccolta Apify o le ricerche, ma andrebbero comunque
  segnalati/risolti separatamente per poter fidarsi della suite CI in
  futuro.
- Non osservato ancora un ciclo notturno reale con la nuova raccolta
  raggruppata (solo chiamate manuali di verifica) — da confermare al primo
  ciclo notturno utile che il raggruppamento e `companyInclude` si
  comportino come nei test manuali anche a piena scala (es. utente 3 con
  12 ricerche Company attive in un'unica chiamata).
