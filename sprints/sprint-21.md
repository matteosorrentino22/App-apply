# Sprint 21 — Deploy produzione

## Input
- Sprint 01 (Docker Compose base) e tutti gli sprint precedenti (applicazione completa).
- Riferimenti: `02-specifiche-tecniche-v3.md` §8, §8.5.

## Obiettivo
Configurazione Docker Compose di produzione con Caddy come reverse proxy e HTTPS automatico, segreti in variabili d'ambiente (Apify, Anthropic, Google OAuth, Web Push), backup automatico giornaliero del database su storage esterno al VPS, aggiornamenti di sicurezza automatici del sistema operativo.

## Risultato atteso
L'applicazione è raggiungibile in HTTPS su un dominio di test tramite Caddy; un backup del database viene prodotto ed esportato fuori dal VPS secondo pianificazione; nessun segreto è presente nel repository.

## Criteri di verifica
- `docker compose -f docker-compose.prod.yml up -d` avvia tutti i servizi in produzione senza errori.
- Richiesta HTTPS al dominio/IP di test restituisce certificato valido emesso da Let's Encrypt (`curl -v https://...` o strumento equivalente).
- Verifica statica: nessuna chiave/token/password in chiaro nei file versionati; tutte le chiavi sono lette da variabili d'ambiente.
- Eseguendo manualmente lo script/job di backup, viene prodotto un dump del database presente sullo storage esterno configurato.
- Eseguendo un ripristino di prova dal dump più recente su un ambiente separato, il database risultante contiene i dati attesi (test di restore, non solo di backup).

## Output per lo sprint successivo
Ambiente di produzione funzionante e verificato, base per la validazione finale end-to-end (Sprint 22).

---

## Esito (2026-07-27)

**Stato: completato lato codice/configurazione; verifica finale su VPS reale non eseguibile da questo ambiente (vedi "Cosa manca").**

### Cosa è stato fatto
- **`docker-compose.prod.yml`** (nuovo, alla radice, alternativo a `docker-compose.yml` — coerente con la convenzione già fissata in CLAUDE.md): `db`/`redis`/`worker`/`beat` come in dev ma con `restart: unless-stopped`; `web` esegue `migrate --noinput && collectstatic --noinput` poi serve con **gunicorn** (mai `runserver` in produzione); un nuovo servizio `frontend-build` (one-shot: compila la PWA con `npm run build`, scrive l'output in un volume, poi termina — **nessun processo Node in produzione**, a differenza di dev); `caddy` monta `Caddyfile.prod`, pubblica 80/443(+443/udp) e serve direttamente da volume sia gli statici Django (`/static/*`) sia i media (`/media/*`) sia la PWA compilata, oltre a fare da reverse proxy per `/api`, `/admin`, `/accounts`.
- **`docker/caddy/Caddyfile.prod`** (nuovo): blocco globale `email {$CADDY_EMAIL}` + sito `{$DOMAIN}` — Caddy ottiene/rinnova il certificato Let's Encrypt automaticamente per quel dominio (§8.3), nessuna configurazione TLS manuale. `handle_path` per static/media (file_server diretto, senza passare da Django/gunicorn), `try_files {path} /index.html` per il fallback SPA delle rotte di React Router.
- **Sicurezza Django dietro proxy** (`config/settings.py`, attiva solo se `DEBUG=False`): `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER` (per riconoscere l'HTTPS terminato da Caddy senza loop di redirect), `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`.
- **Backup giornaliero** (`apps/common/tasks.py::backup_database`, pianificato alle **03:30 Europe/Rome** — dopo il ciclo notturno delle 02:00, stessa migrazione dati usata per gli altri task pianificati in Sprint 05/17): `pg_dump -Fc` del database + archivio tar.gz dei file media (PDF dei CV inclusi "per comodità", come indicato esplicitamente da §8.4), caricati su uno **storage compatibile S3** (nessun servizio proprietario: funziona con Hetzner Object Storage, Backblaze B2, AWS S3 o equivalenti) via `boto3`, configurabile solo da variabili d'ambiente. Se il bucket non è configurato, il task si limita a un warning nei log (non fa fallire il ciclo Celery Beat, utile in sviluppo).
- **`restore_backup`** (nuovo management command): scarica un dump datato dal bucket e lo ripristina con `pg_restore --clean --if-exists`; richiede `--confirm` esplicito per evitare un ripristino accidentale che sovrascrive un database (pensato per un ambiente di test separato, mai per la produzione).
- **`docker/vps-setup.sh`** (nuovo, da eseguire una tantum da root sul VPS): installa e attiva `unattended-upgrades` (aggiornamenti di sicurezza automatici del sistema operativo, §8.5 — l'unica manutenzione di sistema ricorrente richiesta dalle specifiche).
- **`DEPLOY.md`** (nuovo, alla radice): runbook con i passi di deploy, le variabili d'ambiente aggiuntive richieste in produzione, i comandi per lanciare un backup manuale e per eseguire un ripristino di prova.
- **`.env.example`** aggiornato con le nuove variabili di produzione (`DOMAIN`, `CADDY_EMAIL`, `BACKUP_S3_*`), tutte vuote di default — nessun segreto reale nel repository (verificato anche con una ricerca statica mirata sul diff).
- **Dipendenze aggiunte** (segnalate esplicitamente, non c'erano alternative già in requirements.txt): `gunicorn` (server WSGI di produzione, necessario perché il server di sviluppo Django non è adatto alla produzione) e `boto3` (client S3 standard per il caricamento dei backup, nessuna libreria più leggera copre altrettanto bene provider S3-compatibili diversi). `postgresql-client` aggiunto al `Dockerfile` (fornisce i binari `pg_dump`/`pg_restore`, assenti da `psycopg2-binary`).

### Decisioni tecniche non esplicitamente richieste, da segnalare
- Il backup è un **task Celery** pianificato via lo stesso meccanismo (`django_celery_beat`, migrazione dati) già usato per il ciclo notturno e le notifiche, invece di un cron di sistema separato dentro un container dedicato: riusa l'infrastruttura di scheduling già presente, coerente con "no over-engineering".
- La PWA in produzione **non gira più come processo Node**: è compilata una volta (`frontend-build`, servizio one-shot) e servita da Caddy come file statici — semplifica il footprint di produzione rispetto a tenere un server Vite sempre acceso, che in dev serve solo per l'HMR.
- Log del backup tramite il logger Python standard, non tramite il modello `RunLog` (Sprint 05, scoped a `user`/`job` per il ciclo notturno per-utente): un backup è un'operazione di sistema, non per-utente, forzarla in quel modello avrebbe richiesto allargarne il dominio (nuovo `TaskType`) per un log tecnico già coperto dai log del container.
- Aggiunte `SECURE_SSL_REDIRECT`/`SECURE_PROXY_SSL_HEADER`/cookie sicuri non erano elencate esplicitamente nei criteri di sprint ma sono necessarie per un funzionamento corretto dietro Caddy in HTTPS (senza `SECURE_PROXY_SSL_HEADER` si genera un loop di redirect, verificato empiricamente in questo sprint).

### Verifica eseguita (in questo ambiente sandbox, senza VPS/dominio reale)
- `docker compose -f docker-compose.prod.yml config` — sintassi e interpolazione delle variabili verificate corrette per tutti i servizi.
- `gunicorn config.wsgi:application` avviato realmente con `DJANGO_DEBUG=false`: confermato il redirect a HTTPS quando manca l'header `X-Forwarded-Proto`, confermata l'assenza di loop di redirect e una risposta corretta quando l'header è presente (simula il comportamento di Caddy dietro cui girerà davvero).
- `python manage.py collectstatic --noinput` eseguito realmente, produce i file statici attesi.
- **Round-trip reale di backup/ripristino**: `pg_dump -Fc` sul database locale (PostgreSQL 16, stessa versione major dell'immagine `postgres:16-alpine` usata in produzione) seguito da `pg_restore --clean --if-exists` in un database di prova separato — il numero di righe ripristinate corrisponde esattamente a quello di partenza (stesso comando usato, verbatim, da `backup_database` e da `restore_backup`).
- `npm run build` produce la build statica della PWA che `frontend-build` compilerà in produzione.
- Backend: `python manage.py test` → **103/103 passati** (98 pre-esistenti + 5 nuovi in `apps/common/tests.py`: pianificazione del task di backup, skip quando il bucket non è configurato, dump+upload mockati con verifica delle chiavi caricate, `restore_backup` che rifiuta senza `--confirm`/senza bucket configurato); `makemigrations --check` pulito.
- Verifica statica: nessuna chiave/token/password in chiaro nei file versionati (tutte le nuove variabili lette da env, `.env.example` senza valori reali, `.env` resta in `.gitignore`).

### Cosa manca
- **Emissione reale di un certificato Let's Encrypt** e **avvio effettivo di `docker compose -f docker-compose.prod.yml up -d`**: richiedono rispettivamente un dominio pubblico raggiungibile su 80/443 e un demone Docker funzionante — questo ambiente sandbox non ha un demone Docker realmente eseguibile (`docker info` funziona, ma `docker compose build/up` falliscono per l'assenza del socket) e non ha un dominio/VPS reale. Solo la validazione statica della configurazione (`config`) è stata possibile qui.
- **Backup reale su storage a oggetti esterno e test di ripristino end-to-end** con credenziali S3 vere: verificata solo la logica (mockata per S3, reale per `pg_dump`/`pg_restore`), non il giro completo con un bucket reale.
- **`unattended-upgrades` su un sistema operativo VPS reale**: lo script è scritto secondo la procedura standard Debian/Ubuntu, ma non eseguibile/verificabile in un container sandbox senza un vero OS host da amministrare.

Questi tre punti restano da eseguire e confermare direttamente sul VPS del committente, seguendo `DEPLOY.md`.