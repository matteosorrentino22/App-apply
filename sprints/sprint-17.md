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