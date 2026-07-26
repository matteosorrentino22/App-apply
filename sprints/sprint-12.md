# Sprint 12 — Generazione manuale + quote/credito

## Input
- Sprint 10 (servizio generazione CV); `DailyQuota` e `User.extra_credit` (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.7, §4.11; `02-specifiche-tecniche-v3.md` §4.6, §5.2.

## Obiettivo
Endpoint API di generazione manuale (anche per rigenerazione e per retry di un fallimento automatico) con: guardia di concorrenza (`cv_generation_in_progress`), controllo/riserva atomica del contatore `manual_cv_count` o del credito (`extra_credit` scalato secondo `PRICE_MANUAL_CV_EXTRA`), restituzione della riserva su fallimento.

## Risultato atteso
Un utente può richiedere la generazione manuale di un CV per qualsiasi job entro il proprio massimale o a credito; richieste concorrenti sullo stesso job vengono rifiutate; un fallimento non consuma budget.

## Criteri di verifica
- Utente Free: la 1ª generazione manuale nel giorno riesce e consuma `manual_cv_count`; la 2ª, con saldo credito insufficiente, è rifiutata con messaggio di limite raggiunto; con saldo sufficiente, la 2ª prosegue e scala `PRICE_MANUAL_CV_EXTRA` da `extra_credit`.
- Utente Pro: le prime 10 generazioni manuali nel giorno consumano il contatore; l'11ª (senza credito) è rifiutata.
- Due richieste ravvicinate sullo stesso Job: la seconda, inviata mentre `cv_generation_in_progress=True`, è rifiutata senza consumare quota/credito (contatore/saldo invariato dopo il rifiuto).
- Simulando un fallimento nel servizio di generazione, il contatore consumato viene decrementato o il credito scalato riaccreditato, secondo la modalità di addebito registrata; il Job torna a `new`.
- Il retry di un fallimento automatico (Job tornato a `new` da uno stato 4–5 fallito) consuma il massimale manuale tramite lo stesso endpoint/contatore, non un budget separato.
- Un job in Archivio, dopo generazione riuscita, risulta `is_archived=False` e nella sua sezione d'origine.

## Output per lo sprint successivo
Meccanismo di generazione manuale completo, riusato dall'arricchimento (Sprint 13) prima di ogni chiamata di generazione/rigenerazione.

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.cv.manual_generation.request_manual_cv_generation(job, enrichment="")` — punto d'ingresso unico per generazione manuale, rigenerazione e "riprova" dopo un fallimento automatico (stesso endpoint/contatore, nessun budget separato, come richiesto dal criterio):
  1. `_guard_and_reserve(job)` (in un'unica transazione `@transaction.atomic`): `select_for_update` sulla riga `Job` per serializzare le richieste concorrenti sullo stesso job — una seconda richiesta blocca finché la prima non ha committato, poi vede `cv_generation_in_progress=True` già impostato e viene respinta **prima** di arrivare alla riserva di quota/credito (nessun doppio addebito, criterio "due richieste ravvicinate").
  2. `_reserve_quota_or_credit(user)`: `select_for_update` su `DailyQuota` (creato per il giorno Europe/Rome se assente) — se `manual_cv_count` è sotto il massimale di piano (`MANUAL_CV_PLAN_LIMITS`: Free 1, Pro 10), incrementa e ritorna `"quota"`; altrimenti `select_for_update` su `User` e, se `extra_credit >= PRICE_MANUAL_CV_EXTRA`, scala il prezzo e ritorna `"credit"`; altrimenti solleva `ManualGenerationRejected` senza scrivere nulla.
  3. Generazione vera e propria via `apps.cv.generation.generate_cv` (Sprint 10). Su successo: `Job.status = cv_generated`, `date_cv_generated`, `cv_generation_in_progress=False`, **`is_archived=False`** (un job in Archivio torna alla sua sezione d'origine dopo una generazione riuscita, §4.5/§5.2 funzionali). Su fallimento: `_refund` restituisce ciò che era stato riservato (decremento del contatore o riaccredito del prezzo, secondo la modalità registrata al punto 2), `RunLog` di fallimento, `Job` torna a `new` con `cv_generation_in_progress=False`, e viene sollevata `ManualGenerationFailed` (distinta da `ManualGenerationRejected`, per permettere alla view di rispondere con codici HTTP diversi: rifiuto vs fallimento di generazione).
- `PRICE_MANUAL_CV_EXTRA` (default placeholder `1.50`, esplicitamente segnalato come "valore da fissare prima del rilascio" per §11 tecniche) aggiunto in `settings.py`/`.env.example` come `Decimal`, mai `float`, coerente con CLAUDE.md.
- `POST /api/jobs/<id>/generate-cv/` (`apps.jobs.views.GenerateCvView`) — primo endpoint dell'app `jobs` (nessuno esisteva prima; la lista job completa arriva nello Sprint 15, qui si introduce solo questa azione mirata). Isola per utente tramite `get_object_or_404(Job, pk=pk, user=request.user)`; accetta un campo opzionale `enrichment` nel body (già collegato al servizio di generazione, pronto per l'endpoint di arricchimento dello Sprint 13 senza modifiche a questa view). Risponde `201` con l'id del `CVDocument`, `409` se la richiesta è respinta (`ManualGenerationRejected`: concorrenza o quota/credito insufficiente), `502` se la generazione stessa fallisce (`ManualGenerationFailed`).
- **Bug trovato e corretto durante la verifica manuale (non dai test automatici)**: `_refund` usava `select_for_update()` senza un `@transaction.atomic` proprio. Nei test automatici questo non emergeva perché `TestCase` avvolge già ogni test in una transazione; testando manualmente via `runserver` + richiesta HTTP reale (fuori da quel wrapper) è comparso `TransactionManagementError: select_for_update cannot be used outside of a transaction`. Corretto aggiungendo `@transaction.atomic` a `_refund`; riverificato con una richiesta HTTP reale (fallita per assenza di una vera chiave Anthropic, come atteso in sandbox) che il fallimento ora restituisce correttamente la riserva (contatore tornato a 0, `Job` tornato a `new`, `RunLog` con l'errore reale di autenticazione Claude) invece di un errore 500 non gestito.

### Decisione tecnica non esplicitamente richiesta, da segnalare
`02-specifiche-tecniche-v3.md` §5.2 descrive la generazione manuale come **asincrona**: la riserva avviene "all'accodamento", poi "il worker genera il CV" mentre "l'utente può continuare a usare l'app" (attesa tipica 10–15s lato client, gestita con indicatore di caricamento). In questo sprint `POST /api/jobs/<id>/generate-cv/` esegue invece l'intera pipeline **sincronamente nella request** (nessuna coda Celery per questo percorso). Scelta deliberata per restare aderente ai criteri di verifica dello sprint, che si aspettano una risposta diretta di successo/rifiuto sulla stessa chiamata, e per evitare di introdurre — senza che il frontend (Sprint 18+) ne definisca il bisogno — un meccanismo di polling/websocket per notificare il completamento di un task in coda (coerente con "no over-engineering" di CLAUDE.md). La guardia di concorrenza e la riserva atomica di quota/credito restano corrette in entrambi i casi (sono indipendenti dal fatto che l'esecuzione sia sincrona o accodata); il passaggio a un task Celery reale, se richiesto in futuro, è un cambiamento circoscritto a `apps.jobs.views.GenerateCvView` (accodare `request_manual_cv_generation` invece di chiamarlo direttamente), senza toccare la logica di `apps.cv.manual_generation`.

### Verifica eseguita
`python manage.py test apps.cv apps.jobs` (36/36, incluse le 9 nuove di `ManualCvGenerationTests`) e `python manage.py test` sull'intero progetto (48/48, nessuna regressione); `makemigrations --check` pulito (nessuna modifica ai modelli). Verifica manuale end-to-end via `runserver` + richieste HTTP reali (registrazione utente, creazione profilo/job, chiamata all'endpoint) che ha permesso di individuare e correggere il bug di `_refund` sopra descritto.

| Criterio | Esito |
|---|---|
| Free: 1ª generazione riesce e consuma `manual_cv_count`; 2ª con credito insufficiente rifiutata; con credito sufficiente prosegue e scala `PRICE_MANUAL_CV_EXTRA` | ✅ |
| Pro: prime 10 generazioni consumano il contatore; l'11ª senza credito è rifiutata | ✅ |
| Due richieste ravvicinate sullo stesso Job: la seconda (con `cv_generation_in_progress=True`) rifiutata senza consumare quota/credito | ✅ |
| Fallimento simulato: contatore decrementato o credito riaccreditato secondo la modalità di addebito; Job torna a `new` | ✅ (verificato per entrambe le modalità di addebito, sia nei test automatici sia nella verifica manuale end-to-end) |
| Retry di un fallimento automatico consuma il massimale manuale tramite lo stesso endpoint/contatore | ✅ |
| Job in Archivio, dopo generazione riuscita, risulta `is_archived=False` e nella sua sezione d'origine | ✅ |

### Cosa manca
- Nessuna verifica end-to-end reale della chiamata Claude all'interno del flusso manuale (stessa riserva già registrata per Sprint 10/11); la verifica manuale end-to-end ha comunque coperto l'intero percorso HTTP → guardia → quota/credito → generazione → risposta, fermandosi solo sull'assenza di una chiave Anthropic reale in sandbox.
- `PRICE_MANUAL_CV_EXTRA` resta un valore placeholder, da fissare prima del rilascio (§11 tecniche).
- Esecuzione asincrona reale via Celery (§5.2 tecniche) non introdotta in questo sprint — vedi "Decisione tecnica" sopra.
- Endpoint per l'arricchimento del profilo prima della generazione: Sprint 13 (il parametro `enrichment` è già accettato e inoltrato, pronto per essere popolato da quell'endpoint).
