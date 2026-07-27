# Sprint 20 — Frontend: gestione account, notifiche push

## Input
- Sprint 18/19 (UI base); Sprint 06 (ricerche API); Sprint 17 (notifiche backend) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §3 (Gestione account), §4.11, §4.12; `02-specifiche-tecniche-v3.md` §3.3 (nota iOS), §3.8.

## Obiettivo
Schermata account con piano attuale e saldo credito (sola lettura, gestiti da amministratore), gestione CRUD ricerche salvate da UI, impostazioni (lingua interfaccia, lingua CV, opzione foto); flusso di sottoscrizione alle notifiche push con richiesta permesso browser e istruzione dedicata per iOS ("aggiungi alla home per ricevere le notifiche").

## Risultato atteso
L'utente vede piano e credito correnti, gestisce le proprie ricerche salvate da UI rispettando i limiti di piano già applicati dal backend, modifica le impostazioni, e attiva le notifiche push (con messaggio dedicato su iOS quando la PWA non è installata sulla home).

## Criteri di verifica
- Test e2e: la schermata account mostra piano e saldo credito coerenti con i dati impostati via Django Admin per l'utente di test (nessun controllo di checkout/pagamento presente in UI).
- Test e2e: creare/attivare/disattivare/eliminare una ricerca da UI e verificare che i messaggi di limite di piano restituiti dal backend siano mostrati correttamente.
- Test e2e: modificare lingua interfaccia, lingua CV e opzione foto dalle impostazioni e verificare la persistenza (ricaricando la pagina, i valori restano quelli impostati).
- Test manuale su browser mobile/emulatore iOS: se la PWA non è aggiunta alla home, il flusso di attivazione notifiche mostra l'istruzione dedicata invece di richiedere direttamente il permesso push.
- Test e2e (browser desktop/Android): completando il flusso di sottoscrizione, viene creata una `PushSubscription` associata all'utente (verificabile lato backend/API).

## Output per lo sprint successivo
Applicazione funzionalmente completa (backend + frontend) rispetto al perimetro MVP delle specifiche funzionali, pronta per il deploy (Sprint 21).

---

## Esito (2026-07-27)

**Stato: completato.**

### Cosa è stato fatto
- **Backend, due aggiunte minime** (stesso pattern degli sprint precedenti: il frontend scopre un piccolo gap non coperto da nessun endpoint esistente):
  - `UserOnboardingSerializer.extra_credit` — il saldo credito non era mai esposto da `/api/accounts/me/` (solo `plan` lo era); aggiunto come campo di sola lettura, coerente con "nessun checkout self-service, gestione solo da Django Admin".
  - `GET /api/notifications/vapid-public-key/` (`VapidPublicKeyView`) — la chiave pubblica VAPID (Sprint 17) era letta solo lato server per firmare gli invii, mai esposta al client, che ne ha bisogno per `PushManager.subscribe()`.
- **`AccountPage`**: piano e credito (sola lettura, badge + importo formattato `Intl.NumberFormat('it-IT', {style:'currency'})`); CRUD ricerche salvate (creazione da form, attiva/disattiva/elimina da lista, messaggio di errore del backend mostrato testualmente quando si supera il limite di piano); impostazioni (lingua interfaccia, lingua CV, opzione foto) con salvataggio in background e toast di conferma; sezione notifiche con quattro rami di stato (non supportato / iOS non installato alla home / attivo / bottone di attivazione).
- **`frontend/src/lib/push.js`** (nuovo): solo Web API standard (`Notification`, `PushManager`, nessuna libreria), `isPushSupported()`, `isIOS()`/`isStandalone()` per il ramo iOS (iPadOS 13+ si presenta come "Mac" nello user agent ma è touch: serve il controllo esplicito `navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1`, nessuna feature-detection copre questo caso), `subscribeToPush()`.
- **Bug reale trovato e corretto durante i test e2e**: i controlli delle impostazioni (radio lingua CV, checkbox foto) erano legati direttamente a `user.cv_language_mode`/`user.cv_include_photo` (da `AuthContext`), che si aggiornano solo dopo un giro completo PATCH + refresh — il controllo restava visivamente fermo per una finestra breve ma reale dopo il click, sembrando "non rispondere". Corretto introducendo uno stato locale ottimistico, aggiornato subito al click, con la persistenza in background — non un accorgimento per far passare il test, ma un difetto UX reale per qualunque utente.
- **`set_e2e_account`** (nuovo management command, DEBUG-only): imposta `plan`/`extra_credit` per un utente dato, simulando un'azione da Django Admin — necessario perché questi campi sono modificabili solo da amministratore, mai da API utente.
- **`apps/accounts/tests.py`** (nuovo file: l'app non aveva alcuna copertura di test finora) — aggiunti test mirati sul campo `extra_credit` e sul comando `set_e2e_account`; non è stato un obiettivo di questo sprint colmare l'intera assenza storica di test su login/registrazione.

### Decisioni tecniche non esplicitamente richieste, da segnalare
- **Service worker assente in `npm run dev`**: `devOptions.enabled: false` (deciso nello Sprint 18 per non interferire con l'HMR) significa che il flusso di sottoscrizione push reale non è testabile contro il dev server. Per verificarlo è stato aggiunto un blocco `preview` in `vite.config.js` (Vite non condivide il proxy `server.proxy` con `vite preview`) ed è stata usata una build di produzione (`npm run build && vite preview`) come secondo server, solo per il test dedicato alle notifiche — tutti gli altri test e2e restano sul dev server.
- **Chromium non supporta la Push API reale nei contesti browser isolati di Playwright** (trattati come "incognito": limite noto della piattaforma, https://crbug.com/401439, non aggirabile né lato app né lato configurazione test). Il test e2e sulla sottoscrizione mocka quindi solo `Notification.requestPermission` e `PushManager.prototype.subscribe` via `page.addInitScript()`, mantenendo reale il service worker della build di produzione — verifica così il codice di integrazione scritto in questo sprint, non l'API nativa del browser (non testabile in questo ambiente).
- Chiavi VAPID di test generate localmente (`vapid --gen`, già disponibile transitivamente da `pywebpush`) solo per abilitare l'esecuzione dei test in sandbox — non sono le chiavi di produzione.

### Verifica eseguita
- Backend: `python manage.py test` → **98/98 passati** (92 pre-esistenti + 6 nuovi: `MeEndpointTests`, `SetE2eAccountCommandTests`, `VapidPublicKeyApiTests`); `makemigrations --check` pulito (nessuna modifica ai modelli).
- Frontend: `npm run build` e `npm run lint` senza errori (solo warning pre-esistenti, non introdotti da questo sprint).
- Test e2e Playwright: **`frontend/e2e/account.spec.js`, 5 nuovi test** (piano/credito da Django Admin; CRUD completo di una ricerca salvata con badge "In uso"; messaggio di limite di piano oltre le ricerche consentite; persistenza delle impostazioni dopo reload; istruzione dedicata su iOS non installato alla home, verificata con uno user agent iPhone e assenza del bottone di attivazione diretta) — tutti eseguiti contro il dev server. **`frontend/e2e/push-subscription.spec.js`, 1 nuovo test** (flusso di attivazione mockato end-to-end, eseguito contro `vite preview`, con verifica finale lato backend via Django shell che la `PushSubscription` con l'endpoint atteso esiste per l'utente). Suite e2e completa: **22/22 passati**.
- Test manuale iOS: non eseguito su un vero emulatore Safari/iOS (non disponibile in questo ambiente); il criterio è stato verificato tramite il test e2e con user agent iPhone spoofato (stesso meccanismo usato per il rilevamento in `isIOS()`), che copre la logica applicativa ma non un vero Safari.

### Cosa manca
- Verifica manuale reale su un dispositivo/emulatore iOS Safari (Chromium/Playwright non può eseguire questo test): la logica di rilevamento è verificata via user-agent spoofing, ma non è un sostituto di un test manuale su hardware reale.
- Sottoscrizione push end-to-end con l'API nativa del browser: non testabile in Playwright/Chromium per il limite di piattaforma descritto sopra; verificata solo l'integrazione applicativa via mock.