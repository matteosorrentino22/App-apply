# Sprint 03 — Autenticazione

## Input
- Sprint 02 completato (modello `User` esteso disponibile).
- Riferimenti: `01-specifiche-funzionali-v4.md` §3 (Setup e onboarding), §4.1; `02-specifiche-tecniche-v3.md` §3.7.

## Obiettivo
Implementare registrazione/login email+password (sistema utenti nativo Django) e login Google (django-allauth), esposti via API REST (Django REST Framework); gestione dei campi onboarding su `User` (`timezone`, `interface_language`, `cv_language_mode`, `cv_include_photo`, `objective_statement`).

## Risultato atteso
Un utente può registrarsi via API con email/password, autenticarsi, e ottenere credenziali valide (token/sessione); un utente può autenticarsi via Google OAuth; i campi onboarding sono leggibili/scrivibili via API.

## Criteri di verifica
- `POST` all'endpoint di registrazione con email/password crea uno `User`; il campo password in DB è un hash, mai la password in chiaro.
- Login con credenziali corrette restituisce credenziali valide (token/sessione); con password errata restituisce 4xx.
- Un endpoint protetto (es. `GET /api/profile/`) restituisce 401/403 senza autenticazione e 200 con autenticazione valida.
- Flusso OAuth Google configurato in ambiente di sviluppo: redirect a Google, callback crea/collega uno `User` (verificabile manualmente con credenziali OAuth di test).
- API consente di impostare e rileggere `timezone`, `interface_language`, `cv_language_mode`, `cv_include_photo`, `objective_statement` sull'utente autenticato.

## Output per lo sprint successivo
Sistema di autenticazione funzionante, riusato da tutte le API successive (profilo, ricerche, job) per l'identificazione e l'isolamento dati per utente.

---

## Esito (2026-07-26)

**Stato: completato**, con una riserva sul flusso Google OAuth end-to-end (vedi Criticità, stesso tipo di limite ambientale degli sprint precedenti).

### Cosa è stato fatto
- **Email/password (DRF, token).** `apps.accounts.email` è ora `unique=True` (era il campo non-unique di `AbstractUser`): l'email è l'identificativo di accesso, come da §3.7/§4.1 tecniche; lo `username` nativo di Django resta popolato (uguale all'email) solo perché richiesto dallo schema `AbstractUser` già migrato dallo Sprint 01, ma non è mai usato dal client.
  - `POST /api/accounts/register/` — crea l'utente (`RegisterSerializer`, valida email univoca e password con i validator nativi di Django) e restituisce un token DRF (`rest_framework.authtoken`).
  - `POST /api/accounts/login/` — verifica le credenziali con `django.contrib.auth.authenticate()` e restituisce lo stesso token (creato se non esiste già); credenziali errate → 400 con messaggio di errore.
  - `GET/PATCH /api/accounts/me/` — endpoint protetto (`IsAuthenticated`) che espone i campi di onboarding (`timezone`, `interface_language`, `cv_language_mode`, `cv_include_photo`, `objective_statement`); `id`, `email`, `plan` sono presenti ma read-only (il piano si cambia solo da Admin/voucher, §4.11 funzionali — non è un campo che l'utente scrive da sé).
  - `TokenAuthentication` aggiunta come prima authentication class in `REST_FRAMEWORK` (oltre alla `SessionAuthentication` già presente dallo Sprint 01, che resta utile per l'admin/browsable API).
- **Login Google (django-allauth).** Aggiunte le app `allauth`, `allauth.account`, `allauth.socialaccount`, `allauth.socialaccount.providers.google`, più `django.contrib.sites` (dipendenza richiesta da allauth) e `rest_framework.authtoken`, con `AccountMiddleware` e `AUTHENTICATION_BACKENDS` estesi. URL montati su `/accounts/...` (standard allauth: `/accounts/google/login/`, `/accounts/google/login/callback/`, ecc.). Le credenziali dell'app Google (`client_id`/`secret`) sono lette da variabili d'ambiente (`GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`, aggiunte a `.env.example` vuote) tramite `SOCIALACCOUNT_PROVIDERS["google"]["APPS"]` — **non** tramite un record `SocialApp` da creare a mano in Django Admin, per restare coerenti con la regola di `CLAUDE.md` "solo variabili d'ambiente, mai hardcoded" (l'alternativa via Admin è comunque supportata nativamente da allauth se in futuro si preferisse quella via).
- Aggiunte a `requirements.txt`: `django-allauth`, più le sue dipendenze dirette non transitivamente installate dal resolver minimale (`requests`, `cryptography`) necessarie al provider Google (verifica ID token / chiamate OAuth).
- Nuova migrazione `accounts.0003_alter_user_email` (email `unique=True`) più le migrazioni di terze parti (`account`, `authtoken`, `sites`, `socialaccount`), tutte committate.

### Decisione tecnica non esplicitamente richiesta, da segnalare
Il login usa un **token DRF semplice** (non JWT, non sessione-only) come "credenziali valide" richieste dal criterio di verifica. Motivo: è lo standard più semplice e documentato per un'API REST consumata da una SPA/PWA (coerente con "preferire soluzioni standard/documentate", CLAUDE.md), non richiede gestione di scadenza/refresh (fuori scope MVP) e convive senza conflitti con `SessionAuthentication` (usata da allauth per il flusso Google, che è basato su cookie di sessione). Se in futuro si vorrà unificare i due flussi (es. un token anche dopo il login Google), è un'estensione puntuale, non una modifica architetturale.

### Criticità riscontrate
1. **Verifica end-to-end del login Google non eseguibile in questo ambiente.** Non essendo disponibili credenziali OAuth Google reali (nemmeno di test) nella sandbox, ho verificato che l'app sia *configurata correttamente* fino al punto massimo raggiungibile senza credenziali reali:
   - `GET /accounts/google/login/` → 200, pagina di conferma standard allauth.
   - Il relativo `POST` (submit del form di conferma) → **302 con `Location: https://accounts.google.com/o/oauth2/v2/auth?client_id=&redirect_uri=...%2Faccounts%2Fgoogle%2Flogin%2Fcallback%2F&scope=email+profile&response_type=code&...`**: il redirect verso Google avviene correttamente, con il `redirect_uri` di callback giusto (il `client_id` è vuoto perché `.env` non contiene credenziali reali in questo ambiente).
   - `GET /accounts/google/login/callback/` risponde (401, non 404): la rotta di callback è registrata e raggiungibile.
   Il passo che resta da fare — completare un vero round-trip con Google e verificare che il callback crei/collega uno `User` — richiede credenziali OAuth di test reali (client ID/secret di un progetto Google Cloud) e va eseguito manualmente in un ambiente con accesso a Google (dev locale o staging), impostando `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET` in `.env`. Non è un limite del codice, ma delle credenziali disponibili in sandbox.
2. **`docker compose up` reale non eseguibile**, stessa causa (policy di rete della sandbox) degli Sprint 01–02; `docker compose config` con un `.env` di prova confirma che il file resta sintatticamente valido dopo le nuove dipendenze.

### Verifica eseguita (virtualenv locale + PostgreSQL/Redis di sistema, come negli sprint precedenti)
| Criterio | Esito |
|---|---|
| `POST` registrazione crea `User`, password in DB è hash (mai in chiaro) | ✅ (`pbkdf2_sha256$...`, verificato che la password in chiaro non compare nel campo) |
| Login con credenziali corrette → credenziali valide (token); password errata → 4xx | ✅ (200 + token; 400 con messaggio di errore) |
| Endpoint protetto (`GET /api/accounts/me/`) → 401 senza auth, 200 con auth valida | ✅ |
| Flusso OAuth Google configurato: redirect a Google, callback registrato | ✅ configurazione verificata fino al redirect (vedi Criticità §1); round-trip completo da verificare con credenziali reali |
| API imposta/rilegge `timezone`, `interface_language`, `cv_language_mode`, `cv_include_photo`, `objective_statement` | ✅ (`PATCH` + `GET` su `/api/accounts/me/`, incluso il tentativo di scrivere `plan` correttamente ignorato perché read-only) |
| `makemigrations --check` nessuna differenza | ✅ |

### Cosa manca
- Bridging opzionale "token DRF anche dopo login Google" (non richiesto dai criteri; da valutare quando il frontend PWA — Sprint 18+ — dovrà consumare l'API dopo un login social).
- Verifica manuale del round-trip Google con credenziali reali (vedi Criticità §1).
- Un vero smoke test di `docker compose up -d` (stessa riserva degli sprint precedenti).