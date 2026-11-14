# Sprint 66 — Sicurezza

> **Periodo:** 14/11/2026 · **Numero:** 66 (massimo tra `git log` = 65 e `sprints/` = 64, più uno).
> **Stato:** implementato e verificato in container; **deploy da eseguire a mano** (passi in fondo e in `DEPLOY.md` §4.5).

## Input

- **Audit di sicurezza e privacy del 2026-11-14** (sola lettura, sul commit dello Sprint 65): 1 finding critico (C1, file degli utenti scaricabili senza autenticazione), 4 alti (A1 token, A2 throttling, A3 registrazione e limiti di input, A4 dipendenze), 6 medi (M1 header, M2 push, M3 upload/rendering, M4 backup, M5 admin/allauth, M6 GDPR), 8 bassi (B1–B8). Il report non è nel repository: qui sono riportati solo i punti risolti.
- **Contenimento già applicato in produzione** prima dello sprint: `Caddyfile.prod` risponde 404 su `/media/*`.
- **Decisioni del committente:**
  - token con scadenza dopo **30 giorni di inattività** (scorrevole), non a durata fissa;
  - registrazione **su invito**, con codice in variabile d'ambiente (vuoto = registrazione aperta);
  - il login Google resta nascosto/inattivo (lo sprint 67 se ne occupa): qui non si tocca, salvo quanto serve;
  - gli utenti attuali (10 tester) possono essere costretti a rifare il login;
  - (precisazione successiva) access log di Caddy su file, conservati **14 giorni** come dichiarato nell'informativa privacy.

## Decisioni prese

- **Download con URL firmati** (`django.core.signing.TimestampSigner`, salt distinto per tipo, payload `user_id:doc_id`, validità 1 ora) invece di fetch+blob nel frontend: funziona come semplice `<a href>` anche nella PWA iOS, nessuna dipendenza nuova. Ogni errore risponde 404, mai 403. La pagina del job si ricarica ogni 20 minuti e quando torna visibile, così i link non scadono con la pagina aperta.
- **Nomi file casuali** con `upload_to` callable (`uuid4().hex`), più comando idempotente per i file esistenti (che ricodifica anche le foto). Il volume media non è più montato in Caddy.
- **Token propri** (`AuthToken`, solo SHA-256 nel DB) al posto del Token DRF: uno per login/dispositivo, logout che revoca solo il corrente, `revoke_all_tokens` pronto per cambio password e cancellazione account. SHA-256 senza salt basta perché il token è casuale a 256 bit. `SessionAuthentication` tolta dall'API: l'Admin usa comunque la sessione Django; il login Google (oggi non configurato) andrà completato con un passaggio sessione → token.
- **Throttling** DRF su cache Redis condivisa (prima `LocMemCache` per processo); nei test una `DummyCache`, con `LocMemCache` solo nei test che la richiedono. Login limitato sia per IP sia per email (hash). Admin: wrapper semplice sulla view di login (10 errori per IP in 15 minuti), path configurabile.
- **Sottoscrizioni push oltre il limite di 10**: si eliminano le più vecchie invece di rifiutare la nuova, per non escludere mai il dispositivo corrente.
- **Quota import CV** con codice 409 come le altre quote (non 429, riservato al throttling).
- **HSTS** senza `includeSubDomains`/`preload` (come richiesto): i due warning di `check --deploy` sono silenziati esplicitamente.
- **CSP applicata subito** (non report-only), dopo aver verificato il bundle: nessuno script inline né `eval`, nessuna risorsa esterna, Radix inserisce `<style>` a runtime (quindi `'unsafe-inline'` sugli stili), anteprima PDF in iframe `blob:`.
- **Dipendenze**: aggiornamenti conservativi (minor), nessuna dipendenza nuova.

## Implementazione

### C1 — Download protetti e nomi casuali
- `apps/common/files.py`: `upload_to` casuali per `CVDocument`, `CoverLetterDocument`, `Profile.photo`; firma/verifica (`SIGNED_URL_MAX_AGE = 3600`); `sanitize_photo`.
- `apps/common/views.py` + `apps/common/urls.py`: `GET /api/files/cv/<doc_id>/?s=`, `/api/files/cover-letter/<doc_id>/?s=`, `/api/files/photo/?s=`. Nessuna autenticazione DRF (la firma è la credenziale), verifica di firma, scadenza, documento↔firma, proprietario attivo; `FileResponse` con i nomi suggeriti esistenti e `Cache-Control: private, no-store`.
- `JobSerializer`: `cv_pdf_url`/`cover_letter_pdf_url` firmati; nomi suggeriti estratti in `cv_download_filename`/`cover_letter_download_filename`.
- `ProfileSerializer`: `photo` solo in scrittura, `has_photo` e `photo_url` firmato.
- Le quattro chiamate `pdf_file.save(...)` passano un nome neutro: il nome reale lo decide l'`upload_to`.
- `config/urls.py`: rimossa la rotta `/media/` di sviluppo. `vite.config.js`: rimosso il proxy `/media`.
- **B1 foto**: ricodifica con Pillow (JPEG/PNG/WebP, max 5 MB e 4000×4000, `ImageOps.exif_transpose`, nessun EXIF/GPS/XMP).
- Comando `secure_media_files [--dry-run] [--delete-orphans]` (`apps/common/management/commands/`).
- `docker-compose.prod.yml`: tolto `media_data` dal servizio `caddy`; `Caddyfile.prod` mantiene `respond 404` su `/media/*` con commento aggiornato. WeasyPrint continua a leggere la foto dal filesystem (`file://…photo.path`, verificato dal test esistente "foto inclusa nel PDF").
- Frontend: `JobDetailPage.jsx` (refresh dei link), `ProfilePage.jsx` (anteprima della foto con l'URL firmato), `accept="image/jpeg,image/png,image/webp"` in Profilo e Onboarding. `JobCard.jsx` usa `cv_pdf_url` solo come booleano: nessuna modifica.

### A1 — Token
- `AuthToken` (`apps/accounts/models.py`, migrazione `accounts/0007`), helper in `apps/accounts/tokens.py`, autenticazione `apps/accounts/authentication.py` (`ExpiringTokenAuthentication`, `AUTH_TOKEN_IDLE_DAYS = 30`, `last_used_at` al più ogni ora), Admin in sola lettura.
- `POST /api/accounts/logout/`. Migrazione dati `accounts/0008_delete_drf_tokens` (cancella le righe di `authtoken_token` se la tabella esiste); `rest_framework.authtoken` tolta da `INSTALLED_APPS`.
- Frontend: `logout()` chiama l'endpoint e poi cancella il token locale; su 401 con token `apiFetch` cancella il token ed emette `app-apply:auth-expired`, che `AuthContext` usa per tornare al login; tolto `credentials: 'include'`.

### A2 — Throttling e admin
- `CACHES` su Redis (`REDIS_CACHE_URL`, default `redis://redis:6379/2`), throttle `anon` 60/min, `user` 300/min, `login` 10/min per IP, `login_email` 10/ora per email, `register` 5/ora, `cv_import` 10/ora, `chat` 20/min (solo POST, `PostOnlyScopeMixin`), `draft_preview` 60/min; `NUM_PROXIES = 1`.
- Login: messaggio unico e `authenticate()` anche per email inesistente (tempi uniformi).
- Admin: `apps/accounts/admin_login.py`; `DJANGO_ADMIN_PATH` letto da Django e passato al container `caddy` (`handle /{$DJANGO_ADMIN_PATH:admin/}*`).
- Frontend: messaggio "Troppi tentativi…" (it/en) su 429 in login e registrazione.

### A3/M3 — Registrazione e limiti di input
- `REGISTRATION_INVITE_CODE` (confronto con `hmac.compare_digest`, controllo prima dell'unicità dell'email); campo "Codice di invito" nel form (it/en).
- `max_length` lato server: descrizione job manuale 20.000; indicazioni cover letter/messaggi e istruzione gap 2.000; gap 30 × 500; messaggi chat 2.000 (e 50 `focus_bullets`); destinatario 255/500; `objective_statement` 2.000; sommario 5.000; note istruzione 3.000; bullet 30 × 2.000 e tecnologie 50 × 200. Input serializer dedicati in `apps/jobs/serializers.py`.
- `apps/cv/draft_validation.py`: validazione strutturale e dimensionale del `content_json` di bozze CV e cover letter in PATCH e anteprima.
- Chat: nel prompt solo gli ultimi 20 turni di cronologia.
- Import CV: 5 MB, formato dai primi byte, PDF max 10 pagine, `.docx` max 30 MB decompresso, testo troncato a 30.000 caratteri, quota `DailyQuota.cv_import_count` 5/giorno (migrazione `jobs/0016`), errore AI → 502 con quota restituita.
- `DATA_UPLOAD_MAX_MEMORY_SIZE` 2,5 MB, `FILE_UPLOAD_MAX_MEMORY_SIZE` 5 MB; Caddy `request_body max_size 10MB` su `/api/*`.

### A4 — Dipendenze
- Backend: Django 5.1 → **5.2 LTS** (5.2.19), DRF 3.15 → 3.16 (3.16.1), Celery 5.4 → 5.5 (5.5.3), Pillow 10.4 → **12** (12.3.0), allauth minimo 65.20 (installata 65.22.1). Nessuna deprecazione segnalata eseguendo la suite con `-W default::DeprecationWarning`. Non aggiornati di proposito: WeasyPrint 69 (una major può cambiare l'impaginazione del CV a 1 pagina), gunicorn 23, redis-py 5, python-docx 1.1.
- Frontend: versioni già recenti (React 19.2, Vite 7.3, React Router 7.18, Tailwind 4.3, vite-plugin-pwa 1.2): nessun aggiornamento necessario.

### M1 — Header
- `Caddyfile.prod`: HSTS, `nosniff`, `X-Frame-Options DENY`, `Referrer-Policy strict-origin-when-cross-origin` (allineato anche `SECURE_REFERRER_POLICY` di Django), `Permissions-Policy`, `-Server`, CSP (testo e motivazioni in `Docs/02-specifiche-tecniche-v5.md` §8.3). Le operazioni `header` di Caddy sono differite (c'è una cancellazione) e quindi sostituiscono i valori di Django: nessun duplicato. Django: `SECURE_HSTS_SECONDS` con `DEBUG=false`.

### M2 — Push
- Allowlist dell'endpoint (https, nessuna porta né credenziali, host FCM/Mozilla/Apple/Windows), massimo 10 sottoscrizioni per utente, `webpush(..., timeout=10)`, 404/410 → sottoscrizione eliminata, altri errori registrati (solo id) senza interrompere né le altre sottoscrizioni né gli altri utenti.

### B2/B3/B5
- `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` (pubblici con `AllowAny` esplicito: registrazione, login, download firmati); renderer solo JSON con `DEBUG=false`.
- Lost update di `extra_credit`: confermato (il `save()` completo riscriveva `request.user`); ora `save(update_fields=…)` sui soli campi validati. Aggiunta anche la validazione del fuso orario (un nome non valido avrebbe fatto fallire il task delle notifiche).
- `DEBUG` di default falso; con `DEBUG=false` avvio rifiutato se `DJANGO_SECRET_KEY` è vuota o contiene "insecure".

### B7 — Container non-root
- `backend/Dockerfile`: utente `app` uid 1000, codice di root in sola lettura, scrivibili solo `/app/staticfiles` e `/app/mediafiles`. Verificati come non-root: `pg_dump` (dump schema-only verso `/tmp`), WeasyPrint (rendering di un PDF), avvio dei comandi Django e Celery.
- In `settings.py`, con `manage.py test` il `MEDIA_ROOT` è una cartella temporanea: alcuni test scrivevano file nel `MEDIA_ROOT` di default, cioè, lanciati nel container di produzione, nel volume `media_data`. Nel volume ci sono infatti circa 124 PDF con nomi del tipo `cv_<n>_<n>_<suffisso>.pdf`, in buona parte probabilmente lasciati da esecuzioni precedenti della suite (il suffisso è quello che Django aggiunge quando il nome è già occupato). `secure_media_files --delete-orphans` elimina solo i file non referenziati da nessun record, quindi rimuove quelli dei test e lascia quelli di produzione, qualunque nome abbiano: controllare comunque prima l'elenco del `--dry-run`.

### B8 — Log
- Rotazione `json-file` (5 × 10 MB) per tutti i servizi di `docker-compose.prod.yml`.
- Access log di Caddy in JSON su file nel volume `caddy_logs`, ruotato ogni 24 ore o a 10 MiB e cancellato dopo 14 giorni; parametro `s` sostituito con `REDACTED`, `Authorization`/`Cookie`/`Set-Cookie` rimossi (verificato con un Caddy di prova).
- `LOGGING` Django su stdout: errori 5xx, warning, log del package `apps`.

## Verifica

- **Backend** (immagine ricostruita, nessun container in esecuzione toccato): `docker compose -f docker-compose.prod.yml run --rm --no-deps -e DJANGO_DEBUG=true web python manage.py test --noinput` → **299 test OK** (234 preesistenti + 65 nuovi: `accounts/test_security.py`, `common/test_files.py`, `jobs/test_input_limits.py`, più test aggiunti in `accounts/tests.py`, `notifications/tests.py`, `cv/tests.py`). Adeguati 4 test esistenti al nuovo comportamento (URL firmato del CV, `has_photo`/`photo_url`, endpoint push in allowlist, cache dell'autocomplete).
- `makemigrations --check --dry-run` → nessuna differenza. `check --deploy` con `DEBUG=false` → nessun problema (2 warning HSTS silenziati per scelta).
- **Frontend**: `docker run --rm --entrypoint sh app-apply-frontend-build -c "npm run build && npx oxlint src"` → build OK, oxlint 0 errori (9 warning `only-export-components` preesistenti). Bundle verificato per la CSP.
- **Caddy**: `caddy validate` sul `Caddyfile.prod` → "Valid configuration"; sostituzione di `DJANGO_ADMIN_PATH` verificata con `caddy adapt`; header e access log verificati su un Caddy di prova senza upstream.
- **Non verificato** (richiede il deploy o un browser): anteprima PDF degli editor con la CSP attiva su Chrome/Safari/Firefox, download dalla PWA iOS, e2e Playwright.

## Passi di deploy (manuali, in ordine)

Dettaglio con i comandi in `DEPLOY.md` §4.5.
1. Backup locale del database.
2. `.env`: `REGISTRATION_INVITE_CODE`, eventualmente `DJANGO_ADMIN_PATH` (con "/" finale).
3. `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
4. `docker compose -f docker-compose.prod.yml stop web worker beat`.
5. `chown -R 1000:1000` dei volumi `app-apply_media_data` e `app-apply_static_data` (container `alpine` usa e getta).
6. `docker compose -f docker-compose.prod.yml up -d` (migrazioni; i vecchi token sono cancellati; Caddy ricreato con la nuova configurazione, altrimenti `caddy reload`).
7. `secure_media_files --dry-run --delete-orphans`, poi senza `--dry-run`, poi `--delete-orphans`.
8. Verifiche: stack coerente, `id` = uid 1000, header con `curl -sI`, `/media/...` → 404, login + download + anteprima editor dalla PWA, admin sul nuovo path, access log presente.
9. Comunicare ai tester che devono rifare il login e il codice di invito ai nuovi utenti.

## Cosa manca

- **Login Google**: con `SessionAuthentication` tolta dall'API, un accesso via allauth non produce un token: va completato (o nascosto) nello sprint 67, come già previsto.
- **Fuori perimetro di questo sprint** (restano aperti dall'audit): backup esterno e cifratura (M4), restrizione dell'admin per IP e superficie di allauth (M5), cancellazione/export dei dati e pulizia automatica dei file sostituiti (M6, oggi solo con `secure_media_files --delete-orphans`), race condition minori sulle ricerche (B4), delimitazione dei contenuti di terzi nei prompt (B6).
- Nessun endpoint per annullare la sottoscrizione push al logout.
- `docker-compose.yml` (sviluppo) usa la stessa immagine non-root con il bind-mount del codice: su un host dove la cartella `backend/` non è scrivibile da uid 1000 servono i permessi adeguati (o `user:` nel compose di sviluppo).
- e2e: il limite di 10 login al minuto per IP può far fallire una suite lunga lanciata contro lo stesso ambiente.
- La tabella `authtoken_token` resta nel DB (vuota): si può eliminare in futuro.
