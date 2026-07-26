# Sprint 17 — Notifiche Web Push (backend)

## Input
- `PushSubscription`, `User.last_notified_at`/`last_activity_reset` (Sprint 02); Sprint 09 (ciclo notturno per i nuovi job); Sprint 16 (reset inattività).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.12; `02-specifiche-tecniche-v3.md` §3.8, §5.5, §7.

## Obiettivo
Endpoint di registrazione `PushSubscription`; task schedulato (ogni ~15 minuti) che, per ogni utente alle ~10:00 locali, invia la notifica mattutina se esistono Job con `date_collected > last_notified_at` e aggiorna il timestamp; task che invia la notifica di inattività dopo 7 giorni da `last_activity_reset`.

## Risultato atteso
Simulando l'orario locale di un utente e la presenza di nuovi job, il task invia una notifica Web Push (verificabile via mock di `pywebpush`) e aggiorna `last_notified_at`; senza nuovi job, nessuna notifica; dopo 7 giorni di inattività, parte la notifica di inattività.

## Criteri di verifica
- Utente con `timezone` impostato, orario simulato = 10:00 locale, Job con `date_collected > last_notified_at` presente → il task invoca l'invio push (mock) e aggiorna `last_notified_at` all'istante corrente.
- Stesso scenario ma nessun Job nuovo → nessuna chiamata di invio, `last_notified_at` invariato.
- Eseguendo il task due volte nella stessa finestra oraria senza nuovi Job nel frattempo, non c'è doppio invio (verificabile contando le chiamate mock).
- Utente con `last_activity_reset` più vecchio di 7 giorni e nessuna candidatura nel frattempo → il task di inattività invia la notifica; con `last_activity_reset` più recente di 7 giorni, nessun invio.
- Utente con le 10:00 locali antecedenti al batch delle 02:00 Europe/Rome riceve, al proprio prossimo giro utile, la notifica sul batch più recente disponibile, senza doppio invio rispetto a un giro precedente.

## Output per lo sprint successivo
Backend completo di tutte le funzionalità server-side; pronto per l'integrazione frontend (Sprint 18–20).

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.notifications.services.send_web_push(subscription, payload)` — wrapper su **pywebpush** (nuova dipendenza, richiesta esplicitamente da CLAUDE.md/§3.8 tecniche), autenticato con chiavi VAPID (`VAPID_PRIVATE_KEY`/`VAPID_PUBLIC_KEY`/`VAPID_CLAIMS_EMAIL`, nuove variabili di configurazione in `settings.py`/`.env.example`) — nessun servizio a pagamento.
- `apps.notifications.tasks.send_morning_notification_for_user(user)` — se sono circa le 10:00 locali dell'utente (`user.timezone`, tramite `zoneinfo`) ed esistono Job con `date_collected > last_notified_at`, invia la notifica a tutte le sottoscrizioni dell'utente e aggiorna `last_notified_at` all'istante corrente. Nessun caso speciale per fusi orari a est dell'Europa: la definizione "raccolti dopo l'ultima notifica" (già nel design di `User.last_notified_at`, Sprint 02) copre il caso per costruzione, verificato con un test dedicato su un utente in `Pacific/Auckland`.
- `apps.notifications.tasks.send_inactivity_notification_for_user(user)` — invia il promemoria se sono passati ≥7 giorni da `User.last_activity_reset`.
- **Decisione tecnica non esplicitamente richiesta, da segnalare**: aggiunto `User.last_inactivity_notified_at` (migrazione `accounts.0004`). Motivo: a differenza della notifica mattutina — che ha già una guardia naturale anti-doppio-invio in `last_notified_at` confrontato con `date_collected` — il promemoria di inattività, se richiamato ogni ~15 minuti per tutta la durata dell'inattività (potenzialmente settimane), **rimanderebbe la stessa notifica a ogni giro** senza un secondo timestamp: nessun campo esistente copriva questo caso. Il nuovo campo, confrontato con `last_activity_reset` (`last_inactivity_notified_at >= last_activity_reset` ⇒ già notificato per questo periodo di inattività), garantisce **un solo promemoria per periodo di inattività**, e si "riarma" automaticamente alla prossima "candidatura fatta" (che aggiorna `last_activity_reset`, Sprint 16) senza bisogno di azzerare esplicitamente il nuovo campo.
- **Decisione tecnica non esplicitamente richiesta, da segnalare**: il pin `cryptography>=42.0,<44.0` in `requirements.txt` (esistente dagli sprint precedenti) è incompatibile con `py-vapid` (dipendenza transitiva di `pywebpush`, richiede `cryptography>=46`). Aggiornato a `cryptography>=46.0,<50.0`: nessun codice applicativo importa `cryptography` direttamente (verificato), quindi l'innalzamento del pin non ha impatti oltre a soddisfare questa nuova dipendenza.
- `POST /api/notifications/push-subscriptions/` (`apps.notifications.views.PushSubscriptionView`) — accetta la stessa forma di `PushSubscription.toJSON()` del browser (`endpoint`, `keys.p256dh`, `keys.auth`); `update_or_create` su `(user, endpoint)` evita duplicati se il browser ri-registra la stessa sottoscrizione.
- Migrazione dati `notifications.0002` — crea, in modo idempotente, un `IntervalSchedule` di 15 minuti (§5.5/§7 tecniche: "lo scheduler gira di frequente, es. ogni 15 minuti") e due `PeriodicTask` (`send_morning_notifications`, `send_inactivity_notifications`), coerente con il pattern già usato per il ciclo notturno (Sprint 09) — schedulazione gestibile da Django Admin, non hardcoded.

### Verifica eseguita
`python manage.py test apps.notifications` (10/10) e `python manage.py test` sull'intero progetto (84/84, nessuna regressione); `makemigrations --check` pulito. Verificato da shell che entrambi i `PeriodicTask` esistono con `interval` a 15 minuti ed `enabled=True`.

| Criterio | Esito |
|---|---|
| Utente a ~10:00 locali con Job nuovi → invio push (mock) e `last_notified_at` aggiornato | ✅ |
| Stesso scenario senza Job nuovi → nessuna chiamata di invio, `last_notified_at` invariato | ✅ |
| Esecuzione doppia nella stessa finestra senza nuovi Job nel frattempo → nessun doppio invio | ✅ |
| `last_activity_reset` più vecchio di 7 giorni → invio; più recente di 7 giorni → nessun invio | ✅ |
| Utente con le 10:00 locali antecedenti al batch delle 02:00 Europe/Rome → notifica sul batch più recente disponibile, senza doppio invio | ✅ (verificato con un utente in `Pacific/Auckland`) |

### Cosa manca
- Nessuna verifica end-to-end reale dell'invio Web Push (richiede chiavi VAPID reali e una sottoscrizione browser autentica) — stessa riserva già registrata per Claude/Apify negli sprint precedenti; `pywebpush` e la logica di invio sono comunque testate con `send_web_push` mockato allo stesso modo delle altre integrazioni esterne del progetto.
- Le chiavi VAPID restano vuote di default (`.env.example`): da generare (`vapid --gen`, libreria `py-vapid`) e configurare prima del rilascio.
- Con questo sprint si chiude il backend previsto dal piano fino al frontend (Sprint 18+), come da istruzione dell'utente di procedere fino a "quello del front end".
