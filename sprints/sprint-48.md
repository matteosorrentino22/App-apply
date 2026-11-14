# Sprint 48 — Cap deterministico sulla lingua richiesta dall'offerta

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-09-28 · **Commit:** `c99b873`

## Input
Segnalazione del committente (28/09): compaiono job con punteggio alto in
lingue che il candidato non conosce, spesso in tedesco e su Zurigo.
Richiesta: la lingua richiesta deve essere discriminante, e un job non può
avere un punteggio alto se quella lingua non è nel profilo.

Comportamento osservato in produzione (dal messaggio di commit):
- il modello citava testualmente il requisito di lingua tra i gap (es.
  "sehr gute Deutschkenntnisse") ma assegnava comunque un punteggio alto,
  diluito dagli altri match positivi;
- in un caso ha messo la lingua mancante tra i *match* con una motivazione
  inventata ("adattabilità linguistica").

## Decisioni prese
- **Il cap non è lasciato al modello.** Il modello si limita a dichiarare in
  un campo strutturato se l'offerta richiede una lingua. Il confronto con le
  lingue del profilo e il taglio del punteggio sono fatti in Python, perché
  non ci si può fidare che il modello applichi il vincolo da solo in modo
  affidabile.
- **Tetto:** al massimo 3/10 se la lingua richiesta non è nel profilo a
  nessun livello. Qualsiasi livello, anche elementare, conta come presente.
- **Quando una lingua conta come "richiesta":** se è dichiarata
  esplicitamente come necessaria, oppure se l'offerta è scritta interamente
  in una lingua diversa dall'inglese.
- **Eccezione:** nessun cap se l'offerta dichiara esplicitamente un ambiente
  internazionale o di lavoro in inglese.
- **Confronto per parola intera**, non per sottostringa. Bug intercettato
  in verifica: "es" (codice dello spagnolo) è contenuto in "tedesco".

## Implementazione

### Backend
- `apps/jobs/ai_scoring.py`:
  - nuovo `_LANGUAGE_CHECK_SCHEMA` con i campi `required` (bool),
    `language` (string) e `international_exception` (bool). È aggiunto come
    campo obbligatorio `language_check` in `SCORE_JSON_SCHEMA`;
  - prompt: nuova sezione "Attenzione particolare alla lingua" con i
    criteri e l'eccezione descritti sopra, e due nuove regole:
    - 7: una lingua assente dal profilo non va mai messa in `score_match`;
    - 8: `language_check` va compilato sempre.
- `apps/jobs/scoring.py`:
  - `LANGUAGE_MISMATCH_SCORE_CAP = 3`;
  - `_words()`: tokenizza in parole intere senza distinguere maiuscole e
    minuscole (regex `[^\W\d_]+`, `casefold`);
  - `_profile_language_words(profile)`: parole di tutte le etichette
    localizzate (it/en/fr/de/es, da
    `apps.profiles.language_options.LANGUAGE_NAME_LABELS`) delle lingue del
    profilo. Il codice ISO è escluso di proposito;
  - `_language_score_cap(result, profile)`: restituisce `None` se
    `required` è falso, se c'è l'eccezione internazionale, se la lingua è
    vuota o se c'è almeno una parola in comune con il profilo. Altrimenti
    restituisce il cap;
  - `_apply_score_result(job, result, profile)`: se il cap scatta, il
    punteggio viene abbassato e `score_reasoning` riceve il prefisso
    "Punteggio limitato a 3/10: lingua richiesta (<lingua>) assente dal
    profilo.";
  - `score_job` e `score_jobs`/`_score_call` passano il profilo
    (pre-caricato) anche ad `_apply_score_result`.

### Modello dati / Frontend
Nessuna modifica.

## Verifica
- 4 nuovi test in `apps/jobs/tests.py` (`ScoreJobTests`):
  - cap applicato anche se il modello restituisce 9;
  - nessun cap se la lingua è nel profilo;
  - regressione sottostringa "es" contenuto in "Tedesco";
  - nessun cap con `international_exception`.
- Fixture `FAKE_SCORE_RESULT` aggiornata con `language_check`.
- Il messaggio di commit dichiara una verifica su un campione reale: 349
  job del giorno di un utente con Zurigo tra le location e nessun tedesco
  nel profilo. I job in tedesco con requisito esplicito passano da 6–8 a
  3; quelli in francese (lingua presente nel profilo) restano invariati.

## Note / cosa manca
- Nessun ri-scoring dello storico: i job valutati prima dello sprint
  conservano il punteggio originale.
- Il prefisso aggiunto a `score_reasoning` è sempre in italiano, qualunque
  sia la lingua dell'interfaccia.
- Il cap dipende comunque dal modello: se il modello non segnala la lingua
  (`required=false`), il cap non scatta. Inoltre il prompt di scoring non
  include la località del job (solo titolo, azienda e descrizione).
