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