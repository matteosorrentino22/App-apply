# Deploy e operatività in produzione

> Stato descritto: **as-is al 2026-11-14** (Sprint 70, account, profilo, notifiche e frontend).
> Riferimenti: `Docs/02-specifiche-tecniche-v5.md` §8 (infrastruttura), `CLAUDE.md` (regola "un solo file compose").
> Questo file è nel repository pubblico: **non** riportare qui dominio, IP, email, nomi di account o utenti, token.

---

## 1. Architettura in produzione

Un unico VPS Linux (1 vCPU, ~4 GB RAM) con Docker Engine + plugin Compose. Tutto lo stack parte da **`docker-compose.prod.yml`** (mai `docker-compose.yml`, che è solo per sviluppo — vedi §5).

| Servizio | Immagine / build | Ruolo |
|---|---|---|
| `db` | `postgres:16-alpine` | Database (volume `postgres_data`) |
| `redis` | `redis:7-alpine` | Broker/result backend Celery (db 0/1) e cache Django condivisa (db 2: throttling, limite login admin, cache autocomplete) |
| `web` | `./backend` | `migrate` + `collectstatic` all'avvio, poi `gunicorn --workers 4 --timeout 1800` |
| `worker` | `./backend` (stessa immagine) | `celery worker` — concorrenza = n. CPU (oggi 1) |
| `beat` | `./backend` (stessa immagine) | `celery beat` con `DatabaseScheduler` (task schedulati salvati nel DB) |
| `frontend-build` | `./frontend` | One-shot: `npm run build` della PWA nel volume `frontend_dist`, poi termina |
| `caddy` | `caddy:2-alpine` | HTTPS automatico (Let's Encrypt) su `$DOMAIN`, reverse proxy `/api/*`, path dell'admin (`DJANGO_ADMIN_PATH`), `/accounts/*` → `web:8000`; serve direttamente `/static/*` e la PWA con fallback su `index.html`; **`/media/*` → 404** (il volume `media_data` non è montato in Caddy); header di sicurezza e access log (§8.1) |

`web`, `worker` e `beat` girano come utente non privilegiato `app` (**uid 1000**, `backend/Dockerfile`, Sprint 66): codice di root in sola lettura, scrivibili solo `/app/staticfiles`, `/app/mediafiles` e `/app/backups` (volume `local_backups` dei backup locali, montato su `web` e `worker`, Sprint 67). Tutti i servizi hanno la rotazione dei log Docker (`json-file`, 5 × 10 MB per container).

Perché `--timeout 1800` e 4 worker gunicorn: la **raccolta manuale** ("Collect now") esegue raccolta + scoring in sincrono dentro la richiesta HTTP (fino a ~100 job, scoring in parallelo con `SCORING_CONCURRENCY=5`); con il timeout di default i worker venivano uccisi a metà lasciando job senza punteggio (Sprint 45). Stesso rischio per generazione CV/cover letter (Sprint 44).

Dipendenze di sistema nell'immagine backend (`backend/Dockerfile`): librerie Pango/Cairo per WeasyPrint, `postgresql-client` (`pg_dump`/`pg_restore` per backup/ripristino), **`fonts-crosextra-caladea`** (font compatibile Cambria usato dal template CV — senza, Pango ricade su DejaVu; Sprint 52).

Servizi esterni:
- **AWS Bedrock** (Claude) — scoring, generazione CV/cover letter/messaggi, chat degli editor, parsing CV in onboarding.
- **Apify** — actor `cheap_scraper~linkedin-job-scraper` per la raccolta offerte (pay-per-result, minimo 150 risultati fatturati per chiamata).
- **LinkedIn guest API** (`jobs-guest/jobs/api/jobPosting/{id}`, nessuna chiave) — import di un job da URL.
- **Nominatim (OpenStreetMap)** — autocomplete città, nessuna chiave.
- **Web Push** (VAPID) — notifiche, nessun servizio a pagamento.
- **Gmail SMTP** (Sprint 67) — email di servizio (verifica dell'indirizzo, recupero password, conferma di cancellazione), inviate dal worker Celery. Facoltativo: senza credenziali l'app funziona senza email (§3).

## 2. Provisioning una tantum del VPS

```
./docker/vps-setup.sh
```

Installa e attiva `unattended-upgrades`. Docker Engine + Compose vanno installati a parte.

**Attenzione alle porte 80/443:** sul VPS non devono girare altri stack che le pubblicano. Incidente reale (17/10/2026): dopo un riavvio del server, un vecchio stack di prototipo (n8n + Traefik, `restart: always`) ha preso le porte 80/443 prima di Caddy (`unless-stopped`) → sito in 404. Risolto con `docker compose down` su quello stack (volumi preservati, container rimossi). Dopo ogni riavvio del VPS verificare con `ss -tlnp | grep -E ':80 |:443 '` e `docker ps -a` che le porte siano di `app-apply-caddy-1`.

## 3. Configurazione (`.env`)

Copiare `.env.example` in `.env` alla radice del repo sul VPS e compilare. `.env` non è mai committato. Chiavi:

| Gruppo | Chiavi | Note |
|---|---|---|
| Django | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Host = dominio reale; origins = `https://<dominio>`. Dallo Sprint 66 `DJANGO_DEBUG` mancante = `false`, e con `DEBUG=false` l'avvio fallisce se `DJANGO_SECRET_KEY` è vuota o contiene "insecure" |
| Admin | `DJANGO_ADMIN_PATH` (default `admin/`, con "/" finale) | Sprint 66. Letta da Django **e** dal container `caddy` (`docker-compose.prod.yml` la passa a entrambi dal `.env`): Caddy inoltra a Django solo quel path. Un path non standard riduce i tentativi automatici; il valore reale non va scritto nel repository |
| Registrazione | `REGISTRATION_INVITE_CODE` | Sprint 66. Se valorizzato la registrazione richiede questo codice (da comunicare ai tester); vuoto = registrazione aperta |
| Titolare del trattamento | `LEGAL_CONTROLLER_NAME`, `LEGAL_CONTROLLER_EMAIL`, `LEGAL_CONTROLLER_ADDRESS` (facoltativo) | Sprint 67. Mostrati nelle pagine pubbliche `/privacy` e `/terms` (via `GET /api/legal/`). **Solo nel `.env`, mai nel repository.** Se nome o email mancano le pagine mostrano l'avviso "dati del titolare da completare" |
| Email | `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `EMAIL_HOST` (`smtp.gmail.com`), `EMAIL_PORT` (587), `EMAIL_USE_TLS` (true), `PUBLIC_BASE_URL` | Sprint 67. `EMAIL_HOST_PASSWORD` è una **password per le app** dell'account Google (richiede la verifica in due passaggi; gli spazi sono ignorati). `DEFAULT_FROM_EMAIL` vuota = `EMAIL_HOST_USER`. `PUBLIC_BASE_URL` (link nelle email) vuota = `https://$DOMAIN`. **Senza utente/password**: nessuna email (warning nei log del worker), nuovi account già verificati, "Password dimenticata?" mostra "non disponibile", registrazione con email già usata → errore esplicito come prima |
| Cache | `REDIS_CACHE_URL` (default `redis://redis:6379/2`) | Sprint 66. Cache Django condivisa dai worker gunicorn |
| Database | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST=db`, `POSTGRES_PORT=5432` | |
| Celery | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis del compose |
| AI (Bedrock) | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BEDROCK_REGION`, `BEDROCK_SCORING_MODEL`, `BEDROCK_CV_GENERATION_MODEL`, `BEDROCK_CV_PARSING_MODEL` | Scoring su Haiku 4.5, generazione e parsing su Opus 5. Dallo Sprint 67 **in UE**, come dichiarato nell'informativa: `AWS_BEDROCK_REGION=eu-central-1` e profili di inferenza `eu.anthropic.claude-haiku-4-5-20251001-v1:0` / `eu.anthropic.claude-opus-5` (instradamento solo verso regioni AWS dell'UE; vanno abilitati in Bedrock → Model access nella regione di Francoforte). Sono anche i default del codice. L'API Anthropic diretta non è più usata (dal 18/08/2026) |
| Fonte offerte | `APIFY_API_TOKEN` | Unica variabile letta dal codice (altre varianti nel `.env` sono ignorate) |
| Login Google | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | **Oggi vuote in produzione** → login Google non attivo e, dallo Sprint 67, pulsante nascosto (compare solo con `GOOGLE_OAUTH_CLIENT_ID` valorizzato). Non valorizzarle prima di aver completato il flusso (sessione → token, accettazioni legali) |
| Push | `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL` | |
| Prezzi extra (€) | `PRICE_MANUAL_CV_EXTRA` (1.50), `PRICE_IMPORT_EXTRA` (0.50), `PRICE_COVER_LETTER_EXTRA` (1.50), `PRICE_MANUAL_JOB_EXTRA` (0.50), `PRICE_REFERRAL_MESSAGE_EXTRA` (1.00), `PRICE_CV_DRAFT_CHAT_MESSAGE` (0.20), `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE` (0.20) | Facoltative: tra parentesi il default in `config/settings.py` |
| Deploy | `DOMAIN`, `CADDY_EMAIL` | Solo `docker-compose.prod.yml` |
| Backup | `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY`, `BACKUP_S3_REGION`, `BACKUP_LOCAL_DIR` (default `/app/backups`) | **S3 oggi vuote in produzione** → backup locale ruotato a 7 giorni (Sprint 67), vedi §6 |

Dopo una modifica a `.env` un `restart` **non basta**: i container vanno ricreati (§4.2).

## 4. Avvio e aggiornamento

### 4.1 Primo avvio / rilascio di una nuova versione

```
cd /root/App-apply
git pull                                   # oppure si lavora direttamente su main sul VPS
docker compose -f docker-compose.prod.yml up -d --build
```

`web` applica le migrazioni e `collectstatic` a ogni avvio; `frontend-build` ricompila la PWA nel volume e Caddy la serve subito. `web`, `worker` e `beat` condividono la stessa immagine: dopo una modifica al backend vanno ricostruiti **tutti e tre** (altrimenti il worker esegue codice vecchio).

### 4.2 Applicare una modifica a `.env`

```
docker compose -f docker-compose.prod.yml up -d --force-recreate web worker beat
```

### 4.3 Verifica di coerenza dello stack (prima e dopo ogni intervento)

```
for c in $(docker ps -q); do docker inspect $c --format '{{.Name}} {{index .Config.Labels "com.docker.compose.project.config_files"}}'; done
```

Tutti i container `app-apply-*` devono riportare `.../docker-compose.prod.yml`. Vedi l'incidente del 17/08/2026 in `CLAUDE.md`.

### 4.4 Test

```
docker compose -f docker-compose.prod.yml build web
docker compose -f docker-compose.prod.yml run --rm --no-deps -e DJANGO_DEBUG=true -e REGISTRATION_INVITE_CODE= web python manage.py test --noinput   # suite backend (465 test, OK al 2026-11-14, Sprint 71)
docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py check --deploy                     # con DEBUG=false: nessun problema atteso
cd frontend && npm run test:e2e                                                     # Playwright (e2e/*.spec.js)
```

`run --rm --no-deps` usa l'immagine appena ricostruita senza toccare i container in esecuzione (si collega al `db` di produzione solo per creare/distruggere il database di test). Nei test la cache è una `DummyCache`: niente contatori su Redis. Dallo Sprint 67 i test ignorano le credenziali SMTP e il codice di invito del `.env` (email in memoria, task Celery eseguiti in linea) e il gate delle accettazioni legali è spento salvo nei test dedicati. Frontend senza toccare la PWA in produzione: `docker compose -f docker-compose.prod.yml build frontend-build` e poi `docker run --rm --entrypoint sh app-apply-frontend-build -c "npm run build && npx oxlint src"` (mai `run`/`up` del servizio `frontend-build`, che sovrascrive il volume servito da Caddy). Caddyfile: `docker run --rm -v $PWD/docker/caddy/Caddyfile.prod:/etc/caddy/Caddyfile:ro -e DOMAIN=example.com -e CADDY_EMAIL=a@example.com caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile`.

`-e DJANGO_DEBUG=true` è necessario: con la configurazione di produzione (`DEBUG=false` → redirect HTTPS) il test client riceve 301 su tutte le chiamate API e circa 60 test falliscono senza che ci sia una regressione. Il database di test è separato (`test_<db>`), i dati di produzione non vengono toccati.

Con `REGISTRATION_INVITE_CODE` valorizzato in `.env` due test di registrazione (`accounts/test_security.py`) rispondono 400: aggiungere `-e REGISTRATION_INVITE_CODE=` al comando dei test. Per non condividere il server PostgreSQL di produzione (e il nome `test_<db>`) con altre esecuzioni in parallelo, si può usare un PostgreSQL usa e getta su una rete Docker dedicata, passando `POSTGRES_HOST`/`POSTGRES_PASSWORD` di quel container (procedura usata nello Sprint 68, `sprints/sprint-68.md`).

I test e2e usano i comandi `set_e2e_account` e `seed_e2e_jobs` per preparare account e job di prova. Contro un backend con `REGISTRATION_INVITE_CODE` valorizzato va passato lo stesso codice in `E2E_INVITE_CODE` (Sprint 70); le registrazioni via API presuppongono un backend senza invio email configurato (Sprint 67). Dallo Sprint 66 il login è limitato a 10 tentativi al minuto per IP: una suite e2e lunga lanciata contro lo stesso ambiente può ricevere 429.

### 4.5 Rilascio dello Sprint 66 (sicurezza) — passi una tantum, in ordine

Da eseguire a mano sul VPS, nella cartella del repository. Effetti visibili: **tutti gli utenti devono rifare il login** (i vecchi token vengono cancellati) e la registrazione richiede il codice di invito, se configurato.

1. **Backup locale** del database (§6, "Backup manuale locale").
2. **`.env`**: aggiungere `REGISTRATION_INVITE_CODE=<codice>` e, se si vuole spostare l'admin, `DJANGO_ADMIN_PATH=<path>/` (con "/" finale; da quel momento `/admin/` non risponde più). `REDIS_CACHE_URL` serve solo se diverso dal default.
3. **Build** delle immagini: `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
4. **Fermare** i servizi applicativi: `docker compose -f docker-compose.prod.yml stop web worker beat`.
5. **Proprietario dei volumi** (i container ora girano come uid 1000; i volumi esistenti sono di root):
   ```
   docker run --rm -v app-apply_media_data:/m -v app-apply_static_data:/s alpine chown -R 1000:1000 /m /s
   ```
   I volumi creati da zero dopo questo sprint ereditano già il proprietario giusto dall'immagine.
6. **Avvio**: `docker compose -f docker-compose.prod.yml up -d`. `web` applica le migrazioni (`accounts/0007` `AuthToken`, `accounts/0008` cancella i vecchi token DRF, `cv/0009`, `profiles/0009`, `jobs/0016`), `frontend-build` ricompila la PWA, `caddy` viene ricreato (cambiano volumi e variabili) e carica il nuovo `Caddyfile.prod`. Se `caddy` non fosse stato ricreato: `docker compose -f docker-compose.prod.yml exec caddy caddy reload --config /etc/caddy/Caddyfile`.
7. **File media esistenti** (nomi casuali, foto ripulite dai metadati, eliminazione dei file non più referenziati):
   ```
   docker compose -f docker-compose.prod.yml exec web python manage.py secure_media_files --dry-run --delete-orphans   # solo elenco
   docker compose -f docker-compose.prod.yml exec web python manage.py secure_media_files                             # rinomina
   docker compose -f docker-compose.prod.yml exec web python manage.py secure_media_files --delete-orphans            # elimina gli orfani
   ```
   Il comando è idempotente: rilanciato, non rinomina di nuovo i file già sistemati.
8. **Verifiche**: coerenza dello stack (§4.3); `docker compose -f docker-compose.prod.yml exec web id` → `uid=1000(app)`; `curl -sI https://<dominio>/` mostra `strict-transport-security`, `content-security-policy`, `x-frame-options` e nessun header `server`; un vecchio URL `/media/...` risponde 404; dalla PWA: login, download di CV e cover letter, anteprima PDF negli editor (CSP), foto nel profilo; login all'admin sul path configurato; access log presente in `docker compose -f docker-compose.prod.yml exec caddy ls -la /var/log/caddy`.

### 4.6 Rilascio dello Sprint 67 (privacy e GDPR) — passi una tantum, in ordine

Effetti visibili: al prossimo accesso **tutti gli utenti esistenti vedono la schermata di accettazione** di informativa, termini ed età minima (gli utenti esistenti risultano già con email verificata); con l'email configurata i nuovi iscritti devono confermare l'indirizzo prima di accedere.

1. **Backup locale** del database e dei media (§6, "Backup manuale locale").
2. **Data di entrata in vigore**: se il rilascio non avviene il 14/11/2026, aggiornare `PRIVACY_DATE` e `TERMS_DATE` in `backend/apps/accounts/legal.py` alla data effettiva (è la data mostrata agli utenti) prima della build.
3. **`.env`** (valori reali solo lì):
   - `LEGAL_CONTROLLER_NAME`, `LEGAL_CONTROLLER_EMAIL` e, se si vuole, `LEGAL_CONTROLLER_ADDRESS`;
   - `EMAIL_HOST_USER` (indirizzo Gmail), `EMAIL_HOST_PASSWORD` (password per le app: Account Google → Sicurezza → Verifica in due passaggi → Password per le app), facoltativo `DEFAULT_FROM_EMAIL`; `PUBLIC_BASE_URL` solo se i link non devono puntare a `https://$DOMAIN`;
   - Bedrock UE: `AWS_BEDROCK_REGION=eu-central-1`, `BEDROCK_SCORING_MODEL=eu.anthropic.claude-haiku-4-5-20251001-v1:0`, `BEDROCK_CV_GENERATION_MODEL=eu.anthropic.claude-opus-5`, `BEDROCK_CV_PARSING_MODEL=eu.anthropic.claude-opus-5` (prima verificare in console che i profili `eu.` siano abilitati per le credenziali in uso).
4. **Build**: `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
5. **Avvio**: `docker compose -f docker-compose.prod.yml up -d`. `web` applica `accounts/0009` (campi `email_verified`, `notifications_enabled`, tabella `LegalAcceptance`) e `accounts/0010` (utenti esistenti verificati); viene creato il volume `local_backups` (proprietario uid 1000 ereditato dall'immagine); `frontend-build` ricompila la PWA. Il `Caddyfile.prod` è cambiato (access log): se `caddy` non viene ricreato, `docker compose -f docker-compose.prod.yml exec caddy caddy reload --config /etc/caddy/Caddyfile`.
6. **Verifiche**:
   - coerenza dello stack (§4.3); `docker compose -f docker-compose.prod.yml exec worker ls -ld /app/backups` → proprietario `app`;
   - da browser senza login: `/privacy` e `/terms` in italiano e inglese, **senza** l'avviso "dati del titolare da completare";
   - accesso con un utente esistente → schermata di accettazione; dopo l'accettazione l'app funziona; in Impostazioni compaiono le versioni accettate;
   - registrazione di prova (con il codice di invito) → email di verifica ricevuta (controllare anche lo spam), link → "Indirizzo confermato", login; "Password dimenticata?" → email → nuova password;
   - Impostazioni → "Esporta i miei dati" scarica lo ZIP; eliminare l'account di prova → email di conferma;
   - backup locale lanciato a mano (§6) e file presenti in `/app/backups`;
   - una generazione o uno scoring riusciti (profili Bedrock `eu.`): in caso di errore i `RunLog` riportano il messaggio di Bedrock;
   - log del worker senza warning "Email non configurata".
7. **Comunicare ai tester** che al prossimo accesso dovranno accettare informativa e termini.
8. **Dopo 7 giorni**: eliminare dal VPS i dump manuali più vecchi in `backups/` del repository (es. `pre_*.dump`, `pre_sprint66_media.tgz`): contengono dati personali, non rientrano nella rotazione e l'informativa dichiara una conservazione dei backup di 7 giorni.

### 4.7 Rilascio dello Sprint 68 (lista job, scoring, raccolta) — passi una tantum, in ordine

Lo sprint contiene tre migrazioni `jobs/0017` (nuovi campi), `jobs/0018` (backfill della ricerca di provenienza) e `jobs/0019` (rimozione di `discarded_by_cap`). La **0019 si rifiuta di partire finché esistono job con `discarded_by_cap=True`**: per questo, prima di `up -d`, si applicano le migrazioni fino alla 0018 e si lanciano i comandi con un container usa e getta. Se si facesse subito `up -d`, `web` non partirebbe (errore esplicito della 0019 nei log): basta eseguire i passi 5–6 e rilanciare `up -d`.

1. **Backup locale** del database (§6, "Backup manuale locale"): i passi 6 e 7 eliminano e modificano dati.
2. **Build**: `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
3. **Fermare** i servizi applicativi: `docker compose -f docker-compose.prod.yml stop web worker beat`.
4. **Migrazioni fino alla 0018**: `docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py migrate jobs 0018`.
5. **Job del vecchio cap di intake** (decisione del committente: eliminarli con documenti e bozze):
   ```
   docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py delete_discarded_by_cap_jobs            # dry-run: conteggi per stato e documenti collegati
   docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py delete_discarded_by_cap_jobs --confirm
   ```
   Al 2026-11-14 (dump di prima dello Sprint 66) erano 988 job, nessuno con CV, cover letter, messaggi o bozze; uno era marcato "candidatura fatta". Un job da conservare va smarcato prima del `--confirm` (il campo non è più nel modello Django, quindi non da Admin): `docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py dbshell -- -c "UPDATE jobs_job SET discarded_by_cap = false WHERE id = <id>;"`.
6. **Punteggi storici su scala 1–5** (×2, marcati con `score_rescaled_from_legacy`; idempotente):
   ```
   docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py rescale_legacy_scores            # dry-run: quanti per valore
   docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py rescale_legacy_scores --confirm
   ```
   Taglio di default 2026-09-24 21:00 UTC (passaggio reale alla scala 1–10, verificato sui dati: vedi `sprints/sprint-68.md`). Il dry-run segnala eventuali punteggi > 5 prima del taglio, che non vengono toccati.
7. **Avvio**: `docker compose -f docker-compose.prod.yml up -d` (`web` applica la `jobs/0019` e le migrazioni non ancora applicate; `frontend-build` ricompila la PWA).
8. **Facoltativo — job senza punteggio**: il ciclo notturno li ritenta da solo (al massimo 3 fallimenti per job). Per farlo subito: `docker compose -f docker-compose.prod.yml exec web python manage.py retry_unscored_jobs --dry-run`, poi senza `--dry-run` (una chiamata AI per job).
9. **Verifiche**: coerenza dello stack (§4.3); in Admin la lista Job non ha più il filtro "discarded by cap", i job riscalati hanno `score_rescaled_from_legacy`; la mattina dopo, `RunLog` `collection` con le righe per gruppo e i contatori degli scarti.

### 4.8 Rilascio dello Sprint 70 (account, profilo, notifiche, frontend)

Nessuna migrazione, nessuna variabile d'ambiente nuova, nessun comando sui dati. Il cambio dell'email di accesso è disponibile solo con l'invio email configurato (Sprint 67, `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`).

1. **Build**: `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
2. **Avvio**: `docker compose -f docker-compose.prod.yml up -d` (`frontend-build` ricompila la PWA).
3. **Prima volta dopo il rilascio**: le schede già aperte eseguono ancora il bundle precedente, che non conosce l'avviso "Nuova versione disponibile": vanno ricaricate una volta a mano (o chiuse e riaperte). Dai rilasci successivi l'avviso compare da solo (entro 30 minuti o al ritorno sulla scheda).
4. **Verifiche**: coerenza dello stack (§4.3); dalla PWA: Impostazioni con il titolo "Impostazioni", "I tuoi limiti di oggi" con contatori e prezzi, fuso orario modificabile; "Esci" (icona in alto a destra) da una pagina qualsiasi; Profilo con foto rimovibile, tecnologie e obiettivo; cambio email di prova (link al nuovo indirizzo, avviso al vecchio, login con il nuovo indirizzo dopo la conferma).

### 4.9 Rilascio dello Sprint 71 (testi del backend in it/en) e traduzioni

Nessuna migrazione, nessuna variabile d'ambiente nuova, nessun cambio alla build: il catalogo compilato `backend/locale/en/LC_MESSAGES/django.mo` è nel repository ed entra nell'immagine con il resto del codice (l'immagine non contiene `gettext`).

1. **Build**: `docker compose -f docker-compose.prod.yml build web worker beat frontend-build` (il `worker` serve per le notifiche e lo scoring in inglese, `frontend-build` perché la PWA invii `Accept-Language`).
2. **Avvio**: `docker compose -f docker-compose.prod.yml up -d`.
3. **Prima volta dopo il rilascio**: le schede aperte con il bundle precedente non mandano ancora `Accept-Language` e ricevono i messaggi in italiano (o nella lingua del browser, se italiano o inglese) finché non si aggiornano ("Nuova versione disponibile — Aggiorna", Sprint 70).
4. **Verifiche**: coerenza dello stack (§4.3); dalla PWA con interfaccia in inglese un login con password errata mostra "Invalid credentials.", in italiano "Credenziali non valide."; il Django Admin resta in italiano. Da shell: `curl -s -H 'Accept-Language: en' -H 'Content-Type: application/json' -d '{"email":"x@example.com","password":"x"}' https://$DOMAIN/api/accounts/login/`.

**Aggiungere o modificare un testo rivolto all'utente** (regola in `CLAUDE.md`): marcarlo con `gettext` (`_("…")`, msgid in italiano, segnaposto con nome `%(nome)s`), poi rigenerare `.po` e `.mo` in un container usa e getta con `gettext` installato, dalla radice del repository:

```
docker compose -f docker-compose.prod.yml build web
docker run --rm -u root -v "$PWD/backend:/app" -e DJANGO_DEBUG=true app-apply-web sh -c "
  apt-get update -qq && apt-get install -y -qq --no-install-recommends gettext >/dev/null &&
  python manage.py makemessages -l en --add-location=file --no-obsolete --ignore=staticfiles --ignore=mediafiles --ignore=backups &&
  python manage.py compilemessages -l en --ignore=staticfiles --ignore=mediafiles --ignore=backups"
```

Poi completare in `backend/locale/en/LC_MESSAGES/django.po` le voci con `msgstr ""` e togliere i `#, fuzzy` (makemessages propone in automatico traduzioni di frasi simili, spesso sbagliate: vanno controllate e il flag rimosso), rilanciare lo stesso comando per ricompilare il `.mo` e committare entrambi i file. `apps/common/test_i18n.py` fallisce se restano voci vuote o fuzzy o se il `.mo` non corrisponde al `.po`. Il comando non usa il database e scrive solo in `backend/locale/`; i file creati da root nel bind mount vanno eventualmente riassegnati all'utente del repository.

## 5. Task schedulati (Celery Beat, `DatabaseScheduler`)

Creati da migrazioni dati (modificabili da Django Admin → Periodic tasks):

| Task | Quando | Migrazione |
|---|---|---|
| Ciclo notturno — `apps.jobs.tasks.run_nightly_cycle` (oggi solo raccolta + scoring: cap di intake e CV automatici rimossi; il nome del PeriodicTask è rimasto quello storico) | 02:00 Europe/Rome | `jobs/0003_schedule_nightly_cycle` |
| Notifica mattutina (nuovi job) e promemoria di inattività (7 giorni) | ogni 15 minuti; la notifica mattutina parte solo nell'ora 10 locale dell'utente | `notifications/0002_schedule_notification_tasks` |
| Backup giornaliero database + media (S3 se configurato, altrimenti locale ruotato a 7 giorni) | 03:30 Europe/Rome | `common/0001_schedule_backup` |

## 6. Backup e ripristino

Il task `apps.common.tasks.backup_database` (03:30) esegue `pg_dump -Fc` + archivio dei file media:
- **con `BACKUP_S3_*` configurato** li carica sul bucket S3-compatibile (fuori dal VPS); la conservazione si regola con le regole del bucket;
- **senza S3 (situazione attuale, Sprint 67)** li scrive nel volume Docker `local_backups`, montato in `/app/backups` su `web` e `worker`: `db-AAAA-MM-GG.dump` e `media-AAAA-MM-GG.tar.gz` (file `0600`, cartella `0700`, uid 1000). A ogni esecuzione cancella i backup con data più vecchia degli **ultimi 7 giorni** (`BACKUP_LOCAL_KEEP_DAYS`), come dichiarato nell'informativa privacy. La rotazione considera solo i file con quel formato di nome: copie con altri nomi messe nella cartella non vengono toccate (e non vanno lasciate lì oltre i 7 giorni). Il dump viene scritto in una sottocartella temporanea e poi spostato: un `pg_dump` fallito non sostituisce né cancella i backup esistenti.

> ⚠️ **Limite:** i backup locali stanno sullo stesso VPS dei dati: un guasto del disco o del server li perde insieme al database. Copiarli periodicamente fuori dal VPS (sotto) o configurare un bucket resta consigliato. I backup non sono cifrati.

Backup lanciato a mano (S3 o locale secondo la configurazione):

```
docker compose -f docker-compose.prod.yml exec worker python manage.py shell -c "from apps.common.tasks import backup_database; backup_database()"
docker compose -f docker-compose.prod.yml exec worker ls -la /app/backups
```

**Copiare un backup fuori dal VPS** (dal proprio computer, con accesso SSH al VPS; il volume si legge con un container usa e getta):

```
# sul VPS: copia del giorno voluto in una cartella temporanea leggibile solo da root
docker run --rm -v app-apply_local_backups:/b:ro -v /root/backup-export:/out alpine \
  sh -c "cp /b/db-AAAA-MM-GG.dump /b/media-AAAA-MM-GG.tar.gz /out/"
# dal proprio computer
scp root@<vps>:/root/backup-export/db-AAAA-MM-GG.dump root@<vps>:/root/backup-export/media-AAAA-MM-GG.tar.gz .
# sul VPS, a copia verificata
rm -rf /root/backup-export
```

Chi conserva una copia fuori dal VPS deve rispettare la stessa conservazione dichiarata (7 giorni) o aggiornare l'informativa.

Backup manuale locale prima di interventi distruttivi (dump nella cartella `backups/` del repo, non versionata, **fuori** dalla rotazione: da cancellare a mano entro 7 giorni):

```
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > backups/manual_$(date +%Y%m%d_%H%M%S).dump
```

Ripristino di prova (**mai contro la produzione**: `pg_restore --clean --if-exists` sovrascrive il database a cui punta il comando; usare un ambiente separato):
- `python manage.py restore_backup AAAA-MM-GG --confirm` — scarica `db-AAAA-MM-GG.dump` dal bucket se S3 è configurato, altrimenti lo cerca in `BACKUP_LOCAL_DIR`;
- `python manage.py restore_backup --file /percorso/db-AAAA-MM-GG.dump --confirm` — da un file qualunque (es. una copia portata fuori dal VPS).
- I file media si ripristinano estraendo l'archivio nella cartella media dell'ambiente di prova: `tar -xzf media-AAAA-MM-GG.tar.gz -C <cartella>` (contiene la cartella `media/`).

## 7. Runbook operativo

Comandi da lanciare in `/root/App-apply`. Abbreviazione usata sotto: `SHELL_DJANGO='docker compose -f docker-compose.prod.yml exec -T web python manage.py shell -c'`. Identificare sempre l'utente per id (`User.objects.get(pk=<id>)`), non scrivere email nei documenti.

### 7.1 Raccolta offerte fallita con 403 da Apify / credito Apify esaurito
Sintomo: raccolta notturna e "Collect now" falliscono per **tutti** gli utenti, `RunLog` di tipo `collection` in `failure` con 403 dall'endpoint `run-sync-get-dataset-items`. Causa tipica: credito mensile dell'account Apify esaurito (piano free = 5 $/mese), non token invalido.
1. Verificare il consumo: `GET https://api.apify.com/v2/users/me/limits` con il token (dal container `web`).
2. Ricaricare credito / cambiare piano sull'account, **oppure** passare a un token di un altro account con credito: aggiornare `APIFY_API_TOKEN` in `.env` (si può tenere il vecchio valore in una variabile di comodo con altro nome: il codice legge solo `APIFY_API_TOKEN`).
3. Ricreare `web worker beat` (§4.2) e verificare `GET https://api.apify.com/v2/users/me` → 200.

### 7.2 Credenziali/modello Bedrock
Le chiamate AI passano tutte da `apps/common/ai.py`. Per ruotare le chiavi AWS o cambiare modello: aggiornare `AWS_*` / `BEDROCK_*` in `.env` e ricreare i container (§4.2). Errori di quota/credenziali compaiono nei `RunLog` (scoring, generazioni, chat).

### 7.3 Utente bloccato dalla quota "Collect now" (409)
Il limite è `COLLECTION_DAILY_LIMIT = 1` raccolta manuale al giorno per utente, uguale per Free e Pro (`apps/jobs/tasks.py`). Per concederne un'altra oggi (Sprint 68): Django Admin → **Users**, selezionare l'utente e scegliere l'azione **"Azzera la quota di raccolta manuale di oggi"**. L'azione **"Azzera tutti i contatori giornalieri di oggi"** azzera anche gli altri contatori (`manual_cv_count`, `cover_letter_count`, `referral_message_count`, `import_count`, `manual_job_count`, `collection_count`, `cv_import_count`); dalla lista **Daily quotas** l'azione "Azzera tutti i contatori delle righe selezionate" vale per righe di qualunque giorno. Il "giorno" è quello di Europe/Rome.

Il 409 può anche indicare una raccolta già in corso (`User.collection_in_progress`, visibile e modificabile nella scheda utente in Admin, sezione "Raccolta e inattività"): dallo Sprint 68 la guardia è condivisa con il ciclo notturno, quindi una raccolta manuale è respinta anche mentre gira il ciclo notturno di quell'utente. Il lock scade da solo dopo 2 ore (`COLLECTION_STALE_AFTER`).

### 7.4 Rilanciare la raccolta notturna per un solo utente
Non esiste un task Celery per singolo utente: si chiama la funzione da shell.
```
$SHELL_DJANGO "
from apps.accounts.models import User; from apps.jobs.tasks import run_nightly_cycle_for_user
print(run_nightly_cycle_for_user(User.objects.get(pk=<id>)))"
```
Dallo Sprint 68 questo percorso usa la stessa guardia della raccolta manuale (se è in corso una raccolta l'utente viene saltato con un `RunLog` `skipped`), non consuma la quota giornaliera e ritenta anche i job senza punteggio. **Ogni gruppo ricerca×location è una chiamata Apify a pagamento** (≥150 risultati fatturati). I job già presenti non vengono duplicati (dedup su `external_id`).

### 7.5 Cambiare piano o credito di un utente
Da Django Admin (`/admin/` → Users: campi `plan`, `extra_credit`) oppure da shell (`u.plan = User.Plan.PRO; u.save(update_fields=['plan'])`). Il passaggio Pro→Free disattiva tutte le ricerche (regola di downgrade, specifiche funzionali §4.2).

### 7.6 Diagnosi rapida
- Log applicativi: `docker compose -f docker-compose.prod.yml logs --tail 200 web|worker|beat|caddy` (errori 5xx di Django, warning, invii push falliti; mai token o query string).
- Access log HTTP (JSON, 14 giorni): `docker compose -f docker-compose.prod.yml exec caddy tail -n 50 /var/log/caddy/access.log`.
- Utente con "sessione scaduta" o da disconnettere da un dispositivo: Django Admin → Auth tokens (eliminare la riga del dispositivo); da shell `from apps.accounts.tokens import revoke_all_tokens; revoke_all_tokens(User.objects.get(pk=<id>))` lo disconnette ovunque.
- Utente bloccato dal limite dei login all'admin (429): attendere 15 minuti dal primo errore.
- Quota giornaliera dell'import CV esaurita (409): contatore `cv_import_count` di `DailyQuota`, stesso schema di §7.3.
- Vulnerabilità note delle dipendenze (controllo manuale periodico): `docker compose -f docker-compose.prod.yml run --rm --no-deps --user root web sh -c "pip install -q pip-audit && pip-audit"` e, in `frontend/`, `npm audit --omit=dev`.
- Esiti di raccolta, scoring, generazioni e chat: modello `RunLog` (Django Admin), con `task_type`, `status`, `message`.
- PDF generato ma "pagina bianca" al download: quasi sempre stack misto dev/prod (§4.3).
- Email di servizio (Sprint 67) non arrivate: log del worker (`docker compose -f docker-compose.prod.yml logs --tail 200 worker`): "Email non configurata" = credenziali mancanti nel `.env`; errori SMTP di autenticazione = password per le app errata o revocata. I task ritentano 3 volte sugli errori di rete. Un utente che non trova l'email di verifica può chiederne un'altra dal login (3 all'ora per indirizzo); in alternativa, da Django Admin → Users, spuntare `email_verified`.
- Utente che non vuole accettare la nuova versione di informativa/termini: dalla schermata di accettazione può comunque esportare i dati o eliminare l'account. Il registro delle accettazioni è in Django Admin → Legal acceptances (sola lettura).
- Richieste sui dati da parte di un utente (accesso, cancellazione): l'utente le fa da solo da Impostazioni ("Esporta i miei dati", "Elimina account"). Anche eliminare un utente da Django Admin (o da shell con `user.delete()`) cancella tutte le sue righe, i suoi file su disco e il testo dei suoi `RunLog` (segnali di `apps/accounts/signals.py`); solo l'email di conferma parte esclusivamente dalla cancellazione fatta dall'utente.
- Copie delle email inviate: Gmail conserva ogni messaggio nella cartella "Posta inviata" dell'account mittente (indirizzo del destinatario e testo, nessun dato del profilo); vanno ripulite periodicamente a mano.
- Job senza punteggio (Sprint 68): il ciclo notturno li ritenta finché `Job.scoring_failures` non arriva a 3; a mano `python manage.py retry_unscored_jobs [--dry-run] [--user-id <id>] [--ignore-limit]` (`--ignore-limit` include quelli già arrivati a 3).
- Raccolta parziale: il `RunLog` `collection` riporta una riga per gruppo (`gruppo <tipo> · <città>, <paese>: ok, offerte=N` oppure `ERRORE …`) e gli scarti (`scartati_campi_mancanti`, `scartati_troppo_lunghi`, `scartati_duplicati`); con almeno un gruppo fallito lo stato è `failure` anche se gli altri gruppi sono stati raccolti.

## 8. Sicurezza HTTP, log e conservazione (Sprint 66)

### 8.1 Header e CSP

`Caddyfile.prod` aggiunge a tutte le risposte (anche a quelle di Django, sostituendone i valori equivalenti: niente header duplicati) `Strict-Transport-Security: max-age=31536000` (senza `includeSubDomains`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (camera, microfono, geolocalizzazione, pagamenti, USB negati), e toglie `Server`. La `Content-Security-Policy` è in modalità applicata (non report-only): solo risorse della stessa origine, stili inline ammessi (Radix), immagini anche `data:`/`blob:`, `frame-src`/`object-src` limitati a `blob:` per l'anteprima PDF degli editor, `frame-ancestors 'none'`. Testo completo e motivazioni in `Docs/02-specifiche-tecniche-v5.md` §8.3. Se una futura modifica della PWA carica risorse esterne (font, script, API di terzi) la CSP va aggiornata, altrimenti il browser le blocca (errore visibile nella console).

Caddy limita inoltre il corpo delle richieste su `/api/*` a 10 MB.

### 8.2 Log e conservazione

- **Access log di Caddy**: JSON su file nel volume `caddy_logs` (`/var/log/caddy/access.log`), ruotato ogni 24 ore (o a 10 MiB) e cancellato automaticamente dopo **14 giorni** (`roll_keep_for 336h`). Contengono gli IP dei client, quindi la conservazione è volutamente breve (14 giorni, come da informativa). La firma dei download e dell'export (`?s=`) e, dallo Sprint 67, i token dei link di verifica email e di recupero password (`?t=`, `?token=`) sono sostituiti con `REDACTED`; `Authorization`, `Cookie`, `Set-Cookie` e `Referer` (che riporterebbe gli stessi token) non sono registrati.
- **Altre conservazioni dichiarate nell'informativa** (Sprint 67): backup 7 giorni (§6), dati del throttling al massimo 24 ore (cache Redis, il limite più lungo è quello giornaliero dell'export), token di accesso 30 giorni di inattività.
- **Log dei container** (Django, Celery, Postgres, Redis, stdout di Caddy): driver `json-file` con rotazione a dimensione (5 file da 10 MB per container). Django registra errori 5xx, warning e i log del package `apps`; nessun token né query string.

## 9. Storico verifiche di deploy

- Sprint 21 (sandbox, senza VPS): validati `docker compose -f docker-compose.prod.yml config`, gunicorn con `DJANGO_DEBUG=false` dietro proxy (redirect HTTPS/cookie sicuri, nessun loop), `collectstatic`, round-trip `pg_dump -Fc` → `pg_restore` su PostgreSQL 16, `npm run build`.
- Produzione reale (da luglio 2026): certificato Let's Encrypt emesso da Caddy, stack completo in esecuzione da `docker-compose.prod.yml`.
- Non ancora verificati in produzione: backup su storage esterno e test di ripristino end-to-end (bucket non configurato, §6).
- Sprint 67 (in container, prima del deploy): backup locale con rotazione e ripristino da file locale coperti dai test con `pg_dump`/`pg_restore` simulati; non ancora verificati in produzione l'invio reale via Gmail, i profili Bedrock `eu.` e un ripristino reale da backup locale.
