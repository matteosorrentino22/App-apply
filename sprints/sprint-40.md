# Sprint 40 — Filtro per ricerca di provenienza nella lista job e migrazione del motore AI ad AWS Bedrock

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-08-15/18 (date ricostruite, vedi Note) · **Commit:** `0833bdb` (commit cumulativo di recupero del 2026-08-22 che contiene insieme Sprint 39–42, vedi `sprint-43.md`, "Nota preliminare")

**Attribuzione.** Il numero "sprint-40" compare nel codice solo sul filtro per
ricerca di provenienza (`backend/apps/jobs/list_service.py`). La migrazione a
Bedrock (2026-08-18) non ha un numero di sprint né nel codice né nello storico
sessioni: è assegnata qui perché cronologicamente cade fra Sprint 39
(2026-08-15) e Sprint 41 (2026-08-19). È una ricostruzione, non un dato
documentato.

## Input
- **Filtro per ricerca di provenienza.** La richiesta originale del committente
  non è stata ritrovata: la sessione in cui è stato scritto il codice non è tra
  quelle disponibili. Dal codice risulta questo obiettivo: nella lista job,
  filtrare i job per la ricerca salvata che li ha prodotti (`Job.matched_search`,
  introdotto in sprint-23), sfruttando il tipo di ricerca Job role/Company dello
  Sprint 39.
- **Motore AI.** Il 2026-08-18 il committente segnala che la generazione dei CV
  non funziona. Causa: credito esaurito sulla chiave dell'API Anthropic diretta
  (errore 400 "credit balance is too low" nei `RunLog`). Il committente chiede
  di usare le proprie credenziali AWS, che danno accesso ai modelli Claude su
  Bedrock, per **tutte** le chiamate AI (scoring, generazione CV, parsing del CV
  importato).

## Decisioni prese
- **Filtro:** non ricostruibili da fonti di sessione. Dal codice: valore `all`
  (nessun filtro), `none` (job senza ricerca di provenienza: importati o item
  Apify senza `searchString`), oppure l'id di una `SavedSearch` dell'utente. Il
  filtro si combina in AND con periodo/score/stato. Come gli altri filtri, viene
  ignorato quando è attiva la ricerca testuale `q`.
- **Bedrock, verificato prima di cambiare il codice:** prima con il listing,
  poi con un invoke reale. Regione `us-east-1`, accesso ai profili di inferenza
  Claude (Opus 5, Sonnet 5, Haiku 4.5).
- **Output strutturato:** Bedrock rifiuta il parametro nativo
  `output_config.format` (json_schema), con errore 400. Si passa al **tool-use
  forzato**: un tool unico `output` con `input_schema` = lo schema atteso e
  `tool_choice` impostato su quel tool. Il comportamento è stato verificato su
  uno schema annidato (array di oggetti, campi nullable) prima di riscrivere i
  call site.
- **Helper unico:** un solo punto di chiamata per tutte le funzioni AI
  (`apps/common/ai.py`), al posto del pattern client+parsing duplicato in tre
  file.
- **Validazione + retry:** aggiunti dopo un primo errore in produzione la sera
  stessa (`KeyError: 'translated_city'`). Con il tool-use forzato il modello a
  volte incapsulava l'output in una chiave spuria (`"jsonPayload"`) o
  aggiungeva campi non richiesti. Per questo la risposta viene validata con
  `jsonschema`, con fino a 3 tentativi, e la descrizione del tool vieta
  esplicitamente chiavi contenitore e campi extra.
- Nessuna nuova dipendenza per il client: `anthropic` (che include
  `AnthropicBedrock`) e `boto3` erano già presenti. Aggiunta solo `jsonschema`.

## Implementazione
### Backend — filtro ricerca
- `apps/jobs/list_service.py`: `_apply_matched_search_filter(queryset, user, search_id)`,
  nuovo parametro `search_id` in `list_jobs`. La stringa che l'actor avrebbe
  restituito viene ricostruita così:
  - **job_role**: `matched_search == "<keywords> - <city>, <country>"`;
  - **company**: `matched_search__iexact == keywords`. Il nome azienda
    restituito da LinkedIn può differire per maiuscole/minuscole.
  - Un id non appartenente all'utente restituisce un queryset vuoto.
- `apps/jobs/views.py` (`JobListView`): nuovo parametro query `search`, che
  accetta `all`, `none` o un id numerico; altrimenti 400.
### Backend — motore AI
- Nuovo `apps/common/ai.py`:
  - `call_claude_structured(model, system, user_content, schema, max_tokens, effort=None)`;
  - client `AnthropicBedrock(aws_region=settings.AWS_BEDROCK_REGION)`;
  - `thinking` disabilitato, `effort` passato in `output_config` solo se
    indicato;
  - `_MAX_ATTEMPTS = 3`, eccezione `StructuredOutputError`.
- Call site migrati: `apps/cv/ai_content.py`, `apps/jobs/ai_scoring.py`,
  `apps/profiles/cv_import.py`.
- `config/settings.py` / `.env.example`: rimossi `ANTHROPIC_API_KEY` e
  `ANTHROPIC_*_MODEL`. Aggiunti:
  - `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (letti da boto3
    dall'ambiente);
  - `AWS_BEDROCK_REGION` (default `us-east-1`);
  - `BEDROCK_CV_PARSING_MODEL` (default `us.anthropic.claude-opus-5`);
  - `BEDROCK_SCORING_MODEL` (default `us.anthropic.claude-haiku-4-5-20251001-v1:0`);
  - `BEDROCK_CV_GENERATION_MODEL` (default `us.anthropic.claude-opus-5`).
- `backend/requirements.txt`: `jsonschema>=4.18,<5.0`.
- `CLAUDE.md`: voce "Motore AI" aggiornata.
### API
- `GET /api/jobs/?search=<all|none|id>` (filtro singolo).
### Frontend
- `frontend/src/api/jobs.js`: `fetchJobs({..., searchId})` aggiunge il parametro
  `search`.
- `frontend/src/pages/JobListPage.jsx`: nuovo `Select` "Ricerca", nascosto e
  ignorato nella sezione Importati. Le voci sono:
  - "Tutte le ricerche";
  - una voce per ogni ricerca salvata, nel formato `Tipo: keywords — città,
    paese` (caricate con `fetchSearches`);
  - "Nessuna ricerca".
- Nuove chiavi i18n: `jobs.searchFilterLabel`, `jobs.searchFilter_all`,
  `jobs.searchFilter_none`.

## Verifica
- **Filtro:** 7 test in `apps/jobs/tests.py` (`JobListTests`):
  - corrispondenza job_role per stringa ricostruita;
  - corrispondenza company case-insensitive;
  - `none`;
  - `all`;
  - id sconosciuto;
  - ricerca di un altro utente;
  - combinazione in AND con score/stato.
- **Bedrock:** prove end-to-end in produzione riportate nella sessione del
  2026-08-18:
  - scoring, parsing CV importato e generazione CV riusciti;
  - PDF servito via Caddy (`200 application/pdf`);
  - dopo l'aggiunta di validazione e retry, 3 generazioni CV consecutive
    riuscite, più scoring e PDF.
- La suite di test **non** era stata aggiornata: i due test di import CV in
  `apps/profiles/tests.py` mockavano ancora la classe `Anthropic` rimossa. Sono
  stati corretti solo il 2026-08-22, nel commit di recupero (ora mockano
  `call_claude_structured`). Nessun test dedicato a `apps/common/ai.py`
  (validazione/retry).

## Note / cosa manca
- **Date:** il filtro è stato scritto in una sessione non disponibile, dopo lo
  Sprint 39 (ne usa `search_type`) e prima del 2026-08-22, quando risulta già
  presente nel codice letto in sessione. La migrazione Bedrock è datata
  2026-08-18 dallo storico sessioni.
- **Superato in seguito:** il filtro a valore singolo è stato reso
  multi-selezione con il parametro `search_ids` / `JobFilterPreset.search_ids`
  (Sprint 63–64). Oggi in `list_service.py` vive come
  `_saved_search_match_q` + `_apply_matched_search_filter(queryset, user, search_ids)`.
- `minItems`/`maxItems` non sono stati reintrodotti negli schemi dopo il
  passaggio al tool-use: i vincoli di quantità restano solo nei prompt.
- **Lavoro non numerato nello stesso commit:**
  - la sezione `CLAUDE.md` "Deploy — non mescolare mai docker-compose.yml e
    docker-compose.prod.yml", nata dall'incidente del 2026-08-17 (PDF
    generati ma non serviti da Caddy);
  - il fine-tuning del prompt CV del 2026-08-11 in `apps/cv/ai_content.py`:
    paragrafi PRIORITÀ DELL'OFFERTA e SOMMARIO, skill rese esplicite nei
    bullet, uso dello spazio nei bullet.

  Nessuno dei due ha un numero di sprint.
- Le specifiche (`02-specifiche-tecniche-v3.md` §3.5, §8.5;
  `Docs/02-specifiche-tecniche-v4.md` stessi §) descrivono ancora "API
  Anthropic" e la "chiave API Anthropic": non sono state aggiornate.
