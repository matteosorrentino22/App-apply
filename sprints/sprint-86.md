# Sprint 86 — Massimali delle ricerche configurabili dal `.env`

> **Periodo:** 2026-11-24 · **Branch:** `sprint-86-limiti-ricerche-env` (da `main` al commit 5d24bfa) · **Stato:** implementato e verificato (test backend, build e lint); **merge e deploy non fatti**.

## Input
Il committente vuole poter cambiare i massimali delle ricerche dei piani Free e Pro. Erano costanti nel codice (`PLAN_LIMITS` in `apps/searches/services.py`, `MAX_CITIES_PER_SEARCH` in `apps/searches/models.py`) e un testo dell'app conteneva il numero "5" scritto a mano.

Numero: `git log` e `ls sprints/` arrivano a 85.

## Decisione del committente
Strada B: massimali configurabili dal `.env`, con i valori di oggi come predefiniti, così si cambiano senza nuovo codice (modifica del `.env` e ricreazione di `web`, `worker` e `beat`, `DEPLOY.md` §4.2).

## Implementazione
- `config/settings.py`: `SEARCH_LIMITS` da sei variabili facoltative (vuote = predefinito): `SEARCH_FREE_MAX_SAVED` (10), `SEARCH_FREE_MAX_ACTIVE_PER_TYPE` (1), `SEARCH_FREE_MAX_CITIES_PER_SEARCH` (1), `SEARCH_PRO_MAX_SAVED` (100), `SEARCH_PRO_MAX_ACTIVE_CITIES` (50), `SEARCH_PRO_MAX_CITIES_PER_SEARCH` (5). Interi ≥ 1: un valore non valido blocca l'avvio con un messaggio chiaro (`ImproperlyConfigured`), invece di applicare in silenzio un limite sbagliato.
- `apps/searches/services.py` (`get_limits`) e `models.max_cities_per_search(plan)` leggono i valori a ogni chiamata; tolte le costanti. Il lavoro dei desideri usa il massimale di città per ricerca del Pro. Con più di una ricerca attiva per tipo consentita sul Free, oltre il massimale l'attivazione è rifiutata (con 1 resta lo spegnimento automatico della precedente, come prima).
- Messaggio del server per una ricerca con troppe città da attivare reso generico ("Con il tuo piano una ricerca può avere al massimo N città…"), tradotto in inglese.
- `/api/search-limits/` aggiunge `pro_max_cities_per_search`. Frontend: testo "Con Pro puoi cercare in {max} città per ricerca" (it/en) dal server; onboarding e lavoro dei desideri prendono il massimale di città dal server (prima 1 e 5 scritti nel codice).
- Abbassare un massimale non disattiva né cancella le ricerche già oltre il nuovo valore: vale dalla creazione o attivazione successiva.

## Verifica
- `apps/searches/test_sprint86.py` (5 test): predefiniti uguali ai valori di prima; con valori cambiati (`override_settings`) ricerche salvate, attive per tipo, città per ricerca e città attive Pro rispettano i nuovi numeri; endpoint dei limiti; lettura delle variabili (vuoto, spazi, valori non validi).
- Suite backend completa: **535 test OK**; `makemigrations --check` senza differenze; catalogo inglese senza voci `fuzzy`.
- Frontend: build OK, `oxlint` 0 errori (9 warning, gli stessi), 672 chiavi presenti in it ed en.
- E2e non rilanciati: per l'utente non cambia nulla con i valori predefiniti (stessi testi e limiti) e la suite completa richiede di fermare la produzione per memoria (Sprint 84).

## Rilascio
Ricostruzione e riavvio di `web`, `worker` e `beat` (nessuna migrazione, nessuna variabile obbligatoria nuova). Per cambiare i massimali dopo: aggiungere o modificare le variabili nel `.env` e `docker compose -f docker-compose.prod.yml up -d --force-recreate web worker beat`.
