# Sprint 04 — Profilo master

## Input
- Sprint 03 completato (autenticazione funzionante).
- Riferimenti: `01-specifiche-funzionali-v4.md` §3, §4.1; `02-specifiche-tecniche-v3.md` §4.2.

## Obiettivo
API REST CRUD per il profilo master e le sue sezioni (`summary`, `key_achievements`, `Experience`, `Education`, `Skill`/`Certification`, `Language`) e upload della foto profilo.

## Risultato atteso
Un utente autenticato può creare, leggere e modificare tutte le sezioni del proprio profilo e caricare una foto; i dati sono isolati per utente.

## Criteri di verifica
- Creare più `Experience` (numero variabile) per un profilo e verificare che vengano tutte restituite in lettura.
- Upload foto profilo (endpoint dedicato o campo multipart) restituisce un riferimento al file salvato, rileggibile successivamente.
- Test di isolamento: una richiesta autenticata come utente A verso il profilo di utente B restituisce 403/404.
- La suite di test automatici del modulo profilo passa (`python manage.py test` o equivalente).

## Output per lo sprint successivo
API profilo completa, riusata dal parsing CV (Sprint 05) per il pre-popolamento e dal servizio di generazione CV (Sprint 10+) come sorgente dati.

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.profiles.views.ProfileViewSet` — `Retrieve`/`Update` filtrati a `Profile.objects.filter(user=request.user)` (isolamento per query, non solo per permesso: un `pk` di un altro utente non è nel queryset → 404) più un'azione dedicata `GET/PATCH /api/profiles/me/` che fa `get_or_create` del profilo dell'utente autenticato (il profilo è 1:1 con `User` ed è creato implicitamente al primo accesso, non richiede un passo "crea profilo" separato). Supporta sia payload JSON sia `multipart/form-data` (`parser_classes`), quindi l'upload della foto è un campo (`photo`) sullo stesso `PATCH /api/profiles/me/`, senza endpoint dedicato aggiuntivo — una delle due opzioni previste dal criterio di verifica.
- `apps.profiles.views.ProfileSectionViewSet` (base) + un `ModelViewSet` concreto per ciascuna sezione ripetibile — `Experience`, `Education`, `Skill`, `Certification`, `Language` — ognuno filtrato a `profile__user=request.user` e con `profile` assegnato automaticamente in `perform_create` (mai accettato dal client): CRUD completo su `/api/experiences/`, `/api/educations/`, `/api/skills/`, `/api/certifications/`, `/api/languages/`.
- `apps.profiles.serializers.ProfileSerializer` espone le sezioni come liste annidate **in lettura** (per restituire il profilo completo in un'unica chiamata a `/api/profiles/me/`); le scritture avvengono sui rispettivi endpoint di sezione, non tramite nested write (scelta per restare nel pattern DRF standard, evitando la complessità di serializer annidati scrivibili non richiesta dai criteri).
- Route montate in `config/urls.py` sotto `/api/` (router DRF in `apps.profiles.urls`); aggiunto anche il serving dei file `MEDIA_URL` in modalità `DEBUG` (`static()` di Django), così il riferimento restituito dall'upload foto è concretamente raggiungibile in sviluppo, non solo un percorso opaco.
- **Suite di test automatici** (`apps/profiles/tests.py`, `APITestCase` di DRF): copre esattamente i tre criteri di verifica (esperienze multiple tutte rilette, upload foto con riferimento rileggibile, isolamento tra utenti) — `python manage.py test apps.profiles` → 3/3 OK.

### Verifica eseguita
Automatica (`python manage.py test`) e manuale via `runserver` + `curl` (registrazione reale di due utenti, creazione di 3 `Experience`, upload di un PNG generato con Pillow, tentativo di lettura cross-utente), sempre con virtualenv locale + PostgreSQL/Redis di sistema (stesso limite ambientale di `docker compose up` degli sprint precedenti — verificata solo la validità sintattica di `docker compose config`).

| Criterio | Esito |
|---|---|
| `Experience` multiple per un profilo tutte restituite in lettura | ✅ (test automatico + manuale: 3 create, 3 rilette in `/api/profiles/me/`) |
| Upload foto profilo → riferimento salvato, rileggibile successivamente | ✅ (`PATCH /api/profiles/me/` multipart → stesso URL riletto con `GET`; file presente su disco e servito su `/media/...` in dev) |
| Isolamento: utente A verso il profilo di utente B → 403/404 | ✅ (404: `pk` di B non è nel queryset filtrato di A) |
| Suite di test automatici del modulo profilo passa | ✅ (`python manage.py test apps.profiles` — 3/3; `python manage.py test` sull'intero progetto — 3/3, nessuna regressione) |
| `makemigrations --check` nessuna differenza (nessun modello toccato in questo sprint) | ✅ |

### Cosa manca
- Pre-popolamento da CV caricato (upload PDF/Word, parsing): Sprint 05.
- Un vero smoke test di `docker compose up -d` (stessa riserva degli sprint precedenti).