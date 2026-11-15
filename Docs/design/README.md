# Redesign UI di App-apply — documentazione di design

> **Stato (2026-11-15, Sprint 81): implementato** negli sprint 72–80 e corretto nello Sprint 81 dopo la prova su iPhone (`IMPLEMENTATION-PLAN.md`), su branch derivati uno dall'altro (`sprint-72-fondamenta` … `sprint-81-correzioni`), **non ancora su `main`** né in produzione. Le specifiche in `Docs/01…03` descrivono già l'app con il redesign (as-is del branch `sprint-81-correzioni`); il rilascio è descritto in `RELEASE.md`.
> **Data della proposta:** 2026-11-14 · **As-is di partenza:** Sprint 71 (branch `design/redesign-ui`).

## Obiettivo
Rendere l'app più semplice e pulita: ogni schermata mostra in primo piano solo ciò che serve a decidere, il resto è a un tocco (accordion, pannelli, menu). Ispirazioni: Revolut (numeri grandi, gerarchia chiara), Booking (filtri e liste dense ma leggibili). **Mobile e desktop sono ugualmente importanti**: il telefono (anche PWA sulla Home di iPhone) è l'uso principale; il desktop usa la stessa colonna singola con più respiro e, nell'editor CV, la chat AI accanto al documento. Tavolozza sabbia/bruno con sfondo più chiaro.

## Come leggere questa cartella (in ordine)
1. `mockups/index.html` — galleria di tutte le **71 schermate** (68 mobile + 3 desktop; immagini 2× + HTML apribile nel browser) più 6 tavole del logo.
2. `DESIGN.md` — principi, layout mobile/desktop, token (e traduzione in Tailwind/shadcn), politica font, logo, regole it/en, componenti da creare, convenzioni. Asset del logo in `logo/`.
3. `SCREENS.md` — schermata per schermata: cosa mostra, a quale route/file React corrisponde oggi, cosa cambia.
4. `SPEC-DELTA.md` — **cambi funzionali** (non solo grafici) da recepire nelle specifiche 01/02 prima o durante l'implementazione.
5. `IMPLEMENTATION-PLAN.md` — piano a sprint per Claude Code, con ordine, perimetro e criteri di chiusura (tutti ✅).
6. `RELEASE.md` — rilascio su `main` e in produzione dei branch 72→81: backup, variabili, migrazioni, deploy, controlli, ripristino, anteprima (Sprint 80).

## Regole per chi implementa
- I mockup sono il **riferimento visivo e di comportamento**, non pixel-perfect: i valori esatti (colori, raggi, spaziature) sono in `DESIGN.md`.
- I testi dei mockup sono in italiano; l'app supporta `it`/`en`: ogni nuova stringa va in **entrambe** le lingue in `frontend/src/i18n/translations.js`.
- **Ambito:** il template PDF del CV (Sprint 52–58, `Docs/03`) è **fuori** dal redesign. Nessun font o risorsa da servizi esterni (Sprint 66): vedi `DESIGN.md §3.2`.
- Dati nei mockup: segnaposto. Nomi e contenuto del CV sono inventati (il repository è pubblico, `CLAUDE.md`); le offerte di lavoro mostrate sono annunci pubblici usati solo come esempio.
- Rispettare `CLAUDE.md`: niente dipendenze nuove senza chiedere (l'elenco di quelle candidate è in `DESIGN.md §6`), niente stati del job oltre ai tre stabili, documentazione as-is nello stesso commit dello sprint.
- Dove un mockup contraddice una specifica o un vincolo di `CLAUDE.md`, vale quanto scritto in `SPEC-DELTA.md` solo se marcato **deciso**; i punti marcati **da decidere** vanno chiesti al committente.

## Come sono stati prodotti i mockup
Generati da uno script (HTML statico, nessuna dipendenza) a partire dai token di `DESIGN.md`; le immagini in `mockups/png/` sono rese a 2× con Chrome headless. Sono sorgenti di riferimento, non codice da riusare. Le stesse tavole sono su un canvas di design condiviso con il committente (non nel repository).

## Stato al rilascio (Sprint 80)
- I mockup sono stati seguiti come riferimento di comportamento; le differenze rimaste sono elencate per area in `SCREENS.md §8` (con il motivo) e nelle schede `sprints/sprint-72.md` … `sprint-80.md`.
- Decisioni ancora **aperte** (`SPEC-DELTA.md §B`): **B8** tema scuro ridisegnato e layout tablet (oggi: valori scuri esistenti adattati ai token nuovi, nessun layout tablet), **B11** forma del messaggio di troppi tentativi (oggi testo nel punto in cui avviene l'errore). **B10** ha una proposta minima implementata nello Sprint 80, da confermare.
- Stati non disegnati aggiunti nello Sprint 80 con soluzioni minime: errore di rete all'avvio e nelle pagine legali, pagina non trovata, notifiche disattivate con la raccolta automatica attiva (`SCREENS.md §8`).
- Non verificabili senza un iPhone vero: area sicura (notch, indicatore Home), `100dvh`, tastiera sopra la chat degli editor, notifiche push dalla Home.
