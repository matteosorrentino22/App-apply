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

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.accounts.User` esteso con tutti i campi di §4.1 tecniche: `plan` (`free`/`pro`), `timezone`, `interface_language` (`it`/`en`), `cv_language_mode` (`english`/`job_language`), `cv_include_photo`, `objective_statement`, `created_at`, `last_activity_reset`, `last_notified_at`, `extra_credit` (`DecimalField`). `last_activity_reset`/`last_notified_at` sono nullable e vengono impostati a `created_at` in `save()` alla creazione dell'utente (denormalizzazione richiesta esplicitamente dalle tecniche per il controllo O(1) dello scheduler). `UserAdmin` esteso con un fieldset dedicato per gestire i nuovi campi da Django Admin (incluso il carico manuale di `extra_credit`).
- Quattro nuove app Django, come da elenco già annunciato in `CLAUDE.md` (`profiles`, `searches`, `jobs`, `cv`) più `notifications`, ciascuna con `admin.py` che registra i propri modelli:
  - `apps.profiles` — `Profile` (1:1 con `User`), `Experience`, `Education`, `Skill`, `Certification`, `Language`, tutte in FK su `Profile`. `Experience.bullets`/`technologies` come `JSONField` (liste, numero variabile per riga). Inline su `ProfileAdmin` per creare un profilo con relative esperienze in un solo form, come richiesto dal criterio di verifica.
  - `apps.searches` — `SavedSearch` (`user`, `name`, `keywords`, `location`, `is_active`); i vincoli di piano (10/1 Free, 100/50 Pro) sono logica applicativa, non ancora implementata (arriverà con Sprint 06 — qui c'è solo il modello dati).
  - `apps.jobs` — `Job` (vincolo di unicità `(user, source, external_id)`, `published_at` nullable, `origin`, `is_archived`, `status` a tre valori stabili + flag separato `cv_generation_in_progress` per lo stato transitorio/guardia di concorrenza, `score` 1–5 nullable con validatori, `score_match`/`score_gaps` come liste JSON, le quattro date di servizio); `DailyQuota` (`user`+`date` unique, `manual_cv_count`, `import_count` — i due pool separati di §4.6/§4.11); `RunLog` (diario tecnico, `job`/`user` nullable con `SET_NULL` per non perdere lo storico se il job/utente viene rimosso).
  - `apps.cv` — `CVDocument` (`job`, `user`, `html_source`, `pdf_file`, `generation_type` `automatic`/`manual`, `enrichment_used`).
  - `apps.notifications` — `PushSubscription` (`user`, `endpoint`, chiavi `p256dh`/`auth`, unicità su `(user, endpoint)`).
- `config/settings.py`: le 5 nuove app registrate in `INSTALLED_APPS`; aggiunte `MEDIA_URL`/`MEDIA_ROOT` (necessarie per `Profile.photo` e `CVDocument.pdf_file`, che sono file field). Aggiunta `Pillow` a `requirements.txt` (dipendenza tecnica obbligatoria di Django per `ImageField`, non una libreria di business logic).
- Migrazioni generate e committate per tutte le app toccate (`accounts.0002_...`, più `0001_initial` per `profiles`, `searches`, `jobs`, `cv`, `notifications`).

### Decisione tecnica non esplicitamente richiesta, da segnalare
`User.created_at` è stato implementato con `default=django_timezone.now` invece di `auto_now_add=True`. Motivo: `accounts.User` ha già una migrazione applicata dallo Sprint 01 (senza questo campo), e Django non permette di aggiungere un campo `auto_now_add=True` a un modello già migrato senza un default "one-off" fornito interattivamente in console — incompatibile con l'esecuzione non interattiva. `default=timezone.now` produce lo stesso comportamento pratico (timestamp fissato alla creazione), semplicemente senza il vincolo "non modificabile" che `auto_now_add` impone lato ORM. Non incide su nessun criterio di verifica né sui flussi descritti nelle specifiche.

### Verifica eseguita (senza Docker, stesso limite d'ambiente dello Sprint 01)
Come nello Sprint 01, `docker compose up` non è eseguibile in questo ambiente (pull immagini bloccato dalla policy di rete della sandbox); `docker compose config` con un `.env` di prova confirma che il file resta sintatticamente valido dopo le modifiche a `requirements.txt`. Verifica funzionale via virtualenv locale + PostgreSQL/Redis di sistema:

| Criterio | Esito |
|---|---|
| `makemigrations --check` nessuna differenza | ✅ |
| `migrate` applica tutto senza errori | ✅ |
| Creare da shell/admin un `User`, un `Profile` con un'`Experience`, una `SavedSearch`, un `Job` | ✅ (verificato da shell; le pagine admin di tutti i nuovi modelli rispondono 302 → redirect login, non 404, confermando la registrazione) |
| Secondo `Job` con stesso `(user, source, external_id)` → errore | ✅ `IntegrityError` |
| `User._meta.get_field('extra_credit').__class__.__name__ == 'DecimalField'` | ✅ |
| `Job` senza `published_at` da shell/admin senza errori | ✅ |

### Cosa manca (rinviato ai prossimi sprint, come da piano)
- Logica applicativa (autenticazione, viste, vincoli di piano su ricerche/quote/credito, ciclo notturno, generazione CV): sprint successivi, come da roadmap.
- Un vero smoke test di `docker compose up -d` resta da fare in un ambiente con accesso a Docker Hub (stessa riserva dello Sprint 01).