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