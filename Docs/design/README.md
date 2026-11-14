# Redesign UI di App-apply — documentazione di design

> **Stato:** proposta di design, **non ancora implementata**. Le specifiche in `Docs/01…03` descrivono l'app **as-is** e restano il riferimento finché uno sprint non le aggiorna (regola in `CLAUDE.md`).
> **Data:** 2026-11-14 · **As-is di partenza:** Sprint 71 (branch `design/redesign-ui`, mai su `main`).

## Obiettivo
Rendere l'app più semplice e pulita: ogni schermata mostra in primo piano solo ciò che serve a decidere, il resto è a un tocco (accordion, pannelli, menu). Ispirazioni: Revolut (numeri grandi, gerarchia chiara), Booking (filtri e liste dense ma leggibili). **Mobile e desktop sono ugualmente importanti**: il telefono (anche PWA sulla Home di iPhone) è l'uso principale; il desktop usa la stessa colonna singola con più respiro e, nell'editor CV, la chat AI accanto al documento. Tavolozza sabbia/bruno con sfondo più chiaro.

## Come leggere questa cartella (in ordine)
1. `mockups/index.html` — galleria di tutte le **71 schermate** (68 mobile + 3 desktop; immagini 2× + HTML apribile nel browser) più 6 tavole del logo.
2. `DESIGN.md` — principi, layout mobile/desktop, token (e traduzione in Tailwind/shadcn), politica font, logo, regole it/en, componenti da creare, convenzioni. Asset del logo in `logo/`.
3. `SCREENS.md` — schermata per schermata: cosa mostra, a quale route/file React corrisponde oggi, cosa cambia.
4. `SPEC-DELTA.md` — **cambi funzionali** (non solo grafici) da recepire nelle specifiche 01/02 prima o durante l'implementazione.
5. `IMPLEMENTATION-PLAN.md` — piano a sprint per Claude Code, con ordine, perimetro e criteri di chiusura.

## Regole per chi implementa
- I mockup sono il **riferimento visivo e di comportamento**, non pixel-perfect: i valori esatti (colori, raggi, spaziature) sono in `DESIGN.md`.
- I testi dei mockup sono in italiano; l'app supporta `it`/`en`: ogni nuova stringa va in **entrambe** le lingue in `frontend/src/i18n/translations.js`.
- **Ambito:** il template PDF del CV (Sprint 52–58, `Docs/03`) è **fuori** dal redesign. Nessun font o risorsa da servizi esterni (Sprint 66): vedi `DESIGN.md §3.2`.
- Dati nei mockup: segnaposto. Nomi e contenuto del CV sono inventati (il repository è pubblico, `CLAUDE.md`); le offerte di lavoro mostrate sono annunci pubblici usati solo come esempio.
- Rispettare `CLAUDE.md`: niente dipendenze nuove senza chiedere (l'elenco di quelle candidate è in `DESIGN.md §6`), niente stati del job oltre ai tre stabili, documentazione as-is nello stesso commit dello sprint.
- Dove un mockup contraddice una specifica o un vincolo di `CLAUDE.md`, vale quanto scritto in `SPEC-DELTA.md` solo se marcato **deciso**; i punti marcati **da decidere** vanno chiesti al committente.

## Come sono stati prodotti i mockup
Generati da uno script (HTML statico, nessuna dipendenza) a partire dai token di `DESIGN.md`; le immagini in `mockups/png/` sono rese a 2× con Chrome headless. Sono sorgenti di riferimento, non codice da riusare. Le stesse tavole sono su un canvas di design condiviso con il committente (non nel repository).

## Punti da verificare in revisione
- Nessuno dei file in questa cartella è stato ancora validato dal committente nella sua forma finale su repo: sono la bozza per la revisione.
- Il redesign **cambia comportamenti funzionali** (raccolta automatica Pro che sostituisce quella notturna, Home eliminata): vedi `SPEC-DELTA.md`, voci **da decidere**.
- Layout tablet, dark mode e versione inglese non sono disegnati (`DESIGN.md §7`).
