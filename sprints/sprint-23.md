# Sprint 23 — Fix post-QA sull'ambiente reale

## Input
Sprint 22 completato; test funzionali manuali del committente sull'ambiente di produzione reale (VPS), da cui sono emersi due bug reali e tre richieste di modifica sulle ricerche salvate.

## Obiettivo
Correggere due bug bloccanti trovati in produzione (scoring notturno, raccolta Apify non selettiva) e implementare quattro modifiche di dettaglio sulle ricerche salvate emerse dai test manuali: modifica di una ricerca esistente, città/paese separati con autocomplete, rimozione del nome ricerca come identificatore, attribuzione del job alla ricerca che l'ha prodotto.

## Esito (2026-07-28/29)

### Bug 1 — Scoring notturno falliva sistematicamente (400 su `effort`)
`apps/jobs/ai_scoring.py` passava `output_config.effort="medium"`, non supportato da `claude-haiku-4-5` (modello di scoring in produzione). Ogni chiamata di scoring falliva con 400, scartando tutti i job raccolti la notte precedente (13/13). Rimosso `effort` e `thinking: {"disabled"}` ridondante. Verificato con una chiamata reale ad Anthropic post-fix: scoring corretto.

### Bug 2 — Job irrilevanti raccolti nonostante ricerche specifiche
Investigato chiamando direttamente l'actor Apify (`cheap_scraper~linkedin-job-scraper`): anche con `keyword`/`location` corretti, l'actor restituisce risultati "simili" LinkedIn non filtrati esattamente sulla keyword (es. cercando "UBS" tornano offerte "Fielmann Group" — ottici). Non risolto in questo sprint (fuori scope, richiede logica di post-filtro sul risultato Apify da valutare separatamente); il fix 4 di questo sprint (ricerca di provenienza visibile sulla card) è stato introdotto proprio per rendere questo comportamento diagnosticabile dall'utente.

### Fix 1 — Modifica di una ricerca salvata
`SavedSearchViewSet` (DRF `ModelViewSet`) già supportava `PATCH`; mancava solo l'UI. Aggiunta modalità di editing inline in `AccountPage.jsx` (stesso form di creazione, precompilato).

### Fix 2 — Città/Paese separati con autocomplete
`SavedSearch.location` sostituito da due campi `city`/`country` (migrazione dati `0002_split_location_remove_name`, split automatico dei valori esistenti). Nuovo endpoint proxy `GET /api/searches-city-autocomplete/` verso **Nominatim (OpenStreetMap)** — gratuito, nessuna chiave richiesta — con cache locmem (1h) per rispettare il limite di 1 req/sec del servizio. Nuovo componente `CityAutocomplete.jsx` (debounce 350ms) usato in `AccountPage` e `OnboardingPage`. La raccolta Apify costruisce `location` da `city`+`country` invece di un campo libero.

### Fix 3 — Nome ricerca rimosso
Campo `SavedSearch.name` eliminato dal modello (stessa migrazione del fix 2, nessun uso residuo nel codice a parte l'admin Django). La card ricerca mostra ora **keyword in grassetto** sopra, **città, paese** sotto — nessun altro identificativo.

### Fix 4 — Ricerca di provenienza sul job
Nuovo campo `Job.matched_search` (migrazione `0004_add_matched_search`), popolato dal campo `searchString` restituito da Apify per ogni offerta raccolta nella notte (vuoto per i job importati manualmente, che non derivano da una ricerca). Mostrato come badge (stesso stile del badge di stato) su `JobCard` e `JobDetailPage`.

### Verifica eseguita
- Backend: `python manage.py test` → **128/128 passati** (118 pre-esistenti + 10 nuovi: update ricerca, isolamento multi-utente su update, normalizzazione Apify `matched_search`, autocomplete città con cache/query corta/auth); `makemigrations --check` pulito.
- Frontend: `npm run build` e `oxlint` puliti sui file toccati.
- **Verifica end-to-end reale in produzione** (non solo mock): chiamata reale a Nominatim per l'autocomplete (200, risultati corretti Zurich/Switzerland); create/update/delete reali di una ricerca via API; raccolta reale da Apify per l'utente di test con verifica che `matched_search` sia popolato correttamente sui job creati (poi rimossi, essendo dati di test).
- Suite e2e Playwright non eseguibile in modo affidabile in questo sprint: l'ambiente sandbox non ha uno stack di sviluppo separato dalla produzione, e il dev server Vite proxato contro il backend di produzione (`DJANGO_DEBUG=false`) riceve redirect HTTPS forzati che rompono le chiamate dirette dei test (`request.post`) — limite ambientale preesistente, non legato alle modifiche di questo sprint. Aggiornati comunque i selettori e i dati dei test `auth-onboarding.spec.js` e `account.spec.js` per il nuovo modello (città/paese, nessun campo nome).

### Deploy
Rebuild delle immagini `web`/`worker`/`beat` e riavvio dei tre servizi in produzione con le migrazioni applicate. Backup del database eseguito prima della migrazione dati (`pg_dump`, non incluso nel repository).

### Cosa manca
- **Bug 2 (selettività raccolta Apify)** resta aperto — da investigare separatamente se il badge "ricerca di provenienza" (fix 4) non è sufficiente a diagnosticare/mitigare il problema in uso reale.
- Suite e2e Playwright da eseguire su un ambiente di sviluppo dedicato (non ancora predisposto in questo sandbox) prima del prossimo giro di QA.
