# Sprint 09 — Ciclo notturno orchestrato

## Input
- Sprint 07 (raccolta) e Sprint 08 (scoring) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.4; `02-specifiche-tecniche-v3.md` §5.1, §7.

## Obiettivo
Orchestrare raccolta → scoring → cap di intake (15 job/utente/giorno, tie-break su `published_at` più recente o casuale se mancante/pareggio persistente) come task Celery Beat schedulato alle 02:00 Europe/Rome; scarto definitivo degli eccedenti; `RunLog` completo dell'esecuzione.

## Risultato atteso
Un'esecuzione simulata del ciclo notturno, per un utente con più di 15 Job scorati, mantiene solo i 15 a punteggio più alto (con tie-break corretto) e scarta definitivamente gli altri.

## Criteri di verifica
- Eseguendo il task orchestratore su dati di test con >15 Job scorati per un utente, al termine risultano tenuti esattamente 15 Job e gli altri sono esclusi in modo da non essere riproposti in esecuzioni successive.
- Test del tie-break: con più Job a pari punteggio al confine del taglio, viene preferito quello con `published_at` più recente; con data mancante su entrambi (o pareggio persistente), la selezione avviene in modo deterministico nel test (tramite seed/mock del meccanismo casuale), senza errori.
- Celery Beat ha una entry schedulata per le 02:00 Europe/Rome (verificabile da configurazione/admin `django_celery_beat`).
- `RunLog` registra l'esecuzione con conteggio job raccolti, scorati, scartati per cap, scartati per fallimento scoring.

## Output per lo sprint successivo
Per ogni utente, al massimo 15 Job/giorno con score, pronti per la generazione automatica del CV (Sprint 11), che si innesta su questo stesso task.

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.jobs.intake.apply_intake_cap(user, scored_jobs)` — applica il cap di 15 job/utente/giorno: mescola il batch (`random.shuffle`), poi ordina in modo stabile per `(-score, -published_at)`. Poiché l'ordinamento Python è stabile, i pareggi (stesso score, stessa data o entrambe assenti) mantengono l'ordine casuale del mescolamento pre-ordinamento — un solo meccanismo copre sia "tie-break su data più recente" sia "casuale se la data manca o il pareggio persiste" (§4.4 funzionali), ed è deterministico nei test con `random.seed(...)`.
- `apps.jobs.tasks.run_nightly_cycle_for_user(user)` — orchestrazione per singolo utente: raccolta (Sprint 07) → scoring (Sprint 08) → cap di intake, con una `RunLog` di riepilogo (`task_type=collection`, `status=success`) che riporta nel messaggio i conteggi raccolti/scorati/scartati-per-scoring/scartati-per-cap/tenuti.
- `apps.jobs.tasks.run_nightly_cycle` — task Celery (`@shared_task`) che itera tutti gli utenti e invoca l'orchestrazione per ciascuno; registrato automaticamente da `app.autodiscover_tasks()` (già configurato dallo Sprint 01, nessuna modifica necessaria a `config/celery.py`).
- **`django-celery-beat`** aggiunto (nuova dipendenza, segnalata come richiesto da CLAUDE.md: il criterio di verifica dello sprint la nomina esplicitamente — "verificabile da configurazione/admin `django_celery_beat`" — quindi non è una scelta arbitraria ma quanto previsto dal piano sprint). `CELERY_BEAT_SCHEDULER` puntato al suo `DatabaseScheduler`, così la schedulazione è gestibile da Django Admin invece che da un dizionario statico in `settings.py` — coerente con l'approccio già scelto per piani/credito/voucher (§9 tecniche). Una migrazione dati (`jobs.0003_schedule_nightly_cycle`) crea, in modo idempotente (`get_or_create`), il `CrontabSchedule` (02:00, `Europe/Rome`) e il `PeriodicTask` collegato a `apps.jobs.tasks.run_nightly_cycle`.
- **Decisione tecnica non esplicitamente richiesta, da segnalare**: aggiunto un nuovo campo booleano `Job.discarded_by_cap` (migrazione `jobs.0002`). Motivo: il cap deve "scartare definitivamente" gli eccedenti in modo che non vengano più mostrati né rientrino nella generazione automatica del CV (Sprint 11) — ma le righe **non vengono cancellate**, perché la deduplica per `(user, source, external_id)` (Sprint 07) verifica l'esistenza della riga in DB, non un suo stato: cancellarle avrebbe permesso a un'offerta scartata di essere ri-raccolta in futuro. Non esiste già un campo adatto per questo (`is_archived` è una dimensione utente-facing — sezione "Archivio" — semanticamente diversa da "scartato dal sistema per il cap"; usarlo per questo scopo avrebbe fatto comparire scorrettamente questi job in Archivio). Il nuovo campo è booleano e ortogonale allo `status`, sullo stesso modello di `is_archived`/`cv_generation_in_progress` già esistenti — non introduce un nuovo valore di `status` (che CLAUDE.md vieta esplicitamente di estendere oltre i tre stabili + il transitorio).

### Verifica eseguita
`python manage.py test apps.jobs` (14/14, incluse le 9 di Sprint 07/08) e `python manage.py test` sull'intero progetto (26/26, nessuna regressione); `makemigrations --check` pulito; verificato da shell che il `PeriodicTask` esiste con `task='apps.jobs.tasks.run_nightly_cycle'`, `crontab.hour='2'`, `crontab.minute='0'`, `crontab.timezone='Europe/Rome'`, `enabled=True`.

| Criterio | Esito |
|---|---|
| >15 Job scorati per un utente → tenuti esattamente 15, gli altri esclusi (mai riproposti: dedup su riga esistente) | ✅ |
| Tie-break: preferito `published_at` più recente al confine del taglio | ✅ |
| Tie-break casuale con data mancante/pareggio persistente, deterministico nel test via seed | ✅ |
| Celery Beat ha una entry schedulata per le 02:00 Europe/Rome, verificabile da `django_celery_beat` | ✅ (`PeriodicTask`/`CrontabSchedule` via migrazione dati) |
| `RunLog` registra l'esecuzione con conteggio raccolti/scorati/scartati-cap/scartati-scoring | ✅ (nel campo `message`, formato leggibile) |

### Cosa manca
- Nessuna verifica end-to-end reale (Apify + Claude) possibile in sandbox — stessa riserva degli sprint precedenti; la logica di orchestrazione è comunque interamente testata con raccolta/scoring mockati.
- Collegamento della generazione automatica del CV per i Job 4–5 tenuti: Sprint 11 (dopo il servizio di generazione del Sprint 10).
