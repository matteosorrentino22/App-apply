# Sprint 01 — Setup progetto & infrastruttura

## Input
- Nessun prerequisito di codice: primo sprint del progetto.
- Riferimenti: `02-specifiche-tecniche-v3.md` §2 (architettura), §3.1–3.2 (Django, Celery/Redis), §8 (hosting e deploy).

## Obiettivo
Creare lo scheletro Django del monolite, configurare Celery + Redis per i task in background, e un Docker Compose di sviluppo con tutti i servizi previsti (Django, PostgreSQL, Redis, worker Celery, Beat, Caddy).

## Risultato atteso
`docker compose up` avvia tutti i servizi senza errori; l'admin Django è raggiungibile (senza modelli custom); un task Celery di prova viene eseguito dal worker.

## Criteri di verifica
- `docker compose up -d` termina senza errori; `docker compose ps` mostra tutti i container in stato "Up"/"healthy".
- `curl http://localhost:<port>/admin/` restituisce 200 o redirect al login.
- `docker compose exec web python manage.py check` non restituisce errori.
- `docker compose exec web python manage.py migrate` applica le migrazioni di default Django senza errori.
- Un task Celery di test (es. una funzione `add(a, b)` decorata `@shared_task`) invocato con `.delay()` viene eseguito dal worker e il risultato è recuperabile tramite `AsyncResult`.

## Output per lo sprint successivo
Repository con scheletro Django/Celery/Docker funzionante e struttura delle app Django pronta per ricevere i modelli dati (Sprint 02).

---

## Esito (2026-07-26)

**Stato: completato**, con una riserva sull'ambiente di verifica (vedi Criticità).

### Cosa è stato fatto
- Progetto Django creato in `backend/`, con package di configurazione `config/` (`settings.py`, `urls.py`, `celery.py`, `wsgi.py`) e app in `backend/apps/`:
  - `apps.accounts` — modello `User` custom (subclass di `AbstractUser`, ancora senza i campi aggiuntivi: arrivano nello Sprint 02), registrato in `AUTH_USER_MODEL` e in Django Admin.
  - `apps.common` — task Celery di prova `add(a, b)` (`@shared_task`).
- `config/settings.py`: `DATABASES` su PostgreSQL, `TIME_ZONE = "Europe/Rome"` (fuso di sistema per batch/quote, §7 tecniche), Celery configurato su Redis (broker DB 0, result backend DB 1), DRF installato (nessuna vista ancora, la useremo da Sprint 15). Tutti i parametri sensibili (secret key, credenziali DB, allowed hosts, broker URL) letti da variabili d'ambiente, mai hardcoded.
- `docker-compose.yml` (sviluppo) con 6 servizi: `db` (postgres:16-alpine, con healthcheck e volume persistente), `redis` (redis:7-alpine, con healthcheck), `web` (`runserver`), `worker` (`celery -A config worker`), `beat` (`celery -A config beat`), `caddy` (reverse proxy su `:8080→:80`, HTTP semplice in dev — l'HTTPS automatico è oggetto dello Sprint 21). Immagine unica (`backend/Dockerfile`) condivisa da `web`/`worker`/`beat`.
- `.env.example` alla radice con tutte le variabili attese; `.gitignore` esclude `.env` reale ma **non** le migrazioni (che vanno committate, vedi CLAUDE.md aggiornato).
- Migrazione iniziale di `accounts.User` generata e committata (necessaria da subito: vedi Criticità).
- Sezione "Convenzioni di codice" di `CLAUDE.md` compilata (struttura cartelle, naming app, gestione migrazioni/segreti/Docker).

### Criticità riscontrate
1. **`docker compose up` non eseguibile in questo ambiente di sviluppo remoto.** Il daemon Docker di questa sandbox non pulls le immagini base (`python:3.12-slim`, `postgres:16-alpine`, ecc.): il proxy di rete della sessione nega esplicitamente (403) l'host CDN di Docker Hub (`production.cloudfront.docker.com`) per policy, non per un errore di configurazione. `docker compose config` conferma che il file è sintatticamente valido; la build/esecuzione reale va verificata su una macchina (o CI) con accesso libero a Docker Hub, oppure su una VPS di deploy. **Non è un limite del codice prodotto**, ma dell'ambiente in cui è stato scritto.
2. **Verifica funzionale alternativa eseguita senza Docker.** Per non lasciare i criteri di verifica non controllati, ho installato le stesse dipendenze (`backend/requirements.txt`) in un virtualenv locale e usato PostgreSQL 16 / Redis 7 già presenti nel sistema (non containerizzati) per riprodurre gli stessi passaggi:
   - `python manage.py check` → nessun errore.
   - `python manage.py makemigrations` + `migrate` → applicate senza errori (incluse le migrazioni Django di default + `accounts.0001_initial`).
   - `python manage.py runserver` + `curl http://localhost:8000/admin/` → **302** (redirect al login), come da criterio.
   - `celery -A config worker` avviato, task `apps.common.tasks.add` registrato; `add.delay(3, 4)` eseguito dal worker e `AsyncResult` risolto a `7`.
   Tutti i comportamenti applicativi richiesti dallo sprint sono quindi verificati; resta da ripetere lo stesso smoke test con `docker compose up -d` reale al primo utilizzo in un ambiente con accesso a Docker Hub (es. VPS di destinazione o CI), cosa consigliata prima di chiudere definitivamente lo sprint.
3. **Decisione tecnica non esplicitamente richiesta dallo sprint, ma necessaria: `AUTH_USER_MODEL` custom fin da subito.** Le specifiche tecniche (§4.1) prevedono che `User` sia "gestito dal sistema nativo di Django, esteso con i campi che ci servono", e lo Sprint 02 è quello che aggiunge tali campi. Se lo Sprint 01 avesse migrato lo `User` di default di Django, cambiare `AUTH_USER_MODEL` nello Sprint 02 avrebbe richiesto un database vuoto da rifare — un problema noto di Django, non aggirabile a posteriori. Ho quindi creato da subito `apps.accounts.User` (sottoclasse vuota di `AbstractUser`, nessun campo extra) e puntato `AUTH_USER_MODEL` lì, cosa che non cambia l'architettura decisa (resta "sistema nativo Django, esteso") ma va segnalata come previsto da CLAUDE.md ("Cosa NON fare" — modifiche di architettura vanno esplicitate).

### Cosa manca
- Il frontend React/PWA (fuori scope: Sprint 18+).
- Configurazione di produzione (`docker-compose.prod.yml`, Caddy con HTTPS reale, backup, aggiornamenti di sicurezza): Sprint 21.
- Un vero smoke test di `docker compose up -d` su un ambiente con accesso a Docker Hub (vedi Criticità §1).
- Tutti i modelli applicativi (`Profile`, `Job`, `SavedSearch`, ecc.): Sprint 02.

### Requisiti soddisfatti (criteri di verifica dello sprint)
| Criterio | Esito |
|---|---|
| `docker compose up -d` senza errori, tutti i container "Up"/"healthy" | ⚠️ Non eseguibile in questo ambiente (pull immagini bloccato dalla policy di rete); file verificato con `docker compose config` (sintassi valida). Da confermare in un ambiente con accesso a Docker Hub. |
| `curl .../admin/` → 200 o redirect login | ✅ Verificato (302), tramite `runserver` locale equivalente al servizio `web` |
| `manage.py check` senza errori | ✅ Verificato |
| `manage.py migrate` applica le migrazioni di default senza errori | ✅ Verificato |
| Task Celery di prova (`add(a, b)`) eseguito dal worker via `.delay()`, risultato recuperabile da `AsyncResult` | ✅ Verificato (worker reale, Redis reale) |