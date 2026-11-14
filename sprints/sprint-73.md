# Sprint 73 — Redesign UI: AppShell e navigazione a 3 voci

> **Periodo:** 2026-11-14 · **Branch:** `sprint-73-appshell` (da `sprint-72-fondamenta`, mai su `main`) · **Stato:** implementato e verificato su uno stack di prova; **merge e deploy non fatti** (in attesa dell'ok del committente). Prima di qualunque merge su `main` gli e2e vanno eseguiti sul computer del committente (comandi sotto).

## Input
Richiesta del committente (perimetro da `Docs/design/IMPLEMENTATION-PLAN.md` e `SCREENS.md`):
- `AppShell`, barra di tab in basso sotto i 1024 px (voce attiva, area sicura iOS) e barra in alto da 1024 px con logo + wordmark, le 3 voci (Jobs · Profilo · Impostazioni) e il selettore della lingua (mockup `desk-jobs`, `jobs-lista`);
- eliminare `HomePage` e la rotta `/home` (redirect a `/list`); statistiche e raccolta arrivano nello Sprint 74, ma fino ad allora il pulsante Raccogli deve restare raggiungibile (soluzione più semplice, motivata qui);
- rimuovere la `Topbar`; "Esci" in Impostazioni con finestra di conferma (decisione A9, mockup `impostazioni`), stringhe it/en;
- logo nelle pagine di accesso e nella barra desktop;
- verificare a 360 e 390 px che nessuna pagina sbordi, usare `viewport-fit=cover`, `100dvh` e l'area sicura iOS;
- e2e: aggiornare gli spec coinvolti senza eseguirli (niente installazioni sul VPS) e scrivere qui i comandi per lanciarli;
- vincoli: nessuna dipendenza nuova, nessun font esterno, nessun cambio di API o backend, template PDF del CV escluso.

## Decisioni prese
- **Raccogli fino allo Sprint 74**: pulsante con icona di aggiornamento accanto al titolo della lista, dove lo mettono i mockup (`jobs-lista`, `desk-jobs`), che apre un `Sheet` "Raccogli nuovi job" (`components/CollectJobsSheet.jsx`). Dentro c'è **tutto quello che c'era nella Home**: la raccolta manuale invariata (stessa API, limite 1/giorno, indicazione del costo della prossima richiesta, riepilogo "Job trovati / Tenuti dopo scoring") e le statistiche (job trovati con "di cui manuali", CV generati, candidature fatte; oggi, ultima settimana, totali). Motivo: è la soluzione più semplice che non toglie nulla all'utente se lo sprint venisse rilasciato da solo; lo Sprint 74 la sostituisce con `StatsSummary` nella lista e i pannelli `collect-*`. Dopo una raccolta riuscita la lista si ricarica.
- **Finestra "Esci"**: nel pacchetto di mockup **non esiste** `logout-confirm`. La finestra segue il modello di `delete-search` (titolo, testo, azione distruttiva a tutta larghezza, "Annulla" testuale): "Vuoi uscire?" / "Uscirai da App-apply su questo dispositivo e qui non riceverai più notifiche push. Gli altri dispositivi restano collegati." Il pulsante "Esci" (testo rosso con icona, mockup `impostazioni`) è in fondo alla pagina Impostazioni attuale, che verrà riorganizzata a sottopagine nello Sprint 78.
- **Selettore lingua**: nella barra desktop e nella testata delle pagine senza navigazione (accesso, legali, verifica email, accettazione); su mobile, dopo il login, si cambia in Impostazioni → Preferenze (già presente), come da `DESIGN.md §2`.
- **Voce attiva**: Jobs è attiva anche su `/jobs/*` (dettaglio, editor). Le voci sono `Link` con `aria-current` gestito da `AppShell`, perché `NavLink` lo applicherebbe solo alla rotta esatta.
- **Barra di tab su tutte le pagine autenticate**, editor compresi: la `ActionBar` che la sostituisce nel dettaglio e negli editor arriva con gli sprint 75–76.
- **Banner del profilo incompleto** invariato nell'aspetto (ridisegnato nello Sprint 74, mockup `jobs-avvisi`), sotto la barra desktop o in cima alla pagina su mobile.

## Implementazione
### Frontend
- `components/AppShell.jsx` (nuovo): `DesktopTopBar` (≥ 1024 px, `sticky`, logo + wordmark, voci a pillola con l'attiva su `--primary-soft`, `LanguageSwitcher` compatto), `BottomTabBar` (< 1024 px, fissa in basso, icona `Briefcase`/`UserRound`/`Settings` + etichetta, `padding-bottom: max(8px, env(safe-area-inset-bottom))`), `PublicHeader` (logo + lingua) per le pagine senza navigazione. Imposta la classe `has-tabbar` su `<html>` quando la navigazione è visibile.
- `components/BrandLogo.jsx` (nuovo): marchio SVG (`src/assets/brand/logo-mark.svg`, variante chiara con `prefers-color-scheme: dark`) + wordmark "App-apply" con font di sistema.
- `components/CollectJobsSheet.jsx` (nuovo): raccolta manuale e statistiche (logica spostata da `HomePage`, invariata).
- `components/LogoutButton.jsx` (nuovo): "Esci" + `Modal` di conferma; usa lo stesso `logout()` di `AuthContext` (revoca il token del dispositivo e ne disattiva le notifiche push).
- `App.jsx`: rimossi `Topbar` e `NavItem`; le rotte sono dentro `AppShell` (il banner del profilo è passato come prop); `/home` → `<Navigate to="/list" replace />`. `pages/HomePage.jsx` eliminata.
- `pages/JobListPage.jsx`: pulsante Raccogli nella testata. `pages/AccountPage.jsx`: `LogoutButton` in fondo.
- `components/LanguageSwitcher.jsx`: variante `compact` (40 px) per le testate; l'etichetta accessibile "Lingua / Language" resta quella usata dagli e2e.
- `index.html`: `viewport-fit=cover`. `index.css`: `#root` con `min-height: 100dvh` (fallback `100vh`); variabile `--app-bottom-bar` (64 px + area sicura sotto i 1024 px con la barra di tab, 0 altrove); area sicura laterale sul `body`; padding superiore `env(safe-area-inset-top)` sulle pagine autenticate su mobile (non hanno testata).
- Elementi fissi in basso spostati sopra la barra di tab con `--app-bottom-bar`: `ToastProvider`, `AppUpdateBanner`, pulsante chat di `CvDraftEditorPage` e `CoverLetterDraftEditorPage`.
- `translations.js` (it/en): `nav.main`, `nav.homeLink`, `account.logoutConfirmTitle`, `account.logoutConfirmBody`; rimosse `home.navLink` e `home.title` (non più usate).
- `playwright.config.js`: il percorso fisso di Chromium (`/opt/pw-browsers/…`, dell'ambiente in cui la suite è nata) si usa solo se esiste; altrimenti il Chromium di Playwright, o `PW_CHROMIUM_PATH`.
- `.gitignore`: `backend/e2e_settings_local.py` (impostazioni locali per gli e2e, sotto).

### Backend / API
Nessun cambio.

## E2e — asserzioni cambiate
| Spec | Prima | Dopo |
|---|---|---|
| `job-list.spec.js` | "il pulsante Esci della barra in alto funziona anche dal dettaglio di un job": clic su "Esci" nel dettaglio → `/login` | **Sostituito** da "Esci da Impostazioni chiede conferma e chiude la sessione": nessun pulsante "Esci" nella lista; voce Impostazioni della navigazione → "Esci" → finestra "Vuoi uscire?"; "Annulla" la chiude restando su `/settings`; "Esci" nella finestra → `/login`, `/list` reindirizza a `/login` |
| `job-list.spec.js` | — | **Nuovo** "navigazione a 3 voci in alto su desktop e /home reindirizza a /list": voci `Jobs, Profilo, Impostazioni`; `aria-current="page"` su Jobs in lista e nel dettaglio, su Profilo in `/profile`; `/home` → `/list` |
| `job-list.spec.js` | — | **Nuovo** "barra di tab in basso con 3 voci e Raccogli raggiungibile dalla lista" (viewport 390 × 844): una sola navigazione, in fondo allo schermo; "Raccogli nuovi job" apre il pannello con "Raccogli ora" e si chiude con "Chiudi"; `scrollWidth ≤ 390` su `/list`, `/profile`, `/settings` |
| `auth-onboarding.spec.js` (2 punti) | `page.getByText('Profilo', { exact: true })` | `page.getByRole('main').getByText('Profilo', { exact: true })`: "Profilo" è anche una voce della barra di navigazione |
| `account.spec.js`, `push-subscription.spec.js` | — | Nessuna modifica necessaria (non usano Home, barra in alto né logout; il titolo "Impostazioni" è un `heading` di livello 1, la voce di menu è un link) |

## Come eseguire gli e2e (computer di sviluppo)
Prerequisiti: Docker (per Postgres e Redis), Python 3.12, Node 22, e per WeasyPrint le librerie Pango (macOS: `brew install pango`; Debian/Ubuntu: `sudo apt install libpango-1.0-0 libpangocairo-1.0-0`). Dalla radice del repository, branch `sprint-73-appshell`:

```bash
# 1. Postgres e Redis di prova (dati usa e getta)
docker run -d --name appapply-e2e-db -p 5432:5432 -e POSTGRES_DB=app_apply -e POSTGRES_USER=app_apply -e POSTGRES_PASSWORD=app_apply postgres:16-alpine
docker run -d --name appapply-e2e-redis -p 6379:6379 redis:7-alpine

# 2. Backend con virtualenv in backend/.venv (gli spec chiamano backend/.venv/bin/python manage.py ...)
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
# Impostazioni solo locali (file ignorato da git): alzano i limiti di frequenza dello
# Sprint 66 (registrazione 5/ora per IP, login 10/min), che la suite supererebbe.
cat > e2e_settings_local.py <<'PY'
from config.settings import *  # noqa: F401,F403
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {k: "100000/min" for k in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]},
}
PY
export DJANGO_DEBUG=true DJANGO_SECRET_KEY=dev-insecure-secret-key DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
       POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_DB=app_apply POSTGRES_USER=app_apply POSTGRES_PASSWORD=app_apply \
       REDIS_CACHE_URL=redis://localhost:6379/2 CELERY_BROKER_URL=redis://localhost:6379/0 CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
       REGISTRATION_INVITE_CODE= EMAIL_HOST_USER= EMAIL_HOST_PASSWORD=
.venv/bin/python manage.py migrate
DJANGO_SETTINGS_MODULE=e2e_settings_local .venv/bin/python manage.py runserver 8000   # lasciarlo aperto

# 3. Frontend (altro terminale, dalla radice del repository)
cd frontend
npm ci
npx playwright install chromium
VITE_BACKEND_URL=http://localhost:8000 npm run dev -- --port 5173                     # lasciarlo aperto
# solo per push-subscription.spec.js (service worker attivo solo nella build): altro terminale
npm run build && VITE_BACKEND_URL=http://localhost:8000 npx vite preview --port 5174

# 4. Suite (altro terminale, in frontend/; le variabili del backend servono anche qui,
#    perché gli spec lanciano manage.py seed_e2e_jobs / set_e2e_account)
export DJANGO_DEBUG=true POSTGRES_HOST=localhost POSTGRES_DB=app_apply POSTGRES_USER=app_apply POSTGRES_PASSWORD=app_apply
E2E_BASE_URL=http://localhost:5173 E2E_PREVIEW_BASE_URL=http://localhost:5174 E2E_INVITE_CODE= npx playwright test
# un solo file: npx playwright test e2e/job-list.spec.js

# 5. Pulizia
docker rm -f appapply-e2e-db appapply-e2e-redis
```

Note: registrazioni e login via API presuppongono **nessuna email configurata** (variabili `EMAIL_HOST_*` vuote) e **nessun codice di invito** (`REGISTRATION_INVITE_CODE` vuoto), come nella configurazione predefinita degli spec. I test non chiamano mai Bedrock, Apify né Gmail. Senza il file `e2e_settings_local.py` la suite si ferma con errori 429 dopo poche registrazioni.

## Verifica
- `npm run build`: OK. Lint `npx oxlint src e2e`: 0 errori, 9 warning (gli stessi di prima).
- Stack di prova usa e getta sul VPS (rete Docker dedicata, Postgres e Redis temporanei, backend dell'immagine di produzione con `DEBUG=true`, dev server Vite del branch; produzione non toccata), utente e job da `seed_e2e_jobs`, sessione tramite token per non incappare nei limiti di login; Playwright 1.62 (immagine `mcr.microsoft.com/playwright`, già scaricata nello Sprint 72: nulla installato sul VPS):
  - **larghezza del documento** = larghezza dello schermo a 360, 390 e 1280 px su `/login`, `/register`, `/privacy`, `/forgot-password` (non autenticato) e `/list`, `/profile`, `/settings`, `/onboarding`, `/privacy`, `/jobs/:id` (autenticato): nessuna pagina sborda;
  - `/home` → `/list` alle tre larghezze; nessun errore JavaScript in pagina;
  - screenshot: lista (barra di tab a 360/390, barra in alto a 1280 come `desk-jobs`), pannello "Raccogli nuovi job" (dal basso su mobile, finestra centrale a 1280), fondo delle Impostazioni con "Esci" e finestra "Vuoi uscire?", dettaglio, profilo, onboarding, login/registrazione con logo e lingua.
- **E2e**: aggiornati, **non eseguiti** (vedi sopra); da lanciare prima del merge su `main`.
- Backend non toccato: test backend non necessari.

## Cosa manca / note
- Statistiche e raccolta stanno nel pannello ponte fino allo Sprint 74 (`StatsSummary`, `collect-pro`/`collect-free`/`collect-running`).
- Il titolo della lista resta "I tuoi job" (il mockup dice "Jobs"): lo cambia lo Sprint 74 insieme al resto della lista.
- La barra di tab resta visibile anche nel dettaglio e negli editor finché gli sprint 75–76 non introducono la `ActionBar`.
- Login con le schermate ridisegnate (`login`, `register`, senza card) nello Sprint 79; qui c'è solo il logo in testata.
- Su un iPhone reale (PWA dalla Home) l'area sicura non è stata provata: verificata la resa con i valori di `env()` a 0 del browser di prova.
