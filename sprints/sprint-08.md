# Sprint 08 — Scoring

## Input
- Sprint 07 completato (Job raccolti); Sprint 04 (profilo per il confronto).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.4; `02-specifiche-tecniche-v3.md` §3.5, §5.1 punto 2.

## Obiettivo
Task di scoring che, per ogni `Job` non ancora valutato, chiama Claude per ottenere `score` (1–5), `score_match`, `score_gaps`, `score_reasoning`; in caso di fallimento della singola chiamata, il Job viene scartato per quella notte e l'evento tracciato in `RunLog`.

## Risultato atteso
Eseguendo il task su un insieme di Job raccolti, ciascuno riceve un punteggio con motivazione e scomposizione match/gap, oppure viene escluso con traccia in `RunLog` se lo scoring fallisce.

## Criteri di verifica
- Con mock della risposta Claude valida, dopo l'esecuzione il Job ha `score` (1–5), `score_match`, `score_gaps`, `score_reasoning` valorizzati.
- Con mock che simula un errore/timeout per un Job specifico, quel Job resta privo di score e in `RunLog` compare una entry che lo referenzia.
- Un Job scartato per fallimento scoring non compare tra i candidati passati al cap di intake (Sprint 09).
- Eseguendo il task su un batch misto (alcuni Job che falliscono, altri no), gli altri Job del batch ricevono comunque lo score senza eccezioni non gestite.

## Output per lo sprint successivo
Job scorati (o scartati con traccia in RunLog), pronti per l'applicazione del cap di intake (Sprint 09).

---

## Esito (2026-07-26)

**Stato: completato**, con la stessa riserva di ambiente già segnalata per Sprint 05/07 (nessuna chiamata reale a Claude verificabile in sandbox).

### Cosa è stato fatto
- `apps.jobs.ai_scoring.score_job_with_claude(job, profile)` — unico punto che chiama Claude per lo scoring: costruisce un riassunto testuale di profilo (sommario, esperienze con bullet, competenze) e offerta (titolo, azienda, descrizione), e ottiene `score`/`score_match`/`score_gaps`/`score_reasoning` tramite `output_config.format` JSON schema (stessa tecnica di Sprint 05, risposta sempre JSON valido). **Solleva** l'eccezione a chi chiama in caso di errore — non la ingoia — perché la gestione del fallimento è responsabilità del chiamante.
- `apps.jobs.scoring.score_job(job)` — orchestrazione del singolo job: cattura qualunque eccezione di `score_job_with_claude`, e in tal caso **non** applica alcuno score (il Job resta scartato per la notte) e crea una `RunLog` (`task_type=scoring`, `status=failure`) che referenzia sia lo `user` sia il `job`. In caso di successo valorizza tutti e 4 i campi più `date_scored`, con lo `score` vincolato a 1–5 per difesa (i vincoli numerici non sono garantiti dagli output strutturati dell'API).
- `apps.jobs.scoring.score_jobs(jobs)` — scoring di un batch: itera i job e isola i fallimenti (usa lo stesso `score_job`, nessuna propagazione di eccezioni tra un job e l'altro), ritornando solo i job scorati con successo — pronta per essere combinata con il cap di intake (Sprint 09), che riceverà così solo job con score valorizzato.
- **Decisione tecnica esplicitamente prevista dalle tecniche, da segnalare per trasparenza**: modello di scoring di default impostato su **`claude-haiku-4-5`** (via nuova `ANTHROPIC_SCORING_MODEL`, configurabile), non `claude-opus-5`. Non è una deviazione arbitraria dalle mie istruzioni generali sul modello di default: `02-specifiche-tecniche-v3.md §3.5` chiede esplicitamente "una famiglia più economica per lo scoring ad alto volume" (gira ogni notte su tutti i job di tutti gli utenti) e riserva un modello più capace alla generazione del CV — la scelta resta un parametro di configurazione via env, non un vincolo architetturale.
- Suite di test automatici aggiunta a `apps/jobs/tests.py` (`ScoreJobTests`, 3 test) con `score_job_with_claude` mockato.

### Verifica eseguita
`python manage.py test apps.jobs` (9/9, incluse le 6 di Sprint 07) e `python manage.py test` sull'intero progetto (21/21, nessuna regressione); `makemigrations --check` pulito (nessun modello nuovo).

| Criterio | Esito |
|---|---|
| Mock risposta Claude valida → `score`/`score_match`/`score_gaps`/`score_reasoning` valorizzati | ✅ |
| Mock errore/timeout su un Job → resta privo di score, entry in `RunLog` che lo referenzia | ✅ |
| Job scartato per fallimento non passa al cap di intake | ✅ per costruzione: `score_jobs` ritorna solo i job scorati con successo (il filtro esplicito arriva comunque con Sprint 09) |
| Batch misto: gli altri Job ricevono comunque lo score, nessuna eccezione non gestita | ✅ (`score_jobs` isola il fallimento di un singolo job) |

### Cosa manca
- Chiamata reale a Claude non verificabile in sandbox (nessuna `ANTHROPIC_API_KEY` reale) — stessa riserva di Sprint 05.
- Orchestrazione schedulata (raccolta → scoring → cap) come task Celery Beat: Sprint 09.
