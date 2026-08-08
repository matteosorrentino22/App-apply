# Sprint 34 — Paese in luogo/date, autocomplete città e date per esperienze/istruzione, "in corso"

## Input
Segnalazione del committente dopo aver ispezionato l'ultimo CV generato:
1. luogo/date di ogni ruolo non mostrano il paese (es. "IT");
2. in modifica profilo, ogni esperienza lavorativa non ha l'autocomplete
   per la località, necessario per ricavare il paese;
3. non si possono inserire data inizio/data fine per i ruoli, necessarie
   per la generazione del CV;
4. come data fine deve sempre essere possibile spuntare "in corso"
   (esperienza/istruzione ancora attiva); la stessa spunta deve esistere
   anche in Istruzione.

Due chiarimenti richiesti e risolti prima di procedere:
- tie-break istruzione "in corso" → trattata come la più recente;
- autocomplete: un solo campo città (niente campo paese separato), stesso
  meccanismo di suggerimento con paese in piccolo già usato in Profilo —
  il paese si deduce dalla città selezionata.

## Esito (2026-08-08)

### 1 — Paese nel luogo del CV
`location_country_code` (2 lettere ISO 3166-1 alpha-2, nuovo campo su
`Experience` ed `Education`, migrazione `0005_...`) derivato
dall'autocomplete Nominatim al momento della selezione della città, non
più delegato a Claude: `location`/`dates` sono dati fattuali del profilo
(come già `technologies`), quindi rimossi dallo schema JSON AI
(`ai_content.py`) e riattaccati per indice dopo la generazione
(`_attach_facts_and_enrichment`, ex `_attach_technologies_and_enrichment`
in `generation.py`). Applicato identicamente a Istruzione.

### 2 — Autocomplete città per esperienze/istruzione
Nuovo componente `CityOnlyAutocomplete.jsx`: variante a campo unico di
`CityAutocomplete` (già in uso per il profilo/ricerche), stessa logica di
suggerimento con paese in piccolo sotto la città — nessun campo paese
visibile, `country_code` derivato dal suggerimento selezionato. Integrato
in `ExperienceGroupEditor.jsx` (per ogni ruolo) e nel nuovo
`EducationListEditor.jsx` (per ogni voce di istruzione).

### 3 — Data inizio/fine per ruoli e istruzione
Aggiunti input `type="date"` per `start_date`/`end_date` su ogni ruolo
(`ExperienceGroupEditor.jsx`) e ogni voce di istruzione
(`EducationListEditor.jsx`), in Onboarding e in Modifica profilo.

### 4 — Spunta "in corso" (esperienze e istruzione)
Checkbox "In corso"/"Ongoing" che, se spuntata, disabilita e azzera il
campo data fine; al salvataggio viene inviato `end_date: null`. Richiede:
- `Education.end_date` reso nullable (era obbligatorio) — migrazione
  `0005_...`, verificato che le 4 righe esistenti avessero già una data di
  fine (nessun rischio di perdita dati);
- `Experience.end_date` era già nullable: l'ordinamento SQL
  `-end_date` mette già i `NULL` per primi su PostgreSQL di default
  (verificato via shell), quindi "in corso" vince già il confronto senza
  modifiche;
- `selection.py`: il tie-break di Istruzione avviene in Python (non SQL),
  quindi serviva un fix esplicito — nuova `_education_end_ordinal` che
  tratta `end_date=None` come "infinito" (vince su qualunque data passata)
  invece di rompersi su `None.toordinal()`; la durata per il secondo
  livello di tie-break usa la data odierna come fine provvisoria;
- CV: nuova etichetta `SECTION_LABELS[...]["ongoing"]` ("Presente"/
  "Present") usata da `_format_date_range` al posto della data di fine
  quando `end_date is None`, sia per esperienze sia per istruzione.

### Editor Istruzione dedicato
`EducationListEditor.jsx` (nuovo componente, sia in Onboarding sia in
Modifica profilo) sostituisce il generico `ListSectionEditor` per
Istruzione: necessario per ospitare autocomplete città + checkbox "in
corso", non esprimibili con la config a campi generici già usata per
competenze/certificazioni/lingue.

### Verifica eseguita
- `python manage.py test`: 169/169 passati (nuovi test in
  `test_selection.py` per il tie-break "in corso" di Istruzione: vince sul
  confronto con date passate, durata calcolata su data odierna);
  `makemigrations --check --dry-run` pulito.
- Frontend: `npm run build` pulito; `oxlint` senza nuovi errori sui file
  toccati in questo sprint.
- Verifica end-to-end via API su un utente di test dedicato (creato e
  poi eliminato): `POST /api/experiences/` e `POST /api/educations/` con
  `end_date: null` → `201 Created`; generazione CV (chiamata diretta a
  `_build_shown_educations`/`_build_shown_experiences`) confermata:
  `location: "Milan, IT"`, `dates: "2023-01 - Presente"`.
- **Problema riscontrato e risolto durante la verifica**: subito dopo aver
  copiato i file aggiornati nel container di produzione (`docker cp`), le
  stesse richieste via API restituivano `500` (esperienze) o `400 "Il
  campo non può essere nullo"` (istruzione), mentre la stessa operazione
  funzionava correttamente da shell Django. Causa: i worker gunicorn già
  in esecuzione avevano ancora in memoria la versione precedente di
  `models.py`/`serializers.py` — `docker cp` aggiorna solo il file su
  disco, non il processo già avviato. Risolto con `docker restart
  app-apply-web-1`; da tenere a mente per i prossimi sprint che
  modificano modelli/serializzatori: dopo il deploy va sempre previsto un
  restart (o rebuild) del servizio `web`, non solo la copia dei file.

### Cosa manca
- Nessun nuovo punto aperto sui 4 difetti segnalati.
- Come già per `country_code` del profilo (Sprint 33), gli utenti con
  esperienze/istruzione già inserite senza località strutturata dovranno
  passare dalla pagina di modifica profilo e riselezionare la città
  dall'autocomplete per popolare `location_country_code` — nessuna
  migrazione dati retroattiva (app in fase di test).
- Resta valido quanto già segnalato negli sprint precedenti (calibrazione
  parametri, qualità reale dei contenuti con una vera `ANTHROPIC_API_KEY`,
  suite e2e da ambiente dedicato).
