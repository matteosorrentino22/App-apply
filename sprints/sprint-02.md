# Sprint 02 — Modello dati completo

## Input
- Sprint 01 completato (scheletro Django/Celery/Docker funzionante).
- Riferimento: `02-specifiche-tecniche-v3.md` §4 (Modello dati).

## Obiettivo
Implementare tutti i modelli Django descritti nelle specifiche tecniche §4: `User` esteso, `Profile` + `Experience` + `Education` + `Skill`/`Certification` + `Language`, `SavedSearch`, `Job`, `CVDocument`, `DailyQuota`, `RunLog`, `PushSubscription`. Registrarli in Django Admin.

## Risultato atteso
Migrazioni applicabili; tutti i modelli gestibili da Django Admin; vincoli chiave implementati (unicità `(user, source, external_id)` su `Job`, `extra_credit` come campo decimale, `published_at` nullable, ecc.).

## Criteri di verifica
- `python manage.py makemigrations --check` non genera differenze (migrazioni committate e aggiornate).
- `python manage.py migrate` applica tutto senza errori.
- Da Django Admin: creare un `User`, un `Profile` con almeno un'`Experience`, una `SavedSearch`, un `Job`.
- Tentare di creare un secondo `Job` con lo stesso `(user, source, external_id)` di uno esistente produce un errore di validazione/integrità.
- Da shell Django: `User._meta.get_field('extra_credit').__class__.__name__` restituisce `'DecimalField'`.
- Creare un `Job` senza `published_at` da admin/shell non produce errori (campo nullable).

## Output per lo sprint successivo
Schema dati completo e stabile su cui costruire autenticazione (Sprint 03), profilo (Sprint 04), ricerche (Sprint 06) e ciclo notturno (Sprint 07+).