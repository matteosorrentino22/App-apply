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

---

## Esito (2026-07-27)

**Stato: completato.**

### Cosa è stato fatto
- **Backend, due aggiunte minime** (nessuna specifica tecnica le definiva esplicitamente, ma servivano perché il frontend potesse funzionare):
  - `GET /api/jobs/<id>/` (`JobDetailView`) — mancava un endpoint di dettaglio singolo job (c'era solo la lista): necessario per una pagina di dettaglio deep-linkabile/che sopravvive al refresh.
  - `JobSerializer.cv_pdf_url` — l'URL del PDF generato non era esposto da nessuna risposta API (`GenerateCvView` restituiva solo `cv_document_id`); esposto come campo calcolato sul job stesso (l'ultimo `CVDocument` generato), evitando una risorsa dedicata che il frontend dovrebbe interrogare a parte.
- **`JobListPage`**: tre sezioni (Raccolti/Importati/Archiviati) come tab, filtri periodo/punteggio/stato, ricerca testuale che disattiva visivamente gli altri filtri quando attiva (coerente con `list_jobs()`, che li ignora lato server). Card job con punteggio colorato in base alla scala semantica del design system approvato, motivo sintetico, azioni dirette (Dettagli, Archivia, Genera/Rigenera CV).
- **Swipe per archiviare** (`SwipeToArchive`, pointer events — funziona sia a dito sia con drag del mouse): resta anche un bottone esplicito equivalente per tastiera/click diretto. Archiviare mostra un toast con "Annulla" che ripristina il job.
- **`JobDetailPage`**: punteggio in grande, giustificazione, corrispondenze/mancanze, descrizione; form di arricchimento opzionale (azienda/ruolo/località/attività a chip/tecnologie/"salva anche nel profilo"); download PDF quando disponibile; link candidatura visibile solo se il CV è stato generato; "segna candidatura fatta".
- **Generazione CV**: la chiamata è sincrona lato backend (nessun task Celery per la generazione manuale, già così dagli sprint precedenti) — il frontend disabilita il pulsante e mostra "Generazione…" per tutta la durata della richiesta, senza bisogno di polling.
- **`ToastProvider`** (nuovo, generico): notifiche in basso con azione opzionale, usato per l'undo dell'archiviazione e per gli errori di generazione CV.
- **Fix minore emerso testando**: il login riportava sempre a `/onboarding` anche per un utente che l'aveva già completato — ora porta a `/list`, coerente con l'esistenza di una vera schermata lista da questo sprint in poi (la registrazione continua a portare a `/onboarding`, corretto per un utente nuovo).
- **Bug reale trovato dal test e2e e corretto**: `generate_cv_with_enrichment` (Sprint 10/13) accedeva a `job.user.profile` direttamente, che solleva `RelatedObjectDoesNotExist` (→ 500 non gestito) per un utente che non ha ancora completato l'onboarding e prova comunque ad "arricchire e salvare nel profilo" prima di aver mai salvato nulla. Corretto con lo stesso `get_or_create` già usato da `ProfileSectionViewSet`. Aggiunto un test di regressione dedicato in `apps/cv/tests.py`.
- **`seed_e2e_jobs`** (nuovo management command, `apps/jobs/management/commands/`): crea un set fisso di 6 Job (tutte le sezioni, tutti gli stati filtrabili, punteggi 1/2/3/4/5) per un utente dato — si rifiuta di girare senza `DEBUG=True`. Necessario perché i Job non sono creabili da un utente normale via API (arrivano solo da raccolta notturna o import), quindi i test e2e non avevano altrimenti un modo per popolare la lista con dati noti.

### Decisioni tecniche non esplicitamente richieste, da segnalare
- Il criterio "una pressione ripetuta durante l'attesa non avvia una seconda generazione" è garantito su due livelli: il pulsante è disabilitato lato client per tutta la richiesta, e il backend ha comunque una guardia di concorrenza indipendente (409 se già in corso) — nessuna delle due dipende dall'altra.
- Lo swipe usa Pointer Events nativi con `setPointerCapture`, non una libreria di gesture: sufficiente per un gesto orizzontale a soglia singola, coerente con "preferire soluzioni standard, non esotiche". Il pointerdown ignora i click che partono da bottoni/link interni alla card, per non rompere gli altri controlli (bug trovato e corretto durante i test e2e).

### Limite noto (coerente con gli sprint precedenti che toccano Claude)
- La generazione CV (con o senza arricchimento) chiama l'API Anthropic: senza `ANTHROPIC_API_KEY` valida in questo sandbox, ogni tentativo fallisce lato server in modo gestito (502, già previsto da `request_manual_cv_generation`). I test e2e verificano quindi l'intero percorso — pulsante disabilitato, indicatore di caricamento, messaggio d'errore, job che torna correttamente a "Nuovo" (non bloccato), quota/credito correttamente restituiti — ma non il percorso di successo "il job passa a CV generato", né lo scaricamento di un PDF reale. Verificato però, con dati seed che simulano lo stato `cv_generated`, che una volta generato il CV il link di candidatura si sblocca e "segna candidatura fatta" funziona.

### Verifica eseguita
- Backend: `python manage.py test` → **92/92 passati** (84 pre-esistenti + 8 nuovi: `JobDetailApiTests`, `SeedE2eJobsCommandTests`, il test di regressione su `generate_cv_with_enrichment`); `makemigrations --check` pulito (nessuna modifica ai modelli).
- Frontend: `npm run build` e `npm run lint` senza errori.
- Test e2e Playwright (`frontend/e2e/job-list.spec.js`, **9 nuovi test, tutti passati**, eseguiti insieme alla suite dello Sprint 18 — **16/16 totali**): sezioni/filtri/ricerca con dati seed noti, swipe reale (drag del mouse) e bottone esplicito per l'archiviazione con undo verificato, generazione CV con indicatore di caricamento e messaggio d'errore gestito, apply-link gated sullo stato del CV, marcatura candidatura fatta, arricchimento con "salva anche nel profilo" verificato leggendo `/api/experiences/` dopo il tentativo di generazione.
- Verifica visiva con screenshot reali (Playwright, tema chiaro) di lista (tutte le sezioni, filtro punteggio, ricerca), dettaglio job, form di arricchimento (stato incompleto/completo), toast di errore — confrontati con l'artifact di design system approvato prima dell'implementazione dello Sprint 18.

### Cosa manca
- Percorso di successo reale della generazione CV (richiede `ANTHROPIC_API_KEY` valida, non disponibile in questo sandbox) e verifica di un download PDF reale — entrambi implementati e testabili solo con una chiave Claude vera.
- Nessuna UI per l'import di un job da URL (Sprint 14, Pro): non era tra gli input elencati per questo sprint, la sezione "Importati" mostra job importati via API ma non offre ancora il modulo di inserimento — verrà valutato se aggiungerlo in un sprint successivo o se resta backlog oltre l'MVP tracciato.