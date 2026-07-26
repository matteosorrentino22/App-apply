# Specifiche Tecniche — App di ricerca lavoro e generazione CV

> **Documento:** 02 — Specifiche tecniche
> **Versione:** 3 — integra le decisioni della chat di revisione criticità (luglio 2026)
> **Stato:** revisionato
> **Ambito:** definisce *come* è costruita l'applicazione (architettura, stack, modello dati, deploy, sicurezza). Il *cosa* resta definito nel documento `01-specifiche-funzionali-v4.md`, con cui questo documento è coerente.
>
> **Vincoli guida adottati** (dichiarati dal committente):
> 1. Semplicità prima di tutto: soluzione **monolitica**, non microservizi.
> 2. Manutenibile da **una persona / piccolo team**.
> 3. Tecnologie **mature, ben documentate, ampia community**; niente scelte esotiche o sperimentali.
> 4. Copertura: backend, frontend, database, hosting/deploy, autenticazione.
> 5. MVP per una **cerchia ristretta di utenti di test**: nessun requisito di scala.
>
> **Nota di versione (v2).** Recepiva: batch di raccolta globale alle 02:00 Europe/Rome; credito come pool unico; riserva dei contatori all'accodamento con restituzione su fallimento; reset quote a mezzanotte UTC; campi per il timer di inattività; foto on/off; pipeline di parsing del CV caricato.
>
> **Nota di versione (v3).** Questa revisione recepisce le decisioni della chat di revisione criticità:
> 1. **Credito come saldo in denaro.** `User.extra_credit` diventa un **importo in euro** (campo decimale). Ogni azione oltre massimale ha un **prezzo unitario configurabile** (parametri applicativi, valori da definire) scalato dal saldo. Il fallimento restituisce anche l'eventuale importo scalato, non solo lo slot di contatore (§4.1, §4.6, §5.2).
> 2. **Word eliminato dall'MVP.** Il CV generato esce **solo in PDF** (HTML → WeasyPrint). Sparisce la pipeline python-docx di *generazione*; `python-docx` resta in stack solo per la *lettura* dei CV caricati in onboarding (§3.6, §4.5, §6).
> 3. **Raccolta come chiamata unica per utente con limite 50/100.** Per ogni utente, la raccolta notturna è **una sola chiamata Apify** che include tutte le ricerche attive come filtri, con un limite massimo di job restituiti: **50 (Free) / 100 (Pro)** per utente per notte. La finestra "24h a ritroso" è un parametro della chiamata. **Assunzione da validare**: che l'actor supporti più coppie keywords/location in una singola chiamata (§5.1, §11).
> 4. **Reset delle quote a mezzanotte Europe/Rome.** Allineato al fuso del batch: i riferimenti temporali dell'app scendono da tre a **due** (Europe/Rome per batch e quote; fuso locale dell'utente per notifiche e "oggi") (§4.6, §7).
> 5. **`published_at` tollerata come assente.** Il job senza data è ammesso; il tie-break del cap dei 15 degrada a scelta **casuale** quando la data manca o il pareggio persiste (§5.1).
> 6. **Notifica mattutina basata su `User.last_notified_at`.** "Nuovi job" = job con `date_collected` successiva all'ultima notifica mattutina inviata. Anti doppio-invio e corretta gestione dei fusi a est (§4.1, §5.5).
> 7. **Guardia di concorrenza sulla generazione.** Pulsante disabilitato lato PWA + rifiuto lato server di richieste duplicate sullo stesso job in lavorazione (§5.2).
> 8. **Fallimento dello scoring nel batch:** offerta scartata per quella notte, traccia nel `RunLog` (§5.1).
> 9. **"Apertura lista immediata" = reattività dell'API**, nessuna cache offline nella PWA (§3.3).

---

## 1. Sintesi delle decisioni

Questa tabella riassume le scelte prese; il resto del documento le motiva e le dettaglia.

| Area | Scelta | In una frase |
|---|---|---|
| Architettura | Monolite modulare | Un'unica applicazione, non tanti servizi separati. |
| Backend | Python + Django | Framework "tutto incluso", maturo, poco codice da mantenere. |
| Task in background | Celery + Redis | Esegue raccolta notturna, scoring e CV senza bloccare l'utente. |
| Frontend | React, come PWA | Web app installabile sul telefono, adatta a swipe e liste. Nessuna cache offline. |
| Database | PostgreSQL | Database relazionale standard, gratuito, affidabile. |
| Fonte offerte | Apify (LinkedIn), dietro interfaccia interna | Una chiamata per utente/notte, limite 50/100 job, componente sostituibile. |
| Motore AI | API Anthropic (Claude) | Scoring, match/gap, generazione CV, parsing del CV caricato. |
| Generazione CV | Template **HTML → PDF** (WeasyPrint) | Solo PDF nell'MVP; il Word è evoluzione futura. |
| Credito | Saldo in € + listino prezzi unitari configurabile | Azioni oltre massimale scalano un prezzo dal saldo. |
| Autenticazione | Email/password **+** login Google | Registrazione classica e accesso rapido con Google. |
| Notifiche | Web Push standard | Notifica mattutina e di inattività, senza servizi esterni a pagamento. |
| Hosting | VPS economico (es. Hetzner) | Un server singolo, gestito con Docker. |
| Deploy | Docker Compose + Caddy | Installazione riproducibile, HTTPS automatico. |
| Amministrazione | Django Admin | Pannello già pronto per gestire piani e credito (in €), più sicuro del DB a mano. |

Le scelte derivano in parte dal **prototipo n8n esistente** del committente (workflow *01 Job Collection*, *02 Job Scoring*, *03 CV Generation*), da cui sono stati recuperati l'actor Apify, i prompt e il layout del CV. Il prototipo usava Google Sheets come database e Google Drive per i documenti: entrambi vengono **sostituiti** nella app vera (PostgreSQL e generazione PDF sul server), per i motivi spiegati in §10.

---

## 2. Architettura generale

### 2.1 Il principio: un monolite, tre "motori" di lavoro

L'applicazione è un **unico programma** (monolite) che espone:

- un'**interfaccia web** (la PWA che l'utente usa dal telefono);
- un'**API interna** che la PWA interroga (login, lista job, generazione CV su richiesta, ecc.);
- alcuni **lavori in background** che girano da soli (raccolta notturna, scoring, generazione automatica dei CV, notifiche).

Il motivo della scelta monolitica è diretto: con pochi utenti e un piccolo team, spezzare l'app in tanti servizi separati (microservizi) aggiungerebbe solo complessità di rete, deploy e debugging, senza alcun vantaggio reale. Un monolite ben organizzato in moduli interni è più facile da capire, testare e mettere online.

### 2.2 I tre pilastri a runtime

Anche se è un unico progetto, a runtime girano tre processi complementari:

1. **Web server (Django)** — risponde alle richieste della PWA in tempo reale (aprire la lista, generare un CV su richiesta, archiviare un job, ecc.).
2. **Worker (Celery)** — esegue i compiti lenti o programmati senza far aspettare l'utente: la raccolta notturna, lo scoring, la generazione dei CV, l'invio delle notifiche. Quando l'utente preme "genera CV" e le specifiche prevedono 10–15 secondi di attesa (§6 del doc funzionale), è il worker a lavorare mentre la PWA mostra l'indicatore "CV in generazione".
3. **Scheduler (Celery Beat)** — è la "sveglia" che fa partire i compiti a orari prestabiliti (la raccolta notturna, il controllo delle notifiche delle 10:00, il promemoria di inattività).

Tutti e tre condividono lo stesso codice e lo stesso database. Redis fa da "lavagna condivisa" tra web server e worker (coda dei compiti).

### 2.3 Schema a blocchi

```
        ┌──────────────────────────────────────────────┐
        │              UTENTE (smartphone)             │
        │        PWA React installata sulla home        │
        └───────────────────────┬──────────────────────┘
                                 │ HTTPS
                                 ▼
              ┌──────────────────────────────────┐
              │      Caddy (reverse proxy)        │  ← HTTPS automatico
              └───────────────┬──────────────────┘
                              ▼
        ┌─────────────────────────────────────────────┐
        │            MONOLITE (Django)                │
        │  • API interna (REST)                        │
        │  • Autenticazione (email/pw + Google)        │
        │  • Django Admin (gestione piani/credito)     │
        └───────┬───────────────────────────┬─────────┘
                │                           │
                ▼                           ▼
      ┌───────────────────┐        ┌────────────────────┐
      │   PostgreSQL      │        │   Redis (coda)     │
      │ (dati applicativi)│        └─────────┬──────────┘
      └───────────────────┘                  ▼
                              ┌───────────────────────────────┐
                              │  Celery Worker + Beat         │
                              │  • raccolta notturna          │
                              │  • scoring                    │
                              │  • generazione CV             │
                              │  • notifiche                  │
                              └───────┬───────────┬───────────┘
                                      ▼           ▼
                            ┌──────────────┐  ┌──────────────┐
                            │ Apify        │  │ Anthropic    │
                            │ (LinkedIn)   │  │ (Claude API) │
                            └──────────────┘  └──────────────┘
```

Tutti i componenti (Django, Postgres, Redis, worker, Caddy) girano sullo **stesso VPS** come container Docker orchestrati da Docker Compose (§8).

---

## 3. Stack tecnologico in dettaglio

### 3.1 Backend — Python + Django

**Scelta: Django.** È un framework web Python maturo, con vent'anni di storia, enorme community e documentazione eccellente. È "batterie incluse": porta con sé, già pronti e collaudati, i pezzi che altrimenti andrebbero costruiti e mantenuti a mano — sistema utenti e autenticazione, gestione del database senza scrivere SQL (ORM), migrazioni dello schema, protezioni di sicurezza (CSRF, SQL injection, XSS), e un **pannello di amministrazione** automatico.

Per l'API interna consumata dalla PWA si usa **Django REST Framework**, lo standard de facto per esporre API con Django.

Perché Django e non alternative:
- rispetto a scrivere tutto a mano (es. con micro-framework come Flask/FastAPI), Django fa risparmiare moltissimo codice proprio sulle parti noiose e critiche (utenti, permessi, admin), che è esattamente ciò che un piccolo team non vuole mantenere;
- il linguaggio Python è lo stesso del prototipo n8n (nodi "Code" in JavaScript a parte) e delle librerie AI/PDF che useremo, quindi tutto lo stack resta in un unico ecosistema.

### 3.2 Task in background — Celery + Redis

I compiti lenti o programmati non possono girare "dentro" la richiesta web dell'utente, altrimenti bloccherebbero l'interfaccia. **Celery** è la libreria standard nell'ecosistema Django per eseguire compiti in background e programmati; **Redis** fa da coda (la lista dei compiti da svolgere) e da memoria veloce condivisa.

Questo copre esattamente i flussi asincroni delle specifiche: la raccolta notturna, lo scoring, la generazione automatica dei CV (4–5), la generazione manuale su richiesta (i 10–15 secondi di attesa con indicatore di caricamento), e l'invio delle notifiche.

### 3.3 Frontend — React come PWA

**Scelta: React, distribuito come PWA** (Progressive Web App). È una web app normale che però l'utente può "installare" sulla schermata home del telefono e usare come un'app, con notifiche push. Niente pubblicazione sugli store Apple/Google (costi, tempi di revisione, account developer), aggiornamenti immediati per tutti.

React è la libreria frontend più diffusa, con la community più grande: trovare esempi, componenti pronti (es. per le liste con **swipe**) e persone che la conoscono è semplice. Si adatta bene a un'interfaccia fatta di liste reattive, filtri e gesti, che è il cuore di questa app.

**Nessuna cache offline.** Il requisito funzionale "apertura lista senza attesa percepibile" (§6 funzionale) è stato chiarito come **reattività**: la PWA interroga l'API a ogni apertura e l'API deve rispondere rapidamente (query semplici e indicizzate su pochi dati per utente — largamente sufficiente per l'MVP). **Non** si implementa una cache/sincronizzazione offline dei dati (service worker limitato al minimo richiesto per l'installabilità e le push): un sottosistema di sync sarebbe la parte più complessa del frontend, con benefici nulli per una cerchia di test. Recepito anche lato funzionale (§5.20 funzionale).

**Nota sui limiti PWA su iPhone.** Le notifiche push via web funzionano su iOS **solo** se l'utente ha aggiunto la PWA alla schermata home. È un limite noto della piattaforma Apple, non del nostro codice: va comunicato all'utente in onboarding con una breve istruzione ("aggiungi alla home per ricevere le notifiche"). Su Android non ci sono questi vincoli.

### 3.4 Database — PostgreSQL

**Scelta: PostgreSQL.** È il database relazionale open source più solido e diffuso, gratuito, con supporto nativo e ottimo in Django. I dati dell'app (utenti, profili, ricerche, job, CV, contatori, saldi) sono chiaramente relazionali e strutturati: un database relazionale è la scelta naturale, non serve nulla di più esotico.

Sostituisce integralmente i Google Sheets del prototipo (`JOB_TRACKER`, `SEARCH_CONFIG`, `MASTER_CV`, `RUN_LOG`), che erano adatti a un uso personale ma non a un'app multi-utente (vedi §10).

### 3.5 Motore AI — API Anthropic (Claude)

Tutte le operazioni "intelligenti" passano dall'**API di Anthropic (Claude)**, chiamata dal worker:

- **scoring** di ogni offerta (punteggio 1–5 + match/gap), riusando il prompt del prototipo;
- **generazione del CV** (contenuti su misura), riusando e ripulendo il prompt del prototipo;
- **parsing del CV caricato** in onboarding per pre-popolare il profilo (§4.1 funzionale).

**Parsing del CV caricato — pipeline in due passi.** Il CV di partenza si accetta in **PDF e Word (.docx)**. L'estrazione avviene **lato server**, non delegando a Claude il file grezzo:
1. **Estrazione del testo** con librerie Python mature — es. `pdfplumber`/`pypdf` per i PDF, `python-docx` per i .docx (unico uso di python-docx rimasto in stack: la generazione Word è fuori MVP — §3.6). Si ottiene il testo grezzo del CV.
2. **Strutturazione con Claude:** al modello si passa **solo il testo** estratto, che lo riorganizza nelle sezioni del profilo master (sommario, esperienze, istruzione, ecc.).

Questo approccio costa meno (non si inviano a Claude i byte del documento) e uniforma i due formati a un unico percorso testuale. **Fallback:** se l'estrazione restituisce testo **vuoto o irrisorio** — caso tipico dei **PDF scannerizzati / immagine**, per cui servirebbe l'OCR, escluso nell'MVP per costo/semplicità — non si chiama Claude con una stringa vuota: si mostra all'utente un messaggio del tipo *"non siamo riusciti a leggere il CV, compila il profilo manualmente"* (vedi §5.4 e §11).

Il prototipo, nonostante le descrizioni citassero "Claude", nei fatti chiamava modelli OpenAI (`gpt-4o-mini` per lo scoring, `gpt-4.1` per il CV). Nella app si adotta Claude in modo uniforme, come richiesto. La scelta del modello preciso (una famiglia più economica per lo scoring ad alto volume, una più capace per il CV) è un parametro di configurazione, non un vincolo architetturale.

### 3.6 Generazione del documento CV — HTML → PDF (solo PDF)

Trattata a fondo in §6. In sintesi:

- il CV si progetta come una **pagina HTML/CSS** (un template flessibile che ripete i blocchi "esperienza" quante volte servono);
- il **PDF** — **unico formato di output nell'MVP** — si ottiene convertendo l'HTML con **WeasyPrint**, una libreria Python matura pensata proprio per HTML/CSS → PDF, con buon controllo dell'impaginazione a 1 pagina.

**Il download in Word è fuori dall'MVP** (decisione della revisione criticità, recepita nelle funzionali v4 §5.19). La semplificazione è significativa: sparisce la seconda pipeline di rendering (python-docx per la generazione), sparisce il problema di fedeltà visiva PDF↔Word, e la garanzia "1 pagina" va assicurata su un solo motore, controllabile lato server. L'HTML salvato come sorgente di verità (§4.5) rende comunque possibile aggiungere in futuro un esportatore Word senza toccare la generazione dei contenuti.

Si abbandona l'approccio del prototipo (Google Doc con "trova e sostituisci" dei placeholder `{{...}}`), incompatibile con un template a numero di esperienze variabile.

### 3.7 Autenticazione — email/password + Google

Due modalità di accesso:
- **email + password**, gestita dal sistema utenti nativo di Django;
- **login con Google** (OAuth), tramite la libreria matura **django-allauth**, che integra entrambe le modalità in modo standard e collaudato.

Non si costruisce nulla di custom sulla sicurezza dell'autenticazione: si usano componenti standard e ben mantenuti. Le password sono salvate solo come hash (mai in chiaro), comportamento predefinito di Django.

### 3.8 Notifiche — Web Push

Le due notifiche previste (mattutina alle 10:00 locali; inattività dopo 7 giorni) si inviano con lo **standard Web Push**, gratuito e supportato dai browser, tramite una libreria Python dedicata (es. `pywebpush`). Non serve un servizio di notifiche a pagamento. Lo scheduler (Celery Beat) controlla a intervalli chi deve ricevere cosa, rispettando il **fuso orario di ciascun utente** (§5.5, §7).

---

## 4. Modello dati

Descrizione delle principali "tabelle" (in Django: *modelli*). I nomi sono indicativi; i tipi sono espressi in modo semplice. Questa sezione traduce in dati le entità del documento funzionale.

### 4.1 `User` (utente)
Gestito dal sistema nativo di Django, esteso con i campi che ci servono.
- `id`
- `email`, `password_hash` (o account Google collegato)
- `plan` — piano attuale: `free` | `pro`
- `timezone` — fuso orario dell'utente (es. `Europe/Rome`), per notifiche e "oggi" (§7)
- `interface_language` — `it` | `en` (default dalla lingua del dispositivo)
- `cv_language_mode` — `english` | `job_language` (scelta in onboarding, §4.7 funzionale)
- `cv_include_photo` — vero/falso (opzione foto on/off; scelta in onboarding e modificabile — §4.1 funzionale)
- `objective_statement` — la dichiarazione di situazione/obiettivo raccolta in onboarding (dato **inerte** nell'MVP, §5.6 funzionale)
- `created_at` — usato anche come valore iniziale del timer di inattività (§4.12 funzionale)
- `last_activity_reset` — timestamp da cui si conta l'inattività: inizializzato a `created_at`, **aggiornato a ogni marcatura "candidatura fatta"**. Denormalizzato apposta perché lo scheduler, che gira di frequente su tutti gli utenti, possa controllare i 7 giorni con una lettura diretta (O(1)) senza aggregare i job dell'utente a ogni giro (§4.12 funzionale)
- `last_notified_at` — timestamp dell'**ultima notifica mattutina inviata** (inizializzato a `created_at`). Definisce cosa è "nuovo" per la notifica delle 10:00: esistono job con `date_collected > last_notified_at` → si notifica e si aggiorna il timestamp (§5.5). Garantisce che ogni batch sia annunciato una sola volta e fa da guardia anti doppio-invio per lo scheduler a intervalli
- `extra_credit` — **saldo in euro** (campo decimale, es. `Decimal`, mai float per il denaro), caricato manualmente via Django Admin. Le azioni oltre massimale scalano dal saldo il **prezzo unitario** del tipo di azione (§4.6)

### 4.2 `Profile` (profilo master) e sezioni
Il profilo master è strutturato in sezioni (§4.1 funzionale). Si modella come un profilo principale con tabelle collegate per gli elementi ripetibili:
- `Profile` — `user`, `summary` (sommario professionale), `photo` (immagine), `key_achievements` (risultati chiave)
- `Experience` — `profile`, `company`, `role`, `location`, `start_date`, `end_date`, `bullets` (elenco di punti), `technologies` — **una riga per ogni esperienza** (numero variabile: è ciò che rende il CV dinamico)
- `Education` — `profile`, `institution`, `title`, `location`, `dates`, `notes` — **sezione mai riscritta dall'AI** (§4.7 funzionale: "istruzione invariata")
- `Skill` / `Certification` — voci di competenze e certificazioni
- `Language` — `profile`, `language`, `level`

Questa struttura sostituisce il campo unico `cv_text` che nel prototipo stava in un Google Sheet: lì era un blob di testo modellato su una sola persona; qui diventa dati strutturati e per-utente.

### 4.3 `SavedSearch` (ricerca salvata)
- `user`, `name`, `keywords`, `location`, `is_active` (attiva/disattiva)
- Vincoli di piano applicati dalla logica: Free ≤10 salvate / 1 attiva; Pro ≤100 salvate / ≤50 attive (§4.2 funzionale)

### 4.4 `Job` (offerta)
Il cuore del sistema. Un record per ogni offerta raccolta o importata, **per utente** (isolamento dati, §6 funzionale).
- `user`, `source` (es. `linkedin`), `external_id` (l'ID LinkedIn, per la deduplica)
- Campi dall'annuncio: `title`, `company`, `location`, `description`, `apply_url`, `published_at` (**nullable**: la data può mancare — §5.1), campi opzionali (retribuzione, ecc.)
- `origin` — `collected` (raccolto) | `imported` (importato) — determina la **sezione** insieme all'archiviazione
- `is_archived` — vero/falso — attributo ortogonale allo stato (§4.6 funzionale)
- `status` — `new` | `cv_generated` | `application_done` (i tre stati stabili). Lo stato transitorio "CV in generazione" **non** è un valore qui, ma un flag separato `cv_generation_in_progress`, che funge anche da **guardia di concorrenza**: una richiesta di generazione su un job con il flag attivo viene rifiutata (§5.2)
- `score` — 1–5
- `score_match` / `score_gaps` — le due liste di punti affinità/lacune
- `score_reasoning` — breve motivazione
- date di servizio: `date_collected`, `date_scored`, `date_cv_generated`, `date_application_done` (istante in cui il job è stato marcato "candidatura fatta"; valorizzato solo dopo la marcatura). È il dato di verità del singolo evento; il reset del timer di inattività a livello utente è tenuto in `User.last_activity_reset` (§4.1)

**Deduplica** (§4.3 funzionale): vincolo di unicità su (`user`, `source`, `external_id`), così lo stesso job non compare due volte allo stesso utente anche se restituito da più ricerche.

### 4.5 `CVDocument` (CV generato)
- `job`, `user`
- `html_source` — l'HTML generato (sorgente di verità del documento; rende possibile un futuro esportatore Word senza rigenerare i contenuti)
- `pdf_file` — il PDF prodotto (unico formato di download nell'MVP)
- `generated_at`, `generation_type` (`automatic` | `manual`)
- `enrichment_used` — eventuale dettaglio di arricchimento usato solo per questo CV (§4.8 funzionale)

I CV già prodotti **non** cambiano se il profilo master viene modificato dopo (§4.1 e §5.14 funzionale): il documento è congelato, salvo rigenerazione manuale.

### 4.6 `DailyQuota` (contatori giornalieri) e listino prezzi

Traduce i **due massimali separati e indipendenti** (§4.11 funzionale). Un record per (`user`, `date`), con **`date` riferita al giorno Europe/Rome**:
- `manual_cv_count` — generazioni manuali di CV usate oggi (Free max 1, Pro max 10)
- `import_count` — import manuali usati oggi (Pro max 3)

I due contatori sono **distinti**: sono due pool separati, come richiesto. La generazione **automatica** non ha un contatore proprio (è limitata di fatto dal cap di intake di 15 job/giorno, §4.4 funzionale).

**Reset a mezzanotte Europe/Rome.** Il "giorno" della quota è quello del fuso **Europe/Rome**, lo stesso riferimento del batch notturno (§5.1): i contatori si azzerano a mezzanotte Europe/Rome (in pratica: il record `DailyQuota` di un nuovo giorno parte da zero). Rispetto alla v2 (mezzanotte UTC) sparisce un terzo riferimento temporale: l'app usa ora **due orologi** — Europe/Rome per batch e quote, fuso locale dell'utente per notifiche e "oggi" di visualizzazione (§7). Per gli utenti europei quota e giorno locale coincidono di fatto; per fusi lontani resta lo scarto già accettato (§11).

**Credito: listino prezzi unitari.** Quando un contatore ha raggiunto il massimale del piano, l'azione può proseguire scalando da `User.extra_credit` il **prezzo unitario** del tipo di azione. I prezzi (es. `PRICE_MANUAL_CV_EXTRA`, `PRICE_IMPORT_EXTRA`) sono **parametri di configurazione applicativa** (valori da definire — §11), modificabili senza toccare il codice della logica. Un'azione oltre massimale con saldo **insufficiente** viene rifiutata con il messaggio di limite raggiunto. **L'import resta riservato al Pro** a prescindere dal credito (§4.9 funzionale): il controllo di piano precede quello di quota/credito.

**Riserva all'accodamento (anti doppia-spesa).** Il contatore pertinente viene **incrementato — o l'importo a credito scalato — al momento in cui il task viene messo in coda**, non a fine lavorazione. Serve a evitare che due richieste ravvicinate superino entrambe il controllo prima che il contatore si aggiorni (rischio concreto sul Free a 1/giorno, dati i 10–15 secondi di generazione). In caso di **fallimento** della generazione, si **restituisce ciò che era stato riservato**: decremento del contatore **oppure riaccredito dell'importo scalato**, a seconda di come l'azione era stata pagata (per questo il record dell'operazione tiene traccia della modalità di addebito). Coerente con "il fallimento non consuma budget" (§4.7 funzionale). La stessa logica vale per `import_count` (§5.2).
> **Nota implementativa.** Controllo e riserva vanno eseguiti in modo **atomico** a livello DB (transazione con `select_for_update` sul record di quota/utente, o aggiornamenti con espressioni `F()` condizionate), altrimenti la race condition che la riserva vuole prevenire si ripresenta tra check e incremento.

### 4.7 `RunLog` (diario delle esecuzioni)
Registro tecnico di ogni esecuzione dei task notturni (raccolta, scoring, generazione), erede del foglio `RUN_LOG` del prototipo: utile per capire cosa è successo una certa notte, per diagnosi lato backend. Registra anche le **offerte scartate per fallimento di scoring** (§5.1). Non visibile all'utente.

### 4.8 `PushSubscription` (iscrizione alle notifiche)
Dati tecnici necessari a inviare le notifiche Web Push al dispositivo dell'utente.

---

## 5. I flussi principali, tradotti in tecnica

### 5.1 Ciclo notturno (raccolta → scoring → cap → CV automatici)

Ripercorre i tre workflow del prototipo, ma dentro il monolite e per **ogni** utente:

1. **Raccolta** (Celery Beat la fa partire di notte). Il batch è **globale e unico per tutti gli utenti**, schedulato alle **02:00 Europe/Rome**. Non è una raccolta per-fuso: tutti gli utenti vengono processati nella stessa esecuzione. Per ogni utente si effettua **una sola chiamata Apify** (attraverso l'interfaccia interna "fonte offerte", §5.3) che include **tutte le ricerche attive** dell'utente come filtri, con due parametri chiave:
   - **finestra temporale:** offerte pubblicate nelle **24 ore precedenti** (pre-filtro dell'actor, non calcolato da noi);
   - **limite di risultati:** massimo **50 job (Free) / 100 job (Pro)** per utente per notte, complessivi su tutte le ricerche.
   Le offerte tornano, vengono **deduplicate** per `external_id` (già mostrate → scartate) e filtrate: un'offerta senza uno dei campi obbligatori (title, company, location, description, apply_url) **non** viene salvata (§4.3 funzionale). La **data di pubblicazione può mancare**: l'offerta è comunque ammessa, con `published_at` nullo.
   > **Assunzione da validare (§11).** Si assume che l'actor supporti **più coppie keywords/location in una singola chiamata**. Se in fase di implementazione risultasse non supportato, il fallback è una chiamata per ricerca con il tetto complessivo 50/100 applicato dalla nostra logica dopo l'aggregazione — senza alcun effetto visibile all'utente.
   > **Nota (freschezza per fusi non europei).** Con un unico batch alle 02:00 Europe/Rome, gli utenti europei ricevono job appena raccolti prima delle loro 10:00 locali; un utente in un fuso lontano vede alla propria notifica delle 10:00 job raccolti diverse ore prima nel suo tempo locale. Effetto atteso, accettato per l'MVP (cerchia di test perlopiù europea) e registrato lato funzionale (§8.19) e in §11. Da tenere presente anche il piccolo scostamento DST di Europe/Rome (§11).
2. **Scoring.** Ogni offerta raccolta (entro il limite 50/100) viene valutata da Claude (1–5 + match/gap). Se lo scoring di una singola offerta **fallisce** (timeout, errore API), l'offerta viene **scartata per quella notte**: non entra nel passo successivo, non viene ritentata; l'evento è registrato nel `RunLog`. Nessun messaggio d'errore all'utente (coerente con §6 funzionale).
3. **Cap di intake.** Tra le offerte scorate si tengono le **15 a punteggio più alto**. In caso di pareggio al confine: si preferisce la **più recente** per `published_at`; se la data manca o il pareggio persiste, la scelta tra i pari merito è **casuale** (§4.4 funzionale). Le eccedenti sono scartate e non riproposte. *(Lo scoring avviene su tutto ciò che passa il limite 50/100 — al massimo 100 valutazioni per utente Pro a notte; costo Claude contenuto dal limite stesso, vedi §11.)*
4. **CV automatici.** Per i job 4–5 tenuti, il worker genera subito il CV (§6). Vale per **tutti i piani**, Free incluso (§4.7 funzionale). I job nascono `new` (1–3) o `cv_generated` (4–5).
5. **Notifica.** Alle 10:00 **locali** dell'utente, se ci sono job nuovi rispetto all'ultima notifica, parte la notifica (§5.5, §7).

### 5.2 Generazione manuale su richiesta (con attesa 10–15 s)

Quando l'utente preme "genera CV" (o "rigenera", o "riprova" dopo un fallimento automatico):

1. **Guardia di concorrenza.** Lato PWA, il pulsante "genera" del job si disabilita immediatamente e mostra l'indicatore di caricamento. Lato server, se il job ha già `cv_generation_in_progress` attivo, la richiesta viene **rifiutata** (nessun consumo): la doppia protezione ("cintura e bretelle") costa una riga e chiude ogni spiraglio di doppio addebito sullo stesso job.
2. **Controllo di quota e addebito.** Il web server verifica il **contatore manuale** del giorno (Free 1, Pro 10). Se il massimale è raggiunto, verifica il **saldo** `extra_credit`: se copre il prezzo unitario `PRICE_MANUAL_CV_EXTRA`, l'azione prosegue a credito; altrimenti risponde con il messaggio di limite raggiunto (blocco netto).
3. **Riserva all'accodamento.** Se ammesso, il sistema **riserva subito** (incremento atomico del contatore, oppure scalo dell'importo dal saldo — registrando la modalità di addebito), attiva `cv_generation_in_progress`, mette in coda il task; l'utente può continuare a usare l'app.
4. Il worker genera il CV (§6). Al termine, il job passa a `cv_generated`, il flag di lavorazione si spegne e la PWA aggiorna la riga.
5. Se il job era in **Archivio**, esce automaticamente e torna alla sezione d'origine (§4.5 funzionale).
6. In caso di **fallimento**: messaggio "impossibile creare CV per questo job", il job torna a `new`, il flag si spegne, compare "riprova", e **si restituisce ciò che era stato riservato** — decremento del contatore o **riaccredito dell'importo** sul saldo, secondo la modalità di addebito registrata al punto 3. Così **il fallimento non consuma budget** in nessuna delle due modalità (§4.7 funzionale). Il "riprova" su un fallimento **automatico** conta come generazione **manuale** (passa dai punti 1–3 come qualsiasi altra).

La stessa struttura (guardia → quota/credito → riserva → esecuzione → conferma o restituzione) vale per l'**import manuale** (contatore `import_count`, prezzo `PRICE_IMPORT_EXTRA`, con il vincolo aggiuntivo che il piano deve essere Pro).

### 5.3 La "fonte offerte" come componente sostituibile

Le specifiche (§4.3) chiedono che LinkedIn/Apify sia **sostituibile** in futuro. Tecnicamente si realizza con un **modulo interno con un'interfaccia unica** ("dammi le offerte per queste ricerche, entro questa finestra, fino a questo limite"): oggi dietro c'è Apify, domani potrà esserci un'altra fonte, senza toccare raccolta, scoring o CV. L'actor usato è `cheap_scraper~linkedin-job-scraper` in modalità `run-sync-get-dataset-items`; il token Apify va in configurazione sicura (variabile d'ambiente), **non** cablato nell'URL come nel prototipo.

> **Nota di conformità.** Lo scraping di LinkedIn tramite terze parti può violare i termini di servizio di LinkedIn. È una scelta consapevole del committente per l'MVP; resta un rischio da tenere presente (§11).

### 5.4 Pre-popolamento del profilo da CV caricato (onboarding)

Realizza il pre-popolamento previsto dalle funzionali (§4.1). Formati accettati: **PDF e Word (.docx)**.

1. **Upload e estrazione testo (lato server).** Il file viene salvato temporaneamente ed elaborato con una libreria di estrazione (`pdfplumber`/`pypdf` per PDF, `python-docx` per .docx). Si ottiene il **testo grezzo**; il file binario **non** viene inviato a Claude (§3.5).
2. **Controllo di consistenza.** Se il testo estratto è **vuoto o irrisorio** (tipico dei PDF scannerizzati/immagine, per cui servirebbe l'OCR — fuori MVP), si interrompe qui e si mostra all'utente *"non siamo riusciti a leggere il CV, compila il profilo manualmente"*, portandolo alla compilazione manuale delle sezioni.
3. **Strutturazione con Claude.** Se il testo è valido, viene passato a Claude, che lo mappa nelle sezioni del profilo master (§4.2). Il risultato **pre-popola** i campi, che restano **modificabili** dall'utente prima del salvataggio (nessun dato viene dato per definitivo).

L'estrazione lato server è la scelta più economica (non si pagano i byte del documento a Claude) e uniforma i due formati; il costo è la mancata copertura dei CV solo-immagine, gestita col fallback (§11).

### 5.5 Notifica mattutina: meccanismo

Lo scheduler gira a intervalli frequenti (es. ogni 15 minuti). A ogni giro, per ogni utente per cui **in quel momento sono circa le 10:00 locali**:
1. verifica se esistono job con `date_collected > User.last_notified_at`;
2. se sì, invia la notifica Web Push e aggiorna `last_notified_at` all'istante corrente;
3. se no, nessuna notifica (nessun aggiornamento del timestamp).

Il timestamp fa da guardia naturale contro i doppi invii (lo scheduler può ripassare più volte nella finestra delle 10:00 senza rinotificare) e risolve i **fusi a est dell'Europa**: se le 10:00 locali di un utente cadono prima del batch delle 02:00 Europe/Rome, quell'utente riceve la notifica sui job del **batch più recente disponibile** (quello della notte europea precedente, se non ancora annunciato), e mai due volte sullo stesso batch. Nessun caso speciale nel codice: la definizione "raccolti dopo l'ultima notifica" copre tutto.

---

## 6. Generazione del CV in dettaglio (il punto più critico)

### 6.1 Perché il template del prototipo non è riusabile così com'è

Il template `Master_CV_template_PLACEHOLDERS` e il prompt del workflow *03* sono modellati sul CV di **una persona specifica**. In particolare contengono:

- **dati personali fissi** scritti nel documento (nome "Matteo Sorrentino", telefono, email, LinkedIn, città "Zurich, CH");
- **esperienze cablate** nella struttura: slot rigidi e nominali per "Kuwait Petroleum Q8" (6 bullet), "Deloitte" (2 bullet), "Police of the Netherlands" (1 bullet), più education e lingue fisse;
- una **frase hardcoded** imposta come chiusura del summary ("Relocating to Switzerland to be closer to my partner…");
- un **numero fisso di 21 placeholder** e un **nome file** "CV_Matteo_…".

Tutto questo va reso **generico e per-utente**. Il numero di esperienze e di bullet non può essere fisso: dipende dal profilo di ciascuno.

### 6.2 La nuova pipeline di generazione

1. **Raccolta contesto.** Si prende il profilo master strutturato dell'utente (§4.2) + la descrizione del job + (opzionale) il dettaglio di arricchimento (§4.8 funzionale).
2. **Chiamata a Claude per i contenuti.** Claude riceve i dati reali dell'utente e produce i **contenuti testuali** su misura: sommario riformulato, bullet delle esperienze riscritti e riordinati per il job, aree di competenza selezionate, ecc. Le regole del prompt del prototipo che restano valide e vengono mantenute: **non inventare nulla** che non sia nel profilo (grounding), riformulare/riordinare/enfatizzare sì, tradurre sì (per la lingua del CV), rispettare la lunghezza. Le regole **da rimuovere**: la frase fissa sulla Svizzera, i riferimenti nominali a Q8/Deloitte/Police, il numero fisso di bullet.
3. **Composizione HTML.** I contenuti prodotti si inseriscono in un **template HTML flessibile** (uno solo nell'MVP, §6.4): un ciclo ripete il blocco "esperienza" per quante esperienze ci sono; la sezione **istruzione** è copiata **invariata** dal profilo; la foto è inclusa **solo** se l'utente ha attivato l'opzione (§6.5).
4. **Controllo "1 pagina".** Il template HTML/CSS è progettato per stare in una pagina; WeasyPrint permette di verificare il numero di pagine risultanti. Se il contenuto eccede, si applica una strategia di compattamento definita (vedi §11: la garanzia "1 pagina" resta un punto di attenzione, ora però su un solo formato controllato lato server).
5. **PDF.** WeasyPrint converte l'HTML in **PDF** — unico formato di output.
6. **Salvataggio.** HTML e PDF finiscono in `CVDocument`; il job passa a `cv_generated`.

### 6.3 Dove finiscono i dati personali fissi

Tutto ciò che nel template era scritto a mano diventa **campo del profilo utente**: nome, contatti, città, link LinkedIn stanno in `User`/`Profile` e vengono iniettati nell'HTML in fase di composizione. Nessun dato personale resta nel template.

### 6.4 Un solo template nell'MVP (ma predisposto per averne altri)

Nell'MVP c'è **un unico template** CV, ben fatto e flessibile. La "scelta del template" prevista dalle specifiche esiste come impostazione, ma per ora offre una sola opzione. L'architettura HTML rende banale aggiungerne altri in seguito (bastano nuovi file di template), senza toccare la logica di generazione.

### 6.5 Foto: opzione on/off

La foto profilo viene inclusa nel CV **solo se** l'utente attiva l'opzione `cv_include_photo` (§4.1). Quando la foto è assente, il template deve gestire con grazia lo spazio lasciato libero (dettaglio realizzativo minore, §11).

---

## 7. Fuso orario e multi-utenza

Le specifiche (§6 funzionale) richiedono che "oggi" e le "10:00" siano **locali per ciascun utente**. Tecnicamente:

- ogni utente ha il proprio `timezone`;
- il database salva gli orari in formato universale (UTC), convenzione standard;
- la conversione all'ora locale avviene solo al momento di decidere quando inviare una notifica o cosa conta come "oggi" per quell'utente;
- lo scheduler gira di frequente (es. ogni 15 minuti) e, a ogni giro, invia le notifiche mattutine secondo il meccanismo di §5.5 e controlla i timer di inattività (7 giorni da `User.last_activity_reset`, §4.1).

**Due riferimenti temporali (semplificati dalla v3, erano tre).**
- **Europe/Rome** — governa il **batch di raccolta** (02:00, §5.1) **e** il **reset dei massimali giornalieri** (mezzanotte, §4.6). Un unico "orologio di sistema" per tutto ciò che è globale.
- **Fuso locale dell'utente** — governa **notifiche** (le 10:00 sono le sue 10:00) e l'**"oggi" di visualizzazione** della lista.

La coesistenza dei due è voluta e accettata per l'MVP; le piccole incoerenze percepibili solo su fusi lontani sono a verbale in §11.

Ogni utente vede **solo i propri dati** (job, profilo, ricerche, CV): l'isolamento è garantito dal fatto che ogni record è legato a un `user` e ogni query filtra per l'utente autenticato.

---

## 8. Hosting e deploy

### 8.1 VPS singolo

**Scelta: un VPS economico** (es. Hetzner, indicativamente 5–10 €/mese), un server virtuale su cui gira tutto. Per un MVP con pochi utenti è più che sufficiente e molto economico. Non si usa una piattaforma gestita (tipo Render/Railway) perché il committente preferisce il VPS; in cambio ci si fa carico di un po' più di configurazione iniziale, mitigata da Docker (sotto).

### 8.2 Docker Compose

Tutti i componenti (Django, PostgreSQL, Redis, worker Celery, Caddy) girano come **container Docker** orchestrati da un unico file **Docker Compose**. Vantaggi per un piccolo team:
- l'ambiente è **riproducibile**: la stessa configurazione gira identica sul portatile dello sviluppatore e sul server;
- l'installazione sul VPS si riduce a poche istruzioni;
- aggiornare l'app significa ricostruire e riavviare i container.

### 8.3 Caddy per HTTPS

**Caddy** fa da reverse proxy davanti a Django e ottiene/rinnova **automaticamente** il certificato HTTPS (Let's Encrypt), senza configurazione manuale. È la via più semplice per avere il sito in `https://` senza pensarci.

### 8.4 Backup

Dato che i dati vivono su un unico server, il backup è essenziale:
- **dump automatico giornaliero** del database PostgreSQL, salvato **fuori dal VPS** (es. uno storage a oggetti economico o un altro spazio), così un guasto del server non porta via anche i backup;
- i file PDF dei CV sono rigenerabili dall'HTML salvato, ma vanno comunque inclusi nel backup per comodità.

### 8.5 Configurazione e segreti

Tutte le chiavi (token Apify, chiave API Anthropic, credenziali Google OAuth, chiavi Web Push) stanno in **variabili d'ambiente**, mai nel codice e mai nel repository. Anche i **prezzi unitari del credito** e i **limiti di raccolta** (50/100) sono parametri di configurazione applicativa (modificabili senza toccare la logica). Questo corregge esplicitamente il token Apify cablato nell'URL del prototipo.

### 8.6 Aggiornamenti di sicurezza

Il VPS va tenuto aggiornato: si attivano gli **aggiornamenti di sicurezza automatici** del sistema operativo e si aggiornano periodicamente le dipendenze dell'app. È l'unica manutenzione di sistema ricorrente richiesta.

---

## 9. Amministrazione (piani e credito)

Il committente ha scelto di gestire piani e credito **direttamente sul database**. Django offre già, senza sviluppo aggiuntivo, il **Django Admin**: un pannello web protetto da cui un amministratore può modificare gli stessi dati (cambiare il piano di un utente, **caricare credito in euro** sul saldo `extra_credit`, applicare un voucher) in modo più sicuro e comodo che toccando le tabelle a mano — riducendo il rischio di errori che corromperebbero i dati.

La raccomandazione tecnica è quindi: **stessa decisione operativa** (l'admin gestisce piani/credito a mano, niente checkout — coerente con §4.11 funzionale), ma **attraverso il Django Admin** invece che via SQL diretto. Resta comunque possibile agire sul DB se necessario. Questo copre:
- cambio piano via voucher / intervento amministrativo;
- caricamento manuale del **credito** (saldo in €; l'MVP non ha checkout self-service — §4.11 funzionale).

---

## 10. Cosa cambia rispetto al prototipo n8n

Riepilogo esplicito, utile a chi conosce il prototipo, di cosa viene **riusato** e cosa viene **sostituito**.

**Riusato (con adattamenti):**
- l'**actor Apify** e la modalità di chiamata (ora una chiamata per utente con più filtri e limite di risultati — assunzione da validare, §11);
- il **prompt di scoring** (scala 1–5, criteri prioritizzati, JSON match/gaps): quasi invariato;
- l'impianto logico del **prompt CV** (grounding, no invenzioni, traduzione sì, controllo lunghezze): mantenuto, ripulito dalle parti personali;
- il **layout visivo** del CV come punto di partenza per il template HTML.

**Sostituito:**
- **Google Sheets → PostgreSQL.** I fogli erano un database improvvisato per un solo utente; servono dati relazionali, multi-utente e isolati.
- **Google Drive + Google Doc "trova e sostituisci" → template HTML + WeasyPrint.** Il metodo a placeholder fissi non regge un CV a struttura variabile.
- **OpenAI → Claude.** Uniformato al fornitore scelto.
- **n8n (schedulazione e orchestrazione) → Celery + Beat dentro il monolite.** Un solo sistema da gestire, per-utente.
- **Template modellato su una persona → template generico** con dati presi dal profilo di ciascun utente.
- **Token/segreti nel workflow → variabili d'ambiente.**

---

## 11. Punti da verificare in revisione

Dubbi tecnici residui e decisioni da riesaminare in fase di implementazione o nella successiva revisione di semplicità/manutenibilità. In **v3** sono stati **chiusi**: l'ordine scoring/cap (deciso: si scora tutto entro il limite 50/100, poi si taglia a 15), il Word "1 pagina" e la fedeltà PDF↔Word (Word eliminato), il comportamento a limite esaurito (definito: prosecuzione a credito o blocco), il reset quota (allineato a Europe/Rome), la gestione di `published_at` mancante, la concorrenza sulla generazione e il fallimento dello scoring. La numerazione è stata rifatta.

1. **Supporto multi-filtro dell'actor Apify** *(nuovo, v3 — da validare presto)*. Il disegno della raccolta (§5.1) assume che l'actor accetti **più coppie keywords/location in una singola chiamata**, con un limite complessivo di risultati. Va verificato con l'actor reale a inizio implementazione. **Fallback già definito** (una chiamata per ricerca + tetto 50/100 applicato dalla nostra logica), quindi il rischio è di costo/latenza, non di funzionalità.

2. **Distribuzione dei risultati tra ricerche con limite complessivo** *(nuovo, v3)*. Con un tetto unico 50/100 su più ricerche, la fonte decide di fatto quanti risultati arrivano da ciascuna: ricerche molto prolifiche possono "affamare" le altre. Da osservare in test con dati reali; registrato anche lato funzionale (§8.8).

3. **Costo scoring per notte** *(aggiornato)*. Il limite 50/100 rende il costo Claude del ciclo notturno **prevedibile e limitato** (worst case: 100 valutazioni per utente Pro a notte). Resta da stimarlo con i prezzi del modello scelto per lo scoring e da monitorare insieme ai costi Apify e storage backup. Non esiste ancora una soglia di scala dichiarata.

4. **Garanzia "1 pagina" (solo PDF)**. WeasyPrint dà buon controllo, ma un profilo molto ricco può eccedere la pagina. Serve definire la strategia esatta di compattamento (ridurre spaziature? troncare bullet? ridurre esperienze mostrate?) e il suo limite. Con l'eliminazione del Word, la garanzia va assicurata su un solo motore, controllato lato server: il problema è dimezzato ma non sparito.

5. **Prezzi unitari del credito da fissare** *(nuovo, v3)*. `PRICE_MANUAL_CV_EXTRA` e `PRICE_IMPORT_EXTRA` sono parametri di configurazione senza valore deciso (lato funzionale: §8.18, "0,50 €" è solo un esempio). Vanno fissati prima del rilascio, insieme ai prezzi dei piani.

6. **Arrotondamenti e contabilità del saldo** *(nuovo, v3)*. Il saldo è denaro: campo decimale (mai float), addebiti e riaccrediti sempre atomici e registrati (la modalità di addebito di ogni operazione va tracciata per la restituzione su fallimento — §4.6, §5.2). Per l'MVP basta la coppia saldo + log delle operazioni; una contabilità formale (ledger) è rimandata a quando ci sarà il checkout.

7. **Conformità scraping LinkedIn.** L'uso di Apify per raccogliere offerte LinkedIn può violare i termini di servizio di LinkedIn. Scelta consapevole per l'MVP; è un rischio (di blocco della fonte o legale) da mettere a verbale e rivalutare prima di un pubblico reale. Resta il rischio più serio del progetto insieme al punto 8: da verificare **prestissimo** in test.

8. **Notifiche push su iPhone.** Funzionano solo con PWA aggiunta alla home. Il canale che veicola il valore centrale del prodotto è fragile proprio su iOS: va verificato in fase di test quanto incide sull'esperienza reale e come comunicarlo efficacemente in onboarding.

9. **Privacy e cancellazione dati (GDPR).** Il documento funzionale (§5.16, §8.13) rimanda la gestione privacy fuori dall'MVP. Tecnicamente va ricordato che, prima di un pubblico reale in UE, serviranno almeno: cancellazione account e dati, ed esportazione. L'architettura (un `user` a cui tutto è collegato) rende la cancellazione a cascata relativamente semplice da implementare quando servirà.

10. **Backup e ripristino testati.** Avere i backup non basta: va verificato almeno una volta che il **ripristino** funzioni davvero. Da inserire nella checklist operativa.

11. **Modelli Claude da fissare.** Quale famiglia di modelli per lo scoring (alto volume, conviene economico) e quale per il CV (serve più qualità) è un parametro da fissare in fase di tuning, con impatto su costi e qualità.

12. **Freschezza per fusi non europei (batch globale).** Il batch unico alle 02:00 Europe/Rome (§5.1) rende i dati "freschi al mattino" solo per gli utenti europei; per fusi lontani i job possono avere ore di ritardo alla notifica delle 10:00 locali. Il meccanismo `last_notified_at` (§5.5) garantisce comunque annunci corretti e senza doppioni per tutti i fusi. Accettato per l'MVP; da rivalutare se il prodotto si apre a utenti globali (in tal caso: raccolta per-fuso o più finestre). Registrato anche lato funzionale (§8.19).

13. **DST del batch (Europe/Rome).** Ancorare batch e reset quote a Europe/Rome comporta uno spostamento di un'ora in UTC tra ora solare e legale, con un caso limite nei due giorni di cambio ora. Irrilevante per pochi utenti di test; da tenere presente se la puntualità della finestra 24h diventasse critica.

14. **Affidabilità delle date di pubblicazione Apify.** La finestra "24h" (pre-filtro dell'actor) e il tie-break "più recente" dipendono dai dati della fonte. La gestione della data **mancante** è ora definita (ammissione + tie-break casuale); resta da validare in test la qualità delle date quando **presenti** (imprecisioni degradano il tie-break, non la funzionalità).

15. **Scarto tra "giorno di quota" (Europe/Rome) e "oggi" locale.** Ridotto rispetto alla v2 (le quote seguono ora lo stesso fuso del batch, e per gli utenti europei coincidono di fatto col giorno locale). Per fusi lontani il tetto giornaliero può ancora azzerarsi in un momento inatteso della giornata locale. Accettato per semplicità; registrato anche lato funzionale (§8.20).

16. **CV solo-immagine non leggibili in onboarding.** L'estrazione testo lato server (§5.4) non copre PDF scannerizzati/immagine (niente OCR nell'MVP). Il fallback rimanda l'utente alla compilazione manuale. Da verificare in test quanto frequente sia il caso e se valga la pena aggiungere l'OCR in futuro.

---

*Fine del documento. Prossima chat prevista: revisione di semplicità e manutenibilità dello stack qui proposto.*
