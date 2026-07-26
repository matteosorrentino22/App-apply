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