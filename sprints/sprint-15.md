# Sprint 15 — Vista lista job (API)

## Input
- Sprint 07/09 (Job raccolti), Sprint 14 (Job importati), Sprint 12 (stati/archiviazione) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.5, §4.6, §7.

## Obiettivo
API di lettura lista job con le tre sezioni (Principale, Job importati, Archivio), filtri temporali (oggi/settimana/mese/tutti), filtri score/stato (multiselect), barra di ricerca testuale confinata alla sezione corrente (che ignora gli altri filtri quando attiva), ordinamento per punteggio decrescente; endpoint di swipe archivia/rimuovi-da-archivio con undo.

## Risultato atteso
Chiamando l'API lista con vari parametri si ottengono esattamente i job attesi per sezione/filtro; le azioni di swipe modificano correttamente `is_archived` e sono annullabili.

## Criteri di verifica
- Creando Job in tutte le combinazioni (`origin`, `is_archived`, `status`), ciascuna delle tre sezioni restituisce esattamente i Job attesi.
- Il filtro temporale "oggi" restituisce solo Job con `date_collected` di oggi; "tutti" restituisce l'intero storico della sezione.
- Il filtro score multiselect `[4,5]` e il filtro stato multiselect `["new"]` restituiscono l'intersezione corretta, in tutte e tre le sezioni.
- I risultati sono sempre ordinati per `score` decrescente, anche con filtro temporale applicato.
- La ricerca testuale su "Principale" non restituisce job di "Archivio" o "Job importati"; quando la query è presente, gli altri filtri passati vengono ignorati (verificabile passando filtri contraddittori e osservando che vengono ignorati).
- Lo swipe "archivia" imposta `is_archived=True`; l'endpoint undo lo riporta a `False`; lo swipe "rimuovi da archivio" riporta il job alla sezione d'origine mantenendo lo `status` precedente.

## Output per lo sprint successivo
API di navigazione job completa, pronta per essere consumata dal frontend (Sprint 18+) e per l'endpoint di candidatura (Sprint 16).

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.jobs.list_service.list_jobs(user, section, period, scores, statuses, query)` — logica di filtro centrale:
  - **Sezioni** (`SECTION_FILTERS`): `main` = raccolti non archiviati, `imported` = importati non archiviati, `archived` = tutti gli archiviati a prescindere dall'origine — dipendono solo da `origin`/`is_archived`, mai da `status` (§4.5/§4.6 funzionali).
  - **Filtro temporale**: "oggi" calcolato sulla **mezzanotte locale dell'utente** (`user.timezone`, via `zoneinfo`, §7 funzionali — non UTC), "settimana"/"mese" come finestre rolling di 7/30 giorni, "tutti" nessun filtro.
  - **Score/stato multiselect**: `score__in`/`status__in`; solo i tre stati stabili sono ammessi (`FILTERABLE_STATUSES`), il transitorio `cv_generation_in_progress` non è un valore filtrabile per stato (è un flag separato, già esposto in lettura nel serializer).
  - **Ricerca testuale**: quando `query` è presente, filtra solo su `title`/`company`/`location` (mai sulla descrizione) **e ignora completamente** periodo/score/stato — implementato con un `if/else` esplicito piuttosto che comporre i filtri, per garantire l'esclusione reciproca richiesta dal criterio.
  - **Ordinamento**: sempre per `score` decrescente (con `nulls_last=True`, esplicito — di default Postgres mette i `NULL` per primi in `DESC`, il che avrebbe messo i job non ancora scorati in cima), poi per `date_collected` decrescente come tie-break.
- `apps.jobs.list_service.archive_job`/`unarchive_job` — un'unica funzione di "rimozione dall'archivio" copre sia lo swipe "rimuovi da archivio" sia l'undo di un'archiviazione accidentale: sono la stessa operazione (`is_archived=False`), lo stato non viene mai toccato in nessuno dei due flussi (§4.6 funzionali: l'archiviazione è ortogonale allo stato).
- `apps.jobs.serializers.JobSerializer` — espone tutti i campi rilevanti per riga di lista e dettaglio (titolo, azienda, località, punteggio, scomposizione affinità/lacune, stato, flag di generazione in corso, date di servizio); un solo serializer copre sia la vista lista sia il dettaglio (nessuna descrizione via endpoint separato: non richiesto dai criteri di questo sprint).
- Endpoint REST in `apps.jobs.views`/`urls`: `GET /api/jobs/?section=&period=&score=&status=&q=` (validazione esplicita di sezione/periodo/score/stato con `400` e messaggio se non ammessi), `POST /api/jobs/<id>/archive/`, `POST /api/jobs/<id>/unarchive/`.

### Verifica eseguita
`python manage.py test apps.jobs` (36/36, incluse le 8 nuove `JobListTests` e le 3 nuove `ArchiveJobApiTests`) e `python manage.py test` sull'intero progetto (69/69, nessuna regressione); `makemigrations --check` pulito (nessuna modifica ai modelli: tutti i campi usati esistevano già). Verifica manuale end-to-end via `runserver` + richieste HTTP reali (`GET /api/jobs/` con vari filtri, sezione non valida) per confermare il comportamento anche fuori dai test mockati.

| Criterio | Esito |
|---|---|
| Job in tutte le combinazioni (`origin`, `is_archived`, `status`) → ciascuna sezione restituisce esattamente i Job attesi | ✅ |
| Filtro "oggi" → solo Job con `date_collected` di oggi (locale utente); "tutti" → storico intero | ✅ |
| Filtri score `[4,5]` e stato `["new"]` → intersezione corretta, in tutte e tre le sezioni | ✅ |
| Risultati sempre ordinati per `score` decrescente, anche con filtro temporale | ✅ |
| Ricerca testuale su "Principale" non mostra job di Archivio/Importati; con query attiva, gli altri filtri (anche contraddittori) sono ignorati | ✅ |
| Swipe "archivia" → `is_archived=True`; endpoint undo → `False`; "rimuovi da archivio" → sezione d'origine con lo `status` precedente | ✅ |

### Cosa manca
- Nessun endpoint di dettaglio separato (la `JobSerializer` unica copre già i campi di dettaglio, incluso `description`): da rivalutare se il frontend (Sprint 18+) richiedesse una risposta più leggera per la lista.
- Paginazione non implementata: fuori scope per i criteri di questo sprint (nessun limite esplicito richiesto), da valutare se i volumi reali lo richiedessero.
- Tracciamento della candidatura ("candidatura fatta"): Sprint 16.
