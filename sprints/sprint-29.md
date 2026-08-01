# Sprint 29 — Arricchimento vincolato a esperienza esistente (contenuto CV, fase 4/4)

## Input
Sprint 28 completato (nuovo template, loop di ripiego overflow). Ultimo
sprint della serie: implementa `Docs/03-specifiche-funzionali-contenuto-
cv-v4.md` §5.6, che sostituisce l'arricchimento a campi liberi
(company/role/location, Sprint 13) con un arricchimento **vincolato a
un'esperienza già presente** nel profilo master.

## Obiettivo
- L'arricchimento non introduce mai un'azienda/ruolo del tutto nuovo: solo
  attività/progetti aggiuntivi agganciati a un'`Experience` esistente.
- Priorità massima di inclusione nel CV per cui è inserito: protetto sia
  dal taglio al budget bullet (§5.4) sia dal loop di ripiego per overflow
  (§6) — tra gli ultimi a essere rimossi in entrambi i casi.
- Se salvato anche nel profilo master, nei CV **successivi** perde la
  priorità (diventa contenuto normale, soggetto alla riformulazione AI
  come tutto il resto).

## Esito (2026-08-01)

### Contratto API
`CvEnrichmentSerializer` riscritto: `experience_id` (obbligatorio,
un'esperienza esistente) + `additional_bullets` (lista di attività da
aggiungere) al posto dei campi liberi company/role/location/dates/
technologies. `generate_cv_with_enrichment` valida che l'esperienza
appartenga al profilo dell'utente (`EnrichmentExperienceNotFound` → 404
altrimenti, mai un accesso cross-utente).

### Priorità di inclusione — implementazione
La protezione è **meccanica lato server**, non affidata al modello AI (che
potrebbe non rispettarla):
- I bullet di arricchimento sono iniettati **dopo** la chiamata Claude,
  letteralmente (non riformulati, come `technologies`/`location`), sull'
  `Experience` corretta — marcati `protected: True`.
- `selection.py`: i bullet `protected` sono sempre tenuti nel taglio al
  budget (`_cut_bullets_to_budget`), sempre esclusi dai candidati alla
  rimozione nel loop di ripiego (`remove_least_relevant_bullet`), e la loro
  esperienza non può mai finire esclusa dal cap delle 5 mostrate
  (`_select_shown_experiences` — nuova regola: un'esperienza con almeno un
  bullet protetto ha priorità assoluta, sopra la normale logica di swap per
  rilevanza).
- Se `save_to_profile=True`, i nuovi bullet sono accodati (append, non
  sostituzione) all'`Experience` esistente nel profilo master — senza più
  flag `protected` nei CV successivi, coerente con "priorità solo per il CV
  corrente" (§5.6).

### Frontend
`JobDetailPage.jsx`: il form di arricchimento non ha più campi liberi
azienda/ruolo/località — un menu a tendina (componente `Select` esistente)
elenca le esperienze del profilo (caricate da `GET /api/profiles/me/`),
l'utente ne seleziona una e aggiunge le nuove attività con lo stesso
`ChipInput` di prima. Messaggio dedicato se il profilo non ha ancora
esperienze. Traduzioni IT/EN aggiornate.

### Verifica eseguita
- **Nuovi test unitari `selection.py`** (5): bullet protetto sopravvive al
  taglio budget anche con rilevanza bassissima; esperienza con bullet
  protetto non esclusa dal cap anche senza marcatura "altamente rilevante";
  bullet protetto mai rimosso dal loop di ripiego, anche quando l'unico
  bullet non protetto ha rank migliore.
- **Test di integrazione** (`cv/tests.py`, `jobs/tests.py`): arricchimento
  non salvato per default; salvato accoda i bullet all'esperienza esistente
  (non li sovrascrive); non altera lo score del job; rifiuta un
  `experience_id` di un altro utente (404); i bullet di arricchimento
  sopravvivono anche forzando un budget bullet a zero (`test_enrichment_
  bullets_have_priority_over_overflow_cut`).
- **Verifica end-to-end reale**: generato un CV con arricchimento tramite
  l'intera pipeline reale (solo `generate_cv_content` mockato) — confermato
  che sia il bullet esistente sia quello di arricchimento compaiono nel
  CV finale.
- `python manage.py test`: **166/166 passati** (160 pre-esistenti + 6
  nuovi); `makemigrations --check --dry-run` pulito (nessuna modifica al
  modello dati in questo sprint).
- Frontend: `npm run build` e `oxlint` sui file toccati — puliti.
- Aggiornato il test e2e Playwright `job-list.spec.js` che usava ancora il
  vecchio form a campi liberi (crea prima un'esperienza via API, poi la
  seleziona dal nuovo menu a tendina) — non eseguibile in questo sandbox
  per il limite ambientale già documentato (Sprint 23: `SECURE_SSL_REDIRECT`
  rompe le chiamate dirette dei test in produzione), non legato a questo
  sprint.

### Cosa manca
Con questo sprint si chiude l'implementazione di
`Docs/03-specifiche-funzionali-contenuto-cv-v4.md`. Restano, come già
segnalato negli sprint precedenti della serie:
- Calibrazione reale dei valori parametrici e qualità dei contenuti (nessuna
  `ANTHROPIC_API_KEY` di test isolata in questo ambiente).
- Testi esatti di guida/avviso (già punti aperti dichiarati dal documento,
  §14).
- Suite e2e Playwright da eseguire su un ambiente di sviluppo dedicato
  (limite ambientale preesistente, non di questo sprint).
