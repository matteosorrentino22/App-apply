# Sprint 14 — Import manuale di job

## Input
- Sprint 06 (concetto di quota), Sprint 08 (scoring), Sprint 02 (modello `Job`) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.9; `02-specifiche-tecniche-v3.md` §4.6, §5.2.

## Obiettivo
Endpoint API per importare un job LinkedIn tramite link (solo piano Pro), con validazione link, scoring del job importato (senza CV automatico), deduplica, quota giornaliera `import_count` (3/giorno) con estensione a credito (`PRICE_IMPORT_EXTRA`).

## Risultato atteso
Un utente Pro può importare un job valido, che viene scorato e mostrato nella sezione "Job importati" in stato `new`; un utente Free non può importare nemmeno con credito; oltre 3 import/giorno si consuma credito o si blocca.

## Criteri di verifica
- Utente Pro importa un link valido → `Job` creato con `origin='imported'`, `status='new'`, punteggio assegnato (anche se ≥4, nessun `CVDocument` automatico creato).
- Utente Free tenta l'import (anche con `extra_credit` > 0) → richiesta rifiutata.
- Link non valido → risposta con messaggio "impossibile importare quel job", nessun `Job` creato.
- Import di un job già presente nella lista dell'utente → nessun duplicato creato, risposta segnala "questo job è già nella tua lista".
- Utente Pro effettua 3 import nel giorno: il 4° senza credito sufficiente è rifiutato con messaggio di limite; con credito sufficiente, il 4° prosegue e scala `PRICE_IMPORT_EXTRA`.
- Generare poi il CV per un job importato consuma sia `import_count` (già consumato all'import) sia, separatamente, `manual_cv_count` (verificabile leggendo entrambi i contatori dopo le due operazioni).

## Output per lo sprint successivo
Job importati integrati nel modello dati unificato, pronti per essere esposti dalla vista lista (Sprint 15).

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.jobs.import_service.import_job_from_url(user, url)` — pipeline completa, stessa struttura "guardia → quota/credito → riserva → esecuzione → conferma/restituzione" già usata per la generazione manuale (Sprint 12):
  1. **Controllo di piano** (precede quota/credito, §4.6 tecniche): `user.plan != User.Plan.PRO` → `ImportNotAllowed`, anche con `extra_credit` > 0.
  2. **Validazione del link** tramite regex (`LINKEDIN_JOB_URL_RE`), che estrae anche l'ID numerico LinkedIn dal path — usato subito per un controllo di **deduplica locale** (nessuna chiamata alla fonte offerte solo per verificare se il job è già presente): se il link non è nel formato atteso, `ImportRejected("Impossibile importare quel job.")`; se l'ID risulta già tra i job dell'utente, `ImportDuplicate` (nessuna quota toccata in entrambi i casi).
  3. **Riserva quota/credito** (`_reserve_import_quota_or_credit`, `@transaction.atomic` con `select_for_update` su `DailyQuota`/`User`, stessa tecnica dello Sprint 12): incrementa `import_count` se sotto il massimale Pro (3/giorno), altrimenti scala `PRICE_IMPORT_EXTRA` dal saldo, altrimenti `ImportRejected` col messaggio di limite.
  4. **Recupero dei dettagli** tramite il nuovo `ApifyLinkedInSource.fetch_by_url(url)` (stessa fonte offerte sostituibile, §5.3 tecniche, estesa con un secondo metodo dell'interfaccia anziché una classe parallela). Se il recupero fallisce (rete non raggiungibile, risposta vuota/incompleta) la riserva viene **restituita** e si solleva `ImportRejected`.
  5. **Creazione e scoring**: `Job` salvato con `origin=imported`, poi passato a `apps.jobs.scoring.score_job` (Sprint 08) — **nessuna generazione automatica di CV**, anche con punteggio 4–5, a differenza del ciclo notturno (Sprint 11): l'import è un percorso sempre manuale.
- `PRICE_IMPORT_EXTRA` (default placeholder `0.50`, stesso trattamento di `PRICE_MANUAL_CV_EXTRA`) aggiunto in `settings.py`/`.env.example`.
- `POST /api/jobs/import/` (`apps.jobs.views.ImportJobView`) — `403` per `ImportNotAllowed` (non-Pro), `409` per `ImportRejected`/`ImportDuplicate` (messaggi distinti), `201` con `job_id`/`status`/`score` in caso di successo.
- **Bug trovato e corretto durante la verifica manuale (non dai test automatici)**: il recupero dei dettagli (`fetch_by_url`) non era protetto da un `try/except` — un errore di rete reale (in sandbox: `ProxyError`, nessun accesso reale a LinkedIn/Apify) si propagava non gestito fino a un 500 HTTP, senza restituire la riserva di quota. Nei test automatici questo non emergeva perché la fonte offerte è sempre mockata. Corretto racchiudendo la chiamata in un `try/except Exception` che tratta qualunque fallimento di recupero come "offerta non disponibile" (stesso ramo già previsto per una risposta vuota/incompleta), così qualsiasi causa di fallimento del recupero produce lo stesso comportamento coerente: messaggio "impossibile importare quel job", riserva restituita, nessun `Job` creato. Riverificato via `runserver` + richiesta HTTP reale su un link nel formato corretto: risposta `409` pulita, quota tornata al valore precedente.

### Verifica eseguita
`python manage.py test apps.jobs` (27/27, incluse le 7 nuove `ImportJobTests`) e `python manage.py test` sull'intero progetto (60/60, nessuna regressione); `makemigrations --check` pulito (nessuna modifica ai modelli: `Job.origin`/`DailyQuota.import_count` esistevano già dagli Sprint 02/06). Verifica manuale end-to-end via `runserver` + richieste HTTP reali (link non valido, link valido con fallimento di rete reale) che ha permesso di individuare e correggere il bug di gestione errori sopra descritto.

| Criterio | Esito |
|---|---|
| Utente Pro importa link valido → `Job` con `origin='imported'`, `status='new'`, punteggio assegnato, nessun `CVDocument` automatico anche con score ≥4 | ✅ |
| Utente Free tenta l'import anche con `extra_credit` > 0 → richiesta rifiutata | ✅ |
| Link non valido → messaggio "impossibile importare quel job", nessun `Job` creato | ✅ (verificato anche per fallimento di rete reale nel recupero, non solo formato del link) |
| Import di un job già presente → nessun duplicato, messaggio "questo job è già nella tua lista" | ✅ |
| 3 import/giorno poi 4° senza credito rifiutato con messaggio di limite; con credito sufficiente prosegue e scala `PRICE_IMPORT_EXTRA` | ✅ |
| CV generato per un job importato consuma `manual_cv_count` separatamente da `import_count` (già consumato all'import) | ✅ |

### Cosa manca
- Nessuna verifica end-to-end reale della chiamata Apify (stessa riserva già registrata per la raccolta, Sprint 07) — la verifica manuale ha comunque confermato che un fallimento di rete reale viene gestito correttamente (restituzione della riserva, messaggio coerente), non solo il caso mockato.
- `PRICE_IMPORT_EXTRA` resta un valore placeholder, da fissare prima del rilascio (§11 tecniche), come già segnalato per `PRICE_MANUAL_CV_EXTRA`.
- Sezione "Job importati" nella UI e filtri/ricerca sulla lista completa: Sprint 15.
