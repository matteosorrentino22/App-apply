# Sprint 77 — Raccolta automatica Pro, Free solo manuale, nessun ciclo notturno

> **Periodo:** 2026-11-15 · **Branch:** `sprint-77-raccolta` (da `sprint-76-editor`, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato e verificato (backend 488/488, e2e 46/46, migrazione provata su un database di prova); **merge e deploy non fatti** (in attesa dell'ok del committente). Nessun accesso al database di produzione.

## Input
`Docs/design/IMPLEMENTATION-PLAN.md` (sprint 77), `SPEC-DELTA.md` A4/A5 e B1–B4, piano approvato dal committente il 2026-11-15. Mockup `collect-pro`, `collect-free`, `collect-running`, `settings-limiti`.

Prima dello sprint (commit separato `4c78973` sullo stesso branch): istanza di anteprima con dati finti (`DEPLOY.md` §10) e blocco `anteprima.{$DOMAIN}` nel Caddyfile di produzione, applicato con `caddy reload` dopo il via libera (diff e `caddy validate` mostrati prima; produzione 200 prima e dopo).

## Decisioni del committente
- **Una raccolta al giorno per utente**, automatica o manuale, sul giorno di Europe/Rome (azzeramento a mezzanotte come oggi), per il costo delle chiamate Apify (B2 corretta: l'automatica **consuma** `COLLECTION_DAILY_LIMIT`).
- **Pro:** raccolta automatica all'orario scelto, nel **fuso dell'utente** (B3); la manuale resta ma condivide la stessa quota (B1). Se l'automatica ha già girato, "Raccogli" è bloccato con "già eseguita oggi alle HH:MM"; se l'utente raccoglie a mano prima dell'orario, l'automatica di quel giorno è saltata (`RunLog` SKIPPED).
- **Free:** solo manuale, 1 al giorno; opzione automatica bloccata con invito al Pro.
- **Niente ciclo notturno delle 02:00 né notifica delle 10:00** per nessuno; ai Pro una notifica a fine raccolta automatica se ci sono job nuovi; restano i promemoria di inattività (B4).
- Senza ricerche attive **non si consuma la quota**, né per la manuale né per l'automatica.
- Correggere il difetto latente: la quota restituita torna **sulla riga giornaliera riservata**, non sul giorno corrente.
- Fallimento dopo chiamate già pagate: la quota resta consumata; blocco con scadenza a 2 ore come oggi.
- Migrazione dati: automatica alle **07:00** per i Pro esistenti; i nuovi Pro partono con l'automatica spenta.
- Informativa 1.0 → 1.1 (it/en), nuovo dato in elenco dati ed export.
- **Il mockup `collect-pro` mostra automatica e manuale come due limiti separati ("1 raccolta manuale al giorno"): non vale, vale la quota unica.** Allo stesso modo `settings-limiti` ("Raccolta manuale 1/1") diventa una riga "Raccolta giornaliera 0/1".

## Implementazione
### Backend
- **Modello:** `User.auto_collection_enabled` (default no), `auto_collection_time` (default 07:00), `auto_collection_last_local_date` (data locale dell'ultima automatica avviata) — `accounts/0011`; `DailyQuota.collection_done_at` (inizio della raccolta di oggi) — `jobs/0021`.
- **Migrazioni dati:** `accounts/0012_enable_auto_collection_for_pro` (Pro esistenti: automatica alle 07:00, data locale di oggi già segnata → prima raccolta il giorno dopo il rilascio; fuso non valido → Europe/Rome; inversa no-op); `jobs/0022_replace_nightly_cycle_schedule` (toglie "Ciclo notturno…", crea "Raccolte automatiche Pro (ogni 15 minuti)"; l'inversa ricrea il crontab delle 02:00); `notifications/0003_remove_morning_notification` (toglie la notifica mattutina; l'inversa la ricrea).
- **`apps/jobs/tasks.py`:** rimossi `run_nightly_cycle` e `run_nightly_cycle_for_user`. Nuovi: `_reserve_collection_quota` (riserva e `collection_done_at`, oppure `CollectionDailyLimitReached` con "Raccolta di oggi già eseguita alle HH:MM…" nel fuso dell'utente, con la data se il suo "oggi" non coincide), `_refund_collection_quota(quota_pk)` (sulla riga riservata), `run_automatic_collection_for_user` (guardia, SKIPPED per raccolta in corso / nessuna ricerca attiva / raccolta di oggi già fatta, refund se fallisce del tutto, notifica se `collected > 0`), task `run_automatic_collection(user_id)` (ricontrolla piano e attivazione), `automatic_collection_due` (ora "da orologio" nel fuso dell'utente ≥ orario e data locale non ancora segnata), task `run_automatic_collections` (Beat ogni 15 minuti; segna la data locale prima di avviare; errori isolati per utente). `run_manual_collection_for_user`: riserva la quota solo con ricerche attive, refund sulla riga riservata.
- **Notifiche:** rimossi `send_morning_notification(s)`; nuovo `send_new_jobs_notification(user)` (stessi testi, preferenza rispettata, aggiorna `last_notified_at`).
- **API:** `PATCH /api/accounts/me/` con `auto_collection_enabled` (solo Pro, altrimenti 400 "La raccolta automatica è riservata al piano Pro.") e `auto_collection_time` ("HH:MM" a quarti d'ora, altrimenti 400); attivando o cambiando orario dopo l'orario di oggi si parte da domani. `GET /api/accounts/usage/` con `actions.collection.done_at`. 409 di `/api/jobs/collect/` con l'ora.
- **Privacy:** `PRIVACY_VERSION` 1.1 (data 2026-11-15); informativa it/en (PWA e `Docs/legal/`): "attivazione e orario della raccolta automatica (piano Pro)" tra i dati dell'account, "notifiche sui nuovi job a fine raccolta automatica" al posto di "notifiche mattutine"; export con i tre campi nuovi; cancellazione invariata (campi dell'utente).
- **i18n:** 5 testi nuovi in `.po`/`.mo` (orario a quarti d'ora, solo Pro, raccolta già fatta con e senza ora/data).
- Commenti del codice che citavano il ciclo notturno aggiornati.

### Frontend
- `components/CollectJobsSheet.jsx`: riquadro 24 ore, "Raccogli ora" (disattivato con "Raccolta di oggi già eseguita alle HH:MM." quando la quota di oggi è usata), riga "1 raccolta al giorno, automatica o manuale" con l'esito dell'ultima raccolta, riquadro "Raccolta automatica" (Pro: interruttore e orario a quarti d'ora con il fuso, "Ora italiana" per Europe/Rome; Free: lucchetto, interruttore disattivato, "Scopri il piano Pro" → Impostazioni). I dati del consumo si ricaricano a **ogni apertura** del pannello (prima solo all'apertura della pagina: un difetto emerso dall'e2e, il pannello avrebbe mostrato "Raccogli ora" attivo dopo una raccolta automatica o fatta da un altro dispositivo).
- `utils/collection.js`: orari a quarti d'ora, testo "già eseguita" con data e ora nel fuso dell'utente, etichetta del fuso.
- Testi (it/en): nuove chiavi `home.collectDailyRule`, `collectDoneToday`, `collectDoneAt`, `collectDoneOn`, `autoCollectTitle`, `autoCollectHintPro`, `autoCollectHintFree`, `autoCollectTimeLabel`, `autoCollectItalianTime`, `autoCollectProPitch`, `autoCollectDiscoverPro`; riscritti `usage.action_collection` ("Raccolta giornaliera"), `onboarding.firstSearchHint`, `jobs.empty_main`, `account.notificationsHint`, suggerimento del fuso orario; tolti `home.collectHint` e `collectNightly`.
- Informativa (PWA) aggiornata come sopra.

## Casi limite (come gestiti)
| Caso | Comportamento |
|---|---|
| Raccolta riservata prima di mezzanotte e fallita dopo | quota restituita sulla riga del giorno riservato (test) |
| Fallimento parziale (alcuni gruppi riusciti) | quota consumata, `RunLog` FAILURE con i gruppi |
| Fallimento totale dell'automatica | quota restituita, nessun nuovo tentativo automatico lo stesso giorno (si può raccogliere a mano) |
| Nessuna ricerca attiva | manuale: nessuna chiamata alla fonte, quota non consumata, si ritentano i job senza punteggio; automatica: SKIPPED senza quota |
| Raccolta in corso (anche stantia < 2 h) | automatica SKIPPED; manuale 409 |
| Utente fuori dall'Italia | orario nel suo fuso, quota sul giorno di Roma: per un fuso molto diverso la raccolta può contare per il "domani" di Roma; il messaggio mostra data e ora nel suo fuso |
| Orario vicino a mezzanotte | il task gira ogni 15 minuti: un orario come 23:50 può partire alle 00:00 e contare per il nuovo giorno |
| Ora legale (passaggio all'ora legale) | orario inesistente (es. 02:30) → parte al primo giro dopo (03:00) |
| Ora solare (ritorno) | orario ripetuto → una volta sola (data locale già segnata) |
| Cambio di fuso o di orario dopo la raccolta | nessuna seconda raccolta (decide la quota); se l'orario è già passato la prossima è domani |
| Pro tornato Free | il task ricontrolla il piano: non raccoglie; l'impostazione resta salvata |
| Fuso non valido nel profilo | Europe/Rome |
| Worker con 1 CPU | le automatiche girano una alla volta; la manuale gira nel `web` |

## Verifica
- **Backend** (immagine dalla copia di lavoro, Postgres e Redis usa e getta, `-e DJANGO_DEBUG=true -e REGISTRATION_INVITE_CODE=`): prima esecuzione con 6 moduli che non si importavano (test del ciclo notturno e della notifica mattutina da riscrivere, previsto); dopo la riscrittura 2 asserzioni da allineare (isolamento degli errori provato sulla mattutina → sul promemoria di inattività; 409 della raccolta senza ricerche attive → con una ricerca, perché senza non si consuma più la quota); poi **488/488 OK**. `makemigrations --check`: nessuna differenza.
- **Test riscritti:** `jobs/tests.py` (ciclo per utente → `run_automatic_collection_for_user`; schedule delle 02:00 → schedule ogni 15 minuti; test dell'orchestratore notturno sostituito dall'isolamento del dispatcher in `test_sprint77.py`), `jobs/test_sprint68.py` (ritenti dello scoring con la manuale; guardia condivisa con l'automatica, che consuma la quota e la restituisce se fallisce), `notifications/tests.py` (mattutina → fine raccolta), `accounts/test_privacy.py`, `accounts/test_sprint70.py`, `common/test_i18n.py`.
- **Nuovo `jobs/test_sprint77.py` (26 test):** finestre orarie, fusi, fuso non valido, ora legale (orario inesistente e ripetuto) simulando l'ora; dispatcher solo Pro attivi e una volta al giorno; errori isolati; task che ricontrolla il piano; quota condivisa (409 con l'ora, SKIPPED); data nel messaggio con fuso diverso; nessuna quota senza ricerche attive; restituzione sulla riga riservata dopo mezzanotte (automatica e manuale); quota tenuta con fallimento parziale; push solo a fine automatica con job nuovi; API (Free 400, Pro con quarti d'ora, orario già passato → domani, `done_at` in usage, 409 in inglese, export); migrazione dati.
- **Migrazione su database di prova** (Postgres usa e getta, dati finti): schema riportato allo stato prima dello Sprint 77 (`accounts 0010`, `jobs 0020`, `notifications 0002`: le inverse ricreano 02:00 e 10:00), 4 utenti finti (Pro Roma, Pro New York, Pro con fuso non valido, Free), migrazione in avanti: i tre Pro con automatica alle 07:00 e la data locale di oggi segnata, il Free spento; PeriodicTask risultanti: backup, promemoria di inattività, "Raccolte automatiche Pro (ogni 15 minuti)".
- **Sui dati reali farebbe:** per **ogni utente con piano Pro** attiva l'automatica alle 07:00 nel suo fuso, a partire dal giorno dopo il rilascio (nessuna seconda chiamata Apify il giorno del rilascio, già coperto dal ciclo notturno delle 02:00); Free invariati; cancella i PeriodicTask "Ciclo notturno (raccolta, scoring, cap di intake)" e "Notifica mattutina (nuovi job)" e crea quello ogni 15 minuti; aggiunge colonne vuote o con default (nessun dato esistente modificato oltre ai tre campi dei Pro). Da lì in poi i Free non hanno più raccolte automatiche né notifiche del mattino. Al primo accesso tutti gli utenti riaccettano l'informativa 1.1.
- **E2e** sullo stack usa e getta (immagini `appapply-e2e-*` ricostruite): `account.spec.js` (riga "Raccolta giornaliera 0 / 1") e nuovo `collection.spec.js` (Free bloccato, Pro con orario conservato, raccolta di oggi già fatta). Prima esecuzione 8/9: il fallimento era il difetto del pannello descritto sopra (dati del consumo non ricaricati all'apertura), corretto; poi **suite completa 46/46**.
- `npm run build` OK; `npx oxlint src e2e` 0 errori, 9 warning (gli stessi).
- **Screenshot** (360/390/1280 px, utenti di prova): pannello Free, Pro con l'automatica attiva, raccolta di oggi già fatta, limiti di oggi; larghezza del documento = schermo in tutti i 12 casi.
- Stack di prova e database usa e getta abbattuti; produzione non toccata (nessun deploy, nessun accesso al suo database).

## Cosa manca / note
- Nessun deploy: i passi di rilascio sono in `DEPLOY.md` §4.10 (backup, orario di rilascio, verifiche, ritorno indietro).
- Nessuna push dopo la raccolta manuale (scelta: l'utente è nell'app).
- La notifica non dice quanti job: stessi testi della vecchia notifica mattutina (già tradotti).
- "Scopri il piano Pro" porta a Impostazioni (piano e credito): non esiste un acquisto nell'app.
