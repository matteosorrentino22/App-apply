# Sprint 70 — Difetti di account, profilo, notifiche e frontend

> **Periodo:** 14/11/2026 · **Numero:** 70 (lo Sprint 69, stati del job, generazione, editor e chat, networking, è sviluppato in parallelo su un altro ramo; il coordinatore unisce i due lavori).
> **Stato:** implementato e verificato in container su un ramo separato; **deploy da eseguire a mano** (passi in fondo e in `DEPLOY.md` §4.8). Nessuna migrazione.

## Input

- **Richiesta del committente:** correggere i difetti noti di account, profilo, notifiche e frontend elencati nelle specifiche as-is: `Docs/01-specifiche-funzionali-v6.md` §8.A punti 35–44 e 60 (email non modificabile), `Docs/02-specifiche-tecniche-v5.md` §11 punti 11, 22, 33, 35, 40, più i limiti dei testi del profilo (bullet) e l'e2e obsoleto.
- **Fuori perimetro**, perché li tratta lo Sprint 69: pagina del job, editor e chat di CV e cover letter, `apps/cv`, messaggi di networking, stati del job. Non sono stati toccati `JobDetailPage`, `CvDraftEditorPage`, `CoverLetterDraftEditorPage`, i pannelli chat, `JobCard` né `apps/cv`.
- Non richiesti: login Google (punto 33), lingua dei messaggi del server (punto 38).

## Decisioni prese

- **Contatori e prezzi in un endpoint dedicato** (`GET /api/accounts/usage/`) invece di estendere `/me`: `/me` è letto a ogni avvio e dopo ogni impostazione, i contatori servono solo nelle pagine con azioni a massimale. L'endpoint legge le stesse costanti dei servizi e calcola `next_charge` (`included` / `credit` / `blocked` / `unavailable`), così la PWA non replica le regole. È dietro il gate delle accettazioni (permessi di default).
- **Conferma prima dell'addebito con `window.confirm`**, non un dialog: funziona ovunque (anche PWA iOS), nessun componente nuovo, e compare solo quando l'azione andrebbe davvero a credito. Applicata a import da link, job manuale e generazione del CV dalla lista (che è in `JobListPage`, già toccata da questo sprint). **Pagina del job e chat degli editor non toccate**: l'integrazione (un `ActionCostHint` accanto ai pulsanti e `confirmCreditCharge` prima della chiamata, istruzioni in `Docs/02` §5.20) va fatta dopo il merge con lo Sprint 69.
- **Profilo incompleto: banner fisso, non rimando automatico.** Stessa regola della generazione (`Profile.is_complete`, almeno un titolo di studio), esposta da `/me` come `profile_status`. Con profilo vuoto il link porta all'onboarding (che ha l'import del CV), altrimenti al Profilo: l'onboarding crea sempre voci nuove e duplicherebbe quelle di chi ha già un profilo parziale. Nascosto in onboarding e Profilo.
- **Fuso orario senza flag "scelto dall'utente"** (nessuna migrazione): in registrazione la PWA manda il fuso del browser (un nome non valido è ignorato, mai un errore); in onboarding si propone il fuso del dispositivo se quello salvato è ancora il default Europe/Rome. Selettore nativo (`<select>`) con `Intl.supportedValuesOf('timeZone')`.
- **Logout e push:** la PWA manda l'endpoint del browser a `POST /api/accounts/logout/` (il server elimina solo quella `PushSubscription` dell'utente) e poi annulla la sottoscrizione nel browser. Nessun endpoint nuovo. Il dispositivo deve riattivare le notifiche al prossimo accesso.
- **Riallineamento di `last_notified_at`** a "adesso" in entrambi i punti in cui la preferenza torna attiva (`PATCH /me` false→true, nuova sottoscrizione con preferenza spenta). Il promemoria di inattività non cambia.
- **Import CV: `code` stabile in ogni errore** (`CVFileRejected(code, message)`, sottoclasse di `ValueError` per non rompere chi intercettava `ValueError`); la PWA traduce i codici, controlla i 5 MB prima dell'invio e tratta un 413 di Caddy come file troppo grande.
- **Foto: `DELETE /api/profiles/me/photo/`**, file cancellato a commit avvenuto come nei segnali dello Sprint 67. La rimozione è immediata (con conferma), la sostituzione resta legata a "Salva modifiche".
- **Limiti dei bullet: 15 per esperienza × 400 caratteri.** La pipeline CV non ha limiti propri: il budget è di 18 bullet in tutto il CV (doc 03 §5) e ogni bullet deve occupare 1–2 righe (~220 caratteri), quindi 15 × 400 lascia margine. Non retroattivi: su un'esperienza esistente sono ammessi tanti elementi quanti già ne ha (se più di 15) e i testi lunghi già presenti, ma non elementi in più né testi lunghi nuovi (la pagina Profilo rimanda sempre tutti i bullet). Il limite della bozza dell'editor (`apps/cv/draft_validation.py`, 30 × 2.000) non è stato toccato (area Sprint 69). Aggiunto anche un tetto al numero di voci per sezione (30 esperienze, 15 istruzioni, 100 competenze, 50 certificazioni, 36 lingue), solo in creazione. Gli altri testi del profilo che vanno al modello avevano già un `max_length` (sommario 5.000, note 3.000, obiettivo 2.000, campi `CharField` 255, tecnologie 50 × 200).
- **Cambio email con token firmato senza stato** (`TimestampSigner.sign_object({id, old, new})`, salt dedicato, 3 giorni), stesso schema della verifica dello Sprint 67: nessuna tabella. Il token contiene l'email attuale, quindi dopo il cambio non vale più. La richiesta risponde allo stesso modo anche se il nuovo indirizzo è già registrato (in quel caso nessuna email), per non rivelare gli indirizzi registrati; la conferma è pubblica come la verifica (il link può essere aperto altrove). Lo `username` segue l'email (il login lo usa). Sessioni non revocate: chi cambia l'email conosce già la password. **Informativa ed export invariati**: nessun dato nuovo né conservazione nuova (l'export contiene già l'email di accesso; l'elenco delle email di servizio nell'informativa è un esempio, "cambio email" si può aggiungere alla prossima versione dei testi).
- **Nuova versione della PWA senza `virtual:pwa-register`.** Verificato nel codice di `vite-plugin-pwa` 1.2: anche con `registerType: 'prompt'` (il default, già in uso) il modulo ricarica da solo la pagina quando prende il controllo un service worker trovato dopo il caricamento (controllo periodico o un'altra scheda). Il service worker ora è registrato da `src/lib/appUpdate.js` (`injectRegister: false`), che controlla gli aggiornamenti ogni 30 minuti e al ritorno sulla scheda e, al `controllerchange` di una pagina già controllata, mostra "Nuova versione disponibile — Aggiorna". `sw.js` invariato (`skipWaiting` + `clients.claim`): un ricaricamento manuale prende sempre la versione nuova, cosa che con un service worker in attesa non succederebbe.
- **Conflitti rimasti nel merge 66+67+68**: `DEPLOY.md` conteneva ancora i marcatori `<<<<<<<`/`>>>>>>>` in tre punti (§4.4, §4.6/§4.7, §7.6); risolti tenendo entrambe le parti.

## Implementazione

### Backend
- `apps/accounts/usage.py` (nuovo) + `UsageView` → `GET /api/accounts/usage/`.
- `apps/accounts/serializers.py`: `timezone` facoltativo in registrazione (`is_valid_timezone`), `profile_status` in `/me`, riallineamento di `last_notified_at` in `update`, `EmailChangeSerializer`, `EmailChangeConfirmSerializer`.
- `apps/accounts/views.py`: `LogoutView` con `push_endpoint`; `EmailChangeRequestView`, `EmailChangeConfirmView`; `urls.py`: `email/change/`, `email/change/confirm/`, `usage/`.
- `apps/accounts/emails.py`: email `email_change_confirm` / `email_change_notice` (it/en), token `make_email_change_token` / `read_email_change_token`, `send_email_change_emails`.
- `apps/notifications/views.py`: riallineamento di `last_notified_at` alla riattivazione via sottoscrizione.
- `apps/profiles/cv_import.py`: `CVFileRejected` con codice; `views.py`: codici in tutte le risposte d'errore dell'import, `DELETE profiles/me/photo/`, `max_items` per sezione; `serializers.py`: bullet 15 × 400 non retroattivi.

### Frontend
- `App.jsx`: "Esci" nella barra in alto (icona), `ProfileCompletionBanner`, `AppUpdateBanner`, rotta pubblica `/confirm-email-change`.
- Nuovi: `lib/usage.js`, `components/ActionCost.jsx`, `components/UsageLimitsCard.jsx`, `components/TimezoneSelect.jsx`, `components/EmailChangeForm.jsx`, `components/ProfileCompletionBanner.jsx`, `components/AppUpdateBanner.jsx`, `lib/appUpdate.js`, `pages/ConfirmEmailChangePage.jsx`, `api/usage.js`, `utils/money.js`.
- `main.jsx` e `vite.config.js`: registrazione del service worker (sopra).
- `api/auth.js`: logout con endpoint push e annullamento nel browser, `timezone` in registrazione, `requestEmailChange`/`confirmEmailChange`; `lib/push.js`: `currentPushSubscription`; `api/profile.js`: `removeProfilePhoto`; `utils/date.js`: `todayInputValue(timeZone)`, `browserTimeZone`, `timeZoneOptions`.
- `JobListPage.jsx`: tolto "Esci" dall'intestazione, "oggi" nel fuso dell'utente, costi e conferma per import, job manuale e CV dalla lista. `HomePage.jsx`: contatore della raccolta manuale.
- `AccountPage.jsx`: titolo "Impostazioni"/"Settings" (il riquadro delle preferenze si chiama ora "Preferenze"), "I tuoi limiti di oggi", fuso orario, cambio email.
- `ProfilePage.jsx`: obiettivo, rimozione della foto, tecnologie; `OnboardingPage.jsx`: fuso orario, errori dell'import CV, tecnologie tenute dal pre-compilamento; `ExperienceGroupEditor.jsx` e `ChipInput.jsx`: campo tecnologie, `maxLength` e evidenziazione dei bullet troppo lunghi.
- `translations.js`: titolo di Impostazioni e nuovi gruppi `usage`, `timezone`, `appUpdate`, `profileBanner`, `emailChange`, `profileExtras`, `cvImport` (it/en, aggiunti dopo il gruppo `account`).
- e2e: tolto da `job-list.spec.js` il test dell'arricchimento (funzione rimossa nello Sprint 44); codice di invito da `E2E_INVITE_CODE` in tutte le registrazioni (API e modulo); nuovi test: filtri nell'URL dopo il dettaglio, "Esci" dal dettaglio, titolo e limiti in Impostazioni. Il resto era già coerente con gli Sprint 66–68 (token dalla risposta della registrazione, tre spunte, endpoint push in allowlist).

## Verifica

- **Backend** (immagine `appapply-s70-web`, PostgreSQL 16 e Redis 7 usa e getta su una rete Docker dedicata, nessun container di produzione toccato): `python manage.py test --noinput` con `DJANGO_DEBUG=true` → **419 test OK** (386 di base + 33 nuovi in `apps/accounts/test_sprint70.py`). `makemigrations --check --dry-run` → "No changes detected".
- **Frontend** (immagine `appapply-s70-frontend-build`): `npm run build` OK, `npx oxlint src` 0 errori (9 warning `only-export-components` preesistenti). Chiavi i18n: stesso insieme in it ed en, nessuna chiave usata mancante (script nel container). Bundle: `serviceWorker.register("/sw.js",{scope:"/"})`, nessun `registerSW.js` iniettato, manifest presente.
- **Non verificato** (servono un browser o il deploy): e2e Playwright; avviso di nuova versione con un service worker reale; annullamento della sottoscrizione nel browser al logout; aspetto della barra in alto con l'icona "Esci" su schermi stretti; invio reale delle email di cambio indirizzo.

## Passi di deploy

Dettaglio in `DEPLOY.md` §4.8.
1. `docker compose -f docker-compose.prod.yml build web worker beat frontend-build`.
2. `docker compose -f docker-compose.prod.yml up -d` (nessuna migrazione, nessuna variabile nuova).
3. Le schede già aperte vanno ricaricate una volta a mano (il bundle vecchio non conosce l'avviso).
4. Verifiche dalla PWA: Impostazioni (titolo, limiti, fuso, cambio email), "Esci" da più pagine, Profilo (foto, tecnologie, obiettivo).

## Cosa manca

- **Pagina del job e chat degli editor**: costo della prossima generazione di CV/cover letter/messaggi e prezzo della chat non ancora mostrati, nessuna conferma prima dell'addebito; dati già disponibili in `GET /api/accounts/usage/` (`actions.cv`, `actions.cover_letter`, `actions.referral_message`, `chat_prices`). Da integrare dopo il merge con lo Sprint 69 (istruzioni in `Docs/02` §5.20).
- La conferma prima dell'addebito è solo nella PWA: una chiamata diretta all'API va a credito senza conferma, come prima.
- Il fuso proposto in onboarding si basa sul default Europe/Rome (nessun flag "scelto"); gli account esistenti restano su Europe/Rome finché l'utente non lo cambia.
- Il cambio email non ha stato lato server: più richieste producono più link validi fino al primo cambio riuscito; l'app non mostra un "cambio in attesa".
- Informativa: l'elenco di esempio delle email di servizio non cita il cambio email; da aggiungere alla prossima versione dei testi (non giustifica da solo una nuova accettazione).
- Messaggi del server ancora solo in italiano (§8.A punto 38) e login Google (punto 33): non richiesti.
- **File a rischio di conflitto con lo Sprint 69**: `frontend/src/i18n/translations.js` (titolo di Impostazioni e nuovi gruppi dopo `account`), `frontend/src/pages/JobListPage.jsx` (intestazione senza "Esci", `handleGenerateCv` con conferma), `frontend/src/App.jsx`, `frontend/src/components/ExperienceGroupEditor.jsx`, `frontend/e2e/job-list.spec.js`, `Docs/01` §4.1/§4.11/§7/§8.A, `Docs/02` §5/§11/§12/§13, `Docs/CHANGELOG.md`, `DEPLOY.md` §4.
