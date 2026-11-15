# Sprint 80 — Redesign UI: rifinitura e preparazione al rilascio

> **Periodo:** 2026-11-15 · **Branch:** `sprint-80-rifinitura` (da `sprint-79-accesso`, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato e verificato (e2e 63/63, backend 488/488, screenshot); **merge e deploy non fatti** (procedura in `Docs/design/RELEASE.md`, in attesa dell'ok del committente).

## Input
Perimetro da `Docs/design/IMPLEMENTATION-PLAN.md` (sprint 80) e richiesta del committente: (1) tutte le schermate in inglese, testi tagliati, mancanti o non tradotti; (2) 360 e 390 px senza testi tagliati né pagine che sbordano, bersagli ≥ 44 px, contrasto dei token, area sicura iOS e `100dvh` controllati nel codice; (3) stati mancanti con proposte minime (errore di rete, 404, notifiche disattivate); (4) tema scuro: solo controllo di leggibilità, non ridisegnato; nessun layout tablet; (5) pulizia di elementi non usati, verificata; (6) documenti di design all'as-is; (7) `Docs/design/RELEASE.md` (solo il documento). Vincoli: nessun cambio di API o backend, nessuna dipendenza, nessun font esterno, nessun merge né deploy.

Prima di partire: produzione su `main` (f6584e5), tutti i container da `docker-compose.prod.yml`, sito 200; unica modifica locale il blocco dell'anteprima nel Caddyfile, identico alla versione committata (commit `4c78973`). Numero: `git log` e `ls sprints/` arrivano entrambi a 79.

## Come è stato verificato
Uno spec Playwright temporaneo (non committato) percorre 28 stati — accesso, registrazione, recupero e reset, verifica, pagine legali, 404 (con e senza login), errore di rete all'avvio e nelle pagine legali, lista, filtri, raccolta, importati, dettaglio, menu ⋯, editor di CV e cover letter, profilo, impostazioni e sottopagine, onboarding, schermata di accettazione — con un utente Pro di prova (job del seed, un CV e una cover letter modificabili, una ricerca, notifiche spente). Per ogni stato e larghezza misura: larghezza della pagina, elementi con testo tagliato (`overflow`/`ellipsis` con contenuto più largo), controlli toccabili sotto i 44 px, parole italiane nel testo visibile in inglese. Eseguito in **inglese** (360/390/1280, screenshot a 360 e 1280), in **italiano** (360/390) e in inglese con **tema scuro** (360, screenshot).

## Esito per punto
### 1. Inglese
- Nessun testo italiano rimasto nelle schermate in inglese (l'unica parola trovata, "Nessuna", viene dai dati di prova del seed).
- Nessuna chiave mancante: le 615 chiavi usate nel codice esistono in it ed en; nessuna chiave presente in una sola lingua.
- **Corretto:** il segnaposto della ricerca della lista era tagliato a 360 px in entrambe le lingue ("Search title, company, locati…"): ora "Title, company or place" / "Titolo, azienda o luogo", con nome accessibile completo ("Search by title, company or location" / "Cerca per titolo, azienda o località").
- Tagli voluti, lasciati: la qualifica nel riassunto della fisarmonica dell'editor ("Senior Product Ma…", con il testo intero dentro la sezione).

### 2. 360 e 390 px, tocco, contrasto, iPhone
- **Nessuna pagina più larga dello schermo** in nessuno stato, lingua e larghezza misurati.
- **Bersagli di tocco portati a 44 px:** pillole dei filtri e delle sezioni (36 px visibili), interruttori (32 px), pulsante del grassetto nei punti elenco (32 px) e icona del recruiter (22 px) con un'area trasparente (`::after`) senza cambiare l'aspetto; selettore della lingua (40 → 44), pulsanti sposta/elimina degli editor (40 → 44), azione del toast (40 → 44), "Tutte le date" nei filtri, link isolati delle pagine di accesso ("Password dimenticata?", "Registrati", "Accedi", "Torna all'accesso") e del piè di pagina legale. Restano sotto i 44 px solo i link dentro una frase (es. "informativa privacy" nei consensi), ammessi dalle linee guida, e i titoli delle card, che hanno l'intera card come area.
- **Contrasto** (calcolo WCAG sui token di `index.css`, 29 coppie testo/sfondo usate): tutte ≥ 4,5:1; minimo 5,0 nel tema chiaro (testo secondario su `secondary`), 4,77 nel tema scuro (`primary` su `primary-soft`).
- **Area sicura e `100dvh`** (controllo del codice): `viewport-fit=cover`; `env(safe-area-inset-*)` su barra di tab, barra azione, pannelli, chat degli editor, intestazioni e lati del `body`; `--app-bottom-bar` per toast e avvisi fissi; `min-height: 100vh` seguito da `100dvh`; `max-h` di pannelli e finestre in `dvh`; chat sopra la tastiera con `visualViewport`. **Non provabile senza un iPhone vero** (nel browser di prova `env()` vale 0 e non c'è tastiera virtuale).

### 3. Stati mancanti (proposte minime, nessuna API nuova)
| Stato | Prima | Aggiunto | Perché |
|---|---|---|---|
| Errore di rete in una pagina | messaggio generico "Qualcosa è andato storto" | `apiFetch` trasforma l'errore di `fetch` in `ApiError` con status 0 e testo "Connessione non riuscita: controlla la rete e riprova."; un avviso (toast, al massimo uno ogni 5 s) lo mostra in qualsiasi pagina | dire la causa senza toccare le 17 pagine che usano il messaggio generico |
| Server irraggiungibile all'apertura, con sessione salvata | redirect al **login** (sembrava una sessione scaduta) | schermata "Nessuna connessione" con "Riprova"; il token resta | la sessione è valida: rimandare al login era sbagliato |
| Pagine legali senza risposta da `/api/legal/` | caricamento infinito | "Impossibile caricare la pagina" con "Riprova" (testo già esistente, mai usato) | difetto: la pagina non usciva mai dall'attesa |
| Indirizzo inesistente | pagina vuota | "Pagina non trovata" con "Vai ai job" / "Vai all'accesso" | DESIGN.md §7 |
| Notifiche disattivate (B10) | stato solo in Impostazioni | nel pannello "Raccogli", per un Pro con l'automatica attiva e le notifiche spente, avviso con il link a Impostazioni | è l'unico caso in cui le notifiche spente fanno perdere un'informazione (la fine della raccolta); nessun banner fisso nella lista, perché chi le spegne lo ha scelto. **Da confermare** |

### 4. Tema scuro (solo controllo, non ridisegnato)
Nessun testo illeggibile (contrasto sopra; screenshot di lista, filtri, raccolta, dettaglio, editor, impostazioni, profilo, accesso, accettazione, informativa, onboarding). Da segnalare, non corretti perché richiederebbero di ridisegnare il tema (B8 aperto): l'**interruttore spento** ha il pallino quasi dello stesso colore del binario (si capisce poco che è un interruttore); i **pulsanti disattivati** si distinguono poco dallo sfondo; il segnaposto "[da completare]" delle pagine legali resta giallo chiaro (leggibile; scompare con i dati del titolare). Nessun layout tablet.

### 5. Pulizia (verificata)
- Rimossi: `components/MultiSelectFilter.jsx` (non importato da nessun file dallo Sprint 74); in `ui/dialog.jsx` `Dialog`, `DialogTrigger`, `DialogClose`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter` (nessun uso: tutte le finestre sono `Modal` o `Sheet`; restano overlay e pulsante ✕ condivisi); in `ui/card.jsx` `CardHeader/Title/Description/Content/Footer` (resta `Card`).
- Rimosse 29 chiavi di traduzione non usate in it e en (es. `appName`, `onboarding.skipUpload`, `jobs.expandReasons`, `home.statsWeek`, `cvEditor.chatToggle`, `usage.colAction`, `account.settingsTitle`), verificate con uno script che cerca la chiave intera e le chiavi composte dinamicamente. Le 40 "non citate" rimaste sono nomi e livelli delle lingue, letti in blocco da `utils/languageOptions.js`.
- Lasciati: token `accent-foreground`, `secondary-foreground` e i raggi `rounded-sm/xl` (nessun uso diretto, ma parte della base shadcn usata dalle primitive); `ModalTrigger`/`SheetTrigger` (API dei componenti).
- Nessuna dipendenza aggiunta o tolta.

### 6–7. Documenti
`Docs/design/README.md` (stato implementato, stato al rilascio), `DESIGN.md` (§6 componenti as-is, §7, esito dei punti di revisione), `SCREENS.md` (§8: file attuali e differenze rimaste per area, stati aggiunti), `SPEC-DELTA.md` (stato di A e B: aperti B8 e B11, B10 proposta da confermare, B7 e B9 decisi), `IMPLEMENTATION-PLAN.md` (80 ✅), nuovo `RELEASE.md` (merge, backup, variabili, migrazioni, deploy, controlli, ritorno indietro, anteprima). Specifiche: 01 §4.12, §6, §7; 02 §3.3, §13.2; `CHANGELOG.md`.

## E2e
| Spec / test | Dopo |
|---|---|
| `job-list` › ricerca testuale | campo cercato per nome accessibile ("Cerca per titolo, azienda o località") invece che per segnaposto |
| **nuovo** `auth-onboarding` › pagina non trovata | titolo e link "Vai all'accesso" |
| **nuovo** `auth-onboarding` › pagine legali senza risposta | errore, "Riprova", poi 12 sezioni |
| **nuovo** `auth-onboarding` › server irraggiungibile all'avvio | "Nessuna connessione", URL invariato (nessun redirect al login), "Riprova" → lista |
| **nuovo** `auth-onboarding` › errore di rete in un modulo | riquadro d'errore e avviso "Connessione non riuscita", si resta su `/login` |
| **nuovo** `collection` › Pro con notifiche disattivate | avviso e link a Impostazioni |

## Verifica
- `npm run build` OK; `npx oxlint src e2e` 0 errori, 9 warning (gli stessi).
- **E2e** sullo stack usa e getta, sul codice finale: primo giro della suite completa **62/63**. L'unico fallimento (`job-list` › salvare, applicare e rimuovere un filtro preferito, `not.toBeVisible`) non si è ripetuto: lo stesso test 4/4 ripetuto da solo, `job-list.spec.js` intero 25/25 e una seconda esecuzione della suite completa **63/63** (58 + 5 nuovi). Lo considero un'instabilità di tempi dell'ambiente di prova, non un difetto: il flusso non tocca le pillole se non per il clic, e l'area di tocco allargata è solo verticale.
- **Backend** (non modificato): `manage.py test` in un container usa e getta con `-e DJANGO_DEBUG=true -e REGISTRATION_INVITE_CODE=`: **488 test OK**; `makemigrations --check`: nessuna differenza.
- Screenshot di campionamento in inglese a 360 e 1280 px (28 stati) e in tema scuro a 360; percorso in italiano a 360/390 (misure). In totale 168 misure (28 stati): nessuna pagina più larga dello schermo, nessun errore JavaScript, nessun testo italiano in inglese.
- Stack di prova abbattuto. Anteprima aggiornata al branch.

## Cosa manca / note
- Da provare su un iPhone vero: area sicura (notch, indicatore Home) nella PWA dalla Home, `100dvh` con le barre di Safari, chat degli editor sopra la tastiera, notifiche push.
- Decisioni aperte: B8 (tema scuro ridisegnato, tablet), B11 (forma del messaggio di troppi tentativi); B10 da confermare.
- Prima del rilascio servono i dati del titolare del trattamento nel `.env` di produzione (`LEGAL_CONTROLLER_NAME`, `LEGAL_CONTROLLER_EMAIL`: oggi non impostati) — vedi `RELEASE.md §2.1`.
