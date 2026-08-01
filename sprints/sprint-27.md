# Sprint 27 — Pipeline contenuti AI e selezione/taglio server-side (contenuto CV, fase 2/4)

## Input
Sprint 26 completato (modello dati e vincoli profilo). Questo sprint copre
la riscrittura della pipeline di generazione contenuti secondo
`Docs/03-specifiche-funzionali-contenuto-cv-v4.md` §5.1, §5.3, §5.4, §11,
§12, §13: qualifica professionale, Areas of Expertise, ordinamento di
rilevanza, selezione/taglio deterministico lato server.

## Obiettivo
- Calcolo deterministico dei tetti (voci di istruzione mostrate, budget
  bullet B) **prima** della chiamata AI, senza bisogno del modello.
- Un'unica chiamata Claude che produce: sommario, qualifica professionale,
  Areas of Expertise (con riferimento di grounding), bullet riformulati e
  ordinamento di rilevanza per **tutte** le esperienze del profilo, marcatura
  "altamente rilevante", selezione di skills/certifications.
- Selezione e taglio **lato server, senza nuova chiamata AI**: cap a 5
  esperienze con swap singolo, taglio bullet al budget globale, minimo
  garantito per esperienza vecchia ma rilevante.
- Non ancora in scope: nuovo layout template (Sprint 28), loop di ripiego
  overflow con rirenderizzazione (Sprint 28), arricchimento vincolato a
  esperienza esistente (Sprint 29).

## Esito (2026-08-01)

### Nuovo modulo `cv_parameters.py`
Parametri di configurazione centralizzati (§12 del documento): `EDU_MAX_SHOWN`
(3), tabella budget B (1→12, 2→10, 3→9), cap esperienze (5), minimo bullet
garantito (2), min/max Areas of Expertise (4/6). Valori indicativi, da
calibrare in test (già segnalato come punto aperto dal documento stesso).

### Nuovo modulo `selection.py` (puro, senza AI né DB)
- `select_educations_to_show`: le `EDU_MAX_SHOWN` voci più recenti, tie-break
  su durata minore poi casuale (§3.2).
- `compute_bullet_budget`: applica la tabella parametrica.
- `select_and_cut_experiences`: cap a 5 esperienze con swap singolo (la più
  rilevante tra le escluse marcate "altamente rilevante", tie-break sulla più
  recente, sostituisce la meno recente delle 5 selezionate — mai più di uno
  swap), poi taglio bullet al budget globale usando `relevance_rank`, con
  minimo garantito per un'esperienza vecchia ma rilevante altrimenti senza
  bullet (§5.4, §11 punto 4).
- 13 test unitari dedicati (`test_selection.py`), copertura di: tie-break
  istruzione, tabella budget, cap con/senza swap, tie-break dello swap,
  taglio al budget, degradazione a riga singola, minimo garantito.

### Pipeline AI riscritta (`ai_content.py`)
- Nuovo schema JSON: `qualification`, `areas_of_expertise` (4–6 voci
  enforced anche a livello di schema con `minItems`/`maxItems`, non solo nel
  prompt, ciascuna con `grounding_reference`), `experiences` con bullet
  strutturati (`text` + `relevance_rank`) e `highly_relevant` per esperienza,
  `certifications` selezionate (in aggiunta a `skills`, già esistente).
- Il modello riceve **tutte** le esperienze del profilo (§11 punto 1,
  ordinate per data di fine decrescente) — non un sottoinsieme provvisorio:
  la selezione avviene dopo, lato server (nessuna circolarità, coerente con
  la nota di versione v4 del documento).
- Prompt esteso con le regole di generalizzazione della qualifica (§5.1) e
  la licenza di astrazione delimitata per le Areas of Expertise (§5.3:
  sintesi ammessa, deduzione dalla sola job description vietata).

### Orchestrazione (`generation.py`)
- Calcola i tetti (istruzione mostrata, budget B) **prima** della chiamata
  AI; applica selezione/taglio **dopo**, senza ulteriori chiamate AI (§11).
- Il riferimento di grounding delle Areas of Expertise è salvato in
  `CVDocument.areas_of_expertise_grounding` (nuovo campo JSON, migrazione
  `0002_cvdocument_areas_of_expertise_grounding`) — mai esposto nel CV,
  solo per diagnosi in fase di tuning (§13).

### Template (adeguamento minimo, non il restyling)
- Aggiunta la riga qualifica sotto il nome e la sezione "Areas of Expertise"
  (due colonne) al template esistente, così il nuovo contenuto ha un
  aggancio visivo verificabile in questo sprint. Il layout completo dal
  riferimento del committente arriva nello Sprint 28.

### Verifica eseguita
- `python manage.py test`: **154/154 passati** (141 pre-esistenti + 13 nuovi
  di `test_selection.py`); nessuna regressione (`_fake_content` e i test che
  ne dipendevano aggiornati al nuovo schema con bullet strutturati).
- `makemigrations --check --dry-run`: pulito.
- Verificato manualmente in shell il caso limite "zero esperienze"
  (neolaureato, §8): `select_and_cut_experiences([], ...)` ritorna lista
  vuota senza errori.

### Cosa manca
- Nuovo layout template dal riferimento del committente, loop di ripiego
  overflow (rimozione bullet + rirenderizzazione, max 4 iterazioni), test
  worst-case A/B del contratto template (§7): **Sprint 28**.
- Arricchimento vincolato a un'esperienza esistente: **Sprint 29**.
- Calibrazione dei valori parametrici e verifica della qualità reale dei
  contenuti (qualifica, Areas of Expertise, ordinamento di rilevanza) con
  una vera `ANTHROPIC_API_KEY` e profili reali: nessuna `ANTHROPIC_API_KEY`
  di test isolata in questo ambiente, stesso limite già segnalato negli
  sprint precedenti che toccano Claude.
