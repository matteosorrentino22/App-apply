# Sprint 74 — Redesign UI: lista Jobs

> **Periodo:** 2026-11-14 · **Branch:** `sprint-74-lista` (da `sprint-73-appshell`, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato e verificato (e2e 35/35, screenshot a 360/390/1280 px); **merge e deploy non fatti** (in attesa dell'ok del committente).

## Input
Perimetro da `Docs/design/IMPLEMENTATION-PLAN.md` (sprint 74) e `SCREENS.md` §1: `JobCard` ridotta con `RecruiterIcon`, 2 gap, tutta cliccabile; `StatsSummary`; pillole; pannello filtri (`Sheet` / finestra); salva filtri; toast con "Annulla"; `EmptyState`; banner profilo incompleto e nuova versione; pulsante Raccogli che apre l'**attuale** raccolta manuale (nessun cambio di backend). Mockup: `jobs-lista`, `jobs-stats`, `jobs-filtri`, `save-filter`, `toast-archived`, `jobs-importati`, `jobs-vuoto`, `add-manual`, `add-manual-cost`, `add-manual-blocked`, `jobs-avvisi`, `confirm-cost`, `collect-free`, `collect-running`, `desk-jobs`. Regole del committente: comportamento esistente con il nuovo aspetto, nessuna API né backend, nessuna dipendenza nuova, font di sistema, stringhe it/en verificate a 360 e 390 px, e2e aggiornati.

## Decisioni prese
- **Card senza pulsanti** (SPEC-DELTA A2, deciso): niente "Dettagli", "Archivia", "Genera CV". Il CV si genera dal dettaglio (che resta quello attuale fino allo Sprint 75); l'archiviazione si fa con lo swipe. **Limite temporaneo**: fino al menu ⋯ del dettaglio (Sprint 75, A7) non c'è un modo di archiviare da **tastiera**.
- **Card tutta cliccabile senza rompere lo swipe**: link "stirato" sul titolo (`data-card-link`); `SwipeToArchive` accetta l'avvio del gesto anche da lì, prende la pointer capture solo quando il movimento è orizzontale (un tocco semplice resta un click sul link) e annulla il click generato a fine swipe (non si apre il dettaglio per errore).
- **Ricerca di provenienza** non è più sulla card (è nel dettaglio, come nel mockup `desk-detail`).
- **Filtri nel pannello, applicazione immediata**: come prima i filtri si applicano subito e restano nella query string; "Mostra risultati" chiude il pannello, "Azzera filtri" e "Cancella" li riportano ai valori di default (date di oggi, nessun altro filtro) lasciando sezione e ricerca testuale. Il conteggio dei filtri attivi è per gruppo (date solo se diverse da oggi–oggi). Nessun "ordinamento" (citato in `SCREENS.md` ma non esistente: l'ordinamento resta fisso, §4.5).
- **Statistiche**: chiuso "nuovi oggi" = job trovati oggi (stessa metrica della Home); aperto i tre gruppi; la riga "di cui manuali" riporta oggi, settimana e totale (il mockup mostra solo il totale: tenuti tutti e tre per non perdere informazioni rispetto alla Home).
- **Raccolta**: pannello come `collect-free` **senza** il riquadro "Raccolta automatica Pro" (Sprint 77); il testo ricorda che la raccolta notturna gira comunque (vero fino allo Sprint 77). Durante l'attesa indicatore e pannello non chiudibile (`collect-running`).
- **Importati**: il mockup dice "import e inserimento manuale riservati al Pro", ma oggi l'inserimento manuale è anche dei Free (§4.15): mantenuta la regola reale; per il Free il riquadro mostra il badge PRO accanto al solo messaggio sull'import.
- **Conferma del costo** (A11): `CostConfirmDialog` sostituisce `window.confirm` **nella lista** (import, job manuale); dettaglio ed editor negli sprint 75–76. Con il massimale raggiunto e saldo insufficiente il pulsante del pannello manuale è disattivato e il motivo è scritto sotto (`DESIGN.md §5`); l'import del Pro idem.
- **Avvisi**: un solo banner per volta in cima alla colonna, prima "Nuova versione disponibile", poi "Profilo incompleto" (`DESIGN.md §5`); il banner della nuova versione non è più una pillola fissa in basso.
- **Toast** scuro (`#2b2317`) come nel mockup, a tutta larghezza su mobile, sopra la barra di tab.
- **Segnaposto della ricerca** accorciato a "Cerca titolo, azienda, località" (come nel mockup): a 360 px quello vecchio veniva troncato.

## Implementazione
### Frontend
- `pages/JobListPage.jsx` riscritta (stessa logica dati): testata con `CollectButton`, ricerca con icona, pulsante Filtri con badge, `StatsSummary` (solo Raccolti), sezioni `FilterPill`, riga filtri attivi, riquadro "Importa un job", `EmptyState`, lista di `JobCard`, `JobFiltersSheet`, `CollectJobsSheet`, `ManualJobSheet`, `Modal` "Salva filtri attuali", `costDialog`. `updateParams` accetta funzioni sul valore corrente nell'URL: corretto un difetto emerso dagli e2e, in cui più clic ravvicinati sulle pillole si annullavano a vicenda leggendo lo stato dell'ultimo render.
- Nuovi: `components/JobFiltersSheet.jsx`, `components/ManualJobSheet.jsx`, `components/StatsSummary.jsx`, `components/RecruiterIcon.jsx`, `components/CostConfirmDialog.jsx` (`useCostConfirm`), `components/SystemBanner.jsx`, `components/ui/pill.jsx` (`FilterPill`), `components/ui/segmented.jsx` (`SegmentedControl`, radio nativi), `utils/jobFilters.js`.
- Riscritti: `components/JobCard.jsx`, `components/SwipeToArchive.jsx`, `components/CollectJobsSheet.jsx` (aperto dal genitore, senza statistiche), `components/AppUpdateBanner.jsx` e `ProfileCompletionBanner.jsx` (su `ui/banner`), `components/ToastProvider.jsx` (aspetto); `lib/appUpdate.js` + `useAppUpdateAvailable`; `components/AppShell.jsx` mostra l'avviso di sistema in cima alla colonna anche nelle pagine senza navigazione; `App.jsx` usa `SystemBanner`.
- `translations.js` (it/en): titolo della lista "Jobs"; `jobs.filtersTitle`, `filtersButton`, `savedFiltersTitle`, `datesGroupTitle`, `locationGroupTitle`, `searchGroupTitle`, `showResults`, `resetFilters`, `activeFiltersOne/Many`, `clearFilters`, `gapsMoreOne/Many`, `emptyFiltered`, `importCardTitle`, `presetNamePlaceholder`; `home.statsNewToday`, `statsThisWeek`, `statsWeekShort`, `statsOpen`, `statsClose`, `statsManualLine`, `collectIntro`, `collect24h`, `collectNightly`, `collectRunningHint`, `collectLastResult`; `usage.confirmTitle`, `usage.confirmProceed`; segnaposto della ricerca accorciato.

### Backend / API
Nessun cambio.

## E2e — asserzioni cambiate
| Spec / test | Prima | Dopo |
|---|---|---|
| `job-list` › filtro punteggio, ricerca testuale, filtri nell'URL | `toggleScore` sulla tendina "Punteggio" | `toggleScore` sul pannello: `inFilters` apre "Filtri", clic sulla pillola, "Mostra risultati" |
| `job-list` › filtro stato, location, candidati | bottoni/campo in pagina | stessi controlli dentro `inFilters` |
| `job-list` › filtro recruiter | select "Recruiter" → opzione | segmento: clic sull'etichetta "Con recruiter" nel pannello |
| `job-list` › filtro ricerca multi-selezione | tendina con contatore "Ricerca (N)" | pillole "parole chiave · città" con `aria-pressed`, URL `search=…`, pulsante "Filtri (1)" |
| `job-list` › filtro preferito | pillole e "Salva filtri attuali" in pagina | nel pannello; il salvataggio apre la finestra "Salva filtri attuali"; eliminazione "Elimina filtro salvato: <nome>" |
| `job-list` › archiviare… annulla | pulsante "Archivia" sulla card | `swipeCard`; "Annulla" nel toast |
| `job-list` › swipe reale | trascinamento inline | helper `swipeCard` (stesso gesto) |
| `job-list` › generare il CV disabilita il pulsante… | "Genera CV" sulla card | dal dettaglio (`openCard`), pulsante "Genera CV" della pagina |
| `job-list` › 5 test che aprono il dettaglio | link "Dettagli" della card | `openCard`: clic sul titolo |
| `job-list` › ricerca testuale | segnaposto "Cerca per titolo, azienda, località…" | "Cerca titolo, azienda, località" |
| `auth-onboarding` › registrazione… | heading "I tuoi job" | heading "Jobs" (livello 1) |

## Verifica
- `npm run build`: OK. `npx oxlint src e2e`: 0 errori, 9 warning (gli stessi di prima; 4 warning nuovi "fast refresh" eliminati spostando costanti e hook fuori dai file dei componenti).
- **E2e** sullo stack usa e getta descritto in `sprints/sprint-73.md` (copia `/root/App-apply-dev`, immagini `appapply-e2e-*`, Postgres/Redis temporanei, `e2e_settings_local.py`, nessun codice d'invito né email, app su `localhost`): prima esecuzione 33/35 (difetto delle pillole sopra, corretto; recruiter da aggiornare), poi **35/35** due volte.
- **Screenshot** (Playwright, 360/390/1280 px, utente Pro di prova con job seed, 2 ricerche salvate, 1 filtro salvato, massimale dei job manuali esaurito nel DB di prova): lista, statistiche aperte, pannello filtri, lista filtrata con "1 filtro attivo · Cancella", pannello di raccolta, Importati, pannello manuale, finestra "Costo dell'azione" sopra il pannello, stato vuoto dei Preferiti. Larghezza del documento = schermo su lista, Importati e Preferiti alle tre larghezze; nessun errore JavaScript.
- Backend non toccato: test backend non necessari.

## Cosa manca / note
- Archiviazione da tastiera assente fino al menu ⋯ del dettaglio (Sprint 75).
- Dettaglio ed editor usano ancora `window.confirm` per i costi (sprint 75–76).
- Raccolta automatica Pro e opzione bloccata per i Free: Sprint 77 (dopo le risposte a B1–B4).
- Badge di stato della card: "Nuovo" su sfondo neutro, gli altri stati su `primary-soft` (come prima); il mockup non disegna gli altri stati.
