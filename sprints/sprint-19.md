# Sprint 19 — Frontend: lista job, generazione CV, candidatura

## Input
- Sprint 18 (auth/onboarding UI); Sprint 15 (API lista); Sprint 12/13 (generazione manuale/arricchimento API); Sprint 16 (candidatura API) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §3, §4.5, §4.6, §4.7, §4.8, §4.10, §6.

## Obiettivo
UI delle tre sezioni con filtri temporali/score/stato, barra di ricerca, swipe archivia/rimuovi con undo, dettaglio job; pulsante genera/rigenera CV con indicatore di caricamento e disabilitazione durante la generazione, form di arricchimento opzionale, download PDF, apertura link candidatura e marcatura "candidatura fatta".

## Risultato atteso
Da UI è possibile navigare le tre sezioni con tutti i filtri, generare manualmente un CV osservando l'indicatore di attesa (~10–15s) e il pulsante disabilitato, scaricare il PDF, e marcare una candidatura come fatta dopo aver generato il CV.

## Criteri di verifica
- Test e2e: applicare filtro temporale/score/stato in ciascuna delle tre sezioni e verificare che la lista mostrata corrisponda ai dati di test seed.
- Test e2e: attivare la barra di ricerca testuale e verificare che gli altri filtri vengano ignorati e i risultati restino confinati alla sezione corrente.
- Test e2e: swipe di archiviazione su un job, comparsa dell'opzione di undo, ripristino verificato in lista.
- Test e2e: premere "genera CV" su un job → il pulsante si disabilita e appare l'indicatore di caricamento; al termine il job passa a "CV generato"; una pressione ripetuta durante l'attesa non avvia una seconda generazione.
- Test e2e: dopo la generazione, il download del PDF restituisce un file; il link di candidatura è cliccabile solo se il CV è stato generato; marcare "candidatura fatta" aggiorna lo stato visibile in lista.
- Test e2e: form di arricchimento compilato prima della generazione, con scelta "salva anche nel profilo" — verificare che al termine il profilo mostri (o meno) il nuovo dettaglio a seconda della scelta.

## Output per lo sprint successivo
Flusso operativo quotidiano completo in UI; pronto per aggiungere gestione account e notifiche push lato client (Sprint 20).