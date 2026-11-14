# App-apply

Web app (PWA) che centralizza e automatizza la ricerca di lavoro: ogni notte raccoglie offerte da LinkedIn in base alle ricerche salvate dall'utente, e ne valuta l'affinità col suo profilo (punteggio 1–10 con match/gap e motivazione). Su ogni offerta l'utente può poi generare su richiesta un CV personalizzato in PDF, una cover letter e messaggi di networking, rifinirli con un editor interattivo assistito da una chat AI e tracciare la candidatura.

> Stato descritto: **as-is al 2026-11-14 (Sprint 64)**. Progetto MVP per una cerchia ristretta di utenti di test.

## Funzionalità (sintesi)

- **Onboarding e profilo master** — import del CV esistente (PDF/DOCX) con pre-compilazione AI, profilo strutturato (sommario, esperienze, istruzione, competenze/certificazioni, lingue), pagina Profilo modificabile.
- **Ricerche salvate** — tipo *Job role keyword* o *Company*, città/paese con autocomplete, limiti per piano (Free / Pro).
- **Raccolta offerte** — ciclo notturno automatico (Apify, actor LinkedIn), raccolta manuale "Collect now" (1/giorno), import di un job da URL LinkedIn, creazione manuale di un job.
- **Scoring AI** — punteggio 1–10 con rubrica, match/gap con motivazione espandibile, tetto automatico se il job richiede una lingua assente dal profilo.
- **Lista job** — sezioni, ricerca testuale, filtri (score, stato, ricerca di provenienza, location, date, n. candidati, recruiter), preferiti, archivio, filtri preferiti salvabili; Home con statistiche.
- **CV personalizzato** — generazione su richiesta (non più automatica di notte) con contenuti AI ancorati al profilo, "colma i gap" opzionale, grassetto sulle keyword rilevanti, template PDF a 1 pagina; **editor del CV** con anteprima live e **chat AI** (proposta → conferma).
- **Cover letter** — generazione con istruzioni riutilizzabili, editor e chat AI dedicati.
- **Messaggi di networking** — messaggio LinkedIn o email per chiedere una raccomandazione sulla posizione.
- **Piani e credito** — massimali giornalieri per piano, credito extra in € con listino per azione.
- **Notifiche push** — notifica mattutina sui nuovi job, promemoria di inattività.

## Stack

Django + DRF · Celery + Redis (Beat con DatabaseScheduler) · PostgreSQL 16 · React (Vite) PWA con Tailwind/shadcn · Claude via **AWS Bedrock** · WeasyPrint (HTML→PDF) · Docker Compose + Caddy su un VPS singolo.

## Struttura del repository

| Percorso | Contenuto |
|---|---|
| `backend/` | Progetto Django (`config/`) e app in `apps/`: `accounts`, `profiles`, `searches`, `jobs`, `cv`, `notifications`, `common` |
| `frontend/` | PWA React (`src/pages`, `src/components`, `src/api`, `src/i18n`), test e2e Playwright in `e2e/` |
| `docker/`, `docker-compose*.yml` | Deploy (Caddy, setup VPS) — `docker-compose.prod.yml` in produzione, `docker-compose.yml` solo sviluppo |
| `Docs/` | Specifiche correnti (vedi sotto) e `archivio/` con le versioni superate |
| `sprints/` | Una scheda per sprint (`sprint-NN.md`): richiesta, decisioni, implementazione, verifica |

## Documentazione

| Documento | Cosa descrive |
|---|---|
| [`Docs/01-specifiche-funzionali-v6.md`](Docs/01-specifiche-funzionali-v6.md) | **Cosa** fa l'app (as-is completo) |
| [`Docs/02-specifiche-tecniche-v5.md`](Docs/02-specifiche-tecniche-v5.md) | **Come** è costruita: architettura, modello dati, flussi, API, infrastruttura |
| [`Docs/03-specifiche-funzionali-contenuto-cv-v5.md`](Docs/03-specifiche-funzionali-contenuto-cv-v5.md) | Regole di contenuto, selezione e impaginazione del CV generato |
| [`Docs/CHANGELOG.md`](Docs/CHANGELOG.md) | Storico delle versioni delle specifiche e mappa sprint → documenti |
| [`DEPLOY.md`](DEPLOY.md) | Deploy in produzione e runbook operativo |
| [`CLAUDE.md`](CLAUDE.md) | Istruzioni e convenzioni per lo sviluppo assistito (Claude Code) |
| [`sprints/`](sprints/) | Storico degli sprint |

## Avvio in sviluppo

```
cp .env.example .env        # compilare almeno le credenziali AWS Bedrock e il token Apify per le funzioni AI/raccolta
docker compose up --build    # db, redis, web (runserver), worker, beat, frontend (Vite), caddy
```

La PWA è servita da Caddy su `http://localhost:8080` (vedi `docker/caddy/Caddyfile`). Test: `docker compose exec web python manage.py test` (backend), `cd frontend && npm run test:e2e` (Playwright).

Produzione: vedi [`DEPLOY.md`](DEPLOY.md).
