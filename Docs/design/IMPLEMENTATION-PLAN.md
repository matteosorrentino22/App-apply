# IMPLEMENTATION-PLAN — sprint per l'implementazione del redesign

> Piano per Claude Code. **La numerazione parte da Sprint 72** (ultimo sprint esistente: 71; regola `CLAUDE.md`: prima di scegliere il numero guardare `git log --oneline` **e** `ls sprints/`). Ogni sprint segue il workflow di `CLAUDE.md`: file `sprints/sprint-NN.md`, specifiche in `Docs/` aggiornate **nello stesso commit**, `CHANGELOG.md`, `DEPLOY.md`/`.env.example` se cambiano deploy o variabili, test.
> Lavorare su un branch derivato da `design/redesign-ui`, mai su `main`. Nessuna nuova dipendenza senza chiedere (`CLAUDE.md`).

## Principi di lavoro
- Un tema per sprint, ogni sprint rilasciabile da solo (l'app deve restare utilizzabile a metà percorso).
- Riferimenti: `DESIGN.md` (token, componenti), `SCREENS.md` (mockup → file), `SPEC-DELTA.md` (comportamento). Dove c'è una voce **da decidere**, **fermarsi e chiedere**.
- Ogni stringa nuova in `it` **e** `en` (`translations.js`); verificare a 360/390 px e in italiano (testi più lunghi).
- Nessun font esterno; font di sistema (`DESIGN.md §3.2`). PDF del CV non toccato.
- Verifiche a ogni sprint: `npm run build` e `npm run lint` in `frontend/`, test e2e Playwright aggiornati, test backend nel container con `-e DJANGO_DEBUG=true -e REGISTRATION_INVITE_CODE=` (`DEPLOY.md §4.4`), `makemigrations --check` se tocca i modelli.

## Sprint

| Sprint | Tema | Perimetro | Chiusura |
|---|---|---|---|
| **72** ✅ | **Fondamenta** (fatto: `sprints/sprint-72.md`) | Token in `index.css` (`DESIGN.md §3.5`), raggi, ombre; restyling di `ui/button, card, badge, input, dialog, select, checkbox, radio-group, textarea`; nuovi `Sheet`, `Modal` (su Radix Dialog), `Banner`, `Field`, `ScoreChip`, `EmptyState`, `Spinner`; **nuovi asset logo** (`public/`, `vite.config.js` icone, `apple-touch-icon`); policy font verificata (nessun URL esterno nel build) | Storybook non richiesto; pagina esistenti invariate nel flusso ma con i nuovi token; build e e2e verdi |
| **73** ✅ | **AppShell e navigazione** (fatto: `sprints/sprint-73.md`) | `AppShell`, `BottomTabBar` (mobile) e barra in alto (≥ 1024 px); 3 voci; eliminazione di `HomePage` e della rotta `/home` (redirect a `/list`); `Topbar` rimossa; logout in Impostazioni con conferma **[A9 deciso]**; area sicura iOS | Navigazione identica su mobile/desktop; `auth-onboarding.spec.js` e `account.spec.js` aggiornati |
| **74** ✅ | **Lista Jobs** (fatto: `sprints/sprint-74.md`) | `JobCard` ridotta + `RecruiterIcon`, 2 gap, tutta cliccabile; `StatsSummary`; pillole; pannello filtri (`Sheet`/finestra); salva filtri; toast con "Annulla"; `EmptyState`; banner profilo incompleto / nuova versione; pulsante Raccogli che apre l'**attuale** raccolta manuale (senza cambio backend) | `job-list.spec.js` aggiornato; swipe e URL dei filtri invariati |
| **75** | **Dettaglio job** | `SplitButton` Genera CV ▾, `CounterToggle`, "Colma i gap" in `Sheet`, cover letter e messaggio in `Sheet`, `DocumentRow`, `Modal` di conferma costo (`CostConfirmDialog`) al posto di `window.confirm`, annulla candidatura, avvisi multipagina | Nessun cambio ai flussi di generazione sincrona |
| **76** | **Editor CV e cover letter** | Layout con fisarmoniche, segmento Modifica/Anteprima, chat in `Sheet` su mobile e colonna fissa a destra su desktop (`desk-editor`), `Modal` "bozza superata", avvisi AI e costi | I due editor funzionano a 390 px e ≥ 1280 px |
| **77** | **Raccolta automatica Pro e solo manuale per i Free** *(richiede B1–B4 decisi; A5 è già deciso)* | Backend: orario per utente, task di raccolta programmata **solo per i Pro con raccolta automatica attiva**, **rimozione totale del ciclo notturno delle 02:00 per tutti** (i Free non hanno più alcuna raccolta automatica: solo manuale 1/giorno), ridefinizione notifica, ritenti scoring dei Free al prossimo "Raccogli"; Frontend: `Sheet` raccolta Pro/Free con opzione bloccata; aggiornamento specifiche 01/02, `CLAUDE.md` (riga Scheduler), `DEPLOY.md §7` | Test backend aggiornati (`jobs/tests.py`, `test_sprint68.py`); informativa controllata |
| **78** | **Profilo, impostazioni, ricerche** | Profilo a fisarmoniche; `AccountPage.jsx` spezzata in sottopagine (Ricerche, Notifiche, Account: email, fuso, limiti, privacy, password, elimina); `UsageLimitsCard` restyling; istruzioni notifiche iOS | `account.spec.js` e `push-subscription.spec.js` aggiornati |
| **79** | **Accesso, onboarding, legale** | Login/registrazione (senza Google, **A10**), verifica email, password dimenticata/reset, conferma cambio email, onboarding con `Stepper`, schermata di accettazione, pagine legali a fisarmonica | `auth-onboarding.spec.js` aggiornato |
| **80** | **Rifinitura** | Verifica in `en`, 360 px, iPhone PWA da Home, contrasto; stati vuoti/errore mancanti; (se deciso **B8**) dark mode e tablet | Checklist di `DESIGN.md §1.7` |

> Gli sprint 72–76 e 78–80 sono **solo frontend** e non dipendono dalle decisioni di `SPEC-DELTA.md §B`. Lo sprint 77 è l'unico con backend.

## Istruzioni operative per ogni sprint
1. Leggere `CLAUDE.md`, `Docs/design/README.md`, `DESIGN.md`, la sezione dello sprint in `SCREENS.md` e le voci di `SPEC-DELTA.md` interessate.
2. Confrontare i mockup (`mockups/png/*.png`) con il file React indicato; implementare il **comportamento esistente** con il nuovo aspetto, senza cambiare API.
3. Aggiornare/creare `sprints/sprint-NN.md` (richiesta, decisioni, implementazione, verifica, cosa manca) e le specifiche in `Docs/` toccate, nello **stesso commit**.
4. Commit sul branch dello sprint (non su `main`); chiedere conferma prima di merge e deploy; deploy sempre da `docker-compose.prod.yml` (`CLAUDE.md`).

## Punti da verificare in revisione
1. Ordine e granularità degli sprint: 72–73 sono prerequisiti, il resto si può riordinare (es. editor prima del dettaglio).
2. Lo sprint 77 è bloccato dalle decisioni B1–B4 (A5, Free solo manuale, è deciso); si può posticipare dopo il 80 senza impatto sugli altri.
3. Sul VPS il frontend servito da `frontend_dist`: ogni sprint grafico richiede rebuild dell'immagine `frontend` (procedura in `DEPLOY.md`).
4. Se un file supera le dimensioni gestibili (`AccountPage.jsx` 677 righe, `JobDetailPage.jsx` 872, `CvDraftEditorPage.jsx` 780), spezzarlo in componenti **dentro** lo sprint di competenza, non prima.
