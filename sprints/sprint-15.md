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