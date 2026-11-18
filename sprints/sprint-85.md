# Sprint 85 — Admin delle ricerche salvate con tutte le città

> **Periodo:** 2026-11-18 · **Branch:** `sprint-85-admin-ricerche` (da `main` al commit c5fad96) · **Stato:** implementato e verificato; rilascio con il solo riavvio di `web` (OK del committente).

## Input
Dopo il rilascio dello Sprint 84 il committente ha notato che, nel Django Admin, l'elenco delle SavedSearch mostrava una sola città per ricerche che nell'app ne hanno due.

Numero: `git log` e `ls sprints/` arrivano a 84.

## Diagnosi (2026-11-18, solo lettura in produzione)
- Nel database le città sono complete: campo `cities` (`jsonb`), per esempio `["Zurich", "Geneva"]`; la colonna `city` non esiste più dalla migrazione `searches/0004`.
- L'elenco dell'Admin (`apps/searches/admin.py`) usava ancora `city`, che dallo Sprint 84 è una proprietà di compatibilità che restituisce la prima città: un problema solo di visualizzazione.
- La raccolta usa tutte le città: per l'account di prova, gruppi simulati (senza chiamare Apify) uno per tipo e città, località "City, Country" in inglese e `distance` 25; l'ultimo `RunLog` di raccolta aveva gli stessi gruppi.
- Il conteggio delle città attive era corretto (tutte le città delle ricerche attive, quelle del desiderio una volta sola).
- Le ricerche migrate non erano toccate dal problema.

## Decisione del committente
Correggere l'Admin come proposto: colonna "Città" con tutte le città, colonne tipo, modalità e "Nascosta (desiderio)", filtri per `is_wish` e tipo.

## Implementazione
- `apps/searches/admin.py`: `list_display` con keywords, tipo, "Città" (`cities` unite con la virgola), paese, "Modalità" (etichetta della scelta), "Nascosta (desiderio)" (`is_wish`, icona sì/no), utente, attiva; `list_filter` per attiva, `is_wish` e tipo. Nessun cambio di modello, API o frontend.

## Verifica
- `apps/searches/test_sprint85.py` (2 test: elenco con tutte le città, tipo, modalità e colonna nascosta; filtri per `is_wish` e tipo).
- Suite backend completa: **530 test OK** (`DJANGO_DEBUG=true`, `REGISTRATION_INVITE_CODE=` vuoto); `makemigrations --check` senza differenze.

## Rilascio
Solo ricostruzione e riavvio di `web` (l'Admin gira solo lì), senza migrazioni, in un momento senza task Celery in corso. `worker` e `beat` restano con l'immagine dello Sprint 84 (codice identico per loro); si allineano al prossimo rilascio completo.
