# Deploy e operatività in produzione

> Stato descritto: **as-is al 2026-11-14** (Sprint 66, sicurezza).
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

`web`, `worker` e `beat` girano come utente non privilegiato `app` (**uid 1000**, `backend/Dockerfile`, Sprint 66): codice di root in sola lettura, scrivibili solo `/app/staticfiles` e `/app/mediafiles`. Tutti i servizi hanno la rotazione dei log Docker (`json-file`, 5 × 10 MB per container).

Perché `--timeout 1800` e 4 worker gunicorn: la **raccolta manuale** ("Collect now") esegue raccolta + scoring in sincrono dentro la richiesta HTTP (fino a ~100 job, scoring in parallelo con `SCORING_CONCURRENCY=5`); con il timeout di default i worker venivano uccisi a metà lasciando job senza punteggio (Sprint 45). Stesso rischio per generazione CV/cover letter (Sprint 44).

Dipendenze di sistema nell'immagine backend (`backend/Dockerfile`): librerie Pango/Cairo per WeasyPrint, `postgresql-client` (`pg_dump`/`pg_restore` per backup/ripristino), **`fonts-crosextra-caladea`** (font compatibile Cambria usato dal template CV — senza, Pango ricade su DejaVu; Sprint 52).

Servizi esterni:
- **AWS Bedrock** (Claude) — scoring, generazione CV/cover letter/messaggi, chat degli editor, parsing CV in onboarding.
- **Apify** — actor `cheap_scraper~linkedin-job-scraper` per la raccolta offerte (pay-per-result, minimo 150 risultati fatturati per chiamata).
- **LinkedIn guest API** (`jobs-guest/jobs/api/jobPosting/{id}`, nessuna chiave) — import di un job da URL.
- **Nominatim (OpenStreetMap)** — autocomplete città, nessuna chiave.
- **Web Push** (VAPID) — notifiche, nessun servizio a pagamento.

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
| Cache | `REDIS_CACHE_URL` (default `redis://redis:6379/2`) | Sprint 66. Cache Django condivisa dai worker gunicorn |
| Database | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST=db`, `POSTGRES_PORT=5432` | |
| Celery | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis del compose |
| AI (Bedrock) | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BEDROCK_REGION`, `BEDROCK_SCORING_MODEL`, `BEDROCK_CV_GENERATION_MODEL`, `BEDROCK_CV_PARSING_MODEL` | Oggi: scoring su Haiku 4.5, generazione e parsing su Opus 5 (ID inference-profile `us.anthropic.*`). L'API Anthropic diretta non è più usata (dal 18/08/2026) |
| Fonte offerte | `APIFY_API_TOKEN` | Unica variabile letta dal codice (altre varianti nel `.env` sono ignorate) |
| Login Google | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | **Oggi vuote in produzione** → login Google non attivo, solo email/password |
| Push | `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL` | |
| Prezzi extra (€) | `PRICE_MANUAL_CV_EXTRA` (1.50), `PRICE_IMPORT_EXTRA` (0.50), `PRICE_COVER_LETTER_EXTRA` (1.50), `PRICE_MANUAL_JOB_EXTRA` (0.50), `PRICE_REFERRAL_MESSAGE_EXTRA` (1.00), `PRICE_CV_DRAFT_CHAT_MESSAGE` (0.20), `PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE` (0.20) | Facoltative: tra parentesi il default in `config/settings.py` |
| Deploy | `DOMAIN`, `CADDY_EMAIL` | Solo `docker-compose.prod.yml` |
| Backup | `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_BUCKET`, `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY`, `BACKUP_S3_REGION` | **Oggi vuote in produzione** → vedi §6 |

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
docker compose -f docker-compose.prod.yml run --rm --no-deps -e DJANGO_DEBUG=true web python manage.py test --noinput   # suite backend (299 test, OK al 2026-11-14, Sprint 66)
docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.prod.yml run --rm --no-deps web python manage.py check --deploy                     # con DEBUG=false: nessun problema atteso
cd frontend && npm run test:e2e                                                     # Playwright (e2e/*.spec.js)
```

`run --rm --no-deps` usa l'immagine appena ricostruita senza toccare i container in esecuzione (si collega al `db` di produzione solo per creare/distruggere il database di test). Nei test la cache è una `DummyCache`: niente contatori su Redis. Frontend senza toccare la PWA in produzione: `docker compose -f docker-compose.prod.yml build frontend-build` e poi `docker run --rm --entrypoint sh app-apply-frontend-build -c "npm run build && npx oxlint src"` (mai `run`/`up` del servizio `frontend-build`, che sovrascrive il volume servito da Caddy). Caddyfile: `docker run --rm -v $PWD/docker/caddy/Caddyfile.prod:/etc/caddy/Caddyfile:ro -e DOMAIN=example.com -e CADDY_EMAIL=a@example.com caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile`.

`-e DJANGO_DEBUG=true` è necessario: con la configurazione di produzione (`DEBUG=false` → redirect HTTPS) il test client riceve 301 su tutte le chiamate API e circa 60 test falliscono senza che ci sia una regressione. Il database di test è separato (`test_<db>`), i dati di produzione non vengono toccati.

I test e2e usano i comandi `set_e2e_account` e `seed_e2e_jobs` per preparare account e job di prova. Dallo Sprint 66 il login è limitato a 10 tentativi al minuto per IP: una suite e2e lunga lanciata contro lo stesso ambiente può ricevere 429.

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

## 5. Task schedulati (Celery Beat, `DatabaseScheduler`)

Creati da migrazioni dati (modificabili da Django Admin → Periodic tasks):

| Task | Quando | Migrazione |
|---|---|---|
| Ciclo notturno — `apps.jobs.tasks.run_nightly_cycle` (oggi solo raccolta + scoring: cap di intake e CV automatici rimossi; il nome del PeriodicTask è rimasto quello storico) | 02:00 Europe/Rome | `jobs/0003_schedule_nightly_cycle` |
| Notifica mattutina (nuovi job) e promemoria di inattività (7 giorni) | ogni 15 minuti; la notifica mattutina parte solo nell'ora 10 locale dell'utente | `notifications/0002_schedule_notification_tasks` |
| Backup giornaliero database | 03:30 Europe/Rome | `common/0001_schedule_backup` |

## 6. Backup e ripristino

Il task `apps.common.tasks.backup_database` esegue `pg_dump -Fc` + archivio dei file media e li carica sul bucket S3-compatibile configurato in `BACKUP_S3_*`. Se le variabili sono vuote il task registra solo un warning e **non salva nulla**.

> ⚠️ **Stato attuale:** `BACKUP_S3_*` non è configurato in produzione, quindi **non esiste un backup automatico fuori dal VPS**. Esistono solo dump manuali locali in `backups/` (gitignored), fatti prima di interventi distruttivi (es. `pre_cv_wipe_20260828_*.dump`). Configurare un bucket è un'azione consigliata.

Backup manuale locale (dump nella cartella `backups/` del repo, non versionata):

```
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > backups/manual_$(date +%Y%m%d_%H%M%S).dump
```

Backup su S3 lanciato a mano: `docker compose -f docker-compose.prod.yml exec worker python manage.py shell -c "from apps.common.tasks import backup_database; backup_database()"`.

Ripristino di prova (**mai contro la produzione**, ambiente separato puntato allo stesso bucket): `python manage.py restore_backup AAAA-MM-GG --confirm` (scarica `db-AAAA-MM-GG.dump` e fa `pg_restore --clean --if-exists`).

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
Il limite è `COLLECTION_DAILY_LIMIT = 1` raccolta manuale al giorno per utente, uguale per Free e Pro (`apps/jobs/tasks.py`). Per concederne un'altra oggi:
```
$SHELL_DJANGO "
from apps.accounts.models import User; from apps.jobs.models import DailyQuota; from apps.jobs.tasks import _today_europe_rome
q = DailyQuota.objects.get(user=User.objects.get(pk=<id>), date=_today_europe_rome()); q.collection_count = 0; q.save(update_fields=['collection_count']); print('ok')"
```
Stesso schema per gli altri contatori di `DailyQuota` (`manual_cv_count`, `import_count`, `cover_letter_count`, `manual_job_count`, `referral_message_count`). Il 409 può anche indicare una raccolta già in corso (`User.collection_in_progress`): il lock scade da solo dopo 2 ore (`COLLECTION_STALE_AFTER`).

### 7.4 Rilanciare la raccolta notturna per un solo utente
Non esiste un task Celery per singolo utente: si chiama la funzione da shell.
```
$SHELL_DJANGO "
from apps.accounts.models import User; from apps.jobs.tasks import run_nightly_cycle_for_user
print(run_nightly_cycle_for_user(User.objects.get(pk=<id>)))"
```
Attenzione: nessuna guardia di quota/lock su questo percorso e **ogni gruppo ricerca×location è una chiamata Apify a pagamento** (≥150 risultati fatturati). I job già presenti non vengono duplicati (dedup su `external_id`).

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

## 8. Sicurezza HTTP, log e conservazione (Sprint 66)

### 8.1 Header e CSP

`Caddyfile.prod` aggiunge a tutte le risposte (anche a quelle di Django, sostituendone i valori equivalenti: niente header duplicati) `Strict-Transport-Security: max-age=31536000` (senza `includeSubDomains`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` (camera, microfono, geolocalizzazione, pagamenti, USB negati), e toglie `Server`. La `Content-Security-Policy` è in modalità applicata (non report-only): solo risorse della stessa origine, stili inline ammessi (Radix), immagini anche `data:`/`blob:`, `frame-src`/`object-src` limitati a `blob:` per l'anteprima PDF degli editor, `frame-ancestors 'none'`. Testo completo e motivazioni in `Docs/02-specifiche-tecniche-v5.md` §8.3. Se una futura modifica della PWA carica risorse esterne (font, script, API di terzi) la CSP va aggiornata, altrimenti il browser le blocca (errore visibile nella console).

Caddy limita inoltre il corpo delle richieste su `/api/*` a 10 MB.

### 8.2 Log e conservazione

- **Access log di Caddy**: JSON su file nel volume `caddy_logs` (`/var/log/caddy/access.log`), ruotato ogni 24 ore (o a 10 MiB) e cancellato automaticamente dopo **14 giorni** (`roll_keep_for 336h`). Contengono gli IP dei client, quindi la conservazione è volutamente breve (14 giorni, come da informativa). La firma dei download (`?s=`) è sostituita con `REDACTED`; `Authorization`, `Cookie` e `Set-Cookie` non sono registrati.
- **Log dei container** (Django, Celery, Postgres, Redis, stdout di Caddy): driver `json-file` con rotazione a dimensione (5 file da 10 MB per container). Django registra errori 5xx, warning e i log del package `apps`; nessun token né query string.

## 9. Storico verifiche di deploy

- Sprint 21 (sandbox, senza VPS): validati `docker compose -f docker-compose.prod.yml config`, gunicorn con `DJANGO_DEBUG=false` dietro proxy (redirect HTTPS/cookie sicuri, nessun loop), `collectstatic`, round-trip `pg_dump -Fc` → `pg_restore` su PostgreSQL 16, `npm run build`.
- Produzione reale (da luglio 2026): certificato Let's Encrypt emesso da Caddy, stack completo in esecuzione da `docker-compose.prod.yml`.
- Non ancora verificati in produzione: backup su storage esterno e test di ripristino end-to-end (bucket non configurato, §6).
