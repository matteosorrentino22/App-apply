# Sprint 33 — Fix layout intestazione, esperienze e istruzione nel CV

## Input
Ulteriori 7 difetti segnalati dal committente dopo lo Sprint 32, in
inglese (con richiesta di applicare lo stesso approccio a qualsiasi lingua
di generazione del CV).

## Esito (2026-08-08)

### 1 — Riga contatti riordinata, LinkedIn come link ipertestuale
Nuovo ordine fisso: **Città, PAESE | telefono | email | LinkedIn**.
- `Profile.country_code` (nuovo campo, 2 lettere ISO 3166-1 alpha-2,
  migrazione `0004_profile_country_code`): derivato dall'autocomplete
  Nominatim, che ora restituisce anche `country_code` (esteso `geo.py`,
  già usato dalle ricerche salvate — retrocompatibile, nuova chiave
  aggiuntiva nella risposta).
- `generation.py`: `_build_contact_line` (stringa) → `_build_contact_parts`
  (lista di parti tipizzate `{text, url, is_link}`), perché LinkedIn deve
  essere un link HTML (`<a href>`) mentre gli altri campi sono testo — non
  esprimibile in un'unica stringa concatenata come prima.
- La città è **tradotta da Claude** insieme al resto del contenuto del CV
  (nuovo campo `translated_city` nello schema JSON di `ai_content.py`, col
  paese/acronimo che resta invariato, essendo un codice ISO fisso non
  traducibile).
- Prefisso telefono: nessun nuovo campo, solo placeholder aggiornato
  ("Es. +39 331 3394607") nei form di onboarding/modifica profilo, come
  discusso col committente.
- Città/paese: campo libero sostituito da `CityAutocomplete` (già usato
  per le ricerche salvate) sia in Onboarding sia nella pagina di modifica
  profilo.

### 2 — Riga contatti tra due linee
Aggiunto `border-top` sulla riga contatti (il `border-bottom`
dell'intestazione esisteva già).

### 3 — Corpo del testo più piccolo
Livelli di compattamento (`rendering.py`) ridotti: default 10pt → 9pt (e
8pt/7pt sui livelli di ripiego, invece di 9pt/8pt). I titoli di sezione
(`h2`) sono stati disaccoppiati dal font di base (dimensione fissa 11pt,
non più `base_font_size + 1`) per non farli scendere insieme al corpo,
come richiesto esplicitamente.

### 4 — "Skilled in"/"Certified in" in grassetto solo l'etichetta
`<strong>{{ labels.certified_in }}:</strong> ...` — il contenuto dopo i due
punti resta normale.

### 5 — "Experience" → "Work Experience"
Etichetta di sezione aggiornata in `SECTION_LABELS` (IT: "Esperienza" →
"Esperienza lavorativa"; EN: "Experience" → "Work Experience").

### 6 — Azienda maiuscola+grassetto, ruolo maiuscolo non-grassetto
`.experience-company` già maiuscolo+grassetto (nessuna modifica).
`.experience-role` reso maiuscolo (`text-transform: uppercase`) e privato
del grassetto.

### 7 — Luogo e date sulla riga del ruolo, allineati a destra, date in grassetto
Riprogettato il markup di esperienza e istruzione: rimossa la riga
separata azienda/luogo; luogo e date ora compaiono sulla riga del
ruolo/titolo, allineati a destra (`justify-content: space-between`), con
le sole date in `<strong>` (es. "Rome, IT | **2020 - 2022**"). Applicato
identicamente alla sezione Istruzione (chiesto esplicitamente dal
committente), rimossa la vecchia riga `.education-meta` separata per il
luogo.

### Verifica eseguita
- `python manage.py test`: 167/167 passati (fixture `_fake_content`/
  `_fake_content_with_long_bullets` aggiornate con `translated_city`,
  altrimenti `KeyError` — unica causa di regressione, corretta);
  `test_geo.py` aggiornato per il nuovo campo `country_code` nella risposta
  Nominatim; `makemigrations --check --dry-run` pulito.
- Frontend: `npm run build` e `oxlint` sui file toccati — puliti.
- Verifica visiva end-to-end: generato un CV reale con l'intera pipeline
  (solo `generate_cv_content` mockato) con due esperienze nella stessa
  azienda ma ruoli/periodi diversi (scenario esplicitamente citato dal
  committente per il punto 7) — confermati tutti i 7 punti sul PDF
  prodotto, incluso il layout azienda unica con due blocchi ruolo separati.

### Cosa manca
- Nessun nuovo punto aperto. Il campo `country_code` non ha una migrazione
  dati per i profili esistenti (nessun paese pre-esistente da cui derivarlo
  automaticamente): gli utenti che hanno già una città salvata dovranno
  passare dalla pagina di modifica profilo e riselezionare città/paese
  dall'autocomplete per popolare l'acronimo — coerente con l'approccio già
  seguito per i vincoli introdotti negli sprint precedenti (app in fase di
  test, nessuna migrazione dati retroattiva).
- Resta valido quanto già segnalato negli sprint precedenti (calibrazione
  parametri, qualità reale dei contenuti con una vera `ANTHROPIC_API_KEY`,
  suite e2e da ambiente dedicato).
