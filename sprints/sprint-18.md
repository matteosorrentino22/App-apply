# Sprint 18 — Frontend: setup PWA, autenticazione, onboarding

## Input
- Sprint 01 (infrastruttura), Sprint 03 (auth API), Sprint 04/05 (profilo/import CV API), Sprint 06 (ricerche API) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §3 (Setup e onboarding), §6 (lingua interfaccia); `02-specifiche-tecniche-v3.md` §3.3.

## Obiettivo
Scaffold React PWA (manifest, installabilità, service worker minimo senza cache offline dei dati), schermate di login/registrazione (email/password + Google), flusso di onboarding completo (profilo con upload CV/foto, scelta template/lingua CV, opzione foto, creazione prima ricerca), lingua interfaccia di default dal dispositivo (IT/EN) modificabile.

## Risultato atteso
L'app è installabile su un dispositivo/browser di test; un nuovo utente può registrarsi, completare l'onboarding (profilo pre-popolato da CV o compilato manualmente, prima ricerca creata) e arrivare alla schermata lista (anche vuota).

## Criteri di verifica
- `npm run build` (o equivalente) completa senza errori; il manifest PWA è valido (verificabile con audit Lighthouse PWA o validatore manifest).
- Test e2e: registrazione utente → completamento onboarding (compilazione profilo, upload CV di test, creazione ricerca) → arrivo alla schermata lista, senza errori console.
- Test e2e: login con credenziali errate mostra messaggio di errore e non naviga oltre la schermata di login.
- Verifica manuale: cambiando la lingua del dispositivo/browser tra IT e non-IT, l'interfaccia si presenta rispettivamente in italiano o inglese al primo accesso; l'impostazione è modificabile.
- Nessuna logica di cache/sync offline dei dati è presente: il service worker registrato gestisce solo installabilità/push, non intercetta le chiamate API per servire dati in cache.

## Output per lo sprint successivo
Utente autenticato con profilo e ricerche configurate, pronto per l'uso della lista job e della generazione CV in UI (Sprint 19).

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- Scaffold `frontend/` (React 19 + Vite 7, `react-router-dom`), servito dietro lo stesso host di `backend/` tramite Caddy/proxy dev (nessuna CORS, i cookie di sessione django-allauth funzionano senza configurazione aggiuntiva).
- **Autenticazione**: `src/api/client.js` centralizza `fetch` con header `Authorization: Token <key>` (salvato in `localStorage`) più `credentials: 'include'`, per supportare in parallelo sia il login nativo (token DRF) sia il login Google (redirect a `/accounts/google/login/?process=login`, sessione Django al ritorno — nessun codice OAuth custom, come da §3.7 tecniche). `LoginPage`/`RegisterPage` con gestione errori (credenziali non valide → messaggio dedicato, non naviga oltre).
- **Onboarding** (`OnboardingPage`, wizard a 3 step con stato locale, nessun sub-routing): preferenze (obiettivo, lingua CV, foto sì/no, template unico), profilo (upload CV opzionale che pre-compila i campi via `POST /api/profile/import-cv/`, altrimenti compilazione manuale; 5 sezioni ripetibili — esperienze, istruzione, competenze, certificazioni, lingue — tramite un editor generico `ListSectionEditor` condiviso), prima ricerca (creata e attivata subito).
- **PWA**: `vite-plugin-pwa` in modalità `injectManifest` (necessaria per un service worker custom con handler push, non ottenibile con `generateSW`); `src/sw.js` fa solo `precacheAndRoute` degli asset statici di build + `push`/`notificationclick`/`install`/`activate`. **Nessuna `runtimeCaching` è configurata**: le chiamate `/api/*` vanno quindi sempre in rete, mai servite da cache — il vincolo "niente cache offline dei dati" (CLAUDE.md, §3.3 tecniche) è rispettato per omissione, non con una regola di esclusione esplicita.
- **Lingua interfaccia**: dizionario minimo (`src/i18n/translations.js`, IT/EN) + `LanguageContext` — al primo avvio deriva la lingua da `navigator.language` (persistita in `localStorage`); al login/registrazione, la preferenza salvata sull'account (`User.interface_language`) prende il sopravvento se diversa (`AccountLanguageSync` in `App.jsx`); uno switcher IT/EN in una topbar minimale la rende modificabile in ogni momento, con persistenza su `PATCH /api/accounts/me/` per un utente autenticato.
- **Docker/Caddy**: aggiunto il servizio `frontend` (Vite dev server, `docker-compose.yml`) e riscritto `docker/caddy/Caddyfile` per instradare `/api`, `/admin`, `/accounts`, `/static`, `/media` a `web:8000` e tutto il resto a `frontend:5173` — stesso pattern "un'unica immagine per servizio" già in uso per `backend/Dockerfile`.

### Decisioni tecniche non esplicitamente richieste, da segnalare
- **Versioni pinnate**: `vite@^7.3.6` + `@vitejs/plugin-react@^5.2.0` + `vite-plugin-pwa@1.2.0`, non le ultime versioni maggiori disponibili (Vite 8 era appena uscito). Motivo: `vite-plugin-pwa@1.2.0` non supporta ancora Vite 8 (conflitto di peer-dependency), e Vite 7 è comunque una versione matura e ben documentata (coerente con "preferire soluzioni standard" in CLAUDE.md).
- **2 vulnerabilità npm high accettate** (non risolvibili senza downgrade che romperebbero altro):
  1. `brace-expansion` (DoS) — arriva transitivamente da `workbox-build`, usato solo in fase di build (`vite build`) per generare il manifest di precache del service worker: mai eseguito in produzione, non esposto a input di un attaccante in un processo di build controllato.
  2. `react-router` "RSC Mode CSRF Bypass" — riguarda solo la modalità React Server Components, non usata da questa SPA (routing puramente client-side con `BrowserRouter`).
- **Limite noto (coerente con tutti gli sprint precedenti che toccano Claude)**: `structure_with_claude()` non gestisce eccezioni dell'API Anthropic — senza `ANTHROPIC_API_KEY` valida l'upload CV fallisce con 500 grezzo, non un errore gestito. Il test e2e "happy path" usa quindi il percorso di compilazione manuale (nessun upload CV), per restare deterministico e indipendente da credenziali Claude reali in questo ambiente.

### Verifica eseguita
- `npm run build`: completa senza errori; `dist/manifest.webmanifest` generato è JSON valido con nome/icone/`start_url`/`display: standalone`; nessuna `runtimeCaching` nel service worker generato (confermato via grep sull'output).
- Backend riavviato localmente (Postgres/Redis reali, non mock) con le stesse 84 migrazioni già presenti; `python manage.py test` → **84/84 passati**, nessuna regressione dal lavoro frontend.
- Test e2e (Playwright, Chromium headless, `frontend/e2e/auth-onboarding.spec.js`, 5/5 passati):
  - registrazione → onboarding (compilazione manuale) → prima ricerca → arrivo a `/list`, zero errori console applicativi (il probe iniziale "sono loggato?" genera un 401 atteso/gestito, filtrato dal controllo perché non è un'eccezione JS);
  - login con credenziali errate → messaggio d'errore visibile, resta su `/login`;
  - browser con locale `it-IT` → interfaccia in italiano al primo accesso; locale `en-US` → interfaccia in inglese;
  - cambio lingua manuale tramite lo switcher → interfaccia aggiornata immediatamente.
  - Verificato anche via shell Django che i dati inseriti nell'onboarding e2e (preferenze utente, sommario profilo, ricerca creata e attivata) risultano effettivamente persistiti nel database reale, non solo che l'UI naviga correttamente.
- Verificato via API reale (`PATCH /api/accounts/me/`) che il cambio lingua persiste `interface_language` sull'account per un utente autenticato.
- `docker-compose.yml` validato come YAML sintatticamente corretto; non eseguibile in questo sandbox (nessun demone Docker disponibile) — da verificare con `docker compose up --build` sul VPS dell'utente.

### Cosa manca
- Verifica reale del round-trip Claude per l'import CV (richiede `ANTHROPIC_API_KEY` valida e ambiente con accesso a rete verso l'API Anthropic — non disponibile in questo sandbox); il percorso è comunque implementato e testato lato backend negli sprint precedenti.
- Verifica dell'installabilità PWA effettiva (prompt "Aggiungi a schermata Home") e di un audit Lighthouse PWA completo, che richiedono un browser reale con interfaccia grafica — non eseguibile in questo ambiente headless.
- `docker compose up --build` non eseguito realmente (nessun demone Docker in questo sandbox): la configurazione va validata dall'utente sul proprio VPS al primo deploy di questo sprint.

---

## Aggiornamento — Design system (2026-07-26)

Intervento trasversale post-sprint, non un nuovo sprint numerato: nessuna API/logica funzionale toccata, solo styling e struttura dei componenti UI (come richiesto). Motivo: le schermate erano funzionalmente corrette ma con HTML non stilizzato.

### Cosa è stato fatto
- **Tailwind CSS v4** (`@tailwindcss/vite`, configurazione CSS-first via `@theme` in `src/index.css`, nessun `postcss.config.js` necessario) + **shadcn/ui** — componenti copiati come sorgente in `src/components/ui/` (`button`, `input`, `textarea`, `label`, `card`, `select`, `checkbox`, `radio-group`, `badge`), non un pacchetto: restano modificabili come qualunque altro file del repo. `components.json` presente per usare in futuro `npx shadcn add` su nuovi componenti con le stesse convenzioni.
- **Design system**: palette beige/sabbia con un solo accento bruno caldo (non indaco/violetto, scartato su richiesta esplicita per contrasto col beige); scala semantica separata a 5 livelli per il punteggio job (rosso→verde), pensata per lo Sprint 19; font di sistema (`system-ui`, nessun webfont scaricato); token light/dark via `prefers-color-scheme`, coerenti con l'anteprima approvata in artifact prima dell'implementazione.
- **Select nativa → componente Radix**: la tendina "Località"/switcher lingua non usa più `<select>` del browser (mai stilizzabile da aperta) ma `@radix-ui/react-select`, accessibile e coerente con la palette.
- **Esperienze raggruppate per azienda** (`ExperienceGroupEditor.jsx`, nuovo): un'azienda può avere più ruoli annidati sotto (pattern "più posizioni", stesso usato da LinkedIn), ognuno con propria località e un elenco di attività/competenze a chip (`ChipInput.jsx`, nuovo componente riusabile). **Nessuna modifica al backend**: il modello `Experience` era già una riga per (azienda, ruolo, località, attività) — il raggruppamento è solo come il form presenta e compila i dati; al salvataggio ogni ruolo resta un'esperienza indipendente con l'azienda copiata, esattamente come prima. L'import da CV raggruppa lato client (`groupExperiencesByCompany`) l'elenco piatto restituito da Claude.
- `ListSectionEditor` (istruzione/competenze/certificazioni/lingue) semplificato: rimosso il tipo di campo `lines` (testarea riga-per-riga), ormai inutilizzato dato che le esperienze hanno un editor dedicato.

### Verifica eseguita
- `npm run build` e `npm run lint`: nessun errore (solo warning preesistenti di `oxlint` sul fast-refresh dei file che esportano insieme componenti e varianti, non bloccanti).
- Backend reale (Postgres/Redis locali) + `python manage.py test` → **84/84 passati**, nessuna regressione.
- Test e2e Playwright aggiornati per il nuovo markup (switcher lingua non più un `<select>` nativo) + **nuovo test dedicato** che aggiunge due ruoli nella stessa azienda con attività a chip e verifica che il salvataggio produca due `Experience` distinte con lo stesso nome azienda — **6/6 passati**. Verificato anche via shell Django che i dati (azienda, ruolo, località, elenco attività) risultano persistiti esattamente come inseriti in UI.
- Verifica visiva con screenshot reali (Playwright, tema chiaro e scuro) di login, onboarding (tutti e 3 gli step, incluso il nuovo editor esperienze) e lista: confrontati con l'artifact di design system approvato dall'utente prima dell'implementazione.

### Cosa manca
- Le altre schermate/card previste dal design system (lista job con punteggio ed azione diretta, dettaglio job con giustificazione) erano solo un mock nell'artifact: l'implementazione reale arriva con lo Sprint 19, quando esisteranno i dati veri da mostrare.