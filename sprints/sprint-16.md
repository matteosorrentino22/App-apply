# Sprint 16 — Candidatura

## Input
- Sprint 15 (stati job); `User.last_activity_reset` (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.10, §4.12 (parte inattività).

## Obiettivo
Endpoint per marcare un job come "candidatura fatta" (consentito solo se esiste già un CV per quel job), con aggiornamento di `date_application_done` e reset di `User.last_activity_reset`.

## Risultato atteso
Un job con CV generato può essere marcato come candidatura fatta; un job senza CV non può esserlo; la marcatura azzera il timer di inattività dell'utente.

## Criteri di verifica
- Marcare come "candidatura fatta" un Job in stato `cv_generated` → successo, `status='application_done'`, `date_application_done` valorizzato.
- Marcare come "candidatura fatta" un Job in stato `new` (senza CV) → richiesta rifiutata.
- Dopo la marcatura, `User.last_activity_reset` risulta aggiornato all'istante della richiesta (confrontabile con il valore precedente).

## Output per lo sprint successivo
`User.last_activity_reset` aggiornato correttamente, consumato dal task di notifica di inattività (Sprint 17).

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.jobs.application.mark_application_done(job)` — `select_for_update` sul Job (stessa guardia di concorrenza già usata per la generazione manuale, Sprint 12, per evitare una doppia marcatura concorrente): se `status != cv_generated` solleva `ApplicationMarkRejected` senza scrivere nulla; altrimenti imposta `status=application_done`, valorizza `date_application_done` e aggiorna `User.last_activity_reset` all'istante corrente in un'unica transazione atomica.
- `POST /api/jobs/<id>/mark-application-done/` (`apps.jobs.views.MarkApplicationDoneView`) — `200` con il Job aggiornato in caso di successo, `409` con messaggio se il job non ha ancora un CV generato (anche per un job già in `application_done`: la marcatura non è ripetibile, verificato manualmente).

### Verifica eseguita
`python manage.py test apps.jobs` (41/41, incluse le 3 nuove `MarkApplicationDoneTests` e le 2 nuove `MarkApplicationDoneApiTests`) e `python manage.py test` sull'intero progetto (74/74, nessuna regressione); `makemigrations --check` pulito (nessuna modifica ai modelli: tutti i campi usati esistevano già dagli Sprint 02/09). Verifica manuale end-to-end via `runserver` + richieste HTTP reali, incluso il caso di doppia marcatura sullo stesso job (correttamente rifiutata al secondo tentativo).

| Criterio | Esito |
|---|---|
| Marcatura di un Job `cv_generated` → successo, `status='application_done'`, `date_application_done` valorizzato | ✅ |
| Marcatura di un Job `new` (senza CV) → richiesta rifiutata | ✅ |
| Dopo la marcatura, `User.last_activity_reset` aggiornato all'istante della richiesta | ✅ |

### Cosa manca
- Nessuna riserva/consumo di quota — coerente con le specifiche: marcare la candidatura non è un'azione a pagamento.
- Task di notifica di inattività che consuma `User.last_activity_reset`: Sprint 17.
