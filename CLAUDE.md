# CLAUDE.md

## Progetto
App che centralizza e automatizza la ricerca di lavoro: raccoglie offerte da LinkedIn (una raccolta al giorno per utente: automatica all'orario scelto per i Pro, manuale "Raccogli" per tutti; Sprint 77) e ne valuta l'affinità con il profilo dell'utente (punteggio 1–10 + match/gap). I Pro ricevono una notifica a fine raccolta automatica se ci sono job nuovi e trovano la lista già pronta; su ogni offerta genera su richiesta CV personalizzato in PDF (con "colma i gap"), cover letter e messaggi di networking, li rifinisce con editor + chat AI e traccia la candidatura. Nessuna generazione automatica di CV (rimossa, Sprint 45).

Riferimenti (documenti vivi, sempre allineati all'as-is):
- `Docs/01-specifiche-funzionali-v6.md` — cosa fa l'app
- `Docs/02-specifiche-tecniche-v5.md` — come è costruita (modello dati, flussi, API, test)
- `Docs/03-specifiche-funzionali-contenuto-cv-v5.md` — regole di contenuto/impaginazione del CV (prevale su 01/02 per questi temi)
- `Docs/CHANGELOG.md` — storico versioni delle specifiche · `DEPLOY.md` — deploy e runbook · `sprints/` — storico sprint
- Le versioni precedenti delle specifiche sono in `Docs/archivio/` (solo storico, non usarle come riferimento). I commenti nel codice citano ancora `§` delle versioni v3/v4: la numerazione dei paragrafi esistenti è stata mantenuta nelle nuove versioni.

## Stack
- **Backend:** Python + Django (+ Django REST Framework per l'API interna consumata dalla PWA)
- **Task in background:** Celery + Redis (raccolte automatiche Pro raccolta+scoring, promemoria di inattività, backup). Le azioni su richiesta (generazione CV/cover letter/messaggi, chat degli editor, raccolta manuale "Raccogli ora") girano invece in modo **sincrono** nella richiesta HTTP (gunicorn `--timeout 1800`)
- **Scheduler:** Celery Beat con `DatabaseScheduler` (ogni 15 min: raccolte automatiche dei Pro all'orario scelto nel loro fuso e promemoria di inattività; backup 03:30 Europe/Rome). Nessun ciclo notturno né notifica delle 10:00 (rimossi nello Sprint 77). **Una raccolta al giorno per utente**, automatica o manuale (`COLLECTION_DAILY_LIMIT`, giorno Europe/Rome): ogni raccolta costa chiamate Apify
- **Frontend:** React come PWA (no pubblicazione store, no cache offline — solo reattività dell'API)
- **Database:** PostgreSQL
- **Fonte offerte:** Apify (actor `cheap_scraper~linkedin-job-scraper`), dietro un'interfaccia interna sostituibile — una chiamata per gruppo (tipo ricerca × location) per utente/raccolta, non per singola ricerca salvata (sprint-39); nessun tetto di piano sui job creati né cap di intake (rimossi, Sprint 45–46: ogni chiamata è già a pagamento indipendentemente dai risultati usati). Resta solo il limite per singola chiamata Apify (`MAX_ITEMS_PER_CALL=150`, minimo billing pay-per-result dell'actor). L'import di un singolo job da URL usa invece l'API guest di LinkedIn (sprint-24), senza Apify
- **Motore AI:** Claude via AWS Bedrock (SDK `anthropic`, client `AnthropicBedrock`, non l'API Anthropic diretta — passaggio 18/08/2026 per credito esaurito sulla chiave Anthropic) — scoring, generazione CV/cover letter/messaggi di networking, chat degli editor, parsing del CV caricato in onboarding. Modelli per uso configurati da env (`BEDROCK_SCORING_MODEL`, `BEDROCK_CV_GENERATION_MODEL`, `BEDROCK_CV_PARSING_MODEL`). Bedrock non supporta l'output strutturato nativo (`output_config.format`): l'helper condiviso `apps/common/ai.py` forza lo schema via tool-use (`tool_choice`), unico punto da toccare per tutte le chiamate AI
- **Generazione CV/cover letter:** template HTML/CSS → PDF (WeasyPrint, font Caladea compatibile Cambria installato nell'immagine). Solo PDF, nessuna pipeline Word. Editor in-app con bozza (`CVDraft`/`CoverLetterDraft`) e chat AI a proposta→conferma (Sprint 51–63)
- **Credito extra:** saldo in euro (`Decimal`) con listino prezzi unitari configurabile per azione
- **Autenticazione:** email/password (nativa Django) + login Google (django-allauth; implementato ma oggi non configurato in produzione)
- **Notifiche:** Web Push standard (es. libreria `pywebpush`), nessun servizio esterno a pagamento
- **Hosting:** VPS singolo economico (es. Hetzner)
- **Deploy:** Docker Compose (Django, PostgreSQL, Redis, worker Celery, Caddy) + Caddy come reverse proxy con HTTPS automatico
- **Amministrazione:** Django Admin per gestione piani e credito (nessun voucher implementato, nessun checkout self-service nell'MVP)

## Principi guida
- Semplicità e manutenibilità prima di tutto: no over-engineering
- Architettura monolitica, non introdurre microservizi/servizi extra
- Preferire soluzioni standard/documentate a quelle esotiche
- MVP per una cerchia ristretta di utenti di test: nessun requisito di scala da rispettare
- Il *cosa* è definito nelle specifiche funzionali, il *come* nelle specifiche tecniche: in caso di dubbio implementativo, verificare prima lì

## Convenzioni di codice
Proposte nello Sprint 01, in vigore da qui in avanti:

- **Struttura repo:** codice Django in `backend/`, PWA React in `frontend/`, deploy (`docker-compose*.yml`, `docker/`) alla radice, specifiche in `Docs/` (versioni superate in `Docs/archivio/`), schede sprint in `sprints/`.
- **Progetto Django:** cartella di settings/config si chiama `config` (non il nome dell'app), con `config/settings.py` unico (niente split `base/dev/prod`: la differenza dev/prod passa da variabili d'ambiente e da `docker-compose.yml` vs `docker-compose.prod.yml`, non da moduli di settings diversi — coerente con "no over-engineering").
- **App Django:** vivono in `backend/apps/<nome_app>/`, importate come `apps.<nome_app>` in `INSTALLED_APPS`. Un'app per dominio funzionale (`accounts`, `common`, `profiles`, `searches`, `jobs`, `cv`, `notifications`), non un'unica app monolitica né un'app per modello.
- **Migrazioni:** sempre generate e **committate** nel repository (mai in `.gitignore`); `makemigrations --check` deve restituire nessuna differenza prima di chiudere uno sprint che tocca i modelli.
- **Config/segreti:** solo variabili d'ambiente (mai hardcoded), lette in `settings.py` con `os.environ.get(...)`; `.env.example` alla radice documenta le chiavi attese, `.env` reale mai committato.
- **Docker:** un'unica immagine (`backend/Dockerfile`) condivisa da `web`/`worker`/`beat`, differenziati solo dal comando lanciato in `docker-compose.yml`.
- **Testi rivolti all'utente nel backend (Sprint 71):** ogni nuovo messaggio d'errore/validazione, testo di notifica o di email va scritto in italiano dentro `gettext` (`_("…")`, `gettext_lazy` per le costanti di modulo; segnaposto con nome `%(nome)s`, mai f-string) e tradotto in inglese in `backend/locale/en/LC_MESSAGES/django.po`, ricompilando e committando anche il `.mo` (comandi in `DEPLOY.md` §4.9; `apps/common/test_i18n.py` fallisce con voci vuote, `fuzzy` o `.mo` non aggiornato). Fuori da una richiesta (task Celery) usare `translation.override(user.interface_language)`. Non si traducono prompt AI, log, `RunLog` e Django Admin.
- **Stile Python:** niente docstring multi-riga salvo motivare un vincolo non ovvio (es. perché `AUTH_USER_MODEL` punta a un modello custom fin dal primo sprint); niente helper/astrazioni introdotte in anticipo su bisogni futuri.

## Deploy — non mescolare mai `docker-compose.yml` e `docker-compose.prod.yml`

Incidente reale (17/08/2026): sul VPS, `caddy` girava da `docker-compose.prod.yml`
(volumi Docker `static_data`/`media_data`/`frontend_dist`), mentre
`web`/`worker`/`beat`/`frontend` erano stati avviati da `docker-compose.yml`
(dev, bind-mount locale). I due stack non condividono lo storage: i CV
generati finivano nella cartella locale del bind-mount, invisibile a Caddy,
che serve `/media/*` e `/static/*` direttamente dai volumi Docker (vedi
`Caddyfile.prod`) — risultato: PDF generato ma introvabile, pagina bianca al
download, apparentemente casuale/legato al dispositivo ma in realtà
100% lato server.

Regola: su questo VPS pubblico (dominio con TLS reale) **tutti** i servizi
vanno avviati da un solo file compose — sempre `docker-compose.prod.yml`
(procedura in `DEPLOY.md`), mai un mix. Prima di ogni deploy o intervento sul
VPS, verificare la coerenza dello stack in esecuzione:

```
docker inspect <container> --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}'
```

Deve restituire lo stesso path (`.../docker-compose.prod.yml`) per **tutti**
i container del progetto. Se qualcuno avvia `docker-compose.yml` (dev) sul
VPS per debug rapido, va sempre riportato a `docker-compose.prod.yml` con
`build` + `up -d` prima di lasciare il server, non lasciato "per ora così".

## Sicurezza e privacy — regole fisse (Sprint 66–67)
- I file degli utenti (CV, cover letter, foto, export) **non si servono mai** da `/media/*` (Caddy risponde 404): solo da URL firmati a scadenza generati per il proprietario (`apps/common/files.py`). Ogni nuovo tipo di file segue lo stesso schema, con nome casuale su disco.
- Ogni nuova view eredita i permessi di default (login + accettazione legale): dichiarare `permission_classes` solo per gli endpoint che devono esserne esenti, motivandolo.
- Nuovi dati personali raccolti, nuovi fornitori che li ricevono o nuove conservazioni vanno riportati nell'informativa (`frontend/src/legal/`, copia in `Docs/legal/`) aumentandone la versione in `apps/accounts/legal.py` (gli utenti la riaccettano al prossimo accesso), e coperti da export e cancellazione account.
- Testi liberi che finiscono al modello AI o nei PDF hanno sempre un `max_length` lato server.

## Redesign UI (sprint 72–81)
Il redesign è documentato in `Docs/design/` (`README.md`, `DESIGN.md`, `SCREENS.md`, `SPEC-DELTA.md`, `IMPLEMENTATION-PLAN.md`; sprint da 72). Finché uno sprint non lo implementa, **le specifiche in `Docs/01…03` e il codice restano l'as-is**. Le decisioni sulla raccolta (SPEC-DELTA A4/A5, B1–B4) sono implementate nello Sprint 77 e descritte nelle specifiche: Free solo raccolta manuale 1/giorno; Pro raccolta automatica all'orario scelto (nel fuso dell'utente; la attiva l'utente, mai preimpostata — Sprint 81) che condivide la stessa quota giornaliera della manuale; nessun ciclo notturno per nessuno. Le voci ancora **da decidere** sono in `SPEC-DELTA.md §B`: in caso di dubbio chiedere, non assumere.
- Il template PDF del CV è fuori dal redesign; nessun font o risorsa da servizi esterni.

## Cosa NON fare
- Non introdurre dipendenze/librerie non necessarie senza chiedere
- Non modificare l'architettura decisa nelle specifiche tecniche
  senza segnalarlo esplicitamente
- Non reintrodurre il download CV in Word (escluso dall'MVP — solo PDF)
- Non implementare cache offline o sincronizzazione dati sul dispositivo nella PWA ("apertura lista immediata" = reattività dell'API, non cache locale)
- Non introdurre filtri di ricerca oltre keywords, location e tipo ricerca
  (Job role keyword / Company — introdotto sprint-39, unica deviazione
  esplicita accettata da questo vincolo, per poter usare `companyInclude`
  lato Apify sulle ricerche Company: vedi `sprints/sprint-39.md`)
- Non aggiungere stati del job oltre ai tre stabili (nuovo, CV generato, candidatura fatta) più il transitorio (CV in generazione)
- Non far scalare due volte lo stesso massimale/credito per la stessa azione (vedi guardia di concorrenza sulla generazione CV, §5.2 tecniche)

## Workflow sprint
Il progetto è diviso in sprint, ognuno in un file sprint-NN.md nella
cartella /sprints. Ogni sprint va completato e verificato prima di
passare al successivo. A fine sprint, aggiornare il relativo file con
esito, problemi riscontrati, requisiti soddisfatti.

**Documentazione as-is obbligatoria a ogni sprint** (regola introdotta il
2026-11-14 dopo che gli sprint 40–64 erano stati rilasciati senza
documentazione e ricostruiti a posteriori):
1. Prima di scegliere il numero, guardare sia `git log --oneline` sia
   `ls sprints/`: il numero è il successivo al massimo dei due, e lo
   stesso numero va usato nel commit, nei commenti del codice e nel file
   (in passato le tre numerazioni sono divergite — vedi `sprints/sprint-44.md`).
2. Creare/aggiornare `sprints/sprint-NN.md` (richiesta, decisioni prese col
   committente, implementazione, verifica, cosa manca).
3. Aggiornare **nello stesso commit** le specifiche in `Docs/` toccate dalla
   modifica (01 funzionali, 02 tecniche — modello dati, flussi, tabella API
   §12, test §13 —, 03 contenuto CV), così che descrivano sempre l'as-is;
   aggiornare la riga corrispondente in `Docs/CHANGELOG.md`. Se cambiano
   deploy, variabili d'ambiente o procedure operative: `DEPLOY.md` e
   `.env.example`.
4. Interventi operativi fatti a mano sul VPS (dati, `.env`, container) che
   cambiano il comportamento dell'app vanno annotati nel runbook di
   `DEPLOY.md` §7 in forma generica (mai email, nomi utente, token: il
   repository GitHub è pubblico).
5. Test backend nel container di produzione: sempre con
   `-e DJANGO_DEBUG=true` (vedi `DEPLOY.md` §4.4), altrimenti ~60 test
   falliscono per il redirect HTTPS senza che ci sia una regressione; e con
   `-e REGISTRATION_INVITE_CODE=` (il codice di invito reale del `.env` fa
   fallire i test di registrazione).
