# DESIGN — principi, token e componenti

> Riferimento per il redesign. I valori sono quelli usati nei mockup (`mockups/html/*.html`). **Stato: proposta**, da recepire in `frontend/src/index.css` e nei componenti (`IMPLEMENTATION-PLAN.md`). Aggiornato al 2026-11-14 sull'as-is dello **Sprint 71**.

## 1. Principi
1. **Una decisione per schermata.** In primo piano solo ciò che serve a decidere; il resto dietro un tocco (accordion, pannello dal basso, menu).
2. **Un'azione primaria per schermata**, sempre nello stesso posto (barra fissa in basso quando l'azione è "il passo successivo").
3. **Icone con etichetta** per le azioni frequenti; solo icona (con `aria-label`) per quelle secondarie (modifica, scarica, preferito).
4. **Mobile-first, colonna singola.** Nessun layout a due colonne: su desktop la stessa colonna è centrata con più respiro.
5. **Tutta la card è cliccabile** quando porta a un dettaglio (link "stirato" sul titolo); i controlli interni (cuoricino) restano separati.
6. **Niente testo lungo aperto per default**: troncare (2–3 righe) con "Leggi tutto", contare con un numero tappabile ("7 corrispondenze", "1 gap").
7. **Accessibilità minima:** bersagli ≥ 44×44 px, testo ≥ 4.5:1, controlli veri (`button`, `a`, `input`, `label`), `aria-expanded` su accordion e contatori, `role="switch"` sugli interruttori, `role="dialog"` su pannelli e finestre.

## 2. Layout e navigazione
- **Navigazione a 3 voci: Jobs · Profilo · Impostazioni.** La Home (`/home`) viene eliminata: statistiche e "Raccogli ora" passano in Jobs. L'app si apre su Jobs (`/list`).
- **Mobile (< 768px):** barra di tab in basso (icona + etichetta, voce attiva in colore primario), con area sicura iPhone (`env(safe-area-inset-bottom)`) perché la PWA gira anche dalla Home di iOS.
- **Desktop (≥ 1024px, disegnato in `desk-jobs`, `desk-detail`, `desk-editor`):** barra in alto a tutta larghezza con logo + wordmark "App-apply", le stesse 3 voci come pillole (voce attiva su `--primary-soft`) e il selettore lingua a destra. Il **logout non è nella barra**: sta in Impostazioni (decisione di design, da confermare: oggi è nella barra in alto).
- **Colonna centrale:** liste, dettagli, impostazioni e profilo usano una colonna singola di **640 px**, centrata, con più respiro verticale (28 px sopra). Fa eccezione l'**editor CV/cover letter**: due aree affiancate (contenuto flessibile + chat AI fissa di 400 px, gap 24 px, larghezza massima 1112 px). Su mobile la chat torna a pannello dal basso.
- **Tablet (768–1023 px):** non disegnato; si assume il layout mobile con colonna centrata (max 640 px) e barra di tab in basso.
- **Barra azione fissa in basso** (`ActionBar`) nelle schermate di dettaglio ed editor: sostituisce la barra di tab. Bordo superiore, sfondo bianco, padding inferiore 28px (area sicura). Su desktop è a tutta larghezza con contenuto allineato alla colonna (640 px) o all'editor (1112 px).
- **Pannello dal basso** (`Sheet`) per: filtri, raccolta, generazione (gap, cover letter, messaggio), nuova ricerca, assistente AI (mobile), inserimento manuale job. **Finestra centrale** (`Modal`) per conferme e salvataggi brevi (salva filtri, elimina, esci, conferma di un costo, annulla candidatura, bozza superata). Su desktop gli `Sheet` diventano finestre centrali larghe 480 px (stesso contenuto).
- **Impostazioni a sottopagine** (progressive disclosure): l'elenco mostra gruppi di righe con valore a destra e chevron; ogni riga complessa (limiti di oggi, email, fuso orario, privacy e sicurezza, password, elimina account) apre una sottopagina con ← Impostazioni.
- **Testi legali** (informativa, termini): sezioni a fisarmonica; titoli reali delle 12 sezioni della privacy e delle 11 dei termini (`frontend/src/legal/`).
- Il selettore lingua esce dalla testata e va in Impostazioni (resta in alto solo in login/registrazione e nella barra desktop).

## 3. Token

### 3.1 Colori (variabili CSS in `index.css`)
Stessa famiglia sabbia + bruno; **cambia solo lo sfondo (più chiaro, card bianche)** e qualche testo scurito per il contrasto.

| Token | Oggi | Proposto | Uso |
|---|---|---|---|
| `--background` | `#fbf8f2` | `#fdfbf7` | sfondo pagina |
| `--card` | `#fbf8f2` | `#ffffff` | card, barre, pannelli |
| `--foreground` | `#2b2317` | invariato | testo |
| `--muted-foreground` | `#7c6f58` | `#6f6350` | testo secondario (≥ 4.5:1 su bianco) |
| `--primary` | `#6b4a2e` | invariato | azione primaria, voce attiva |
| `--primary-soft` | `#f1e1c8` | `#f3e8d6` | badge "primary", icone in riquadro |
| `--border` | `#e2d5be` | `#ebe2d1` | bordi card, separatori |
| `--input` | `#cbb58c` | `#e0d4bd` | bordi campi e bottoni secondari |
| `--secondary` / `--muted` | `#f3ecdf` | invariato | pillole non attive, segmenti |
| `--success` | `#3e7a52` | `#2f6a45` | testo su `--success-soft` |
| `--success-soft` | `#e7f1e9` | invariato | badge "primi 25 candidati", documenti pronti |
| `--destructive` | `#b3473c` | invariato | icone gap, cuoricino pieno, "Elimina/Esci" |
| `--destructive-soft` | `#fbeeea` | invariato | contatore gap, errori |
| **nuovo** `--destructive-text` | — | `#9a3a30` | testo su `--destructive-soft` |
| **nuovo** `--tint` | — | `#f8f3e9` | blocco "Da colmare", riga selezionata, bolla proposta |
| **nuovo** `--note` | — | `#f7efe0` | riquadri informativi (nota 24 ore, invito Pro) |
| **nuovo** `--chip` / `--chip-foreground` | — | `#f1e8d8` / `#5a4a36` | badge neutri (stato "Nuovo", ricerca di provenienza) |
| overlay | — | `rgba(43,35,23,0.5)` | sfondo di pannelli e finestre |

**Punteggio (chip 44×44, 56×56 nel dettaglio).** Si mantiene la logica esistente a fasce da 2 valori (`utils/scoreStyle.js`, `ceil(score/2)`); cambiano solo i colori per il contrasto:
| Fascia (punteggio) | Sfondo | Testo |
|---|---|---|
| 5 (9–10) | `#e7f1e9` | `#2f6a45` |
| 4 (7–8) | `#eef2de` | `#566b22` |
| 3 (5–6) | `#f7f0da` | `#7a6212` |
| 2 (3–4) | `#fbf1e6` | `#8a4f17` |
| 1 (1–2) | `#fbeeea` | `#9a3a30` |

> Attenzione: nei mockup il punteggio 8 è disegnato in verde (fascia 5) e il 7 in oliva: è un'imprecisione del mockup. **In implementazione vale la fascia esistente** (7–8 oliva, 9–10 verde).

### 3.2 Tipografia
**Politica font (vincolo, Sprint 66):** nessun servizio esterno (Google Fonts, CDN di font, `@import` remoti). Si mantiene lo **stack di sistema** già in `index.css` (`-apple-system, BlinkMacSystemFont, "Segoe UI", "Segoe UI Variable", Roboto, …`): zero byte da caricare, nessun dato verso terzi, rendering nativo su iOS/Android/desktop. Se in futuro si vorrà un font di marca, va **incluso nel repository** (`frontend/src/assets/fonts/`, WOFF2, `@font-face` con `font-display: swap`) e servito da Caddy/Vite dal nostro dominio; mai da un fornitore terzo. Il wordmark "App-apply" usa lo stesso stack (peso 700, `letter-spacing −0.02em`). Scala:
| Ruolo | Dimensione / peso |
|---|---|
| Titolo pagina (Jobs, Impostazioni, Profilo) | 28 / 700, `letter-spacing −0.02em` |
| Titolo dettaglio job | 24 / 700 |
| Titolo editor / pannello | 22 / 700 · 20 / 700 |
| Titolo card | 16 / 650 |
| Corpo | 15 / 400, interlinea 1.5 |
| Secondario (azienda · località, sottotitoli) | 14 / 400, `--muted-foreground` |
| Didascalia, badge, stato | 12–13 (badge 11 / 600) |
| Etichetta di sezione (overline) | 12 / 700, maiuscolo, `letter-spacing 0.06em`, `--muted-foreground` |
| Numeri in evidenza (riepilogo) | 26 / 700 (statistiche aperte 24) |

### 3.3 Spaziature, raggi, ombre
- Margine pagina 16px; padding card 16px; spazio tra card/sezioni 14–16px; spazio interno ai blocchi 12px.
- Raggi: card 16 · bottone primario 14 · campi/segmenti/bottoni piccoli 12 · pillole e badge 999 · chip punteggio 12 (16 nel dettaglio) · pannello dal basso 24 (solo sopra) · finestra 20.
- Ombre: card `0 1px 2px rgba(43,35,23,.04)` · menu/popover `0 12px 32px rgba(43,35,23,.16)` · finestra `0 16px 40px rgba(43,35,23,.25)` · toast `0 10px 28px rgba(43,35,23,.30)`.
- Altezze: bottone primario 52 (44 nelle azioni secondarie dentro pannelli) · campo 48 · pillola 36 · barra di tab ≈ 64 + area sicura.

### 3.4 Logo e icona dell'app
- **Concetto:** due spirali che si cercano e si incontrano in un'unica linea continua (candidato e hiring manager). Proposta scelta dal committente: **n. 1 "Incontro"** (linea singola, spessore costante). Alternative scartate in `mockups/html/logo2…5.html`.
- **Geometria:** generata da due spirali di 1,45 giri raccordate da una curva; spessore del tratto = 20% del lato; margine 3% (marchio) / 20% (icona su tessera).
- **Colori:** marchio `#6b4a2e` su sfondo chiaro; `#fdfbf7` su tessera `#6b4a2e` (icona app, favicon). Non usare altre tinte né sfumature.
- **File in `logo/`:** `logo-mark.svg` (+ `-light`), `logo-lockup.svg` (marchio + "App-apply"), `app-icon.svg`, `app-icon-maskable.svg` (area sicura 27%), `favicon.svg`, e PNG pronti: `pwa-192x192.png`, `pwa-512x512.png`, `pwa-maskable-512x512.png`, `apple-touch-icon-180.png`, `favicon-32.png`, `app-icon-1024.png`, `logo-mark-512.png`.
- **Dove si usa:** icone PWA (`frontend/public/pwa-*.png`, `favicon.svg`, voce `icons` di `vite.config.js` incluso `purpose: maskable`), `<link rel="apple-touch-icon">` in `index.html`, schermate di accesso (marchio 34 px + wordmark), barra desktop.
- **Limite noto:** il testo del lockup è un `<text>` SVG con lo stack di sistema (non convertito in tracciati): per usi di stampa va vettorializzato con un font scelto.

### 3.5 Traduzione in Tailwind v4 / shadcn
L'app usa Tailwind v4 con token dichiarati in `frontend/src/index.css` (`:root` + `@theme inline`) e componenti shadcn in `components/ui/`. I nuovi token si aggiungono **nello stesso modo**, senza `tailwind.config.js` e senza nuove librerie:

```css
:root {
  --background: #fdfbf7;  --card: #ffffff;  --muted-foreground: #6f6350;
  --primary-soft: #f3e8d6; --border: #ebe2d1; --input: #e0d4bd;
  --success: #2f6a45;
  --destructive-text: #9a3a30; --tint: #f8f3e9; --note: #f7efe0;
  --chip: #f1e8d8; --chip-foreground: #5a4a36;
  --overlay: rgb(43 35 23 / 0.5);
}
@theme inline {
  --color-primary-soft: var(--primary-soft);
  --color-destructive-text: var(--destructive-text);
  --color-tint: var(--tint);  --color-note: var(--note);
  --color-chip: var(--chip);  --color-chip-foreground: var(--chip-foreground);
}
```
Così si possono usare `bg-tint`, `text-destructive-text`, `bg-note`, `bg-chip` come le altre utility shadcn. I valori del dark mode esistente vanno rivisti (vedi §7). Raggi: oggi `--radius: 0.625rem` (10 px); i mockup usano 16 (card), 14 (bottone), 12 (campi), 20 (finestra), 24 (pannello): definire `--radius-card/-button/-field/-modal/-sheet` e usarli nei componenti (`Card`, `Button`, `Input`, `Dialog`, `Sheet`) invece di valori fissi sparsi.

### 3.6 Due lingue (it / en)
- Ogni stringa nuova va in **entrambe** le lingue in `frontend/src/i18n/translations.js`. L'italiano è mediamente **+20–30%** più lungo dell'inglese: i mockup sono in italiano proprio per questo (caso peggiore).
- Regole di tenuta: pulsanti a larghezza flessibile con `min-height` (mai altezza fissa su testo), etichette di bottone ≤ 2 righe, `min-width: 0` nei contenitori flex per far andare a capo il testo, niente testo dentro icone-pillola a larghezza fissa, contatori e numeri su riga propria (`white-space: nowrap`) con etichetta che può andare a capo (esempio: "7 corrispondenze" / "1 gap" nel dettaglio).
- Etichette lunghe note da verificare in en e it: "Massimale raggiunto", "Oltre il massimale", "Ogni messaggio costa 0,20 € di credito", "Incluso nel piano: ne restano X su Y oggi", titoli delle sezioni legali. Controllare a 360 px (iPhone SE) e 390 px.
- Testi dal backend: arrivano già localizzati (`Accept-Language`, Sprint 71); il frontend non li ritraduce.

### 3.7 Mobile e PWA iPhone
- Il progetto viene usato soprattutto da telefono, anche installato sulla Home di iOS: i mockup mobili (390 × altezza variabile) sono il riferimento primario, il desktop ne è l'adattamento.
- Schermate prioritarie: **lista job**, **dettaglio job**, **editor CV con chat**. Nell'editor mobile la chat è un pannello dal basso (`Sheet`) richiamato da un pulsante "Assistente"; su desktop è la colonna fissa a destra.
- Area sicura iOS: padding inferiore con `env(safe-area-inset-bottom)` su barra di tab e barra azione; `viewport-fit=cover` nel meta viewport; altezza con `100dvh` (non `100vh`) per le finestre a tutta altezza.
- Bersagli ≥ 44 px, nessun hover come unica via d'accesso; swipe per archiviare resta (`SwipeToArchive`).
- Fuori ambito di questo redesign: **template PDF del CV** (Sprint 52–58, ha uno stile proprio definito in `Docs/03`). Non va toccato salvo richiesta esplicita.

## 4. Icone
Si resta su `lucide-react` (già in uso). Usate nei mockup: `Search, SlidersHorizontal, RefreshCw, ChevronDown/Up/Left/Right, Heart, Briefcase, User/UserRound, Settings, Minus, Check, ArrowUpRight, MoreHorizontal, Sparkles, FileText, MessageSquare, Pencil, Download, Clock, Lock, Archive, X, Plus, Trash2, Bell, Globe, Image, Upload, LogOut, ArrowUp, Calendar, MapPin, Link, Save, Send, Share`.

## 5. Convenzioni di interazione
- **Card job:** tutta cliccabile → dettaglio. Cuoricino = preferito. Swipe = archivia (resta, con toast "Job archiviato · Annulla"). Nessun bottone "Dettagli/Archivia/Genera CV" sulla card.
- **Icona recruiter** (`UserRound` in cerchietto `--primary-soft`) accanto alla località, in lista e nel dettaglio, quando l'annuncio ha un recruiter; link al profilo se disponibile (come oggi).
- **Stato del job:** i tre stati stabili + il transitorio (CLAUDE.md). Il chip di stato nel dettaglio è **solo indicativo**; si passa a "Candidatura fatta" con il bottone nella barra azione (nel mockup il chip mostra una freccia: da eliminare, vedi §8).
- **Contatori espandibili** ("7 corrispondenze", "1 gap"): mostrano il numero, il tocco espande la lista.
- **Genera CV con ▾:** bottone primario + bottone attaccato con menu (Genera cover letter, Genera messaggio). Prima della generazione del CV si apre il pannello "Colma i gap" (facoltativo).
- **Dopo la generazione:** compare la sezione **Documenti** con una riga per documento: CV (modifica, scarica, ⋯ rigenera), cover letter e messaggio (pulsante "Genera" se mancanti). La barra azione diventa "Segna candidatura fatta".
- **Stati di attesa:** raccolta e generazione sono sincrone e possono durare minuti → pannello/finestra con spinner, testo che spiega l'attesa, pulsante disattivato.
- **Conferma di un costo (Sprint 68–70):** prima di un'azione che addebita credito extra (azione oltre il massimale del piano) si apre una **finestra di conferma** (`Modal`) con azione, prezzo e saldo; sostituisce il `window.confirm`. Il testo "Incluso nel piano: ne restano X su Y oggi" compare vicino al pulsante quando l'azione è ancora gratuita. Con saldo insufficiente il pulsante è disattivato e il motivo è scritto sotto.
- **Avvisi di sistema in cima alla lista:** *profilo incompleto* (banner con azione "Completa il profilo") e *nuova versione disponibile* (banner con "Aggiorna"); vanno sopra il titolo, uno alla volta (priorità: nuova versione, poi profilo).
- **Avviso AI:** frase fissa "Contenuto generato con l'AI: verificalo prima di usarlo" sotto ogni contenuto generato e sotto la chat (`AiNotice`).
- **I tuoi limiti di oggi:** sottopagina di Impostazioni con saldo e una riga per azione (usate/massimale, barra di avanzamento, prezzo oltre massimale). I contatori ripartono a mezzanotte (Europe/Rome). I numeri nei mockup sono esempi.
- **Account e privacy (Sprint 67):** email e fuso orario modificabili, cambio password, esportazione dati (ZIP), notifiche on/off, eliminazione immediata dell'account con finestra di conferma (digitare la password). Informativa e termini aperti da `LegalFooter`.
- **Errori e vuoti:** testi esistenti in `translations.js`, mostrati nel punto in cui nasce l'errore (es. credito insufficiente dentro la chat).

## 6. Componenti
Esistono già in `frontend/src/components/ui/`: `button, card, badge, checkbox, dialog, input, label, radio-group, select, textarea`. Da aggiungere o rifare:

| Componente | Descrizione | Note |
|---|---|---|
| `AppShell` | Contiene navigazione (tab in basso / pillola in alto) e colonna | sostituisce `Topbar` in `App.jsx` |
| `BottomTabBar` | 3 voci icona + etichetta | |
| `ActionBar` | Barra fissa in basso con 1–2 azioni | dettaglio, editor, profilo |
| `Sheet` | Pannello dal basso con grabber, titolo, ✕, corpo, footer | costruibile su `Dialog` esistente (Radix) |
| `Modal` | Finestra centrale (restyling di `dialog.jsx`) | salva filtri, elimina, esci |
| `SplitButton` + `Menu` | Bottone con ▾ e menu a tendina | richiede un menu accessibile |
| `Accordion` | Sezione comprimibile (titolo, riepilogo a destra, chevron) | profilo, editor CV |
| `Switch` | Interruttore (`role="switch"`) | raccolta automatica, notifiche, foto nel CV |
| `SegmentedControl` | 2–3 opzioni (Modifica/Anteprima, Ruolo/Azienda, Canale) | |
| `FilterPill` / `PillGroup` | Pillole selezionabili (tab liste, filtri) | |
| `StatsSummary` | Riga compatta "192 nuovi oggi · 466 settimana" espandibile | usa l'API statistiche esistente |
| `JobCard` | Versione ridotta (badge, titolo, azienda·località+recruiter, 2 gap, data, ♥) | refactor di `JobCard.jsx` |
| `ScoreChip` | Chip punteggio a fasce | |
| `RecruiterIcon` | Icona recruiter | |
| `CounterToggle` | Contatore "n corrispondenze / n gap" | |
| `DocumentRow` | Riga documento con stato e azioni | |
| `Field` | Etichetta + input/textarea + suggerimento | wrapper dei `ui/input`/`textarea` |
| `Banner` | Riquadro di avviso (info / attenzione / errore / ok) con azione opzionale | profilo incompleto, nuova versione, errori di form |
| `CostConfirmDialog` | Finestra di conferma costo (azione, prezzo, saldo) | sostituisce `window.confirm`; riusa `ActionCost` |
| `UsageLimitsCard` (restyling) | Righe con barra di avanzamento | già esiste; spostarlo in sottopagina |
| `LegalConsents` / `LegalFooter` (restyling) | Checkbox di consenso e link legali | già esistono |
| `Toast` con azione | "Job archiviato · Annulla" | estende `ToastProvider` |
| `Spinner`, `EmptyState`, `Stepper` | stati di attesa, lista vuota, passi onboarding | |

**Dipendenze candidate (richiedono approvazione, `CLAUDE.md`):** `@radix-ui/react-switch`, `@radix-ui/react-accordion` (o `<details>` nativo), `@radix-ui/react-dropdown-menu` (o menu fatto in casa). Tutto il resto si costruisce con ciò che c'è (Radix Dialog/Select/Checkbox/Radio, Tailwind, `class-variance-authority`, `lucide-react`).

## 7. Cosa non è disegnato
- **Tablet 768–1023 px** (si assume il layout mobile centrato).
- **Dark mode**: i token scuri esistenti in `index.css` vanno rivisti sui nuovi token (`--card` bianco → superficie scura, nuovi `--tint/--note/--chip`).
- Versione **inglese** dei testi (si verifica a codice con le regole di §3.6), animazioni e transizioni, scheletro di caricamento delle liste (esiste un `skel` nei mockup di accesso, non applicato alle liste).
- Schermate di errore di rete, pagina 404, stato "notifiche disattivate" nella lista.
- **Template PDF del CV** (fuori ambito, vedi §3.7).

## Punti da verificare in revisione
1. Navigazione desktop: barra in alto con 3 voci e **logout spostato in Impostazioni** (oggi è nella barra): confermare lo spostamento.
2. Dark mode: stesso ciclo o sprint dedicato?
3. Dipendenze Radix da aggiungere (switch, accordion, dropdown-menu) o alternative native (`<details>`, `button role="switch"`, menu fatto in casa)? Proposta predefinita: **nessuna dipendenza nuova**.
4. Colore del punteggio: confermare la logica a fasce esistente (nei mockup il punteggio 8 è disegnato in verde per errore).
5. Chip di stato nel dettaglio: solo indicativo (proposto) o selezionabile? Nel secondo caso va rivisto il vincolo "tre stati stabili" di `CLAUDE.md`. Nei mockup il chip "Nuovo" mostra un chevron: da togliere se resta indicativo.
6. Font: si resta sullo stack di sistema (compatibile con la policy Sprint 66)? Un font di marca andrebbe incluso nel repository.
7. Numeri dei limiti di oggi, testo del 429 e prezzi nei mockup sono **esempi**: quelli reali vengono da `/api/accounts/usage/` e dal listino.
8. Logo: spessore e spaziatura sono una prima versione; per usi di stampa serve il lockup vettorializzato.
