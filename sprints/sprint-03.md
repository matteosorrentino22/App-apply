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