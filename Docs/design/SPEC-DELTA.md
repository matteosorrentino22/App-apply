# SPEC-DELTA — cambi funzionali del redesign

> Cosa cambia **nel comportamento** (non solo nella grafica) rispetto alle specifiche as-is dello Sprint 71 (`Docs/01-specifiche-funzionali-v6.md`, `Docs/02-specifiche-tecniche-v5.md`). Va recepito in 01 v7 / 02 v6 **nello stesso commit** dello sprint che lo implementa (regola `CLAUDE.md`).
> **Deciso** = concordato col committente nelle chat di design. **Da decidere** = serve una risposta prima di implementare.

## A. Decisi

| # | Cambio | Specifiche toccate |
|---|---|---|
| A1 | **Navigazione a 3 voci** (Jobs · Profilo · Impostazioni). La Home (`/home`) viene eliminata; `/` e il login portano a `/list`. Statistiche e "Raccogli ora" passano in Jobs *(fatto nello Sprint 73; statistiche e raccolta in un pannello ponte della lista fino allo Sprint 74)* | 01 §4.x Home/Jobs; 02 §12 (nessuna API da rimuovere: l'API statistiche resta) |
| A2 | **"Genera CV" solo nel dettaglio del job**, con ▾ per cover letter e messaggio. Sulla card di lista non ci sono più azioni di generazione, archivio o dettagli *(fatto nello Sprint 74)* | 01 lista job, dettaglio |
| A3 | **"Colma i gap"** è un passo facoltativo che precede la generazione del CV (pannello dal basso), non una funzione separata *(fatto nello Sprint 75)* | 01 §4.x CV |
| A4 | **Raccolta automatica Pro.** Gli utenti **Pro** hanno **una raccolta automatica al giorno all'orario scelto**; **sostituisce** la raccolta notturna delle 02:00 | 01 §4.14, §4.x raccolta notturna, §piani; 02 §5.1 Beat, `run_nightly_cycle`, migrazione `0003_schedule_nightly_cycle`, `CLAUDE.md` (premessa "ciclo notturno") |
| A5 | **Utenti Free: nessuna raccolta automatica, nemmeno quella delle 02:00.** Possono raccogliere **solo manualmente, 1 volta al giorno** (`COLLECTION_DAILY_LIMIT`); l'opzione automatica compare bloccata con invito al Pro. *(Confermato dal committente il 2026-11-14.)* | 01 piani (oggi "la raccolta notturna è uguale per entrambi"), 01 §4.14, 02 §5.1 |
| A6 | Il raccoglitore prende **solo offerte delle ultime 24 ore** (già così oggi: resta, ma il testo in UI lo dice esplicitamente) | nessuno |
| A7 | **Icona recruiter** in lista e dettaglio quando l'annuncio ha un recruiter; **2 gap principali** sulla card ("+N altri"); riga descrizione annuncio a fisarmonica; **archivio** anche dal menu ⋯ del dettaglio *(lista fatta nello Sprint 74; dettaglio e menu ⋯ fatti nello Sprint 75)* | 01 lista/dettaglio (solo presentazione) |
| A8 | **Filtri salvati** (§4.21) e **filtri in URL** (Sprint 68) restano com'è: cambia solo la presentazione (pannello + pillole) *(fatto nello Sprint 74)* | nessuno |
| A9 | **Logout spostato in Impostazioni**, con finestra di conferma (oggi è nella barra in alto) *(fatto nello Sprint 73)* | 01 account |
| A10 | **Login Google non mostrato** (il codice allauth resta, non configurato in produzione) | 01 §accesso |
| A11 | **Conferma costo in un `Modal` dell'app** al posto di `window.confirm` (Sprint 68–70) *(lista fatta nello Sprint 74, dettaglio nello Sprint 75; negli editor non c'era nessun `window.confirm` da sostituire: verificato nello Sprint 76)* | 01 §costi, 02 flussi |
| A12 | **Impostazioni a sottopagine**: Ricerche, Notifiche, Account (email, fuso, limiti, privacy, password, elimina), Lingua, Esci | 01 impostazioni |
| A13 | Nuovo **logo** e icone PWA (`Docs/design/logo/`) | 02 PWA/manifest |
| A14 | Fuori ambito: template PDF del CV (Sprint 52–58), job con soli 3 stati stabili + transitorio, niente cache offline | — |

## B. Da decidere

| # | Domanda | Opzioni | Impatto |
|---|---|---|---|
| B1 | **Pro: oltre alla raccolta automatica, resta anche la manuale?** | (a) sì, entro `COLLECTION_DAILY_LIMIT` condiviso; (b) sì, separata; (c) no | massimali, UI di `collect-pro` |
| B2 | La raccolta automatica Pro **consuma `COLLECTION_DAILY_LIMIT`**? | sì / no | contatore "Raccolta manuale 1/1" in `settings-limiti` |
| B3 | **Fuso dell'orario scelto.** Oggi tutto segue Europe/Rome; l'utente ha un campo fuso orario (Sprint 70). L'orario è nel fuso dell'utente o in Rome? | utente (consigliato) / Rome | Beat: o una task ogni 15 min che controlla gli orari, o un `PeriodicTask` per utente |
| B4 | **Notifica mattutina delle 10:00** (§4.12): con raccolta all'orario scelto va ridefinita | (a) notifica a fine raccolta se ci sono job nuovi; (b) resta alle 10:00 | 01 §4.12, `notifications/tasks.py`; nei Free non c'è più raccolta notturna → quando notificare? |
| ~~B5~~ | ~~Cosa succede ai Free~~ — **deciso (A5)**: perdono la raccolta notturna, restano con la manuale 1/giorno, senza periodo di transizione | nota nel `CHANGELOG`; testo informativo nella schermata di raccolta | — |
| B6 | **Ritenti scoring** (Sprint 68) oggi al ciclo notturno successivo | per i Free: **al prossimo "Raccogli"** (deciso, conseguenza di A5); per i Pro: sulla raccolta automatica e sul comando manuale (da confermare) | `jobs/tasks.py` |
| B7 | **Chip di stato nel dettaglio**: solo indicativo o selezionabile (vincolo "tre stati stabili") | indicativo (proposto) | chevron da togliere nel mockup |
| B8 | **Dark mode** e **tablet** | stesso ciclo / sprint dedicato | `index.css` |
| B9 | Nuove **dipendenze Radix** (switch, accordion, dropdown-menu) | nessuna (nativo) / aggiungerle | `CLAUDE.md`: chiedere prima |
| B10 | **Notifiche push disattivate**: stato nella lista job non disegnato | banner dedicato o solo in Impostazioni | UI |
| B11 | **Testo del 429** (limite richieste, Sprint 66) | testo in finestra o banner | i18n |

## C. Impatti collaterali da non dimenticare
- **Backend A4/A5:** il ciclo notturno per **tutti** gli utenti (`run_nightly_cycle`, schedule delle 02:00) viene rimosso; la raccolta programmata riguarda solo gli utenti Pro con raccolta automatica attiva; per i Free resta solo `run_manual_collection_for_user`. Inoltre: nuova schedulazione (modello dati: orario e abilitazione per utente, es. su `Profile`/`User`), task `run_scheduled_collection_for_user`, migrazione che **rimuove** la schedule delle 02:00 (`DatabaseScheduler`), test in `jobs/tests.py` e `test_sprint68.py` che oggi citano il ciclo notturno, `RunLog`, `DEPLOY.md §7` (operazione sul VPS), spec 01/02 e `CLAUDE.md` (riga "Scheduler").
- **Privacy:** se compare un nuovo dato personale (orario scelto) va riportato in informativa, export e cancellazione (`CLAUDE.md → Sicurezza e privacy`); probabilmente basta includerlo in export/cancellazione esistenti perché già legato all'utente, ma l'informativa va controllata.
- **i18n backend (Sprint 71):** ogni nuovo messaggio d'errore o notifica in `gettext` + `.po/.mo` en.
- **e2e Playwright:** `job-list.spec.js`, `account.spec.js`, `auth-onboarding.spec.js`, `push-subscription.spec.js` dipendono da testo e struttura: vanno aggiornati con la UI.

## Punti da verificare in revisione
1. A4 contraddice la premessa di `CLAUDE.md` ("ciclo notturno raccolta+scoring"): serve un via libera esplicito prima di toccare lo scheduler.
2. Le voci B1–B4 (e la parte Pro di B6) vanno chiuse **prima** dello sprint di raccolta (`IMPLEMENTATION-PLAN.md`, sprint 77); gli sprint grafici non dipendono da esse.
3. I limiti numerici in `settings-limiti` sono esempi: i valori reali sono in `apps/accounts/usage.py` e nel listino.
