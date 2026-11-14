# Sprint 46 — Filtri della lista job, Preferiti, pagine Profilo/Impostazioni, candidati e recruiter

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 09/09/2026 – 22/09/2026 · **Commit:** `cf8a93c` (22/09, **senza numero di sprint**: "Filtri lista job, sezione Preferiti, pagina Profilo, candidati/recruiter"), attribuito qui perché:
> - il commento `Sprint 46` del codice (`FavoriteJobView`/`UnfavoriteJobView` in `apps/jobs/views.py`) cade proprio su questo lavoro;
> - il commit successivo `bf9a17a` ("Sprint 46") riporta nel titolo "filtri lista job, sezione Preferiti".
>
> Il diff di `bf9a17a` però contiene solo il refactor gap filling, descritto in `sprint-44.md` (numerato 44 nel codice). Nel codice questo lavoro è citato quasi sempre come "sprint corrente" (`list_service.py`, `models.py`, `tasks.py`, `scoreItems.js`). Riconciliazione completa in `sprint-44.md`.

## Input
Sessione `ed44ecc2` (richieste dell'utente):
- **09/09**:
  1. filtri per paese, città e data di importazione;
  2. data di importazione piccola e discreta su card e dettaglio;
  3. motivazione del punteggio tre volte più corta; match e gap brevissimi, con la possibilità di espandere la motivazione;
  4. nella card, i primi 4 gap al posto della motivazione;
  5. "Vai all'annuncio" e "Segna candidatura fatta" anche senza CV generato. Nessun obbligo di rifare i job già raccolti.
- **15/09**:
  1. sezione "Preferiti" subito dopo gli Importati, con un cuoricino a sinistra del punteggio su card e dettaglio;
  2. rinominare "Account" in "Impostazioni"; nuova pagina "Profilo" dopo Jobs (la modifica profilo già esistente); togliere il pulsante "Modifica profilo" dalle Impostazioni e "Torna all'account" dal Profilo.
- **16/09**: i job delle ricerche di due città svizzere non comparivano in lista. Poi:
  1. numero di candidati su card e dettaglio, ben evidente sotto i 25, e filtro per fasce;
  2. icona del recruiter quando c'è il nome, e filtro binario con/senza recruiter.
- **22/09**: "Raccolta già in corso per questo account" senza alcuna raccolta attiva.

## Decisioni prese
Risposte dell'utente alle domande dell'assistente:
- **Location**: un unico filtro testuale sul campo `location` esistente, invece di paese e città separati. A differenza della ricerca testuale principale, deve combinarsi in AND con gli altri filtri.
- **Data**: un unico filtro "intervallo di date" che **sostituisce** i pulsanti periodo (oggi/settimana/mese/tutti). Di default contiene solo la data di oggi.
- **Motivazioni match/gap**: un **unico pulsante globale** "Espandi motivazioni", non uno per riga.
- **Etichetta Genera/Rigenera CV**: basata sull'esistenza reale di un CV (`cv_pdf_url`), non sullo stato.
- **Preferiti + archivio**: un job preferito e poi archiviato compare **solo in "Archiviati"**: il flag resta, ma il job esce da "Preferiti".
- **URL**: cambiato anche l'URL, da `/account` a `/settings`. "Impostazione" è stato normalizzato in "Impostazioni".
- **Nessun limite o quota sui preferiti**.
- **Cap di raccolta**: invece di rendere equo il tetto tra le ricerche, l'utente ha chiesto di **eliminare i tetti** (le chiamate Apify sono comunque pagate). Resta solo il limite di 150 risultati per chiamata. Reintegrare i job di ieri e oggi scartati dal cap.
- **Guardia raccolta**: timeout di sblocco a **2 ore** (l'assistente proponeva 30 minuti).

## Implementazione

### Modello dati
- `Job.is_favorite` (`BooleanField`, default `False`): migrazione `jobs/0009_job_is_favorite`.
- `Job.applicants_count` (intero, nullable), `Job.applicants_bucket` (`ApplicantsBucket`: `under_25` / `over_200`, vuoto se assente), `Job.recruiter_name`, `Job.recruiter_profile_url`: migrazione `jobs/0010_job_applicants_and_recruiter`. Count e bucket non sono mai valorizzati insieme.
- `User.collection_started_at` (DateTime, nullable): migrazione `accounts/0006_user_collection_started_at`.
- `Job.discarded_by_cap` resta sul modello come campo storico, non più impostato da nessun percorso.

### Backend
- `apps/jobs/list_service.py`:
  - `SECTION_FILTERS` acquisisce `"favorites": Q(is_favorite=True, is_archived=False)`;
  - `_apply_date_range_filter(date_from, date_to)` su `date_collected`, nel fuso dell'utente, estremi inclusi; sostituisce `PERIOD_CHOICES`/`_apply_period_filter`;
  - `_apply_location_filter` (`location__icontains`);
  - `APPLICANTS_RANGES = ("under_25", "25_50", "51_100", "101_200", "over_200")` con `_apply_applicants_filter` (OR tra fasce; gli estremi includono anche il bucket testuale);
  - `_apply_recruiter_filter` (con o senza `recruiter_name`);
  - `favorite_job`/`unfavorite_job`.
  - Tutti questi filtri sono ignorati quando è attiva la ricerca testuale `q`.
- `apps/jobs/sources/apify_linkedin.py`:
  - `_parse_applicants_count` su `applicationsCount`: intero puro, "first 25" ⇒ `under_25`, "Over 200" ⇒ `over_200`;
  - `posterFullName`/`posterProfileUrl` ⇒ recruiter. Per l'import da link (pagina pubblica di LinkedIn) questi campi restano vuoti.
- `apps/jobs/ai_scoring.py`:
  - `score_match`/`score_gaps` diventano oggetti `{label, reason}` (`_SCORE_ITEM_SCHEMA`);
  - regola 5: `score_reasoning` al massimo due frasi, circa 40 parole;
  - regola 6: `label` cortissima, `reason` di una frase.
  - I job già scorati restano nel vecchio formato stringa: la UI gestisce entrambi.
- `apps/jobs/application.py`: `mark_application_done` non richiede più lo stato `cv_generated`; rifiuta solo un job già `application_done`. È una deviazione voluta da §4.10.
- `apps/jobs/collection.py`: rimosso `COLLECTION_LIMITS` (50 Free / 100 Pro job per notte), `source.fetch(..., limit=None)`. Eliminato `apps/jobs/intake.py` (`INTAKE_CAP = 15`, `apply_intake_cap`). `tasks.run_nightly_cycle_for_user` fa ora raccolta → scoring e restituisce `kept = scored`.
- `apps/jobs/tasks.py`:
  - `COLLECTION_STALE_AFTER = timedelta(hours=2)`: un `collection_in_progress=True` più vecchio di 2 ore, o senza `collection_started_at`, è considerato stantio e non blocca;
  - il `finally` azzera entrambi i campi.
- `apps/jobs/stats.py`: tolto il filtro `discarded_by_cap=False`.
- `apps/cv/enrichment.py` (poi eliminato con il gap filling): il salvataggio dei bullet sul profilo avviene **dopo** la generazione, non prima. Bug di bullet duplicati nel PDF, corretto il 15/09 nella sessione `49768ee2`.
- `CLAUDE.md`: aggiornata la riga sulla fonte offerte (nessun tetto di piano, resta `MAX_ITEMS_PER_CALL=150`).

### API
- `GET /api/jobs/`:
  - nuovi parametri `section=favorites`, `date_from`/`date_to` (`YYYY-MM-DD`), `location`, `applicants` (CSV di `APPLICANTS_RANGES`), `recruiter` (`yes`/`no`/`all`);
  - rimosso `period`.
- `POST /api/jobs/<id>/favorite/` e `POST /api/jobs/<id>/unfavorite/` (`FavoriteJobView`/`UnfavoriteJobView`) restituiscono il `JobSerializer`.
- `JobSerializer`: nuovi campi `is_favorite`, `applicants_count`, `applicants_bucket`, `recruiter_name`, `recruiter_profile_url`.
- `POST /api/jobs/<id>/mark-application-done/`: ora accetta anche job `new` senza CV; 409 solo se già fatto.

### Frontend
- `App.jsx`:
  - la Topbar diventa Home, Jobs, **Profilo** (`/profile`), **Impostazioni** (`/settings`, sempre `AccountPage`);
  - la route `/account` è rimossa, senza redirect.
- `AccountPage.jsx`: rimosso il pulsante "Modifica profilo". `ProfilePage.jsx`: rimosso il link "Torna all'account".
- `JobListPage.jsx`:
  - sezioni `main`/`imported`/`favorites`/`archived`;
  - campi data "Dal"/"Al" (default oggi–oggi) con link "Tutte le date";
  - campo location con debounce di 300 ms;
  - pulsanti multi-selezione per le fasce di candidati e una `Select` Recruiter (Tutti/Con/Senza);
  - cuoricino con aggiornamento ottimistico (in "Preferiti", togliere il cuore rimuove subito la card).
- `JobCard.jsx`:
  - badge candidati (verde e in grassetto sotto i 25);
  - icona `UserRound` per il recruiter, cliccabile verso il profilo se c'è l'URL, con tooltip "Annuncio pubblicato da: …";
  - riga "Importato: <data breve>";
  - cuoricino `Heart` a sinistra del punteggio;
  - primi 4 gap (solo etichetta) al posto della motivazione;
  - etichetta Genera/Rigenera basata su `cv_pdf_url`.
- `JobDetailPage.jsx`:
  - stessi badge, icona, data e cuoricino;
  - pulsante globale "Espandi motivazioni"/"Nascondi motivazioni";
  - "Vai all'annuncio" e "Segna candidatura fatta" visibili anche senza CV ("Segna" nascosto se lo stato è già `application_done`).
- Nuove utility: `utils/applicants.js` (`applicantsLabel`, `isLowApplicants`), `utils/date.js` (`formatShortDate`, `todayInputValue`), `utils/scoreItems.js` (`scoreItemLabel`, `scoreItemReason`, compatibili con il vecchio formato stringa).
- `api/jobs.js`: `fetchJobs` con `dateFrom`, `dateTo`, `location`, `applicantsRanges`, `hasRecruiter`; `favoriteJob`/`unfavoriteJob`.
- i18n (it/en): `jobs.section_favorites`, `jobs.empty_favorites`, `jobs.applicants*`, `jobs.recruiter*`, `jobs.dateFromLabel`/`dateToLabel`/`dateRangeAll`, `jobs.expandReasons`/`hideReasons`, `jobs.importedOnPrefix`, `profile.navLink`; `account.navLink` = "Impostazioni"/"Settings".

## Verifica
Dalla sessione `ed44ecc2`:
- **15/09**: backend 104/104 test (container usa e getta, con `DJANGO_DEBUG=true` solo per i test, per evitare i 301 di `SECURE_SSL_REDIRECT`), `vite build` pulito. Deploy con `docker-compose.prod.yml` e migrazione `0009` applicata; il bundle servito in produzione contiene "Preferiti" e "Impostazioni".
- **16/09**: suite completa 217/217, build pulito, `makemigrations --check` senza differenze, deploy verificato.
- **22/09**: 220/220 (4 nuovi test sulla guardia stantia), deploy; migrazioni `accounts.0006`, `jobs.0009`, `jobs.0010` verificate come applicate.
- Test nuovi in `apps/jobs/tests.py` e `apps/jobs/sources/tests.py`:
  - parsing di candidati e recruiter;
  - assenza di cap;
  - intervallo di date nel fuso dell'utente;
  - location in AND e case-insensitive, ignorata con `q`;
  - fasce di candidati in OR;
  - recruiter sì/no;
  - Preferiti che esclude gli archiviati;
  - `FavoriteJobApiTests`;
  - candidatura senza CV.
- e2e (`frontend/e2e/job-list.spec.js`): link annuncio e candidatura senza CV, espandi motivazioni, filtro location, badge candidati, icona recruiter, filtri candidati e recruiter, cuoricino e sezione Preferiti. Gli e2e su `/account` sono aggiornati a `/settings`. L'esecuzione degli e2e non è documentata.

## Note / cosa manca
Operazioni sui dati fatte in sessione, non riproducibili dal codice:
- reintegrati 267 job di due giorni rimettendo `discarded_by_cap=False`; i circa 988 più vecchi sono stati lasciati marcati;
- una raccolta Apify straordinaria per un utente, limitata alle ricerche in Svizzera (264 job creati e scorati);
- due sblocchi manuali di `collection_in_progress`;
- l'azzeramento di un contatore `collection_count`.

Note sul codice:
- **Nessun filtro su `discarded_by_cap` nella lista**: in tutto lo storico git `list_service.py` non ha mai escluso questi job. Oggi quindi anche i job storici marcati compaiono in lista e nelle statistiche Home. Questo contrasta con il commento in `intake.py` ("mai visibili") e con il reintegro fatto il 16/09: incongruenza non risolvibile dalle fonti.
- Il lavoro era rimasto per settimane fuori da git (il deploy builda dalla working directory). È stato committato solo il 22/09 su richiesta dell'utente.
- "Paese" e "città" separati non esistono: il filtro location è una sottostringa su un campo testo libero.
- Il titolo della pagina Impostazioni resta `account.title` = "Il tuo account" / "Your account".
- La specifica funzionale non è aggiornata su:
  - §4.4: tetti 50/100 e cap di 15;
  - §4.5: sezioni, filtri periodo, nessun preferito;
  - §4.10: candidatura solo dopo il CV.
  - Dettaglio nel resoconto as-is dell'area lista job.
