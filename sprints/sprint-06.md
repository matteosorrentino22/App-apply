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

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.searches.services` — logica di piano centralizzata, riusabile e testabile a parte dalla vista:
  - `PLAN_LIMITS` (Free: 10 salvate/1 attiva; Pro: 100 salvate/50 attive), `check_can_create` (solleva `PlanLimitExceeded` oltre il tetto di salvate), `activate_search` (su Free disattiva automaticamente l'eventuale ricerca già attiva e ritorna quella disattivata, mai un errore; su Pro rifiuta oltre il tetto di attive), `deactivate_search`.
  - `get_active_searches(user)` — la funzione "ricerche attive per raccolta" richiesta esplicitamente dal criterio di verifica, pronta per essere importata dal modulo di raccolta (Sprint 07) senza passare dall'API.
- `apps.searches.signals` — downgrade Pro→Free: un handler `pre_save`/`post_save` su `User` rileva la transizione `pro→free` e disattiva tutte le ricerche dell'utente (`is_active=False`), senza selezionarne una nuova (comportamento esplicitamente richiesto: l'utente deve rientrare e attivarne una). Le ricerche restano tutte salvate anche oltre 10; la creazione di nuove resta bloccata da `check_can_create` finché non si scende sotto la soglia.
- API REST (`apps.searches.views.SavedSearchViewSet`, isolata per utente): CRUD standard su `/api/searches/` con `is_active` **read-only** sui campi diretti (create/update) — l'attivazione/disattivazione passa solo dalle action dedicate `POST /api/searches/<id>/activate/` e `.../deactivate/`, per non mescolare la scrittura dei campi con la logica di piano. La risposta di `activate/` include `deactivated_previous` quando l'attivazione ha disattivato un'altra ricerca (il modo in cui l'API "avvisa" il chiamante del cambio, §4.2 funzionali).
- Suite di test automatici (`apps/searches/tests.py`): copre tutti e 5 i criteri di verifica dello sprint, incluso il downgrade di piano simulato via `user.plan = FREE; user.save()`.

### Decisione tecnica non esplicitamente richiesta, da segnalare
L'attivazione/disattivazione è stata modellata come **action dedicate** (`POST .../activate/`, `.../deactivate/`) invece che come scrittura diretta del campo `is_active` via `PATCH`. Motivo: l'attivazione ha effetti collaterali non banali (disattivazione automatica su Free, rifiuto oltre soglia su Pro, messaggio di avviso) che non si esprimono bene come side-effect silenzioso di un `PATCH` su un campo tra tanti — un'action esplicita rende l'operazione autodescrittiva e la risposta può includere `deactivated_previous` senza ambiguità. Non cambia il modello dati né l'architettura, resta un dettaglio di esposizione API.

### Verifica eseguita
`python manage.py test apps.searches` (5/5) e `python manage.py test` sull'intero progetto (12/12, nessuna regressione); `makemigrations --check` pulito (nessun modello nuovo, solo logica applicativa).

| Criterio | Esito |
|---|---|
| Free: 11ª ricerca salvata rifiutata | ✅ |
| Free: attivare B disattiva automaticamente A, risposta segnala il cambio | ✅ (`deactivated_previous` in risposta) |
| Pro: 51ª ricerca attiva rifiutata | ✅ |
| Downgrade Pro→Free con 15 salvate (alcune attive): tutte `is_active=False`; nuova ricerca bloccata sotto i 15/sopra la soglia di 10 | ✅ |
| "Ricerche attive per raccolta" restituisce solo `is_active=True` | ✅ (`services.get_active_searches`) |

### Cosa manca
- Consumo effettivo di `get_active_searches` da un vero modulo di raccolta job: Sprint 07.
