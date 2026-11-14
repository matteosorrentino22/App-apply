# Sprint 64 — Filtri preferiti salvabili nella lista job

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 20/10/2026 · **Commit:** `a181e90` ("Sprint 64: filtri preferiti salvabili nella lista job"). Nel codice questo lavoro è citato come "sprint corrente" (`JobFilterPreset` in `apps/jobs/models.py`, `MAX_JOB_FILTER_PRESETS` in `views.py`, `JobFilterPresetSerializer`): nessun commento lo numera esplicitamente.

## Input
Richiesta dell'utente (sessione `ed44ecc2`, 20/10):
- poter salvare una combinazione di filtri con un nome e riapplicarla rapidamente in qualsiasi momento (es. ricerca "X – città", stato "nuovo" + "CV generato", candidati "<25");
- l'intervallo di date non va mai salvato;
- se un valore salvato non esiste più (es. una ricerca eliminata), quel filtro non deve filtrare nulla, ma tutti gli altri valori salvati devono continuare a valere;
- applicare un preset copia i valori nei filtri del momento, che restano modificabili senza toccare il preset;
- prima di implementare, porre tutte le domande sulle criticità.

## Decisioni prese
Risposte dell'utente alle domande dell'assistente:
- Il preset contiene **solo i filtri, non la sezione** (Raccolti/Importati/Preferiti/Archiviati): si applica nella sezione corrente.
- UI a **pillole cliccabili**, ciascuna con una × per eliminarla.
- **Tetto tecnico di 50 preset per utente** (l'assistente proponeva 20), non legato al piano.
- **Nessuna rinomina**: si salva e si elimina; per cambiare nome si ricrea il preset.
- `search_ids` è JSON e non una FK: un id di una `SavedSearch` eliminata semplicemente non risolve a nulla, con la stessa logica di `_apply_matched_search_filter` introdotta nello Sprint 63.

## Implementazione

### Modello dati
- Nuovo `JobFilterPreset` (`apps/jobs/models.py`), migrazione `jobs/0015_jobfilterpreset`. `Meta.ordering = ["created_at"]`. Campi:
  - `user` (FK, `related_name="job_filter_presets"`);
  - `name` (`max_length=100`);
  - `scores`, `statuses`, `search_ids`, `applicants_ranges` (`JSONField`, liste);
  - `location` (testo);
  - `has_recruiter` (`""`, `"yes"` o `"no"`, gli stessi valori del parametro `recruiter`);
  - `created_at`.
- Nessun campo per le date.

### Backend
- `JobFilterPresetSerializer` (`apps/jobs/serializers.py`) valida:
  - nome non vuoto (dopo `strip`);
  - `scores` come lista di interi;
  - `statuses` ⊆ `FILTERABLE_STATUSES`;
  - `search_ids` come lista di `"none"` o di id numerici in forma di stringa;
  - `applicants_ranges` ⊆ `APPLICANTS_RANGES`;
  - `has_recruiter` ∈ {"", "yes", "no"}.
- `MAX_JOB_FILTER_PRESETS = 50` (`apps/jobs/views.py`).

### API
- `GET /api/job-filter-presets/`: elenco dei preset dell'utente (`JobFilterPresetListCreateView`).
- `POST /api/job-filter-presets/`: 201 con il preset creato; 409 `{detail}` oltre i 50; 400 per errori di validazione.
- `DELETE /api/job-filter-presets/<id>/`: 204; 404 se il preset è di un altro utente (`JobFilterPresetDeleteView`).

### Frontend
- `JobListPage.jsx`:
  - riga di pillole sotto la barra filtri, una per preset: un click chiama `applyFilterPreset`, che copia punteggio, stato, ricerca, location, candidati e recruiter, ma non le date; la × chiama `handleDeletePreset`, che rimuove la pillola in modo ottimistico e poi chiama l'API;
  - pulsante "Salva filtri attuali", che apre un `Dialog` con il campo Nome;
  - le pillole e il pulsante sono disattivati durante la ricerca testuale.
- `api/jobs.js`: `fetchFilterPresets`, `createFilterPreset`, `deleteFilterPreset`.
- i18n (it/en): `jobs.savePresetButton`, `deletePreset`, `savePresetDialogTitle`/`Hint`, `presetNameLabel`, `savingPreset`, `savePresetSubmit`, `savePresetError`.

## Verifica
Dalla sessione `ed44ecc2`:
- migrazione generata con Django dentro un container e poi copiata con `docker cp`;
- 7 nuovi test `JobFilterPresetApiTests`:
  - creazione con tutte le dimensioni tranne le date;
  - nome vuoto;
  - valori non validi;
  - isolamento per utente in elenco ed eliminazione;
  - tetto di 50;
- suite backend 234/234 (227 + 7), lint e build del frontend puliti, nessuna migrazione mancante;
- deploy con `docker-compose.prod.yml`; smoke test sull'API live (create + list), con il preset di prova eliminato subito dopo;
- e2e aggiunto (`job-list.spec.js`: "salvare, applicare e rimuovere un filtro preferito"), esecuzione non documentata;
- commit pushato su `origin/main`.

## Note / cosa manca
- **Collisione di numerazione**: il push è avvenuto dopo un altro commit `9bbcbf8`, numerato anch'esso "Sprint 63" (editor e chat della cover letter), diverso dal commit `3b46009` "Sprint 63" sul filtro di ricerca. Il deploy di questo sprint ha portato in produzione anche quelle modifiche.
- Il preset salva anche il filtro "Ricerca" quando lo si crea dalla sezione Importati, dove quel filtro è nascosto e ignorato lato client. Applicato da Raccolti o Archiviati, il filtro torna attivo.
- `handleDeletePreset` non gestisce un errore dell'API: se la DELETE fallisce, la pillola sparisce comunque finché la pagina non viene ricaricata.
- Le specifiche funzionali e tecniche non descrivono i preset.
