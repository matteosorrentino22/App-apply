# Sprint 49 — Scarto delle offerte con campi oltre il `max_length`

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-01 · **Commit:** `4cbcdc8`

## Input
Segnalazione del committente (01/10): nell'ultima raccolta nessun job ha
ricevuto un punteggio.

Causa individuata (dal messaggio di commit):
- un `apply_url` LinkedIn con una query-string di tracking più lunga dei
  1000 caratteri del campo faceva fallire `Job.objects.create()` con un
  `DataError` non catturato, dentro il ciclo di `collect_jobs_for_user`;
- l'eccezione interrompeva la raccolta a metà batch. Le offerte già create
  (254 nel caso reale) restavano in DB senza punteggio, perché lo scoring
  (`score_jobs`) viene chiamato solo dopo che la raccolta è terminata con
  successo.

## Decisioni prese
- Un'offerta con un campo testuale più lungo del `max_length` del modello
  viene **scartata**, come quelle a cui manca un campo obbligatorio.
- **Mai troncata**: un `apply_url` troncato diventerebbe un link di
  candidatura rotto.
- I limiti vengono letti direttamente dal modello `Job`, senza duplicare
  costanti.

## Implementazione

### Backend
- `apps/jobs/collection.py`:
  - nuova tupla `_LENGTH_CHECKED_FIELDS` con `title`, `company`,
    `location`, `apply_url`, `matched_search`, `salary`, `recruiter_name` e
    `recruiter_profile_url`;
  - `_is_valid_offer(offer)`: dopo il controllo su `REQUIRED_FIELDS`,
    confronta per ogni campo della tupla `len(str(valore))` con
    `Job._meta.get_field(campo).max_length`. Se un campo lo supera,
    l'offerta non è valida.

### Modello dati / Frontend
Nessuna modifica.

## Verifica
- Nuovo test `CollectJobsForUserTests.test_offer_with_apply_url_too_long_is_skipped_not_crashed`
  (`apps/jobs/tests.py`): su tre offerte, quella centrale con un
  `apply_url` di oltre 1000 caratteri viene scartata, mentre le altre due
  vengono create.

## Note / cosa manca
- Lo scarto è silenzioso: nessun `RunLog` e nessun contatore delle offerte
  scartate per lunghezza o per campi mancanti.
- Le fonti non dicono se i 254 job rimasti senza punteggio nel caso reale
  siano stati valutati in seguito. Il codice non ha un meccanismo di
  nuovo tentativo per i job senza score.
- `external_id` (`max_length=255`) non è tra i campi controllati.
- Il controllo vale solo per la raccolta (notturna e manuale), non per
  l'import da link (`import_service.py`), che salva l'URL inserito
  dall'utente così com'è.
- Qualsiasi altra eccezione dentro il ciclo di creazione continua a
  interrompere l'intera raccolta dell'utente, lasciando senza punteggio i
  job già creati.
