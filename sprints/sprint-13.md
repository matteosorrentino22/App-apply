# Sprint 13 — Arricchimento profilo

## Input
- Sprint 12 completato (generazione manuale).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.8; `02-specifiche-tecniche-v3.md` §5.2 (nota), §6.2.

## Obiettivo
Endpoint per aggiungere un dettaglio di esperienza reale prima di una generazione/rigenerazione manuale, con scelta se salvarlo anche nel profilo master o solo per quel CV; il dettaglio viene passato al servizio di generazione come contesto aggiuntivo.

## Risultato atteso
Generando un CV con un dettaglio di arricchimento "solo per questo CV", il PDF risultante riflette quel dettaglio ma il profilo master resta invariato; con l'opzione "salva anche nel master", il profilo risulta aggiornato.

## Criteri di verifica
- Invio di un dettaglio di arricchimento con `save_to_profile=False`, seguito da generazione CV → il `CVDocument` risultante referenzia l'arricchimento (`enrichment_used`) e il contenuto generato lo riflette (verificabile tramite mock della chiamata Claude); il `Profile` dell'utente non contiene il nuovo dettaglio.
- Stesso test con `save_to_profile=True` → il `Profile` risulta aggiornato con il nuovo dettaglio (verificabile in lettura API profilo).
- L'aggiunta dell'arricchimento non modifica `Job.score` (score invariato prima/dopo).

## Output per lo sprint successivo
Arricchimento disponibile come step opzionale prima di ogni generazione manuale; profilo e generazione CV completi per l'uso da frontend.

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.cv.serializers.CvEnrichmentSerializer` — valida il dettaglio di arricchimento con gli **stessi campi di `Experience`** (`company`, `role`, `location`, `start_date`, `end_date`, `bullets`, `technologies`), più `save_to_profile` (booleano, default `False`): un dettaglio "di esperienza reale" è per definizione compatibile 1:1 con una riga `Experience`, quindi salvabile tale e quale se l'utente lo richiede.
- `apps.cv.enrichment.generate_cv_with_enrichment(job, detail, save_to_profile=False)` — se `save_to_profile=True`, crea subito un `Experience` sul profilo master dell'utente con i dati del dettaglio (persistente, riusabile in generazioni future); costruisce sempre un testo libero dal dettaglio (`_format_enrichment_text`) e lo inoltra come `enrichment` a `apps.cv.manual_generation.request_manual_cv_generation` (Sprint 12), che lo passa al servizio di generazione (Sprint 10) e lo salva in `CVDocument.enrichment_used`. Nessuna nuova tabella "Enrichment": il dettaglio vive o come `Experience` (se salvato nel master) o come testo in `CVDocument.enrichment_used` (se solo per quel CV) — coerente con CLAUDE.md ("niente helper/astrazioni introdotte in anticipo").
- `POST /api/jobs/<id>/enrich-and-generate-cv/` (`apps.jobs.views.EnrichAndGenerateCvView`) — stesso schema di risposta/errore di `GenerateCvView` (Sprint 12: `201`/`409`/`502`), combinando in un'unica chiamata arricchimento + generazione, come descritto dall'obiettivo dello sprint ("prima di una generazione/rigenerazione manuale").
- Nessuna modifica a `Job.score`: `generate_cv_with_enrichment` non tocca mai il campo (né direttamente né tramite le funzioni che chiama), quindi l'invarianza è garantita per costruzione, non solo verificata a runtime.

### Verifica eseguita
`python manage.py test apps.cv apps.jobs` (41/41, incluse le 3 nuove `EnrichAndGenerateCvTests` a livello di servizio e le 2 nuove `EnrichAndGenerateCvApiTests` a livello HTTP con `APITestCase`) e `python manage.py test` sull'intero progetto (53/53, nessuna regressione); `makemigrations --check` pulito (nessuna modifica ai modelli, `Experience` esisteva già dallo Sprint 04). Verifica manuale end-to-end via `runserver` + richiesta HTTP reale con `save_to_profile=True`: la nuova `Experience` è comparsa correttamente in `GET /api/profiles/me/`, e il fallimento atteso della chiamata Claude (nessuna chiave reale in sandbox) ha lasciato `Job`/`DailyQuota` in stato pulito (stesso comportamento di restituzione della riserva verificato nello Sprint 12).

| Criterio | Esito |
|---|---|
| `save_to_profile=False` + generazione → `CVDocument.enrichment_used` referenzia l'arricchimento e il contenuto lo riflette (verificato tramite mock di Claude); `Profile` non contiene il nuovo dettaglio | ✅ |
| Stesso test con `save_to_profile=True` → `Profile` aggiornato con il nuovo dettaglio, verificabile in lettura API profilo | ✅ (verificato sia a livello di servizio sia via `GET /api/profiles/me/` reale) |
| L'aggiunta dell'arricchimento non modifica `Job.score` | ✅ |

### Cosa manca
- Nessuna verifica end-to-end reale della chiamata Claude (stessa riserva degli sprint precedenti); il contenuto generato è verificato solo indirettamente, controllando che l'argomento `enrichment` passato a `generate_cv_content` contenga il dettaglio fornito.
- Il servizio di generazione CV completo (Sprint 10-13) è ora pronto per l'uso da frontend (Sprint 18+): manca ancora la lista job (Sprint 15), l'import manuale (Sprint 14) e il tracciamento della candidatura (Sprint 16).
