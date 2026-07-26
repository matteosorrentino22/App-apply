# CLAUDE.md

## Progetto
App che centralizza e automatizza la ricerca di lavoro: raccoglie offerte da LinkedIn ogni notte, ne valuta l'affinità con il profilo dell'utente (punteggio 1–5 + match/gap) e genera automaticamente un CV personalizzato in PDF per le offerte più promettenti. L'utente riceve una notifica mattutina e trova la lista già pronta, con possibilità di generazione manuale, import di job, arricchimento del profilo e tracciamento minimo della candidatura.
Riferimenti: `01-specifiche-funzionali-v4.md`, `02-specifiche-tecniche-v3.md`

## Stack
- **Backend:** Python + Django (+ Django REST Framework per l'API interna consumata dalla PWA)
- **Task in background:** Celery + Redis (raccolta notturna, scoring, generazione CV, notifiche)
- **Scheduler:** Celery Beat (batch notturno alle 02:00 Europe/Rome, controllo notifiche 10:00 locali, promemoria inattività)
- **Frontend:** React come PWA (no pubblicazione store, no cache offline — solo reattività dell'API)
- **Database:** PostgreSQL
- **Fonte offerte:** Apify (LinkedIn), dietro un'interfaccia interna sostituibile — una chiamata per utente/notte, limite 50 (Free) / 100 (Pro) job/notte
- **Motore AI:** API Anthropic (Claude) — scoring, generazione CV, parsing del CV caricato in onboarding
- **Generazione CV:** template HTML/CSS → PDF (WeasyPrint). Solo PDF nell'MVP, nessuna pipeline Word
- **Credito extra:** saldo in euro (`Decimal`) con listino prezzi unitari configurabile per azione
- **Autenticazione:** email/password (nativa Django) + login Google (django-allauth)
- **Notifiche:** Web Push standard (es. libreria `pywebpush`), nessun servizio esterno a pagamento
- **Hosting:** VPS singolo economico (es. Hetzner)
- **Deploy:** Docker Compose (Django, PostgreSQL, Redis, worker Celery, Caddy) + Caddy come reverse proxy con HTTPS automatico
- **Amministrazione:** Django Admin per gestione piani, credito, voucher (nessun checkout self-service nell'MVP)

## Principi guida
- Semplicità e manutenibilità prima di tutto: no over-engineering
- Architettura monolitica, non introdurre microservizi/servizi extra
- Preferire soluzioni standard/documentate a quelle esotiche
- MVP per una cerchia ristretta di utenti di test: nessun requisito di scala da rispettare
- Il *cosa* è definito nelle specifiche funzionali, il *come* nelle specifiche tecniche: in caso di dubbio implementativo, verificare prima lì

## Convenzioni di codice
Proposte nello Sprint 01, in vigore da qui in avanti:

- **Struttura repo:** codice Django in `backend/`, deploy (`docker-compose.yml`, `docker/`) alla radice insieme alle specifiche e a `/sprints`. Il frontend React (da Sprint 18) andrà in `frontend/` allo stesso livello di `backend/`.
- **Progetto Django:** cartella di settings/config si chiama `config` (non il nome dell'app), con `config/settings.py` unico (niente split `base/dev/prod`: la differenza dev/prod passa da variabili d'ambiente e da `docker-compose.yml` vs `docker-compose.prod.yml`, non da moduli di settings diversi — coerente con "no over-engineering").
- **App Django:** vivono in `backend/apps/<nome_app>/`, importate come `apps.<nome_app>` in `INSTALLED_APPS`. Un'app per dominio funzionale (es. `accounts`, `common`; seguiranno `profiles`, `searches`, `jobs`, `cv`, `notifications` nei prossimi sprint), non un'unica app monolitica né un'app per modello.
- **Migrazioni:** sempre generate e **committate** nel repository (mai in `.gitignore`); `makemigrations --check` deve restituire nessuna differenza prima di chiudere uno sprint che tocca i modelli.
- **Config/segreti:** solo variabili d'ambiente (mai hardcoded), lette in `settings.py` con `os.environ.get(...)`; `.env.example` alla radice documenta le chiavi attese, `.env` reale mai committato.
- **Docker:** un'unica immagine (`backend/Dockerfile`) condivisa da `web`/`worker`/`beat`, differenziati solo dal comando lanciato in `docker-compose.yml`.
- **Stile Python:** niente docstring multi-riga salvo motivare un vincolo non ovvio (es. perché `AUTH_USER_MODEL` punta a un modello custom fin dal primo sprint); niente helper/astrazioni introdotte in anticipo su bisogni futuri.

## Cosa NON fare
- Non introdurre dipendenze/librerie non necessarie senza chiedere
- Non modificare l'architettura decisa nelle specifiche tecniche
  senza segnalarlo esplicitamente
- Non reintrodurre il download CV in Word (escluso dall'MVP — solo PDF)
- Non implementare cache offline o sincronizzazione dati sul dispositivo nella PWA ("apertura lista immediata" = reattività dell'API, non cache locale)
- Non introdurre filtri di ricerca oltre keywords e location
- Non aggiungere stati del job oltre ai tre stabili (nuovo, CV generato, candidatura fatta) più il transitorio (CV in generazione)
- Non far scalare due volte lo stesso massimale/credito per la stessa azione (vedi guardia di concorrenza sulla generazione CV, §5.2 tecniche)

## Workflow sprint
Il progetto è diviso in sprint, ognuno in un file sprint-NN.md nella
cartella /sprints. Ogni sprint va completato e verificato prima di
passare al successivo. A fine sprint, aggiornare il relativo file con
esito, problemi riscontrati, requisiti soddisfatti.
