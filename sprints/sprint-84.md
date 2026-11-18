# Sprint 84 — Ricerche su più città, modalità di lavoro, lavoro dei desideri, dimensione del testo

> **Periodo:** 2026-11-17 · **Branch:** `sprint-84-ricerche-desiderio` (da `main` al commit 9a4055e, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** **rilasciato in produzione il 2026-11-18** (con l'OK del committente); da provare dal telefono.

## Input
Richieste del committente nel tracking: ID 15 (filtro remote/ibrido nella lista), ID 16 (ricerca più ampia di una città), ID 18 (ricerca "a parole" del lavoro desiderato), ID 27 (modalità di lavoro come opzione Pro della ricerca), ID 28 (testo troppo piccolo nell'app aggiunta alla Home dell'iPhone, dove non c'è lo zoom di Safari).

Numero: `git log` e `ls sprints/` arrivano a 83.

Decisioni prese col committente il 2026-11-17: `Docs/design/SPEC-DELTA.md` **A17–A20** (B12 chiuso). Mockup approvati in `Docs/design/mockups/` (vedi `SCREENS.md`): `ricerca-nuova-citta-pro`, `ricerca-nuova-citta-free`, `ricerche-citta`, `desiderio-pro`, `desiderio-free`, `impostazioni-voci-nuove`, `jobs-card-desiderio`, `detail-desiderio-modalita`, `jobs-filtri-desiderio-modalita`, `settings-dimensione-testo`, `jobs-lista-testo-grande`.

**Deroghe a `CLAUDE.md`, approvate dal committente:** il vincolo "Non introdurre filtri di ricerca oltre keywords, location e tipo ricerca" va aggiornato in questo sprint: si aggiungono la **modalità di lavoro** (solo Pro) e la ricerca nascosta del **lavoro dei desideri** (solo Pro). Ogni altro filtro di ricerca resta escluso.

## Parte 1 — Ricerche su più città (ID 16)
**Cosa deve fare**
- Nella ricerca si sceglie prima il **paese** (elenco), poi le **città**, come chip: **Free 1, Pro fino a 5**.
- La località verso la fonte è sempre in inglese, nel formato "City, Country" (risolve le raccolte finite negli USA per località scritte in italiano).
- Ogni città è cercata in un raggio di **circa 40 km**.
- **Ogni città di una ricerca in uso conta come una ricerca attiva:** Pro al massimo 50 città attive, Free 1 per tipo (come oggi). Restano i massimali di ricerche salvate (Pro 100, Free 10). Il pannello mostra "Ogni città conta come una ricerca attiva: ne usi n di 50"; la pagina Ricerche salvate mostra "Città attive n di 50"; la scheda di ogni ricerca elenca città e paese.
- Il filtro "Ricerca" della lista resta per ricerca (non per città).

**Indicazioni per chi implementa (non vincolanti)**
- La fonte accetta un raggio (`distance`, in miglia: 5, 10, 15, 25, 50): usare 25.
- La raccolta raggruppa già per tipo e località (una chiamata per gruppo, `MAX_ITEMS_PER_CALL` 150): con più città per ricerca il raggruppamento va fatto per città (e per modalità, Parte 2). I doppioni tra città vicine sono già eliminati dalla deduplica.
- Le ricerche esistenti (una città, paese testuale) vanno migrate a "paese + 1 città" senza perderle; verificare i paesi scritti in italiano.
- Al downgrade Pro → Free valgono le regole di oggi (tutte disattivate); una ricerca con più città oltre il limite Free non si può attivare finché non resta una città.

## Parte 2 — Modalità di lavoro (ID 15 + 27)
**Cosa deve fare**
- **Solo Pro:** nella ricerca, segmenti **Qualsiasi / Remoto / Ibrido / In sede** (predefinito Qualsiasi). Per i Free il controllo è visibile ma bloccato con il badge PRO e il testo "Scegliere remoto, ibrido o in sede è incluso nel piano Pro."
- **Per tutti i job raccolti**, l'AI ricava la modalità dalla descrizione durante lo scoring: Remoto, Ibrido, In sede o Non indicata. Se l'AI non la trova e il job viene da una ricerca con modalità, vale quella della ricerca.
- **Dettaglio:** chip con la modalità accanto ad "azienda · località"; con "Non indicata" il chip non compare.
- **Filtri della lista:** gruppo **Modalità** a scelta multipla (Remoto, Ibrido, In sede, Non indicata), in AND con gli altri gruppi; incluso nel conteggio dei filtri attivi e in "Azzera filtri".
- La card di lista non cambia. I job raccolti prima dello sprint non hanno la modalità.

**Indicazioni per chi implementa**
- La fonte accetta `workType` come filtro di ricerca, ma **non** la restituisce nell'output (campo vuoto nel campione di 122 annunci): per questo la modalità del job viene dall'AI. Con il motore di ricerca "AI" di LinkedIn la fonte aggiunge la modalità al testo della query invece di filtrare: non è garantita.
- Aggiungere la modalità all'output dello scoring esistente (nessuna chiamata AI in più); nuovo campo sul `Job` con migrazione, serializer, parametro di filtro in `GET /api/jobs/`.

## Parte 3 — Lavoro dei desideri (ID 18)
**Cosa deve fare**
- **Solo Pro**, uno per utente, in **Impostazioni → Ricerca job → Lavoro dei desideri**, con interruttore Attivo.
- L'utente scrive una **descrizione** (fino a 1000 caratteri) e sceglie **paese** e **fino a 5 città**; le città contano come ricerche attive (Parte 1).
- L'AI ricava dalla descrizione **1–2 keyword molto mirate** (meglio pochi job ma pertinenti). Le keyword diventano una ricerca **nascosta**: **non vengono mostrate all'utente** (decisione del committente: l'utente non deve pensare che sia una ricerca normale) e non compaiono tra le ricerche salvate. Si ricavano di nuovo solo quando cambia la descrizione.
- Durante lo scoring **ogni job**, da qualunque ricerca arrivi (anche da quella nascosta), riceve l'etichetta **Desiderio** solo se l'AI lo giudica **molto affine** alla descrizione: un giudizio sì/no severo, non una soglia di punteggio. Un job della ricerca nascosta non è "desiderio" per il solo fatto di provenire da lì.
- **Card e dettaglio:** etichetta con stellina ("Desiderio" sulla card, "Lavoro dei desideri" nel dettaglio), prima delle altre etichette.
- **Filtri:** "Lavoro dei desideri" è il **primo chip del gruppo Ricerca**, se l'utente ha il desiderio (anche spento, finché ci sono job etichettati); filtra i job con l'etichetta, non quelli che vengono dalla ricerca nascosta.
- **Free:** pagina bloccata con spiegazione e "Scopri Pro". Al downgrade il desiderio viene spento, come le ricerche.
- Testo della pagina: "Ogni giorno cerchiamo lavori in linea con la tua descrizione. Durante la valutazione l'AI segna con Desiderio i job, da qualunque ricerca arrivino, molto vicini a ciò che hai descritto. Le città contano come ricerche attive."

**Indicazioni per chi implementa**
- Costi: una chiamata AI quando la descrizione viene salvata o cambiata; pochi token in più per job nello scoring (la descrizione va nel prompt solo per gli utenti con il desiderio attivo); 1–2 keyword × città chiamate alla fonte in più per raccolta.
- La descrizione è un nuovo dato personale: va in informativa (se serve), export e cancellazione (`CLAUDE.md` → Sicurezza e privacy).

## Parte 4 — Dimensione del testo (ID 28)
**Cosa deve fare**
- Nuovo gruppo **Aspetto** in Impostazioni con **Dimensione del testo** (e Lingua, spostata qui): **Come il telefono** (predefinito), **Normale**, **Grande** (circa +20 %), con un'anteprima.
- Ingrandisce **tutta l'app**: testo, pulsanti, icone, spazi; la pagina si ridispone sulla larghezza dello schermo, senza scorrimento laterale.
- "Come il telefono" segue la dimensione del testo impostata nel sistema (su iPhone anche nell'app aggiunta alla Home).

**Indicazioni per chi implementa**
- Le misure sono in `rem` (Tailwind v4): cambiare la dimensione base del documento ingrandisce tutto. Su iOS "Come il telefono" si può ottenere con il font di sistema dinamico (`-apple-system-body`). La scelta è del dispositivo (non serve salvarla sul server, da confermare).
- Verificare con `layout.spec.js` a 360/390 px in modalità Grande (nessuna pagina più larga dello schermo).

## Da aggiornare nello stesso commit dell'implementazione
`CLAUDE.md` (vincolo sui filtri di ricerca), specifiche 01 (§4.2, §4.4, §4.5, §4.6, §4.22) e 02 (modello dati, raccolta, scoring, API §12, test §13), questa scheda, `CHANGELOG.md`, test backend e e2e (`job-list.spec.js`, `account.spec.js`, `layout.spec.js`). Nessuna dipendenza nuova. Nessun dato personale nei file (repository pubblico).

## Punti da verificare in revisione
Domande della scheda, con la risposta data prima di scrivere il codice (2026-11-17; le scelte su cui non c'erano dubbi sono andate avanti, le due domande aperte le ha decise il committente):
1. **Costi Apify e AI:** nessun tetto nuovo oltre le 50 città attive; da misurare dopo il rilascio (RunLog `collection` per gruppo, credito Apify, token Bedrock).
2. **Raggio:** 25 miglia fisse (`SEARCH_RADIUS_MILES`), non configurabile per ora.
3. **Elenco dei paesi:** tutti i codici ISO 3166 con i nomi di `Intl.DisplayNames` (nessuna dipendenza): mostrati nella lingua dell'interfaccia, salvati e inviati alla fonte in inglese. Suggerimenti delle città solo del paese scelto (`countrycodes` di Nominatim).
4. **Modalità dalla fonte:** passata come `workType`, ma la modalità del job viene sempre dall'AI; una chiamata alla fonte per (tipo, città, paese, modalità).
5. **Severità del "Desiderio":** prompt severo (regola 10); da tarare dopo l'uso reale.
6. **Desiderio spento:** le etichette già date restano; i job già valutati non vengono rivalutati.
7. **Dimensione del testo:** salvata solo sul dispositivo (`localStorage`), applicata con `zoom`; "Come il telefono" dal font di sistema su iOS.
8. **Filtri salvati:** includono Modalità e il chip Desiderio. I job raccolti prima dello sprint (senza modalità) restano fuori dai filtri Modalità.
- **Migrazione delle ricerche esistenti:** `city` → `cities = [city]`; paese vuoto ricavato dalle altre ricerche con la stessa città. Sulla copia dei dati di produzione: 85 ricerche, tutte con 1 città, nessun paese vuoto (anche i paesi erano già in inglese), 59 attive, al massimo 27 città attive per utente (sotto il nuovo limite di 50).
- **Decisioni del committente:** informativa **1.2** con riaccettazione da parte di tutti; descrizione del desiderio modificabile **5 volte al giorno** (giorno Europe/Rome, senza costo a credito).

## Implementazione
**Backend**
- `searches/models.py`: `SavedSearch.cities` (JSON, al posto di `city`, con la property `city` di compatibilità), `work_mode`, `is_wish`; nuovo `JobWish` (descrizione max 1000, paese, città max 5, attivo, keyword nascoste, contatore delle modifiche del giorno). Migrazione `searches/0004` (copia e rimozione di `city`, reversibile).
- `searches/services.py`: città per ricerca (Free 1, Pro 5), conteggio delle città attive (`active_city_count`, desiderio contato una volta) nell'attivazione e nella modifica di una ricerca attiva; `sync_wish_searches` crea le ricerche nascoste (una per keyword). `searches/wish.py`: `save_wish` (solo Pro, validazione, 5 modifiche al giorno, limite città, AI solo se cambia la descrizione e fuori dalla transazione), `derive_wish_keywords` (1–2 keyword, `BEDROCK_SCORING_MODEL`). Downgrade: spegne anche il desiderio.
- API: `/api/searches/` con `country`, `cities`, `work_mode` (nascoste escluse; `city` ancora accettato in scrittura); `/api/search-limits/`; `/api/job-wish/` GET/PUT (mai le keyword; 502 se l'AI non risponde); autocomplete con `country_code`; `/api/jobs/?mode=` e `search=wish`; `work_mode`/`is_wish_match` nel `JobSerializer`; `work_modes` e `"wish"` nei filtri salvati; `wish_filter_available` in `/me`.
- Raccolta (`apify_linkedin.py`): gruppi per tipo × città × paese × modalità, `distance: "25"`, `workType`; etichetta `matched_search` vuota per le offerte della ricerca nascosta.
- Scoring: `work_mode` obbligatorio nello schema (regola 9) con ripiego sulla modalità della ricerca; con il desiderio attivo descrizione e regola 10 nel prompt e `wish_match` nello schema (`is_wish_match`). `Job.work_mode`, `Job.is_wish_match`, `JobFilterPreset.work_modes`: migrazione `jobs/0024`.
- Privacy: informativa 1.2 (it/en, app e `Docs/legal/`): ricerche con paese, città e modalità, descrizione del lavoro dei desideri, uso dell'AI per modalità, keyword ed etichetta. Export con `job_wish` (keyword comprese, diritto di accesso) e README aggiornato; cancellazione in cascata con l'account. 14 messaggi nuovi tradotti in inglese.
- `CLAUDE.md`: vincolo sui filtri di ricerca aggiornato con le deroghe approvate.

**Frontend**
- `components/CityChipsField.jsx` (paese da elenco, città come chip o campo singolo, suggerimenti del paese) e `utils/countries.js`; usati in Ricerche salvate (con la modalità a segmenti, bloccata per i Free, "Città attive n di 50", città · paese e modalità sulla card), onboarding (1 città) e Lavoro dei desideri.
- Lista: gruppo **Modalità** nei filtri (conteggio, Azzera, filtri salvati), chip **"Lavoro dei desideri"** primo del gruppo Ricerca, badge **Desiderio** sulla card; dettaglio con il chip della modalità e "Lavoro dei desideri". Colori `--wish`/`--wish-soft` (anche scuri), variante `wish` del badge.
- Impostazioni: "N città attive su 50", riga **Lavoro dei desideri**, gruppo **Aspetto** con **Dimensione del testo** e Lingua. Pagine nuove `/settings/wish` (`WishPage`, Pro con interruttore che salva subito, descrizione con contatore, modifiche rimaste oggi, "Salva"; Free bloccata con "Scopri Pro", che porta alla pagina dei limiti e del piano `/settings/limits`, decisione del committente del 2026-11-18; non c'è un acquisto self-service) e `/settings/text-size` (`TextSizePage`, con anteprima).
- `lib/textSize.js`: scelta in `localStorage`, `zoom` su `<html>` (Grande 1,2; "Come il telefono" su iOS dal font `-apple-system-body`, limitato a 0,85–1,4), all'avvio, al ritorno nell'app e al ridimensionamento. Con lo zoom la larghezza utile resta di almeno 300 px: su un telefono da 320 px (iPhone SE) Grande vale circa 1,07, perché a 1,2 la barra di tab e le righe dei documenti uscivano dallo schermo (trovato da `layout.spec.js`).
- `ui/action-bar.jsx`: l'altezza della barra si misura con `offsetHeight` (unità CSS) invece che con il rettangolo sullo schermo, già ingrandito dallo zoom.
- **Correzione trovata dai test:** la lista non scarta più le risposte arrivate fuori ordine (con filtri cambiati in fretta una risposta lenta poteva sovrascrivere quella più recente: il test dei filtri salvati falliva a volte).

**Memoria di gunicorn** (richiesta del committente con l'OK al rilascio, 2026-11-18): in `docker-compose.prod.yml` il `web` gira con `--max-requests 300 --max-requests-jitter 60`. Ogni worker riparte dopo 300–360 richieste: con pochi utenti è qualche volta al giorno, abbastanza per contenere la crescita (fino a 430 MB per worker dopo un giorno) senza ripartenze frequenti. Con i worker sync la ripartenza avviene solo dopo la fine della richiesta in corso, quindi una generazione o una raccolta manuale fino a 30 minuti non viene interrotta; il jitter evita che i 4 worker ripartano insieme. Nessuna libreria nuova.

## Verifica
- Backend: suite completa **528 test OK** (con `DJANGO_DEBUG=true`, `REGISTRATION_INVITE_CODE=` vuoto), di cui 21 nuovi in `apps/searches/test_sprint84.py`; `makemigrations --check` senza differenze; catalogo inglese senza voci vuote o `fuzzy`.
- Migrazione `searches/0004` provata su una copia usa e getta del backup di produzione (vedi sopra), poi cancellata.
- Frontend: `npm run build` OK, `oxlint` 0 errori (9 warning, gli stessi di prima), tutte le 672 chiavi usate presenti in it ed en.
- E2e sullo stack usa e getta (un worker, runner con memoria limitata): `auth-onboarding`, `account` (nuovi: Pro con più città e modalità; Free con città unica, modalità e desiderio bloccati; Pro con desiderio senza keyword visibili; dimensione del testo) e `job-list` (nuovo: filtro Modalità, chip "Lavoro dei desideri", etichette su card e dettaglio) verdi; `layout.spec.js` con il nuovo giro in **Grande** a 360/390 px, iPhone 13 e iPhone SE verde, dopo le correzioni sopra. **Suite e2e completa il 2026-11-18: 95/95** in 18,4 minuti (Chromium più `layout.spec.js` su iPhone 13 e iPhone SE), poi di nuovo i test backend: 528 OK.
- **Memoria:** il primo tentativo della suite completa (2026-11-17) è stato fermato per memoria scarsa dopo 3 test verdi. Il `web` di produzione, acceso da 25 ore, occupava 1,25 GiB (4 worker gunicorn cresciuti a 230–430 MB l'uno); insieme allo stack e2e completo il VPS (3,9 GB, senza swap) era al limite. L'anteprima era spenta. Per il secondo giro, con il consenso del committente, `web`, `worker` e `beat` di produzione sono stati fermati dalle 07:43:20 alle 08:05:53 UTC (sito non raggiungibile per circa 22 minuti; nessun task Celery in corso; le raccolte automatiche saltate ripartono al giro successivo del dispatcher). Al riavvio home e `/api/legal/` rispondono 200 e lo stack è tutto da `docker-compose.prod.yml`. Picchi misurati durante la suite: runner 1,19 GiB, `e2e-fe` 260 MiB, `e2e-web` 254 MiB, `e2e-preview` 92 MiB, `e2e-db` 53 MiB; memoria usata al massimo 2,2 GB su 3,9.

## Da provare (anteprima, poi produzione dopo il rilascio)
- iPhone (app dalla Home): Impostazioni → Aspetto → Dimensione del testo, con le tre scelte e con la dimensione del testo di sistema cambiata.
- Ricerca Pro con più città e una modalità; alla raccolta successiva i job con la modalità e, con il desiderio attivo, qualche etichetta Desiderio (taratura della severità).

## Cosa manca / note
- I costi reali (chiamate Apify per città, token dello scoring con il desiderio) vanno misurati dopo il rilascio.
- I job raccolti prima dello sprint non hanno la modalità né l'etichetta: nessuna rivalutazione dello storico (una chiamata AI per job).
- Rilascio: `DEPLOY.md` §4.11 (migrazioni `searches/0004` e `jobs/0024`, informativa 1.2).

## Rilascio (2026-11-18)
Procedura di `DEPLOY.md` §4.11: backup del database (task di backup, dump del giorno nel volume dei backup), tag `pre-sprint84` delle immagini per un ritorno rapido, fast-forward di `main`, build e `up -d` da `docker-compose.prod.yml`. Migrazioni `jobs/0024` e `searches/0004` applicate: 86 ricerche (60 attive), tutte con città e paese. Informativa 1.2 servita (gli utenti la riaccettano al prossimo accesso). Gunicorn con `--max-requests 300 --max-requests-jitter 60`. Dopo il rilascio: home e API 200, nuovo frontend servito, tutti i container da `docker-compose.prod.yml`, `web` a circa 340 MiB (prima 1,25 GiB dopo un giorno acceso).
