# Sprint 07 — Fonte offerte (raccolta)

## Input
- Sprint 06 completato (ricerche attive disponibili); modello `Job` (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.3, §4.4; `02-specifiche-tecniche-v3.md` §5.1, §5.3, §11 punto 1.

## Obiettivo
Modulo interno con interfaccia unica ("offerte per queste ricerche, entro questa finestra, fino a questo limite") dietro cui gira l'integrazione Apify (actor LinkedIn), con limite 50 (Free)/100 (Pro) job/notte per utente, finestra 24h, filtro sui campi obbligatori, deduplica per `(user, source, external_id)`.

## Risultato atteso
Dato un utente con ricerche attive, un task/comando di raccolta popola `Job` con le offerte valide, rispettando il limite di piano e senza duplicati rispetto a job già mostrati.

## Criteri di verifica
- Con mock della risposta Apify che restituisce N offerte (N > limite di piano), l'esecuzione per un utente Free salva al massimo 50 `Job`, per un utente Pro al massimo 100.
- Un'offerta priva di uno tra `title`/`company`/`location`/`description`/`apply_url` non viene salvata (conteggio Job salvati < item del mock).
- Un'offerta senza `published_at` viene comunque salvata (`published_at` NULL in DB).
- Rieseguendo il task con lo stesso `external_id` già presente per l'utente, il conteggio Job resta invariato (nessun duplicato).
- Il token Apify è letto da variabile d'ambiente, non hardcoded nel codice (verifica statica).
- L'interfaccia pubblica del modulo non espone dettagli specifici di Apify al chiamante.

## Output per lo sprint successivo
Job raccolti e salvati per utente, pronti per lo scoring (Sprint 08).