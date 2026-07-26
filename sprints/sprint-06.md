# Sprint 06 — Ricerche salvate

## Input
- Sprint 03 completato (autenticazione); modello `SavedSearch` disponibile (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.2, §7.

## Obiettivo
API CRUD per le ricerche salvate (`keywords`, `location`, attiva/disattiva) con limiti per piano (Free ≤10 salvate/1 attiva, Pro ≤100 salvate/≤50 attive) e logica di downgrade Pro→Free.

## Risultato atteso
Un utente Free non può superare 1 ricerca attiva né 10 salvate; attivare una nuova ricerca su Free disattiva automaticamente la precedente; un downgrade Pro→Free disattiva tutte le ricerche e blocca l'aggiunta di nuove finché non si scende sotto 10 salvate.

## Criteri di verifica
- Utente Free crea 10 ricerche → la richiesta di creazione dell'11ª restituisce errore di limite.
- Utente Free attiva la ricerca B mentre A è attiva → A risulta disattivata dopo la richiesta; la risposta segnala il cambio.
- Utente Pro attiva fino a 50 ricerche contemporaneamente; la 51ª attivazione fallisce.
- Simulare un downgrade Pro→Free su un utente con 15 ricerche salvate (alcune attive): tutte risultano `is_active=False`; creare una nuova ricerca fallisce finché il conteggio non scende sotto 10.
- Un endpoint/metodo "ricerche attive per raccolta" restituisce solo le ricerche con `is_active=True`.

## Output per lo sprint successivo
Elenco di ricerche attive per utente, con relativi limiti di piano, pronto per essere consumato dal modulo di raccolta offerte (Sprint 07).