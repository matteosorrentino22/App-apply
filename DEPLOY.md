# Deploy produzione

Riferimento: `02-specifiche-tecniche-v3.md` §8. Un unico VPS (es. Hetzner), Docker Compose, Caddy con HTTPS automatico.

## 1. Provisioning una tantum del VPS

Da root, subito dopo il provisioning e prima del primo `docker compose up`:

```
./docker/vps-setup.sh
```

Installa e attiva `unattended-upgrades` (aggiornamenti di sicurezza automatici del sistema operativo, §8.5). Installare Docker Engine + plugin Compose separatamente (non coperto da questo script, dipende dalla distribuzione).

## 2. Configurazione

Copiare `.env.example` in `.env` sul VPS e compilare tutti i valori, in particolare rispetto allo sviluppo:

- `DJANGO_DEBUG=false`
- `DJANGO_SECRET_KEY` — valore reale generato (mai quello di sviluppo)
- `DJANGO_ALLOWED_HOSTS` — il dominio reale (es. `app.example.com`)
- `DJANGO_CSRF_TRUSTED_ORIGINS` — `https://<dominio>`
- `DOMAIN` — dominio su cui Caddy richiede il certificato Let's Encrypt
- `CADDY_EMAIL` — email per le notifiche ACME di Let's Encrypt
- `BACKUP_S3_*` — credenziali dello storage a oggetti esterno per il backup giornaliero
- Tutte le chiavi già previste in sviluppo (Apify, Anthropic, Google OAuth, VAPID) con i valori reali di produzione

Nessun segreto va mai committato: `.env` è in `.gitignore`, solo `.env.example` (senza valori reali) è versionato.

## 3. Avvio

```
docker compose -f docker-compose.prod.yml up -d --build
```

Avvia `db`, `redis`, `web` (esegue `migrate` + `collectstatic` poi serve con `gunicorn`), `worker`, `beat`, `frontend-build` (compila la PWA una tantum in un volume) e `caddy` (HTTPS automatico su `DOMAIN`, serve la PWA, i file statici/media e fa da reverse proxy per `/api`, `/admin`, `/accounts`).

Verifica: `curl -v https://<dominio>/` deve restituire un certificato valido emesso da Let's Encrypt.

## 4. Backup

Il backup gira automaticamente ogni notte alle 03:30 Europe/Rome (Celery Beat, task `apps.common.tasks.backup_database`): dump del database (`pg_dump -Fc`) + archivio dei file media, caricati sul bucket S3-compatibile configurato in `BACKUP_S3_*`.

Per lanciarlo manualmente:

```
docker compose -f docker-compose.prod.yml exec worker python manage.py shell -c \
  "from apps.common.tasks import backup_database; backup_database()"
```

## 5. Test di ripristino

Da eseguire **su un ambiente separato** (mai contro il database di produzione), puntando `.env` di quell'ambiente allo stesso bucket di backup:

```
docker compose exec web python manage.py restore_backup 2026-07-27 --confirm
```

Scarica `db-2026-07-27.dump` dal bucket e lo ripristina (`pg_restore --clean --if-exists`) nel database a cui l'ambiente è collegato. Verificare poi che i dati attesi siano presenti (es. conteggio utenti/job).

## Verificato in questo sprint (sandbox, senza VPS reale)

- `docker compose -f docker-compose.prod.yml config` — sintassi e interpolazione delle variabili corrette.
- `gunicorn config.wsgi:application` avviato con `DJANGO_DEBUG=false`: redirect HTTPS e cookie sicuri attivi, nessun loop di redirect dietro un proxy che imposta `X-Forwarded-Proto` (comportamento di Caddy).
- `collectstatic` produce i file statici correttamente.
- Round-trip reale `pg_dump -Fc` → `pg_restore --clean --if-exists` contro PostgreSQL 16 locale: i dati ripristinati in un database di prova corrispondono a quelli di partenza.
- `npm run build` produce la build statica della PWA.

## Non verificabile in questo ambiente

- Emissione reale di un certificato Let's Encrypt (richiede un dominio pubblico e porte 80/443 raggiungibili da Internet).
- Avvio effettivo di `docker compose -f docker-compose.prod.yml up -d` (il sandbox di sviluppo non ha un demone Docker funzionante — build/`up` non eseguibili qui, solo `config` per la validazione statica).
- Backup reale su uno storage a oggetti esterno (nessuna credenziale S3 di test disponibile) e relativo test di ripristino end-to-end su un ambiente separato.
- Comportamento reale di `unattended-upgrades` su un sistema operativo effettivamente installato sul VPS.

Questi punti restano da eseguire e confermare direttamente sul VPS reale.
