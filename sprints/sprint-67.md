# Sprint 67 — Privacy e GDPR

> **Periodo:** 14/11/2026 · **Numero:** 67 (massimo tra `git log` = 66 e `sprints/` = 66, più uno).
> **Stato:** implementato e verificato in container; **deploy da eseguire a mano** (passi in fondo e in `DEPLOY.md` §4.6).

## Input

- **Richiesta del committente:** "accettazione della privacy e tutte le cose obbligatorie per i cittadini europei all'iscrizione", più i punti GDPR rimasti aperti dall'audit dello Sprint 66 (M6 cancellazione/export dei dati, M4 backup) e la gestione del login Google lasciata in sospeso.
- **Bozze dei testi legali** (informativa privacy e termini di servizio, in italiano) fornite dal committente fuori dal repository.
- **Decisioni del committente (vincolanti):**
  - titolare del trattamento come **segnaposto**: nome, indirizzo (facoltativo) ed email privacy da variabili d'ambiente (`LEGAL_CONTROLLER_NAME`, `LEGAL_CONTROLLER_ADDRESS`, `LEGAL_CONTROLLER_EMAIL`), mai nel repository; se mancano, avviso visibile "dati del titolare da completare";
  - email via **Gmail SMTP** (password per le app); senza credenziali l'app continua a funzionare: nessuna email (warning nei log), verifica dell'indirizzo spenta (nuovi account già verificati), recupero password non disponibile con messaggio chiaro;
  - **età minima 16 anni**, dichiarata in registrazione;
  - utenti esistenti (10): **schermata bloccante** di accettazione di informativa, termini ed età al prossimo accesso, con versione e data registrate;
  - **cancellazione dell'account immediata** con conferma (password) ed email di conferma;
  - AI su Bedrock **spostata in UE** (il `.env` lo aggiorna il committente; qui `.env.example`, default e documentazione);
  - backup **locale ruotato**, ultimi 7 giorni (nessun S3);
  - login Google **nascosto** finché `GOOGLE_OAUTH_CLIENT_ID` non è valorizzato, ma citato nell'informativa ("quando sarà disponibile"); il flusso sessione → token resta da completare.

## Decisioni prese

- **Gate delle accettazioni come permesso DRF di default** (`LegalAcceptanceRequired` in `DEFAULT_PERMISSION_CLASSES`), non come middleware: il token si risolve una volta sola, nel normale flusso DRF. Per non lasciare buchi sono state **tolte le `permission_classes = [IsAuthenticated]` esplicite** da tutte le view che le ripetevano (job, profilo, ricerche, notifiche): ora usano il default. Regola: una view che dichiara `permission_classes` è esente dal gate; le uniche esenti sono me, logout, accettazione, export, cancellazione account, cambio password e gli endpoint pubblici. Nei test il gate è spento (`LEGAL_GATE_ENABLED = not TESTING`, quasi tutti gli utenti dei test sono creati senza accettazioni) e riacceso con `override_settings` nei test dedicati.
- **Versioni come costanti** in `apps/accounts/legal.py` (`PRIVACY_VERSION = TERMS_VERSION = "1.0"`, date `2026-11-14`). La dichiarazione d'età ha come versione l'età minima ("16"). Una nuova versione di un testo richiede di nuovo l'accettazione al primo accesso.
- **Testi legali nella PWA come JSX** (`frontend/src/legal/`), nessuna dipendenza markdown; copia di riferimento in `Docs/legal/` (it/en) con i segnaposto.
- **Verifica email con firma Django** (`TimestampSigner`, salt dedicato, payload `id:email`, 3 giorni) invece di un modello di token: nessuna tabella in più. Recupero password con il `default_token_generator` di Django (monouso: cambia con l'hash della password), 3 giorni.
- **Email accodate su Celery già composte** (destinatario, oggetto, corpo): il task non legge il DB, quindi funziona anche per un utente appena cancellato e non ha problemi di commit. Se il broker non risponde l'operazione dell'utente non fallisce (eccezione registrata). Nei test `CELERY_TASK_ALWAYS_EAGER` e backend email locmem; credenziali SMTP e codice di invito del `.env` reale ignorati nei test (`TESTING`), così la suite lanciata nel container di produzione non dipende dal `.env`.
- **Non enumerazione**: con l'email attiva la registrazione risponde `201 {"verification_required": true}` sia per un'email nuova sia per una già registrata (in quel caso nessun account creato e un'email "qualcuno ha provato a registrarsi con il tuo indirizzo"); reinvio della verifica e recupero password rispondono sempre allo stesso modo. Senza email resta il comportamento di prima (400 "email già registrata"), come deciso. Il login segnala `email_not_verified` (403) solo dopo una password corretta.
- **Export via URL firmato** (10 minuti), come i PDF dello Sprint 66: un semplice link funziona anche nella PWA iOS. Il limite di 3 al giorno si applica alla richiesta autenticata che genera il link; lo ZIP è generato in modo sincrono al download.
- **Cancellazione**: i `RunLog` restano (statistiche tecniche) con `user` a NULL (SET_NULL già esistente) e `message` svuotato, perché il messaggio è il testo dell'eccezione e può contenere testo derivato dalle richieste. Pulizia di file e `RunLog` con **segnali** (`post_delete` di `CVDocument`/`CoverLetterDocument`/`Profile`, `pre_delete` di `User`) invece che solo nella view: vale per ogni strada di cancellazione (Impostazioni, Django Admin, shell, cascata). I file si cancellano dopo il commit (`transaction.on_commit`).
- **Foto sostituita**: il caricamento di una nuova foto cancella il file precedente. Era l'unica fonte di file orfani (CV e cover letter creano sempre una riga nuova): senza, una foto vecchia sarebbe rimasta su disco anche dopo la cancellazione dell'account.
- **Notifiche**: spegnere la preferenza elimina tutte le sottoscrizioni push dell'utente (server) e annulla quella del browser corrente; registrare una nuova sottoscrizione (azione esplicita "Attiva notifiche") riaccende la preferenza.
- **Access log di Caddy**: oltre a `s`, ora oscurati anche `t` e `token` (link di verifica e di recupero password aprono la PWA con il token nella query) e rimosso l'header `Referer`, che riporterebbe gli stessi token sulle chiamate API successive.
- **Backup locale**: la data nel nome del file decide la rotazione (non `mtime`), i dump si scrivono in una cartella temporanea dentro il volume e poi si spostano (un dump fallito non tocca quelli buoni), file `0600`, cartella `0700`.

## Implementazione

### Backend
- **Modelli** (`apps/accounts/models.py`, migrazioni `accounts/0009` e `0010`): `User.email_verified` (default False; la migrazione dati 0010 marca verificati tutti gli utenti esistenti), `User.notifications_enabled` (default True), nuovo `LegalAcceptance` (user, document = privacy|terms|age, version, accepted_at; `save()` rifiuta le modifiche alle righe esistenti; Admin in sola lettura).
- **`apps/accounts/legal.py`**: versioni, date, `MIN_AGE = 16`, `missing_acceptances(user)` (una query per richiesta), `record_acceptances`, `public_legal_info`.
- **`apps/accounts/permissions.py`**: `LegalAcceptanceRequired` → 403 `{"code": "legal_acceptance_required"}`.
- **`apps/accounts/emails.py` + `tasks.py`**: testi it/en (verifica, già registrato, recupero password, conferma cancellazione), link costruiti da `PUBLIC_BASE_URL` (default `https://$DOMAIN`), task `send_service_email` con retry su errori di rete.
- **`apps/accounts/account_data.py`**: `delete_account` (cascata in transazione) e `build_export` (ZIP con `README.txt`, `dati.json`, `files/`); **`apps/accounts/signals.py`**: file su disco eliminati dopo il commit alla cancellazione di CV, cover letter e profilo, `message` dei `RunLog` svuotato alla cancellazione dell'utente.
- **View e URL** (`apps/accounts/views.py`, `urls.py`, `config/urls.py`): registrazione con le tre spunte (`accept_privacy`, `accept_terms`, `confirm_age`, validate lato server) e `interface_language`; login con `email_not_verified`; `GET /api/legal/`; `POST legal-acceptance/`, `verify-email/`, `verify-email/resend/`, `password-reset/`, `password-reset/confirm/`, `password/change/`, `delete/`, `export/`; `GET export/download/?s=`.
- **Throttling**: `email_request` 10/ora per IP e `email_address` 3/ora per indirizzo (hash) su reinvio verifica e recupero password; `password_check` 10/ora su cambio password e cancellazione; `data_export` 3/giorno.
- **Me** (`UserOnboardingSerializer`): `email_verified`, `notifications_enabled` (modificabile; a False elimina le sottoscrizioni), `legal_acceptance_required`, `legal_missing`, `legal_acceptances` (ultima versione/data per documento).
- **Notifiche** (`apps/notifications/tasks.py`, `views.py`): i task considerano solo utenti attivi con `notifications_enabled`; la registrazione di una sottoscrizione riaccende la preferenza.
- **Profilo** (`apps/profiles/serializers.py`): cancellazione della foto sostituita.
- **Backup** (`apps/common/tasks.py`): con `BACKUP_S3_BUCKET` vuoto scrive `db-AAAA-MM-GG.dump` (`pg_dump -Fc`) e `media-AAAA-MM-GG.tar.gz` in `BACKUP_LOCAL_DIR` (`/app/backups`) e cancella quelli più vecchi degli ultimi 7 giorni (`BACKUP_LOCAL_KEEP_DAYS`). `restore_backup` accetta `--file <path>` oppure la data: con S3 configurato scarica il dump dal bucket, altrimenti lo cerca nella cartella locale (solo il database; i media si estraggono a mano dall'archivio).
- **Settings**: `LEGAL_*`, `EMAIL_*` (Gmail di default, spazi della password per le app ignorati), `DEFAULT_FROM_EMAIL` (default `EMAIL_HOST_USER`), `PUBLIC_BASE_URL`, `EMAIL_VERIFICATION_MAX_AGE`, `PASSWORD_RESET_TIMEOUT` (3 giorni), `BACKUP_LOCAL_DIR`/`KEEP_DAYS`, default Bedrock UE (`eu-central-1`, profili `eu.`).

### Infrastruttura
- `backend/Dockerfile`: cartella `/app/backups` (uid 1000, `0700`); `.dockerignore` esclude `backups/`.
- `docker-compose.prod.yml`: volume `local_backups` montato in `/app/backups` su `web` e `worker`.
- `Caddyfile.prod`: query `t`/`token` oscurate e `Referer` rimosso dall'access log. La CSP non cambia: le nuove pagine usano solo risorse della stessa origine; il link al Garante e i `mailto:` sono navigazioni, non risorse caricate; il download dell'export è una navigazione verso `/api/...`.

### Frontend
- Pagine pubbliche `/privacy` e `/terms` (`pages/LegalPage.jsx`, testi in `legal/PrivacyContent.jsx` e `legal/TermsContent.jsx`, it/en), con avviso se mancano i dati del titolare; footer discreto con i due link su tutte le pagine (`components/LegalFooter.jsx`).
- Registrazione: tre spunte non pre-selezionate con link (`components/LegalConsents.jsx`), schermata "controlla la tua email" quando serve la verifica.
- Login: messaggio dedicato con "Invia di nuovo il link", link "Password dimenticata?", pulsante Google solo con `google_login_enabled`; dalla pagina di conferma dell'email il primo login prosegue nell'onboarding (`/login?next=/onboarding`), come dopo una registrazione senza verifica.
- Nuove pagine `/verify-email`, `/forgot-password` (con messaggio "non disponibile" se l'email non è configurata), `/reset-password`.
- Gate: `ProtectedRoute` mostra `LegalAcceptancePage` (spunte, export, eliminazione account, esci) finché `legal_acceptance_required`; un 403 `legal_acceptance_required` da qualunque chiamata ricarica l'utente (`LEGAL_REQUIRED_EVENT`); la barra di navigazione resta nascosta.
- Impostazioni: preferenza notifiche, card "Privacy e sicurezza" (cambio password, documenti legali con la versione accettata, "Esporta i miei dati") e "Zona pericolosa" ("Elimina account" con password e conferma esplicita) — `components/AccountDataActions.jsx`.
- Avviso "Contenuto generato con l'AI: verificalo prima di usarlo" (`components/AiNotice.jsx`) nelle chat degli editor CV e cover letter, sotto il pannello "colma i gap" della generazione CV e nei dialoghi di cover letter e messaggi di networking.
- i18n it/en per tutte le stringhe nuove; e2e Playwright aggiornati (spunte in registrazione).

### Testi legali — scostamenti dalle bozze
Correzioni di fatto per allineare i testi al codice (in tutte le versioni, it/en, PWA e `Docs/legal/`):
1. Dati dell'account: aggiunti "stato di verifica dell'email, preferenza sulle notifiche" (nuovi campi).
2. Token di accesso "in forma cifrata **non reversibile**": nel DB c'è solo lo SHA-256.
3. Finalità del contratto: oltre alle notifiche mattutine anche il **promemoria di inattività** (esiste dal Sprint 17).
4. AI in UE: con i profili `eu.` di Bedrock le richieste partono da Francoforte ma possono essere elaborate in **qualunque regione AWS dell'UE**, non solo a Francoforte (§4 e §5).
5. Backup "cancellati automaticamente" (non "sovrascritti"): la rotazione elimina i file.
6. Dati per i limiti di frequenza conservati "al massimo **24 ore**" (non "qualche ora"): il limite dell'export è giornaliero.
7. Aggiunta la conservazione dei **registri tecnici delle elaborazioni** (`RunLog`): durata dell'account, poi solo in forma anonima.
8. Termini §6: i massimali non sono "indicati nell'app" (l'app avvisa quando se ne raggiunge uno) e i messaggi delle chat degli editor scalano **sempre** il credito.

## Verifica

- **Backend** (immagine ricostruita, nessun container in esecuzione toccato): `docker compose -f docker-compose.prod.yml run --rm --no-deps -e DJANGO_DEBUG=true web python manage.py test --noinput` → **345 test OK** (299 preesistenti, di cui 1 sostituito, + 47 nuovi). Nuovi: `apps/accounts/test_privacy.py` (spunte in registrazione, append-only, gate 403 ed eccezioni, accettazione e nuova versione, `/api/legal/` e flag Google, verifica email valida/scaduta/manomessa, login bloccato, reinvio generico e limitato, non enumerazione in registrazione e reset, migrazione utenti esistenti, flusso senza email, reset e cambio password con revoca dei token, cancellazione completa con controllo di **tutte** le FK verso `User` e dei file su disco, stessa pulizia per una cancellazione da admin/shell, export con contenuto, assenza di hash/chiavi/dati di altri utenti, firma, limite 3/giorno e funzionamento senza accettazioni, foto sostituita, preferenza notifiche) e `apps/common/tests.py` (backup locale con rotazione a 7 giorni e `pg_dump` simulato, dump fallito che non tocca i backup esistenti, `restore_backup` da cartella locale e da `--file`). Adeguati i test di registrazione di `test_security.py` (spunte).
- `makemigrations --check --dry-run` → nessuna differenza. `check --deploy` (con `DEBUG=false`) → nessun problema.
- **Frontend**: `docker run --rm --entrypoint sh app-apply-frontend-build -c "npm run build && npx oxlint src"` → build OK, oxlint 0 errori (9 warning `only-export-components` preesistenti). Chiavi i18n: stesso insieme in it ed en e nessuna chiave usata mancante (controllo con script nel container).
- **Caddy**: `caddy validate` sul `Caddyfile.prod` → "Valid configuration".
- **Non verificato** (richiede il deploy, un browser o credenziali reali): invio reale via Gmail, consegna/antispam, flusso completo dalla PWA (registrazione → email → verifica; reset; export su iOS), e2e Playwright, accesso ai profili Bedrock `eu.` dall'account AWS.

## Passi di deploy (manuali, in ordine)

Dettaglio con i comandi in `DEPLOY.md` §4.6.
1. Backup locale del database e dei media (come per lo Sprint 66).
2. Se il rilascio non avviene il 14/11/2026: aggiornare `PRIVACY_DATE`/`TERMS_DATE` in `apps/accounts/legal.py` alla data effettiva (sono la data di entrata in vigore mostrata agli utenti).
3. `.env`: `LEGAL_CONTROLLER_NAME`, `LEGAL_CONTROLLER_EMAIL` (e facoltativo `LEGAL_CONTROLLER_ADDRESS`); `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (password per le app di Google) ed eventualmente `DEFAULT_FROM_EMAIL`; Bedrock UE: `AWS_BEDROCK_REGION=eu-central-1`, `BEDROCK_*_MODEL` con i profili `eu.` (abilitati nella console Bedrock di Francoforte). `PUBLIC_BASE_URL` solo se diverso da `https://$DOMAIN`.
4. `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
5. `docker compose -f docker-compose.prod.yml up -d`: migrazioni `accounts/0009`–`0010`, nuovo volume `local_backups`, PWA ricompilata; `caddy` va ricreato o ricaricato per il nuovo `Caddyfile.prod`.
6. Verifiche: `/privacy` e `/terms` senza login e senza avviso del titolare; accesso di un utente esistente → schermata di accettazione; registrazione di prova → email di verifica; "Password dimenticata?"; export ZIP; backup locale lanciato a mano e presente in `/app/backups`; una chiamata AI riuscita con i profili `eu.`.
7. Informare i tester: al prossimo accesso dovranno accettare informativa e termini.
8. Dopo 7 giorni: eliminare i dump manuali più vecchi in `backups/` sul VPS (`pre_*.dump`, `pre_sprint66_media.tgz`), che contengono dati personali e non rientrano nella rotazione.

## Cosa manca

- **Login Google**: solo nascosto. Il flusso allauth non produce un token per l'API (Sprint 66) e salta le spunte di registrazione e il codice di invito: prima di attivarlo vanno aggiunti il passaggio sessione → token e la raccolta delle accettazioni. Le URL di allauth (`/accounts/*`, compresa la registrazione) restano raggiungibili: un account creato da lì non ottiene comunque un token ed è soggetto al gate.
- **Email inviate via Gmail**: una copia di ogni messaggio (indirizzo del destinatario e testo, mai dati del profilo) resta nella cartella "Posta inviata" dell'account mittente, anche dopo la cancellazione dell'account. Va cancellata periodicamente a mano, o la conservazione va dichiarata nell'informativa: decisione del committente.
- Nessun cambio dell'indirizzo email dall'app (l'email resta in sola lettura, come prima).
- I **backup restano sul VPS**: un guasto del disco li perde insieme ai dati; la copia fuori dal VPS è manuale (`DEPLOY.md` §6). I backup non sono cifrati.
- I `RunLog` di utenti cancellati restano senza messaggio; nessuna pulizia automatica dei `RunLog` in generale.
- Con la verifica email attiva l'onboarding è proposto solo se il primo login parte dal pulsante della pagina di conferma.
- I tre endpoint di reinvio verifica, richiesta e conferma del recupero password condividono lo stesso contatore per IP (`email_request`, 10/ora).
- I test e2e registrano gli utenti via API e usano il token della risposta: funzionano solo contro un backend senza email configurata.
- Export sincrono: per account con moltissimi PDF il download può richiedere qualche secondo (nessun limite di dimensione).
- Fuori perimetro (dall'audit dello Sprint 66): restrizione dell'admin per IP e superficie di allauth (M5), race condition minori sulle ricerche (B4), delimitazione dei contenuti di terzi nei prompt (B6).
