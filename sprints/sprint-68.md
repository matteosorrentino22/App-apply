# Sprint 68 — Difetti di lista job, scoring e raccolta

> **Periodo:** 14/11/2026 · **Numero:** 68 (lo Sprint 67, privacy/GDPR, è sviluppato in parallelo su un altro ramo; il coordinatore unisce i due lavori).
> **Stato:** implementato e verificato in container su un ramo separato; **deploy da eseguire a mano** (passi in fondo e in `DEPLOY.md` §4.6), compresi i comandi sui dati di produzione.

## Input

- `Docs/01-specifiche-funzionali-v6.md` §8.A, punti 1–16 (lista, scoring, dati storici, raccolta), escluso il punto 6 (provenienza multipla, non richiesto).
- `Docs/02-specifiche-tecniche-v5.md` §11, punti 9, 10, 12, 13, 18–22, 36 (per quanto riguarda lista, scoring e raccolta).
- Fuori perimetro, perché li tratta lo Sprint 67: account, notifiche, pagine legali, impostazioni dell'account, backup. Di Impostazioni è stato toccato solo il gestore delle ricerche salvate (`AccountPage.jsx`, funzioni delle ricerche); dell'Admin di `User` solo i campi di raccolta/inattività e le azioni sui contatori.

## Decisioni del committente

- I **job con `discarded_by_cap=True`** (988) vanno **eliminati**, con documenti e bozze, tramite un comando con dry-run di default e `--confirm`, lanciato dal coordinatore in produzione dopo un backup. Il campo si rimuove dal modello solo dopo l'eliminazione, con una migrazione che si ferma in modo esplicito se restano righe marcate.
- I **punteggi storici su scala 1–5** vanno **riscalati ×2** (1→2 … 5→10), con un marcatore nel DB e un comando idempotente con dry-run. Il **limite per lingua dello Sprint 48 non va riapplicato** retroattivamente (costerebbe una chiamata AI per job).
- I **job senza punteggio** vanno ritentati in automatico al ciclo notturno successivo, con un numero massimo di tentativi, e con un comando manuale. Per il job creato a mano con scoring fallito: scegliere tra restituzione della quota e nuovo tentativo di scoring.

## Decisioni prese

- **Job manuale con scoring fallito → nuovo tentativo, nessuna restituzione.** Il job esiste ed è ciò che la quota paga; il nuovo tentativo è lo stesso meccanismo dei job raccolti, senza un percorso di addebito in più; restituire la quota renderebbe gratuito un job che resta in lista. La quota è invece restituita se è la **creazione** a fallire (§11.20).
- **Limite di tentativi:** `MAX_SCORING_FAILURES = 3` fallimenti per job (`Job.scoring_failures`). Ogni tentativo contiene già i 3 retry interni di `call_claude_structured`. I 54 job senza punteggio esistenti partono da 0. Il comando manuale può superare il limite con `--ignore-limit`.
- **Taglio della riscalatura: 2026-09-24 21:00 UTC, non la data del commit.** Il commit `d0faa0d` dello Sprint 47 è del 2026-09-28 14:39 UTC, ma il codice era in produzione dal 24/09 sera. Verificato sul dump del 2026-11-14 (ripristinato in un PostgreSQL usa e getta, mai sul DB di produzione): l'ultimo punteggio 1–5 è delle 08:37 UTC del 24/09 (massimo 5), il primo su 1–10 delle 21:07 UTC dello stesso giorno (un 6), con nessuno scoring in mezzo; la migrazione `jobs/0011` risulta applicata alle 21:10 UTC. Con la data del commit si sarebbero raddoppiati 928 punteggi (tra il 24 e il 28/09) già su 1–10. Il comando accetta `--before` per un taglio diverso e segnala, senza toccarli, eventuali punteggi > 5 prima del taglio.
- **FK della ricerca di provenienza** (`Job.matched_saved_search`, `SET_NULL`): valorizzata dalla fonte, che conosce il gruppo di ogni offerta. Nel gruppo la ricerca si individua dall'etichetta dell'actor (Company: nome azienda; Job role: `"<keywords> - <città>, <paese>"`), senza maiuscole, o perché è l'unica del gruppo. Il **backfill** (migrazione `jobs/0018`) usa la regola testuale del vecchio filtro sui valori attuali delle ricerche e assegna solo le corrispondenze **univoche**. Gli ambigui (es. la stessa azienda cercata in due città) restano senza FK, e per loro il filtro continua a usare il confronto testuale, cioè il comportamento di prima. `matched_search` resta l'etichetta del badge.
- **Esito per gruppo:** un gruppo fallito rende il `RunLog` `collection` **FAILURE** anche se gli altri gruppi sono stati raccolti, per vederlo filtrando in Admin. Se falliscono tutti, la raccolta fallisce come prima: per la raccolta manuale 502 con quota restituita; se fallisce solo una parte, la raccolta manuale riesce (200).
- **Guardia condivisa:** lo stesso `User.collection_in_progress` (con la scadenza di 2 ore). Il ciclo notturno salta l'utente con un `RunLog` nel nuovo stato `skipped`; la raccolta manuale durante il ciclo notturno dell'utente riceve il solito 409 "Raccolta già in corso".
- **PATCH del tipo di ricerca:** cambiare tipo a una ricerca attiva equivale ad attivarla nel nuovo tipo (`activate_search`, in transazione). Su Free spegne l'altra ricerca attiva di quel tipo e la restituisce in `deactivated_previous`, con lo stesso avviso dell'attivazione; su Pro non cambia nulla, perché il pool è unico.
- **Filtri della lista nell'URL** (`useSearchParams`, `replace` a ogni modifica, così i filtri non riempiono la cronologia): il back del browser dal dettaglio torna alla lista filtrata e l'URL è condivisibile. L'ultima query è anche in `sessionStorage`, per il link "Torna alla lista" del dettaglio (che si raggiunge anche dagli editor). Senza parametri le date valgono "oggi". `from=`/`to=` vuoti vogliono dire "tutte le date".
- **Admin dei documenti e delle bozze in sola lettura** (nessuna aggiunta né modifica, eliminazione consentita), senza `html_source`; in lista solo job, utente e date.
- **Test su un PostgreSQL usa e getta** (`postgres:16-alpine` su una rete Docker dedicata) invece del server di produzione, per non collidere sul nome `test_<db>` con l'altro agente. Così non è servito aggiungere `TEST_DB_NAME` ai settings.

## Implementazione

### Modello dati e migrazioni (`apps/jobs`)
- `Job.matched_saved_search` (FK nullable a `searches.SavedSearch`, `SET_NULL`, `related_name="jobs"`), `Job.score_rescaled_from_legacy` (bool), `Job.scoring_failures` (int); `RunLog.Status.SKIPPED`; `Job.discarded_by_cap` rimosso.
- `0017_sprint68_job_fields`: nuovi campi, nuovo stato `RunLog`, `db_default=False` sulla colonna `discarded_by_cap`, così il codice nuovo può inserire job anche prima che la colonna venga rimossa.
- `0018_backfill_matched_saved_search`: backfill univoco (sopra).
- `0019_remove_job_discarded_by_cap`: `RunPython` che si ferma con un `RuntimeError` esplicito ("Ci sono ancora N job con discarded_by_cap=True: eseguire prima …") se restano righe marcate, poi `RemoveField`.

### Comandi (`apps/jobs/management/commands/`)
- `delete_discarded_by_cap_jobs [--confirm]`: legge la colonna con SQL (il campo non è più nel modello), stampa il dettaglio per stato/archiviato/preferito e i documenti e le bozze collegati, elimina in transazione (cascata Django) e cancella i PDF dal disco a commit avvenuto. Se la colonna non c'è più non fa nulla.
- `rescale_legacy_scores [--confirm] [--before ISO]`: `score = score * 2` e `score_rescaled_from_legacy = True` sui job con `date_scored` prima del taglio, punteggio tra 1 e 5 e non ancora marcati. È idempotente.
- `retry_unscored_jobs [--dry-run] [--user-id N] [--ignore-limit]`: stesso insieme di job del retry notturno (`scoring.unscored_jobs_to_retry`), scorato in parallelo con `score_jobs`.

### Raccolta e scoring
- `sources/apify_linkedin.py`: `fetch_groups()` restituisce `{label, offers, error}` per gruppo e intercetta l'eccezione di ciascun gruppo; ogni offerta porta `saved_search_id` (`_attribute_to_search`). `fetch()` resta come appiattimento che solleva il primo errore.
- `collection.py`: `collect_jobs_for_user` restituisce un `CollectionResult` (job creati, scarti per motivo, esiti per gruppo) e solleva `CollectionFailed` se falliscono tutti i gruppi; `offer_rejection_reason()` è condivisa con l'import.
- `scoring.py`: `scoring_failures` +1 a ogni fallimento (anche in `score_job`), `MAX_SCORING_FAILURES`, `unscored_jobs_to_retry()`.
- `tasks.py`: `_run_collection_cycle` (raccolta → scoring dei nuovi e dei job da ritentare → `RunLog` con conteggi, scarti e una riga per gruppo), condiviso da `run_nightly_cycle_for_user` (guardia condivisa, skip con `RunLog` SKIPPED) e da `run_manual_collection_for_user`.
- `ai_scoring.py`: `Località: …` nel testo dell'offerta e una menzione nel prompt di sistema. Il prefisso del cap lingua resta in italiano: la traduzione dei testi del backend è prevista in uno sprint successivo.

### Import, job manuale, ricerche
- `import_service.py`: controlli di `offer_rejection_reason` dopo la lettura dell'offerta (riserva restituita, 409); creazione in savepoint, `IntegrityError` → `ImportDuplicate` con riserva restituita; qualunque altro errore di creazione → riserva restituita.
- `manual_job_service.py`: `_refund` e `ManualJobFailed` se la creazione fallisce dopo la riserva (la view risponde 502).
- `searches/views.py`: `update`/`perform_update` con la regola dell'attivazione quando cambia il tipo di una ricerca attiva, `deactivated_previous` nella risposta.
- `list_service.py`: filtro "Ricerca" per FK, con ripiego sull'etichetta per i job senza FK; "Nessuna ricerca" = etichetta vuota e FK nulla.

### Admin
- `apps/jobs/admin_actions.py`: "Azzera la quota di raccolta manuale di oggi" e "Azzera tutti i contatori giornalieri di oggi" (lista utenti, giorno Europe/Rome), "Azzera tutti i contatori delle righe selezionate" (lista `DailyQuota`).
- `DailyQuotaAdmin` con i 7 contatori; `JobAdmin` senza `discarded_by_cap`, con `score_rescaled_from_legacy`, `scoring_failures` e gli id per `user`/`matched_saved_search`; `JobFilterPresetAdmin` in sola lettura; `cv/admin.py` con `CVDraft`, `CoverLetterDocument`, `CoverLetterDraft`, `ReferralMessageDocument` in sola lettura.
- `accounts/admin.py`: solo un fieldset "Raccolta e inattività" (`collection_in_progress`, `collection_started_at`, `last_inactivity_notified_at`) e le due azioni.

### Frontend
- `JobListPage.jsx`: sezione e filtri nella query string (`section`, `from`, `to`, `q`, `location`, `score`, `status`, `search`, `applicants`, `recruiter`), più `sessionStorage` (`utils/jobListUrl.js`); i preset salvati da Importati hanno `search_ids: []`; eliminazione di un preset con ripristino della pillola e messaggio "Non siamo riusciti a eliminare il filtro. Riprova." (it/en).
- `JobDetailPage.jsx`: "Torna alla lista" con l'ultima query della lista.
- `AccountPage.jsx` (solo le ricerche): `applySearchUpdate` per attivazione e modifica, con il messaggio "Hai già una ricerca attiva di questo tipo: "…" è stata disattivata (il piano Free ne consente una per tipo)." (it/en).
- `translations.js`: testo della card "Raccogli ora" corretto (it/en): la raccolta manuale cerca subito le offerte delle ultime 24 ore, e la raccolta notturna gira comunque.
- Punteggi: nessuna modifica necessaria. `scoreStyle.js` usa le fasce `ceil(score/2)` e `MultiSelectFilter` i valori 1–10; dopo la riscalatura tutti i punteggi sono sulla scala 1–10.

## Conteggi sul dump del 2026-11-14 (prima dello Sprint 66, ripristinato in locale)

- Job totali 15.645; con `discarded_by_cap=True` **988**: **nessuno** ha CV, cover letter, messaggi di networking, bozze o `RunLog` collegati. 985 sono "nuovo" non archiviati, 2 "nuovo" archiviati e **1 "candidatura fatta"**: verrà eliminato anche questo, salvo smarcarlo prima (comando in `DEPLOY.md` §4.6).
- Punteggi su scala 1–5 (prima del taglio): 3.898, di cui 988 sui job da eliminare, quindi **2.910 da riscalare** (1: 152, 2: 1.645, 3: 637, 4: 471, 5: 5). Nessun punteggio > 5 prima del taglio.
- Job senza punteggio: **54** (53 raccolti, 1 creato a mano), tutti ritentabili.
- Backfill della FK: 13.568 job attribuiti su 14.486 con un'etichetta di provenienza (dopo l'eliminazione); 918 restano sul confronto testuale.
- La sequenza di deploy (migrazioni fino alla 0018, 0019 che si rifiuta, eliminazione, riscalatura, 0019) è stata provata per intero su questa copia.

## Verifica

- **Backend** (immagine `appapply-s68-web`, project `appapply-s68`, PostgreSQL usa e getta; nessun container di produzione toccato): **340 test OK** (299 preesistenti + 41 nuovi in `apps/jobs/test_sprint68.py`). Adeguati i test esistenti della raccolta alla nuova interfaccia della fonte (`fetch_groups`) e al risultato di `collect_jobs_for_user`; tolta l'asserzione su `discarded_by_cap`.
- Con `REGISTRATION_INVITE_CODE` valorizzato nel `.env` di produzione, due test di registrazione (`accounts/test_security.py`) rispondono 400: non è una regressione di questo sprint, si risolve passando `-e REGISTRATION_INVITE_CODE=` (annotato in `DEPLOY.md` §4.4).
- `makemigrations --check --dry-run` → "No changes detected".
- **Frontend**: build dell'immagine `appapply-s68-frontend-build`, `npm run build` OK, `npx oxlint src` 0 errori (9 warning `only-export-components` preesistenti).
- **Non verificato** (servono un browser o il deploy): e2e Playwright; comportamento del back del browser e del link "Torna alla lista" sulla PWA iOS; RunLog reali di una notte con un gruppo in errore.

## Passi di deploy (manuali, in ordine)

Dettaglio dei comandi in `DEPLOY.md` §4.6. Se nello stesso rilascio entra anche lo Sprint 67, i suoi passi vanno inseriti prima dell'avvio (passo 7).
1. Backup locale del database.
2. `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
3. `docker compose -f docker-compose.prod.yml stop web worker beat`.
4. `docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py migrate jobs 0018`.
5. `… run --rm --no-deps web python manage.py delete_discarded_by_cap_jobs` (dry-run), poi con `--confirm`.
6. `… run --rm --no-deps web python manage.py rescale_legacy_scores` (dry-run), poi con `--confirm`.
7. `docker compose -f docker-compose.prod.yml up -d` (applica la `jobs/0019`).
8. Facoltativo: `… exec web python manage.py retry_unscored_jobs --dry-run`, poi senza `--dry-run` (54 chiamate AI circa); altrimenti ci pensa il ciclo notturno.
9. Verifiche: stack coerente; in Admin i job riscalati e i nuovi modelli; la mattina dopo, `RunLog` `collection` con gli esiti per gruppo.

## Cosa manca

- Il **limite per lingua** non è riapplicato ai job valutati prima dello Sprint 48 (decisione del committente: costerebbe una chiamata AI per job).
- **Provenienza multipla** (§8.A punto 6): non richiesta.
- Il prefisso del cap lingua, i messaggi del `RunLog` e gli errori API restano in italiano (traduzione dei testi del backend prevista in uno sprint successivo).
- I job di una **ricerca eliminata** perdono la FK (`SET_NULL`) e, salvo coincidenze testuali con un'altra ricerca, non compaiono più sotto nessuna voce del filtro "Ricerca" (come prima).
- Un errore imprevisto durante la creazione dei job interrompe ancora la raccolta dell'utente: i job già creati vengono scorati dal retry, le offerte successive si perdono per quella notte.
- Il ciclo notturno resta sequenziale su tutti gli utenti in un unico task.
- Possibili conflitti di merge con lo Sprint 67 in `apps/accounts/admin.py` (fieldset di `User`), `AccountPage.jsx`, `translations.js`, intestazioni e §11 di `Docs/01`/`Docs/02`, `Docs/CHANGELOG.md` e `DEPLOY.md` §4.
