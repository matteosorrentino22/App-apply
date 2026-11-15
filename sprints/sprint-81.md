# Sprint 81 — Correzioni dopo la prova su iPhone

> **Periodo:** 2026-11-15 · **Branch:** `sprint-81-correzioni` (da `sprint-80-rifinitura`, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato e verificato (e2e 82/82, backend 488/488); **merge e deploy non fatti** (in attesa dell'ok del committente).

## Input
Il committente ha provato l'anteprima su iPhone (Safari) e ha segnalato: (1) nel Profilo "Salva modifiche" sostituiva la barra di tab e non si poteva più cambiare sezione; (2) esperienze e altre sottosezioni del Profilo impaginate male su mobile (campi rientrati e stretti, "Data fine" fuori dalla card); (3) campi data sovrapposti o fuori dal contenitore; (4) l'ora della barra di stato sopra i contenuti scorrendo. In più: **niente raccolta automatica preimpostata per i Pro** (la attivano loro). Metodo richiesto: screenshot anche in WebKit con emulazione di iPhone, controlli automatici su elementi fuori dal contenitore e campi sovrapposti come e2e riutilizzabili, ricerca della stessa classe di difetti in tutto il redesign. Vincoli: nessun cambio di API, backend (salvo la richiesta sulla raccolta), regole o dipendenze; it/en; PDF non toccato.

Prima di partire: produzione su `main` (f6584e5), container invariati da `docker-compose.prod.yml`, sito 200. Numero: `git log` e `ls sprints/` arrivano a 80. Su indicazione del committente aggiunti al `.env` di produzione `LEGAL_CONTROLLER_NAME` e `LEGAL_CONTROLLER_EMAIL` (senza indirizzo), senza ricreare i container: diventano visibili al rilascio.

## Cosa non andava, causa, correzione
| # | Difetto | Causa | Correzione |
|---|---|---|---|
| 1 | Nel Profilo (e in Ricerche) la barra di tab spariva | `ActionBar` aveva un solo comportamento, "al posto della barra di tab" (pensato per dettaglio ed editor, Sprint 75), riusato nelle sezioni principali (Sprint 78) | Variante `stacked`: la barra azione sta sopra la barra di tab, che resta visibile; in Profilo compare solo con modifiche non salvate (istantanea del contenuto senza le chiavi interne), durante il salvataggio o con un errore; spazio in fondo per entrambe. Dettaglio, editor e onboarding come prima (tornare indietro dalla testata: "‹ Jobs", "‹ Torna al job") |
| 1b | A 320 px (iPhone SE) la barra azione dell'editor copriva l'ultima parte del contenuto | altezza della barra presa come valore fisso (93 px) mentre i pulsanti andavano a capo (113 px) | altezza misurata con `ResizeObserver` (`--app-actionbar-h`) |
| 2 | Esperienze: campi rientrati e stretti, azioni sparse | layout a "timeline" (puntino e rientro) con campi `flex-wrap` e larghezze minime | markup nuovo di `ExperienceGroupEditor` (stesse props, dati e limiti): campi a tutta larghezza, ogni ruolo in un riquadro `bg-tint` con bordo e raggio 12, spaziature 6/16/24 px, "Aggiungi un altro ruolo", "Rimuovi ruolo", "Rimuovi azienda" come pulsanti di testo da 44 px a sinistra con icona (rossi solo i "Rimuovi"); stesso criterio per Istruzione e per Competenze, Certificazioni e Lingue (`ListSectionEditor`; lingua e livello affiancati solo con spazio) |
| 2b | Città e paese affiancati uscivano dai riquadri stretti | due campi con larghezza minima 128 px in una riga senza a capo | `CityAutocomplete` a griglia, impilata sotto i 20rem di contenitore |
| 2c | Campo dei punti elenco basso (36 px), testo a 14 px (zoom automatico di iOS al tocco), ✕ con nome solo in italiano | stile del vecchio `ChipInput` | 48 px, testo a 16 px, voci che vanno a capo, nome del ✕ tradotto |
| 3 | Campi data sovrapposti o fuori dalla card | Safari su iPhone dà a `input type=date` una larghezza propria che non si riduce; affiancati in righe `flex-wrap` con larghezze minime | componente condiviso `DateRangeFields` (griglia `minmax(0,1fr)`, impilata sotto i 20rem di contenitore) in esperienze, istruzione (profilo e onboarding) e filtri della lista; in `index.css` tutti i campi data e ora con `appearance: none`, larghezza 100 %, `min-width: 0`, 48 px, testo centrato. Le certificazioni non hanno date (il modello ha solo il nome) |
| 4 | Ora dell'iPhone sopra i contenuti scorrendo | con `viewport-fit=cover` il padding superiore dell'area sicura scorre via con la pagina; `theme-color` era il marrone primario | striscia fissa opaca alta `env(safe-area-inset-top)` con il colore dello sfondo; `theme-color` dello sfondo (chiaro e scuro) in `index.html` e nel manifest |
| 5 | Raccolta automatica attivata ai Pro esistenti alle 07:00 | migrazione dati `accounts/0012` (Sprint 77) | migrazione resa vuota (il nome resta, è già nello storico delle migrazioni dei database di prova); test aggiornato; specifiche, DEPLOY §4.10, RELEASE §3 e §5 aggiornati |

## Perché i controlli precedenti non li avevano visti
- **Solo Chromium.** Gli screenshot e le misure degli sprint 72–80 erano in Chromium, che rende i campi data in modo diverso da Safari su iPhone.
- **Solo la larghezza della pagina.** Il controllo segnalava lo scroll orizzontale della pagina, ma un elemento può uscire dalla sua card senza allargare la pagina (la card è più stretta dello schermo).
- **Nessun controllo di sovrapposizione** e dati di prova corti (azienda e ruolo brevi, pochi punti elenco, date vuote).
- **La barra di tab nascosta era voluta dal disegno dello Sprint 75**, applicato per estensione al Profilo nello Sprint 78: nessun test verificava che dalle sezioni principali si potesse sempre cambiare sezione.
- **Anche ora un limite resta:** il WebKit di Playwright gira su Linux e non ha il campo data nativo di iOS; con l'emulazione di iPhone il difetto dei campi data **non si riproduceva** nemmeno sul codice vecchio. La correzione segue il comportamento noto di Safari su iPhone e va confermata sul telefono.

## Controlli aggiunti (riutilizzabili)
- `e2e/helpers/layout.js` — `findLayoutIssues(page)`: pagina più larga dello schermo; elementi che escono dal rettangolo del loro contenitore visibile (primo antenato con bordo o sfondo; esclusi elementi posizionati e contenitori che scorrono di lato); controlli sovrapposti nello stesso strato (esclusi i contenuti che scorrono sotto barre fisse o sticky e dentro i pannelli, e i menu aperti); spazio in fondo minore delle barre fisse. `openAllSections(page)` apre le fisarmoniche.
- `e2e/layout.spec.js` — 6 gruppi con dati lunghi (azienda e ruolo lunghi, 10 punti elenco, date compilate, due ruoli nella stessa azienda): accesso; lista, filtri, raccolta, job manuale, dettaglio; editor di CV e cover letter; Profilo con tutte le sezioni aperte e con una modifica; Impostazioni e sottopagine, nuova ricerca; onboarding con esperienza e date.
- `playwright.config.js` — progetti `chromium` (tutti gli spec; lo spec di impaginazione a 360/390/1280 px), `iphone-13` e `iphone-se` (WebKit con emulazione, solo lo spec di impaginazione).
- `account.spec.js` › nuovo test a 390 px: barra di tab visibile in Profilo e Ricerche, "Salva modifiche" assente senza modifiche, presente e sopra la barra di tab con una modifica, di nuovo assente tornando al valore iniziale; spazio in fondo per entrambe le barre; "In corso" disattiva e svuota "Data fine"; dalla barra di tab si cambia sezione con modifiche in corso.

## Ricerca della stessa classe di difetti nel resto del redesign
Trovati e corretti: barra azione più alta del previsto a 320 px nell'editor della cover letter (1b); città e paese affiancati nei riquadri stretti (2b); campo dei punti elenco con testo a 14 px che su iPhone fa zoomare la pagina al tocco (2c); filtro date della lista con due campi data affiancati (3); campo data e ora del job manuale (stesso stile globale).
Controllati senza difetti (Chromium 360/390/1280, iPhone 13, iPhone SE, dati lunghi): accesso, lista, filtri, raccolta, job manuale, dettaglio, editor di CV, Profilo, Impostazioni, Ricerche, Limiti, Privacy, nuova ricerca, onboarding.
Falsi positivi del primo controllo, esclusi dopo verifica: controlli che scorrono sotto le barre fisse, sotto il fondo dei pannelli o sotto la barra in alto su desktop, e voci di menu aperti.
Rimasti, noti: il ✕ delle singole voci dei punti elenco è da 28 px (dentro la voce; allargarlo farebbe sovrapporre le voci vicine).

## Incidente durante la verifica
Il primo giro dei nuovi controlli (tre browser in parallelo, WebKit compreso) insieme ai test backend ha esaurito la memoria del VPS (4 GB): il kernel ha chiuso i processi dei browser e un processo di sistema, e la sessione di lavoro si è interrotta due volte. La produzione non ne ha risentito (container attivi da prima, sito 200). Cause: troppi processi insieme e un controllo di sovrapposizione che ricalcolava gli stili per ogni coppia di controlli (48 minuti sul Profilo con dati lunghi). Rimedi: stili calcolati una volta per elemento (Profilo in 20 s), un solo worker, runner con limite di memoria (`--memory=1400m`), mai test backend e browser insieme. Da qui in avanti gli e2e sul VPS vanno lanciati così.

## Verifica
- `npm run build` OK; `npx oxlint src e2e` 0 errori, 9 warning (gli stessi); tutte le chiavi usate esistono in it ed en (616).
- Backend (migrazione e test toccati): `manage.py test` in un container usa e getta con `-e DJANGO_DEBUG=true -e REGISTRATION_INVITE_CODE=`, da solo: **488 test OK**; `makemigrations --check`: nessuna differenza.
- Spec di impaginazione: sul codice dello Sprint 80, dopo aver tolto i falsi positivi, segnalava la barra azione più alta dello spazio riservato nell'editor della cover letter a 320 px (113 contro 93 px) e nient'altro: nemmeno i difetti di esperienze e date, che in WebKit per Linux non si vedono; sul codice corretto **18/18** (6 gruppi × Chromium, iPhone 13, iPhone SE) dopo la correzione dell'altezza.
- **Suite e2e completa** sullo stack usa e getta, codice finale, un solo worker e runner limitato a 1,4 GB: **82/82** in 15,5 minuti (63 di prima + 1 nuovo in `account.spec.js` + 18 di impaginazione). Nessun fallimento, quindi nessuna asserzione da aggiornare: gli e2e esistenti su Profilo, onboarding e filtri passano con il nuovo markup (etichette e nomi dei pulsanti invariati).
- Screenshot di prima e dopo in Chromium e WebKit (iPhone 13, iPhone SE): esperienze nella card a 320 px, date impilate nei riquadri stretti, "Nuova ricerca" sopra la barra di tab.
- Stack di prova abbattuto. Anteprima aggiornata al branch.

## Cosa manca / note
- Da confermare su iPhone vero: campi data (larghezza e testo centrato in Safari), striscia sotto la barra di stato in Safari e nella PWA dalla Home.
- Prima del rilascio: avvisare i Pro che la raccolta automatica non è più attiva da sola.
