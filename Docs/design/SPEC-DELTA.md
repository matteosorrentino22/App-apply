# SPEC-DELTA — cambi funzionali del redesign

> Cosa cambia **nel comportamento** (non solo nella grafica) rispetto alle specifiche as-is dello Sprint 71 (`Docs/01-specifiche-funzionali-v6.md`, `Docs/02-specifiche-tecniche-v5.md`). Va recepito in 01 v7 / 02 v6 **nello stesso commit** dello sprint che lo implementa (regola `CLAUDE.md`).
> **Deciso** = concordato col committente nelle chat di design. **Da decidere** = serve una risposta prima di implementare.
>
> **Stato al 2026-11-15 (Sprint 80):** tutte le voci **A** sono implementate (sprint indicato in ogni riga) e descritte nelle specifiche 01/02 del branch `sprint-80-rifinitura`; delle voci **B** restano aperte **B8** (tema scuro ridisegnato, tablet) e **B11** (forma del messaggio di troppi tentativi); **B10** ha una proposta minima implementata, da confermare. Nulla è ancora su `main` (rilascio: `RELEASE.md`).

## A. Decisi

| # | Cambio | Specifiche toccate |
|---|---|---|
| A1 | **Navigazione a 3 voci** (Jobs · Profilo · Impostazioni). La Home (`/home`) viene eliminata; `/` e il login portano a `/list`. Statistiche e "Raccogli ora" passano in Jobs *(fatto nello Sprint 73; statistiche e raccolta in un pannello ponte della lista fino allo Sprint 74)* | 01 §4.x Home/Jobs; 02 §12 (nessuna API da rimuovere: l'API statistiche resta) |
| A2 | **"Genera CV" solo nel dettaglio del job**, con ▾ per cover letter e messaggio. Sulla card di lista non ci sono più azioni di generazione, archivio o dettagli *(fatto nello Sprint 74)* | 01 lista job, dettaglio |
| A3 | **"Colma i gap"** è un passo facoltativo che precede la generazione del CV (pannello dal basso), non una funzione separata *(fatto nello Sprint 75)* | 01 §4.x CV |
| A4 | **Raccolta automatica Pro.** Gli utenti **Pro** hanno **una raccolta automatica al giorno all'orario scelto**; **sostituisce** la raccolta notturna delle 02:00 *(fatto nello Sprint 77)* | 01 §4.14, §4.x raccolta notturna, §piani; 02 §5.1 Beat, `run_nightly_cycle`, migrazione `0003_schedule_nightly_cycle`, `CLAUDE.md` (premessa "ciclo notturno") |
| A5 | **Utenti Free: nessuna raccolta automatica, nemmeno quella delle 02:00.** Possono raccogliere **solo manualmente, 1 volta al giorno** (`COLLECTION_DAILY_LIMIT`); l'opzione automatica compare bloccata con invito al Pro. *(Confermato dal committente il 2026-11-14.)* *(fatto nello Sprint 77)* | 01 piani (oggi "la raccolta notturna è uguale per entrambi"), 01 §4.14, 02 §5.1 |
| A6 | Il raccoglitore prende **solo offerte delle ultime 24 ore** (già così oggi: resta, ma il testo in UI lo dice esplicitamente) *(testo nel pannello di raccolta, Sprint 74 e 77)* | nessuno |
| A7 | **Icona recruiter** in lista e dettaglio quando l'annuncio ha un recruiter; **2 gap principali** sulla card ("+N altri"); riga descrizione annuncio a fisarmonica; **archivio** anche dal menu ⋯ del dettaglio *(lista fatta nello Sprint 74; dettaglio e menu ⋯ fatti nello Sprint 75)* | 01 lista/dettaglio (solo presentazione) |
| A8 | **Filtri salvati** (§4.21) e **filtri in URL** (Sprint 68) restano com'è: cambia solo la presentazione (pannello + pillole) *(fatto nello Sprint 74)* | nessuno |
| A9 | **Logout spostato in Impostazioni**, con finestra di conferma (oggi è nella barra in alto) *(fatto nello Sprint 73)* | 01 account |
| A10 | **Login Google non mostrato** (il codice allauth resta, non configurato in produzione) *(verificato nello Sprint 79: il pulsante resta condizionato a `google_login_enabled`, quindi oggi non compare; nessun pulsante nei mockup)* | 01 §accesso |
| A11 | **Conferma costo in un `Modal` dell'app** al posto di `window.confirm` (Sprint 68–70) *(lista fatta nello Sprint 74, dettaglio nello Sprint 75; negli editor non c'era nessun `window.confirm` da sostituire: verificato nello Sprint 76)* | 01 §costi, 02 flussi |
| A12 | **Impostazioni a sottopagine**: Ricerche, Notifiche, Account (email, fuso, limiti, privacy, password, elimina), Lingua, Esci *(fatto nello Sprint 78: sottopagine Ricerche, Limiti di oggi, Privacy e sicurezza; pannelli per lingua del CV, email, fuso, lingua, password; notifiche e raccolta automatica come interruttori nell'elenco)* | 01 impostazioni |
| A13 | Nuovo **logo** e icone PWA (`Docs/design/logo/`) *(fatto nello Sprint 72; logo nelle pagine negli sprint 73 e 79)* | 02 PWA/manifest |
| A14 | Fuori ambito: template PDF del CV (Sprint 52–58), job con soli 3 stati stabili + transitorio, niente cache offline | — |

## B. Da decidere

| # | Domanda | Opzioni | Impatto |
|---|---|---|---|
| ~~B1~~ | ~~Pro: resta anche la manuale?~~ — **deciso (2026-11-15)**: sì, ma **condivide la stessa quota giornaliera** dell'automatica | 1 raccolta al giorno in totale, automatica o manuale | `collect-pro` mostra ancora automatica e manuale separate: vale la quota unica (nota in `sprints/sprint-77.md`) |
| ~~B2~~ | ~~L'automatica consuma `COLLECTION_DAILY_LIMIT`?~~ — **deciso (2026-11-15, corretto)**: **sì**. Ogni utente, Free o Pro, al massimo **una raccolta al giorno** (giorno di Europe/Rome, azzeramento a mezzanotte come oggi), per il costo delle chiamate Apify. Pro: se l'automatica ha già girato, "Raccogli" è bloccato con il motivo ("già eseguita oggi alle HH:MM"); se l'utente raccoglie a mano prima dell'orario, l'automatica di quel giorno è saltata (`RunLog` SKIPPED). Fallimento prima delle chiamate a pagamento: quota restituita come per la manuale | — | "I tuoi limiti di oggi": una riga "Raccolta giornaliera 0/1" |
| ~~B3~~ | ~~Fuso dell'orario scelto~~ — **deciso (2026-11-15)**: nel **fuso dell'utente** (campo esistente, Sprint 70), predefinito Europe/Rome; la quota resta sul giorno di Europe/Rome | — | casi limite (mezzanotte, cambio di fuso, ora legale) nel piano dello sprint 77 |
| ~~B4~~ | ~~Notifica mattutina delle 10:00~~ — **deciso (2026-11-15)**: ai Pro una notifica **a fine raccolta automatica** se ci sono job nuovi; **nessuna notifica delle 10:00** per nessuno (i Free non hanno raccolta automatica); restano i promemoria di inattività | — | 01 §4.12, `notifications/tasks.py`, schedule delle notifiche |
| ~~B6~~ | ~~Ritenti scoring~~ — **deciso**: a ogni raccolta, automatica o manuale (come oggi `_run_collection_cycle`); senza raccolte non si ritenta | — | `jobs/tasks.py` |
| ~~B7~~ | ~~Chip di stato nel dettaglio~~ — **deciso (Sprint 75)**: solo indicativo, senza chevron; restano i tre stati stabili + il transitorio | — | `JobDetailPage.jsx` |
| B8 | **Dark mode** e **tablet** — **aperto**. Oggi: valori scuri esistenti adattati ai token nuovi (Sprint 72), controllati nello Sprint 80 (nessun testo illeggibile; interruttore spento e pulsanti disattivati poco distinguibili); nessun layout tablet | stesso ciclo / sprint dedicato | `index.css` |
| ~~B9~~ | ~~Nuove dipendenze Radix~~ — **deciso**: nessuna dipendenza nuova (vincolo di ogni sprint); `button role="switch"`, fisarmonica, menu e `<details>` fatti in casa | — | — |
| B10 | **Notifiche push disattivate**: stato nella lista job non disegnato — **proposta minima implementata nello Sprint 80, da confermare**: nessun banner fisso nella lista (chi spegne le notifiche lo ha scelto); nel pannello di raccolta, per un Pro con l'automatica attiva e le notifiche spente, un avviso con il link a Impostazioni. In Impostazioni lo stato c'era già (Sprint 78) | banner dedicato o solo in Impostazioni | UI |
| B11 | **Testo del 429** (limite richieste, Sprint 66) — **aperto**. Oggi: "Troppi tentativi. Attendi qualche minuto e riprova." nel punto in cui avviene (riquadro del modulo, pannello o avviso) | testo in finestra o banner | i18n |

## C. Impatti collaterali da non dimenticare
- **Backend A4/A5 (fatto nello Sprint 77, `sprints/sprint-77.md`):** il ciclo notturno per **tutti** gli utenti (`run_nightly_cycle`, schedule delle 02:00) e la notifica delle 10:00 vengono rimossi; la raccolta programmata riguarda solo gli utenti Pro con raccolta automatica attiva e **consuma la stessa quota giornaliera della manuale** (B2); per i Free resta solo `run_manual_collection_for_user`. Inoltre: modello dati (abilitazione e orario per utente), task periodica che avvia le raccolte dovute, migrazioni che rimuovono le schedule delle 02:00 e delle 10:00 (`DatabaseScheduler`), test in `jobs/tests.py`, `test_sprint68.py` e `notifications`, `RunLog`, `DEPLOY.md §7`, spec 01/02 e `CLAUDE.md` (righe "Progetto", "Scheduler").
- **Privacy:** se compare un nuovo dato personale (orario scelto) va riportato in informativa, export e cancellazione (`CLAUDE.md → Sicurezza e privacy`); probabilmente basta includerlo in export/cancellazione esistenti perché già legato all'utente, ma l'informativa va controllata.
- **i18n backend (Sprint 71):** ogni nuovo messaggio d'errore o notifica in `gettext` + `.po/.mo` en.
- **e2e Playwright:** `job-list.spec.js`, `account.spec.js`, `auth-onboarding.spec.js`, `push-subscription.spec.js` dipendono da testo e struttura: vanno aggiornati con la UI.

## Punti da verificare in revisione
1. A4 cambia la premessa di `CLAUDE.md` ("ciclo notturno raccolta+scoring"): via libera del committente dato con le decisioni B1–B4 (2026-11-15); `CLAUDE.md` si aggiorna nello sprint 77.
2. I limiti numerici in `settings-limiti` sono esempi: i valori reali sono in `apps/accounts/usage.py` e nel listino.
