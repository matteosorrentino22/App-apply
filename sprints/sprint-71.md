# Sprint 71 — Testi del backend nella lingua dell'interfaccia (it/en)

> **Periodo:** 14/11/2026 · **Numero:** 71 (massimo tra `git log` = 70 e `sprints/` = 70, più uno).
> **Stato:** implementato e verificato in container usa e getta; **deploy da eseguire a mano** (passi in fondo e in `DEPLOY.md` §4.9). Nessuna migrazione, nessuna variabile d'ambiente nuova.

## Input

- **Richiesta del committente:** includere la traduzione dei testi del backend. Messaggi d'errore e di validazione delle API, testi delle notifiche push, prefisso del limite per lingua nella motivazione del punteggio e ogni altro testo che il backend restituisce all'utente erano solo in italiano anche con l'interfaccia in inglese (`Docs/01` §8.A punto 38, `Docs/02` §11 punto 23). Le email di servizio dello Sprint 67 erano già it/en, con un dizionario proprio.
- **Indicazioni:** meccanismo standard di Django (gettext, `locale/en/LC_MESSAGES/django.po`, `LocaleMiddleware`), la PWA invia `Accept-Language` con la lingua dell'interfaccia, `translation.override(user.interface_language)` nei task; msgid italiani; non tradurre prompt AI, log, `RunLog`, Django Admin, commenti; i testi generati dall'AI non cambiano. Nessuna nuova dipendenza.

## Decisioni prese

- **`.mo` compilato e committato**, non compilato nella build. È la soluzione più semplice e robusta qui: nessun pacchetto `gettext` e nessun passo in più nel `Dockerfile` (che restano invariati), e soprattutto funziona anche nello stack di sviluppo, che monta `./backend` su `/app` e nasconderebbe un `.mo` generato nell'immagine. Il rischio tipico dei binari committati (`.po` modificato e `.mo` dimenticato) è coperto da un test che confronta voce per voce il catalogo del `.mo` con il `.po`. `makemessages`/`compilemessages` restano riproducibili con un comando documentato (`DEPLOY.md` §4.9) che installa `gettext` in un container usa e getta.
- **Locale solo per `/api/`**: `apps.common.middleware.ApiLocaleMiddleware` è una `LocaleMiddleware` di Django che agisce solo sulle richieste API. Con la `LocaleMiddleware` normale il Django Admin avrebbe seguito la lingua del browser, mescolando l'inglese di Django con le etichette italiane dell'app; così resta in italiano come prima. A fine richiesta la lingua torna quella di default sul thread (nessuna "eredità" tra richieste o nei test). `LANGUAGE_CODE` passa da `it-it` a `it` (stesso catalogo), `LANGUAGES = [it, en]`: qualunque altra lingua, o nessun header, dà l'italiano.
- **PWA**: `Accept-Language` esplicito in `apiFetch` e nei due `fetch` diretti delle anteprime PDF, con la stessa regola di `LanguageContext` (scelta salvata, altrimenti lingua del dispositivo), letta a ogni chiamata da `src/i18n/language.js`: nessuna sincronizzazione da mantenere con lo stato React, e un cambio di lingua vale dalla chiamata successiva (compresa la `PATCH /me` che lo salva).
- **Email di servizio sullo stesso meccanismo**: il dizionario it/en di `emails.py` è diventato una serie di `gettext_lazy` con msgid italiani, composti dentro `translation.override(lingua del destinatario)`; le traduzioni inglesi sono state copiate nel `.po` in modo automatico dal dizionario precedente, quindi i testi inviati sono identici a prima (verificato da un test). La lingua resta quella dell'utente (`interface_language`), non quella della richiesta.
- **Prefisso del cap lingua**: è salvato in `score_reasoning`, quindi è tradotto nella lingua dell'interfaccia del proprietario del job al momento dello scoring (`translation.override(job.user.interface_language)` in `_apply_score_result`). Le motivazioni salvate prima restano in italiano: nessuna migrazione dati (la parte scritta dall'AI non è traducibile e riscrivere solo il prefisso non è sembrato utile).
- **Notifiche push**: payload come `gettext_lazy` risolti per ogni utente (`notification_payload`), indipendentemente dalla lingua attiva nel processo del worker.
- **Messaggio del 429 proprio** (`apps.common.exceptions.api_exception_handler`): il testo italiano di DRF è tradotto a metà ("La richiesta è stata limitata (throttled). Expected available in N seconds.", manca il plurale nel catalogo di DRF) e per i limiti orari e giornalieri conta migliaia di secondi. Ora: "Troppe richieste: riprova tra N secondi/minuti/ore." / "Too many requests: please try again in N seconds/minutes/hours." (con `ngettext`). Il resto dei messaggi standard di DRF e Django (campo obbligatorio, lunghezza massima, password, autenticazione, non trovato) esce già tradotto nelle due lingue con i cataloghi dei pacchetti: verificato, nessuna voce nel nostro `.po`.
- **Segnaposto con nome** (`%(max)s`, `%(values)s`, `%(path)s`; `{link}` nelle email, già `str.format`) al posto delle f-string, che `makemessages` non estrae. Dove un modulo usava `_` come variabile di scarto (`quota, _ = …get_or_create(…)`, `partition`) è stata rinominata (`_created`, `_sep`), altrimenti avrebbe nascosto `gettext`.
- **Non tradotti, per scelta**: prompt e testi inviati al modello AI (compresi i riepiloghi di profilo "Nessuna esperienza in profilo." ecc.), risposte e contenuti generati dall'AI, log, `RunLog` (le eccezioni registrate sono quelle originali, non i messaggi tradotti per l'utente), Django Admin (etichette, scelte dei modelli, azioni, messaggio del limite dei login all'admin), comandi di gestione, nomi dei file scaricati, chiavi del JSON dell'export (il `README.txt` dell'export era già bilingue), etichette fisse dei documenti (seguono la lingua del documento).

## Implementazione

### Backend
- `config/settings.py`: `LANGUAGE_CODE = "it"`, `LANGUAGES`, `LOCALE_PATHS = [BASE_DIR / "locale"]`, `ApiLocaleMiddleware` dopo `SessionMiddleware`, `REST_FRAMEWORK["EXCEPTION_HANDLER"]`.
- Nuovi: `apps/common/middleware.py` (`ApiLocaleMiddleware`), `apps/common/exceptions.py` (handler con il 429), `backend/locale/en/LC_MESSAGES/django.po` e `django.mo`.
- Testi marcati con `gettext`/`gettext_lazy` in: `accounts` (`views.py`: verifica email, link scaduti/non validi, reset, cambio email, email non disponibile — ora `_email_unavailable_response()`; `serializers.py`: consensi, età minima, invito, email già registrata, credenziali, fuso, password, conferma, cambio email; `authentication.py`: token non valido, sessione scaduta; `permissions.py`: gate legale; `emails.py`: oggetti, corpi e firma delle sei email), `common/files.py` (foto), `cv` (`manual_generation.py`, `cover_letter_manual_generation.py`, `referral_message_manual_generation.py`, `draft.py`, `cover_letter_draft.py`, `draft_chat.py`, `cover_letter_draft_chat.py`, `draft_validation.py`), `jobs` (`views.py`: bozze, chat, filtri della lista, filtri salvati; `serializers.py`; `application.py`; `tasks.py`: raccolta manuale; `import_service.py`; `manual_job_service.py`; `scoring.py`: prefisso del cap), `notifications` (`serializers.py`, `tasks.py`), `profiles` (`views.py`, `serializers.py`, `cv_import.py`), `searches/services.py`.
- **119 voci tradotte** nel `.po` (116 singolari e 3 plurali del 429), 0 `fuzzy`, 0 vuote.

### Frontend
- `src/i18n/language.js` (nuovo): `LANG_STORAGE_KEY`, `SUPPORTED_LANGUAGES`, `detectDeviceLanguage`, `readStoredLanguage`, `currentLanguage`; `translations.js` li ri-esporta, `LanguageContext.jsx` li usa (comportamento invariato).
- `src/api/client.js` e `src/api/jobs.js` (anteprime): header `Accept-Language`.
- Nessuna modifica alle pagine: la PWA mostra già il `detail` del server (toast e messaggi) e gli errori per campo (`formatApiErrorDetail`); dove ha codici stabili (import CV, verifica email, gate, 429 nelle pagine di accesso) usa i propri testi it/en. Verificato che nessun punto confronta o mappa i testi italiani del server. Con l'interfaccia in italiano i testi mostrati sono gli stessi di prima; l'e2e `account.spec.js` che attende "Hai raggiunto il numero massimo di ricerche salvate per il tuo piano." gira con `locale: 'it-IT'` e resta valido.

### Test
- `apps/common/test_i18n.py` (17 test): `.po` senza `fuzzy` né `msgstr` vuoti e `.mo` identico al `.po`; testi it/en secondo `Accept-Language` per login errato (anche senza header, con `fr-FR` → italiano, `en-GB` → inglese), registrazione con codice di invito errato, quota esaurita della generazione CV, import non consentito al piano Free, raccolta manuale già usata, lunghezza massima (messaggio DRF), parametro non valido con segnaposto, gate legale, throttling (429); Admin in italiano con browser inglese; lingua non lasciata attiva dopo la richiesta; payload delle notifiche mattutina e di inattività e prefisso del cap lingua secondo `interface_language` (anche con l'altra lingua attiva sul thread); email di servizio con gli stessi testi dello Sprint 67.

## Verifica

- **Backend** (immagine `appapply-s71-web`, PostgreSQL 16 e Redis 7 usa e getta sulla rete `appapply-s71-net`, rimossi a fine prova; nessun container o dato di produzione toccato): `python manage.py test --noinput` con `DJANGO_DEBUG=true` → **465 test OK** (448 di base + 17 nuovi). `makemigrations --check --dry-run` → "No changes detected"; `check` e `check --deploy` (con `DEBUG=false`) senza problemi.
- **Catalogo**: `makemessages` rilanciato due volte di seguito senza differenze; `msgfmt --check --statistics` → 115 messaggi tradotti al primo giro (prima dei plurali), poi 119 voci nel `.po`; `compilemessages` OK.
- **DRF/Django**: verificati in container i messaggi standard nelle due lingue (`Throttled`, `NotAuthenticated`, `max_length`, `required`); da qui la correzione del 429.
- **Frontend** (immagine `appapply-s71-frontend-build`): `npm run build` OK, `npx oxlint src` 0 errori (9 warning `only-export-components` preesistenti); nel bundle `"Accept-Language": currentLanguage()` su `apiFetch` e anteprime.
- **Marcatori di conflitto**: `git grep -n -E "^(<<<<<<<|>>>>>>>)"` → nessuno.
- **Non verificato** (servono il deploy o un browser): PWA reale con interfaccia in inglese, notifiche push ricevute su un dispositivo, e2e Playwright.

## Passi di deploy

Dettaglio in `DEPLOY.md` §4.9.
1. `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
2. `docker compose -f docker-compose.prod.yml up -d` (nessuna migrazione, nessuna variabile nuova).
3. Le schede aperte si aggiornano con "Nuova versione disponibile — Aggiorna"; finché girano il bundle precedente ricevono i messaggi nella lingua del browser (it/en) o in italiano.
4. Verifiche: login con password errata dalla PWA in inglese ("Invalid credentials.") e in italiano ("Credenziali non valide."); Admin ancora in italiano.

## Cosa manca

- Le **motivazioni con il prefisso del cap** salvate prima dello Sprint 71 restano in italiano, e quelle nuove restano nella lingua del momento dello scoring anche se l'utente cambia lingua dopo.
- Un **testo nuovo non marcato** con `gettext` resta in italiano senza che nessun test se ne accorga: il test del catalogo controlla solo le voci già estratte (regola aggiunta in `CLAUDE.md`, "Convenzioni di codice").
- I messaggi di errore per campo restano preceduti dal **nome tecnico del campo** (`objective_statement: …`) dove la PWA usa `formatApiErrorDetail`, come prima.
- `makemessages` propone traduzioni `fuzzy` per frasi simili (successo durante lo sprint con il messaggio del 429): vanno controllate a mano; il test impedisce di rilasciarle.
- Le pagine di allauth (`/accounts/*`, non usate in produzione) restano in italiano.
- `gettext` non è nell'immagine: rigenerare il catalogo richiede il container usa e getta di `DEPLOY.md` §4.9 (rete per `apt-get`).
