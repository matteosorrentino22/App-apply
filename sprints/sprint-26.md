# Sprint 26 — Modello dati e vincoli profilo (contenuto CV, fase 1/4)

## Input
`Docs/03-specifiche-funzionali-contenuto-cv-v4.md` (documento di estensione,
attivo): riscrive selezione/quantità/struttura del contenuto del CV generato.
Questo sprint copre solo il **delta di modello dati e vincoli di input**
(§0 righe 1, 2, 7, 8; §10.1, §10.2), base per gli sprint successivi (pipeline
AI, template, arricchimento vincolato).

## Obiettivo
- Rimuovere `Profile.key_achievements` (sezione "risultati chiave" eliminata
  dal profilo master — sarà sostituita da "Areas of Expertise" calcolata a
  ogni generazione, Sprint 27/28, non un campo del profilo).
- Sostituire `Education.dates` (libero) con `start_date` (opzionale) +
  `end_date` (**obbligatorio**), necessario per il tie-break di selezione
  delle 3 voci più recenti (doc 03 §3.2).
- Introdurre la nozione di "profilo completo" (§10.2): almeno 1 `Education`.
- Avviso frontend quando l'utente inserisce più di 5 esperienze (§3.1, §3.3).
- Adeguare (non ancora riscrivere) pipeline AI e template al nuovo modello,
  senza toccare ancora qualifica professionale/Areas of Expertise/selezione
  per rilevanza (Sprint 27).

## Esito (2026-07-29)

### Modello dati
- `Profile.key_achievements` rimosso.
- `Education.dates` (CharField libero) rimosso; sostituito da `start_date`
  (DateField, opzionale) ed `end_date` (DateField, **non nullable**).
- Nuova property `Profile.is_complete` (`educations.exists()`) — usata come
  guardia prima di ogni generazione di CV (vedi sotto).
- Migrazione `0003_education_start_end_date_no_key_achievements`: nessun dato
  da preservare (confermato: in produzione un solo profilo di test con
  `Education.dates=''`, nessun `key_achievements` compilato) — la migrazione
  elimina le righe `Education` esistenti prima di rendere `end_date`
  obbligatorio, coerente con "nessuna migrazione dati" del documento (§10.3,
  l'app è in fase di test).

### Guardia "profilo completo" prima della generazione
- `generate_cv` (usato sia dal ciclo automatico che da quello manuale)
  solleva `ProfileIncomplete` se il profilo non ha almeno una `Education`.
- `manual_generation.py` controlla la stessa condizione **prima** di
  riservare quota/credito (stesso pattern della guardia di concorrenza
  esistente), per non consumare massimale su una richiesta comunque respinta.
- Il ciclo notturno (automatico) eredita la protezione tramite `generate_cv`:
  un profilo incompleto fa fallire la generazione con lo stesso path di
  errore già esistente (`RunLog`, job torna a `new`, nessun blocco per gli
  altri utenti del batch).

### Adeguamento minimo di pipeline AI e template (non riscrittura)
- `ai_content.py`, `cv_import.py`: schema JSON e prompt aggiornati per non
  riferire più `key_achievements`; `Education` letta/scritta con
  `start_date`/`end_date`.
- `generation.py`: `_build_educations` compone la stringa data da
  `start_date`/`end_date` invece del vecchio campo libero.
- `cv_template.html`: rimossa la sezione "Risultati chiave" (nessuna nuova
  sezione introdotta in questo sprint — Areas of Expertise arriva con la
  riscrittura della pipeline, Sprint 27, e il nuovo layout, Sprint 28).

### Frontend
- `OnboardingPage.jsx`: campo "Risultati chiave" rimosso dal form; i campi
  istruzione usano `start_date`/`end_date` (input `type="date"`, `end_date`
  obbligatorio); avviso testuale quando le esperienze inserite superano 5
  (§3.1, §3.3 — testo esatto da validare in tuning, coerente con "punti da
  verificare" del doc 03 §14).
- `ListSectionEditor.jsx`: supporto generico a `type`/`required` per campo,
  usato dai nuovi campi data.
- Traduzioni IT/EN aggiornate (`profileAchievements` rimosso,
  `dates`→`startDate`/`endDate`, nuove voci `experiencesLimitWarning`,
  `educationEndDateRequired`).

### Verifica eseguita
- Backend: `python manage.py test` → **141/141 passati** (nessuna
  regressione: aggiornati i test esistenti che creavano profili/istruzioni
  col vecchio schema o senza `Education`, ora bloccati dalla guardia di
  completezza); `makemigrations --check --dry-run` pulito.
- Frontend: `npm run build` pulito; `oxlint` sui file toccati — 0 errori (1
  warning preesistente non introdotto in questo sprint).
- Verificato che la migrazione non sia ancora applicata al database di
  produzione (`showmigrations` → `[ ]` su `0003`): verrà applicata al deploy
  dal comando di avvio (`migrate --noinput`), come per tutte le migrazioni
  precedenti — nessuna azione manuale aggiuntiva richiesta.

### Cosa manca
- Qualifica professionale, Areas of Expertise, ordinamento di rilevanza,
  selezione/taglio server-side, swap singolo esperienze: **Sprint 27**.
- Nuovo template (layout dal riferimento del committente) e loop di ripiego
  overflow: **Sprint 28**.
- Arricchimento vincolato a un'esperienza esistente (non più campi liberi
  company/role): **Sprint 29**.
- Valori esatti dei parametri (budget B, `EDU_MAX_SHOWN`, limiti caratteri)
  e testi esatti (avviso >5 esperienze, guida alla compilazione): da
  calibrare in test, punti espliciti "da verificare" del doc 03 §14 — non
  bloccanti per procedere con gli sprint successivi.
