# Sprint 44 — Home con statistiche e navigazione a schede; "colma i gap" al posto dell'arricchimento

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 28/08/2026 (Home/statistiche/navigazione) e 23/09/2026 (gap filling) · **Commit:** nessun commit intitolato "Sprint 44". Il lavoro è finito in `d0c536f` ("Sprint 45", 08/09: Home e statistiche), `bf9a17a` ("Sprint 46", 28/09: backend gap filling) e `d0faa0d` ("Sprint 47", 28/09: pannello gap in `JobDetailPage.jsx`). La scheda segue la **numerazione dei commenti nel codice** (`Sprint 44` in `apps/jobs/stats.py`, `apps/jobs/views.py`, `apps/cv/gap_filling.py`, `apps/cv/models.py`, `apps/cv/migrations/0004_rename_enrichment_used.py`, `docker-compose.prod.yml`), non quella dei commit.

## Riconciliazione della numerazione (Sprint 44–47)

Più sessioni hanno lavorato in parallelo o in tempi diversi, ciascuna numerando a partire dall'ultimo sprint che conosceva. Risultato:

| Contenuto | Quando | Commit (titolo) | N. nei commenti del codice |
|---|---|---|---|
| Home: statistiche, voce "Jobs" in Topbar | 28/08 | `d0c536f` (Sprint 45) | 44 |
| Home: pulsante "Raccogli ora" (raccolta manuale) | 28/08 (data migrazioni) | `d0c536f` (Sprint 45) | nessuno |
| Timeout gunicorn per generazione CV/cover letter | ≤ 28/08 | mai committato a sé (vedi Note) | 44 |
| Gap filling (sostituisce l'arricchimento) | 23/09 | `bf9a17a` (Sprint 46) + `d0faa0d` (Sprint 47) | 44 |
| Scoring più rigoroso, scoring parallelo, fix raccolta manuale | 23/08 – 08/09 | `d0c536f` (Sprint 45) | 45 → **sprint-45.md** |
| Filtri lista, Preferiti, Profilo/Impostazioni, candidati/recruiter | 09/09 – 22/09 | `cf8a93c` (senza numero) | 46 (Preferiti) → **sprint-46.md** |
| Scoring 1–10 | 28/09 | `d0faa0d` (Sprint 47) | 46 (`ai_scoring.py`, `models.py`, `scoreStyle.js`) |

## Input
- **28/08** (sessione principale del periodo, cancellata — fonte: riassunto dei messaggi utente): aggiungere la sezione "Jobs" nella barra in alto accanto a Home e Account, togliere il pulsante "torna alla lista" dalla pagina Account, rendere più curati i pulsanti di navigazione. Poi: statistiche in Home — job trovati oggi / ultima settimana / totali "di cui x manualmente", idem per CV creati e candidature, più altre metriche a scelta. Infine: cancellare tutti i CV dal DB per ripartire con metriche pulite (operazione sui dati, nessuna traccia nel codice).
- **23/09** (sessione `49768ee2`): prima di generare un CV, l'utente deve poter selezionare uno o più gap trovati dallo scoring (numerati) e scrivere un'indicazione opzionale su come inserirli; senza indicazione il modello usa un default basato sul profilo. Deve **sostituire** la funzione di arricchimento (aggiunta di un'esperienza/bullet durante la generazione). Obiettivo dichiarato: massimo match con l'offerta, con contenuti anche "amplificati", sempre legati al contesto reale del profilo.

## Decisioni prese
- **Statistiche**: tre metriche (job trovati, CV generati, candidature fatte) × tre periodi (oggi, ultima settimana, totali); sotto-dato "di cui manuali" solo per i job. "Altre metriche" chieste dall'utente: nessuna ulteriore risulta implementata.
- **Navigazione**: barra a pillole (`NavLink` con stile `primary` se attivo, `ghost` altrimenti) al posto del singolo link "Account".
- **Gap filling** (risposte dell'utente alle domande del 23/09):
  - accesso **opzionale e collassabile** ("Colma i gap…"), non popup a ogni "Genera CV": il pulsante principale resta un click diretto;
  - si colmano solo **contenuti narrativi** (bullet di esperienze reali, aree di competenza), mai nuove certificazioni/titoli/strumenti certificati, mai un datore di lavoro o ruolo inesistente;
  - il contenuto prodotto **non viene mai salvato nel profilo master** (vale solo per quella generazione);
  - al modello si invia `label (reason)` di ogni gap selezionato, non solo l'etichetta.
- Rimossa interamente la vecchia infrastruttura di arricchimento (endpoint, serializer, bullet "protetti" nel budget di selezione).

## Implementazione

### Modello dati
- `CVDocument.enrichment_used` → rinominato `extra_instructions_used` (migrazione `cv/0004_rename_enrichment_used`, solo `RenameField`, dati storici conservati).
- Nessun nuovo campo per le statistiche (calcolate a richiesta).

### Backend
- Nuovo `apps/jobs/stats.py` → `get_home_stats(user)`: per ogni metrica `{today, week, total}`.
  - "oggi" = da mezzanotte nel fuso dell'utente (`_local_today_start`, da `list_service.py`); "settimana" = ultimi 7 giorni mobili (`now - 7 giorni`); "totali" = tutto.
  - job: `Job` dell'utente su `date_collected`; `manual` = sottoinsieme `origin=imported` (comprende sia l'import da link sia la creazione manuale dello Sprint 43);
  - CV: `CVDocument` dell'utente su `generated_at`;
  - candidature: `Job` con `status=application_done` su `date_application_done`.
  - Nella versione di `d0c536f` i job con `discarded_by_cap=True` erano esclusi; il filtro è stato tolto con `cf8a93c` (Sprint 46, rimozione del cap).
- Nuovo `apps/cv/gap_filling.py` → `build_extra_instructions(gaps, instructions)`: funzione pura che compone il testo `GAP DA COLMARE PER QUESTA OFFERTA` (lista numerata) + `ISTRUZIONI DEL CANDIDATO…` (o `DEFAULT_GAP_INSTRUCTION`); con sole istruzioni e nessun gap produce un'indicazione generica, senza l'eccezione al grounding.
- `apps/cv/ai_content.py`: nuovo paragrafo "GAP DA COLMARE" nel system prompt; parametro `enrichment` → `extra_instructions` in `generate_cv_content`, `generation.generate_cv`, `manual_generation.request_manual_cv_generation`.
- Rimossi: `apps/cv/enrichment.py`, `apps/cv/serializers.py` (`CvEnrichmentSerializer`), la logica `protected_bullets`/`protected_experience_id` in `selection.py`/`generation.py`. Dettaglio della pipeline CV: vedi le schede/resoconti dell'area CV.

### API
- `GET /api/jobs/stats/` (`HomeStatsView`) → `{"jobs": {today, week, total, manual: {today, week, total}}, "cvs": {...}, "applications": {...}}`.
- `POST /api/jobs/<id>/generate-cv/` (`GenerateCvView`) accetta ora `gaps` (lista di stringhe) e `gap_instructions` (testo).
- Rimosso `POST /api/jobs/<id>/enrich-and-generate-cv/` (`EnrichAndGenerateCvView`).

### Frontend
- `App.jsx`: componente `NavItem` + `Topbar` con voci Home (`/home`), Jobs (`/list`), Account (`/account`); nuova route protetta `/home`. (Le voci Profilo e Impostazioni arrivano nello Sprint 46.)
- Nuova `pages/HomePage.jsx`: titolo, sezione "Le tue statistiche" con tre `StatsCard` (icone `Briefcase`, `FileText`, `Send`), ognuna con tre colonne oggi/ultima settimana/totali e, per i job, la riga "di cui manuali". Sotto, card "Raccogli nuovi job" con pulsante "Raccogli ora" (raccolta manuale, vedi Note).
- `AccountPage.jsx`: rimosso il link "← Torna alla lista".
- `api/jobs.js`: `fetchHomeStats()`, `collectJobs()`; `generateCv(id, gaps, gapInstructions)` al posto di `generateCv(id)` + `enrichAndGenerateCv(...)`.
- `JobDetailPage.jsx` (commit `d0faa0d`): blocco collassabile "Colma i gap trovati per questa offerta prima di generare" con checkbox numerate sui `score_gaps`, textarea facoltativa, avviso dell'indicazione di default se ci sono gap selezionati ma nessun testo.
- i18n (it/en): chiavi `home.*`, `jobs.navLink`; `jobs.gapPanel*`/`jobs.gapInstructions*` al posto di `jobs.enrichment*`.

## Verifica
- Statistiche/navigazione: la sessione che le ha sviluppate è stata cancellata, nessun esito di test documentato. Nel codice attuale **non esistono test** su `get_home_stats` né su `/api/jobs/stats/`.
- Gap filling (sessione del 23/09): suite `apps.cv`/`apps.jobs` verde salvo circa 20 fallimenti "ambientali preesistenti" (così riportati, non dettagliati); build frontend pulita; prova reale di generazione su un job vero con 3 gap selezionati e nessuna indicazione: il modello ha amplificato esperienze reali senza inventare aziende o ruoli; bundle verificato in produzione.

## Note / cosa manca
- **Commit di recupero, non contestuali**: Home e statistiche sono entrate su git solo l'08/09 (`d0c536f`, ripristinato da uno stash orfano dopo un `git reset`); il backend del gap filling solo il 28/09 (`bf9a17a`, "non rivisto riga per riga"). Il titolo di `bf9a17a` cita anche "filtri lista job, sezione Preferiti", ma il diff contiene solo il gap filling: quei filtri sono in `cf8a93c`.
- **Build frontend rotta tra `bf9a17a` e `d0faa0d`**: in `bf9a17a` `JobDetailPage.jsx` importa ancora `enrichAndGenerateCv`, già tolto da `api/jobs.js`; la pagina è stata allineata 16 secondi dopo in `d0faa0d` (Sprint 47).
- **Raccolta manuale dalla Home** (`CollectJobsView`, `POST /api/jobs/collect/`, `run_manual_collection_for_user`, `User.collection_in_progress` migrazione `accounts/0005`, `DailyQuota.collection_count` migrazione `jobs/0008`, `COLLECTION_DAILY_LIMIT = 1`): nasce nello stesso giorno (28/08, date delle migrazioni) ed è nella stessa pagina, ma **nessun commento la numera**. La metto qui per vicinanza; la correzione (SystemExit, timeout) è nello Sprint 45.
- **Timeout gunicorn "Sprint 44"**: il commento in `docker-compose.prod.yml` parla di un rischio "già noto per la generazione CV/cover letter (Sprint 44)" e di un timeout a 120 s, ma nella versione precedente su git il comando gunicorn **non aveva `--timeout`** (default 30 s). È probabile che 120 s fosse un valore intermedio mai committato: non ricostruibile.
- La cancellazione di tutti i CV dal DB (28/08) è un'operazione sui dati, non verificabile dal repository.
- La specifica funzionale §4.8 (arricchimento) e il modello `CVDocument.enrichment_used` delle tecniche (§4.5) sono superati da questo sprint e non sono stati aggiornati.
