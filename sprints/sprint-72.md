# Sprint 72 — Redesign UI: fondamenta (token, componenti, logo)

> **Periodo:** 2026-11-14 · **Branch:** `sprint-72-fondamenta` (da `design/redesign-ui`, mai su `main`) · **Stato:** implementato e verificato su uno stack di prova; **merge e deploy non fatti** (in attesa dell'ok del committente).

## Input
Richiesta del committente: implementare il redesign UI documentato in `Docs/design/` (`README.md`, `DESIGN.md`, `SCREENS.md`, `SPEC-DELTA.md`, `IMPLEMENTATION-PLAN.md`, mockup in `Docs/design/mockups/`, logo in `Docs/design/logo/`), uno sprint alla volta, a partire dallo Sprint 72 "Fondamenta": token in `index.css` come in `DESIGN.md §3.5`, restyling di `components/ui/`, nuovi `Sheet`/`Modal`/`Banner`/`Field`/`ScoreChip`/`EmptyState`/`Spinner`, asset del logo (`public/`, icone in `vite.config.js`, apple-touch-icon). Regole: comportamento esistente invariato, nessuna API né backend toccati, nessuna dipendenza nuova, solo font di sistema, PDF del CV escluso, ogni stringa nuova in it ed en con verifica a 360 e 390 px.

## Decisioni prese
- **Nessuna dipendenza nuova**: `Sheet` e `Modal` sono costruiti su `@radix-ui/react-dialog`, già presente; le animazioni sono keyframe CSS in `index.css` (nessun plugin `tw-animate`), disattivate con `prefers-reduced-motion`.
- **Tema scuro**: non ridisegnato (`DESIGN.md §7`, `SPEC-DELTA.md` B8 ancora da decidere). Restano i valori scuri esistenti; ai token nuovi è stato dato solo un equivalente scuro coerente, così nessuna superficie resta chiara su sfondo scuro.
- **Scala dei raggi**: aggiunti i raggi per ruolo (`rounded-card/-button/-field/-modal/-sheet`) senza togliere la scala storica `rounded-sm…xl`, ancora usata dalle pagine che verranno ridisegnate negli sprint 73–79.
- **Bottoni ad altezza minima** (non fissa) e testo che può andare a capo (`DESIGN.md §3.6`). Taglie: `default` 44 px (bersaglio minimo), `sm` 36 px per le azioni dentro righe e card già esistenti, `lg` 52 px per l'azione primaria, `icon` 44 px. Nuova variante `text` (azioni tipo "Annulla" dei mockup). Il `secondary` usa ora testo bruno come nei mockup.
- **Campi** a 48 px con testo a 16 px: oltre a seguire il mockup, evita lo zoom automatico di iOS sui campi con testo più piccolo.
- **Punteggio**: invariata la logica a fasce di `utils/scoreStyle.js` (7–8 oliva, 9–10 verde, come chiede `DESIGN.md §3.1` nonostante l'imprecisione dei mockup); cambiano solo i colori.
- **Logo nelle pagine** (schermate di accesso, barra desktop): rimandato agli sprint che le ridisegnano (73, 79). In questo sprint solo favicon, icone PWA e apple-touch-icon.
- **`viewport-fit=cover` e area sicura della barra**: rimandati allo Sprint 73 (`AppShell`), perché con la barra attuale il contenuto finirebbe sotto la status bar dell'iPhone in modalità standalone. I componenti nuovi (`SheetFooter`) hanno già il padding con `env(safe-area-inset-bottom)`, che vale 0 finché il viewport non lo abilita.

## Implementazione
### Frontend — token (`src/index.css`)
- Valori di `DESIGN.md §3.1`: `--background #fdfbf7`, `--card #ffffff`, `--muted-foreground #6f6350`, `--primary-soft #f3e8d6`, `--border #ebe2d1`, `--input #e0d4bd`, `--success #2f6a45`.
- Token nuovi (utility `bg-tint`, `text-destructive-text`, ecc.): `tint`, `note` (+ `note-border`, `note-foreground`), `chip` (+ `chip-foreground`), `destructive-text`, `destructive-border`, `success-border`, `label` (etichette dei campi, `#4a3a26`), `overlay`, `grabber`.
- Colori del punteggio (testo/sfondo per fascia): 5 `#2f6a45`/`#e7f1e9`, 4 `#566b22`/`#eef2de`, 3 `#7a6212`/`#f7f0da`, 2 `#8a4f17`/`#fbf1e6`, 1 `#9a3a30`/`#fbeeea`.
- Raggi `--radius-card 16`, `-button 14`, `-field 12`, `-modal 20`, `-sheet 24`; ombre `--shadow-card`, `-popover`, `-modal`, `-toast` (`DESIGN.md §3.3`).
- Keyframe di dissolvenza, scorrimento dal basso e comparsa (`.app-overlay`, `.app-modal`, `.app-sheet`): animano solo `transform`, perché la centratura di Tailwind v4 usa la proprietà `translate`.

### Frontend — componenti (`src/components/ui/`)
- **Restyling**: `button`, `card` (raggio 16, ombra leggera, padding 16/20), `badge` (+ varianti `success`, `destructive`; `neutral` su `chip`), `input`, `textarea`, `select` (48 px, menu con ombra `popover` e voci da 44 px), `checkbox` (24 px), `radio-group` (20 px), `label` (13/600), `dialog` (stessa API: overlay sabbia, raggio 20, ✕ da 44 px con etichetta tradotta).
- **Nuovi**:
  - `modal.jsx`: finestra centrale (`Modal`, `ModalContent`, `ModalTitle`, `ModalDescription`, `ModalActions`, `ModalClose`), azioni impilate, larghezza max 420 px, margini 20 px su mobile.
  - `sheet.jsx`: pannello dal basso (`Sheet`, `SheetContent`, `SheetHeader` con maniglia, titolo e ✕, `SheetBody` scorrevole, `SheetFooter` con bordo e area sicura); da 1024 px finestra centrale di 480 px.
  - `banner.jsx`: varianti `info`, `note`, `error` (`role="alert"`), `success`; icona, titolo e azione facoltativi.
  - `field.jsx`: etichetta + controllo + suggerimento/errore, collega `id`, `aria-describedby`, `aria-invalid`.
  - `score-chip.jsx`: 44 px (`md`) o 56 px (`lg`), "–" se manca il punteggio, etichetta accessibile.
  - `empty-state.jsx`, `spinner.jsx` (anello come nei mockup; `framed` = cerchio da 56 px).
- I componenti nuovi non sono ancora usati dalle pagine: li adottano gli sprint 73–80.

### Frontend — logo e icone
- `public/favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`, `pwa-192x192.png`, `pwa-512x512.png`, `pwa-maskable-512x512.png` da `Docs/design/logo/`; `index.html` con favicon PNG e `<link rel="apple-touch-icon">`; manifest con l'icona `maskable` e `background_color #fdfbf7`. Gli SVG del logo non contengono riferimenti esterni (verificato).

### Frontend — correzioni di impaginazione
- **Barra in alto** (`App.jsx`, `Topbar`): va a capo sugli schermi stretti. Su `main` **tutte le pagine autenticate sbordano già in orizzontale** a 360 e 390 px (larghezza documento 472 px), perché le 4 voci, il selettore della lingua e il pulsante "Esci" aggiunto nello Sprint 70 non stanno su una riga. La barra sarà sostituita da `AppShell` nello Sprint 73.
- **Lista job** (`JobListPage.jsx`): righe delle date e delle sezioni con `flex-wrap`, perché i campi data più alti e larghi (testo 16 px) non stavano più a 360 px.
- Aggiunte a `translations.js` (it/en): `common.close`, `common.cancel`, `common.scoreLabel`, `common.scoreNone`.

## Verifica
- `npm run build`: OK; bundle senza risorse esterne (nessun font, CDN o `@import` remoto: gli unici URL sono link testuali e messaggi d'errore delle librerie).
- Lint: `npx oxlint src` → 0 errori, 9 warning (gli stessi di prima). Nota: `npm run lint` lanciato dentro l'immagine Docker del frontend analizza anche `node_modules` e `dist` (lì manca il `.gitignore` del repository), quindi va eseguito da un checkout o limitato a `src`.
- **Stack di prova usa e getta** (rete Docker dedicata, Postgres e Redis temporanei, backend dell'immagine di produzione con `DEBUG=true`, dev server Vite del branch; produzione non toccata), utente e job da `seed_e2e_jobs`, screenshot con Playwright 1.62 (immagine `mcr.microsoft.com/playwright`) a 360, 390 e 1280 px:
  - vetrina temporanea dei componenti (non nel repository): banner, bottoni con etichetta lunga, badge, chip del punteggio 1–10, card, campi con suggerimento ed errore, select, checkbox, radio, spinner, stato vuoto, `Modal`, `Sheet` (pannello su mobile, finestra a 1280), `Dialog`;
  - pagine esistenti: login, registrazione, informativa, lista, dettaglio, impostazioni, profilo.
- **Larghezza del documento** (scrollWidth) misurata con sessione autenticata: `main` 472 px su tutte le pagine a 360 e 390; branch 360/390 su lista, impostazioni, profilo, informativa, dettaglio.
- **e2e Playwright**: nessun test toccato (lo sprint non cambia testi, etichette né struttura). La suite non è stata eseguita: presuppone un ambiente di sviluppo locale (`backend/.venv`, Postgres su `localhost`) che sul VPS non c'è.
- Backend non toccato: test backend non necessari.

## Cosa manca / note
- Le pagine adottano i nuovi componenti dagli sprint 73–80; fino ad allora convivono stile nuovo (token) e struttura vecchia.
- Tema scuro e tablet non ridisegnati (`SPEC-DELTA.md` B8).
- Per eseguire gli e2e sul VPS servirebbe un'immagine di test con Python e browser, oppure un adattamento degli helper di `e2e/*.spec.js` (che chiamano `backend/.venv/bin/python manage.py seed_e2e_jobs`): da decidere col committente.
- Deploy: solo frontend (`docker compose -f docker-compose.prod.yml build frontend-build` e `up -d`), nessuna migrazione né variabile nuova; da fare solo dopo l'ok e il merge.
