# Sprint 47 — Scoring da scala 1–5 a 1–10 con rubrica esplicita per fascia

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-09-24 → 2026-09-28 · **Commit:** `d0faa0d`

## Input
Segnalazione del committente (24/09): troppi job ricevono lo stesso
punteggio (in particolare 4). Richiesta: portare lo score da 1–5 a 1–10,
con proposte e criticità prima di procedere.

Diagnosi riportata nel commit: la scala 1–5 era troppo grezza per
distinguere i match "buoni ma non perfetti" e il modello convergeva su un
valore intermedio di default.

## Decisioni prese
- Tra le alternative proposte il committente ha scelto la cosiddetta
  "opzione 2". Il dettaglio delle alternative non si può ricostruire (la
  sessione è stata cancellata); quello che è stato implementato è una
  scala 1–10 con una **rubrica esplicita per fascia**, legata al conteggio
  dei requisiti "hard" soddisfatti o mancanti, al posto di un giudizio
  complessivo.
- **Storico non riscalato**: i punteggi dati prima dello sprint restano
  nella vecchia scala 1–5. È una scelta esplicita: nessun dato precedente
  supera 5. Non c'è nessuna migrazione dati.
- **Filtro score** nella lista job: diventa una tendina a multiselezione
  invece di 10 pulsanti affiancati.
- **Colore del badge** del punteggio: a fasce (5 fasce da 2 valori ciascuna,
  sugli stessi 5 colori già esistenti) invece di un colore per ogni valore.

## Implementazione

### Modello dati
- `Job.score`: il validatore passa da `MaxValueValidator(5)` a
  `MaxValueValidator(10)`. Migrazione `jobs/0011_alter_job_score.py`, che
  cambia solo il validatore e non tocca i dati.

### Backend
- `apps/jobs/ai_scoring.py`, `SCORING_SYSTEM_PROMPT`:
  - intervallo dichiarato "da 1 a 10 (10 = massima affinità)";
  - nuova sezione "Come scegliere il punteggio": prima di scegliere il
    numero, il modello conta i requisiti hard (competenze, esperienza,
    seniority dichiarate come necessarie, non preferenziali) soddisfatti e
    mancanti. Fasce: 9–10 tutti soddisfatti; 7–8 manca al più un elemento
    secondario; 5–6 manca almeno un requisito hard o la seniority non è
    allineata; 3–4 più requisiti mancanti o forte disallineamento di
    ruolo/settore; 1–2 profilo non pertinente. Il prompt chiede inoltre di
    usare tutta la scala in modo differenziato;
  - regola 2 (descrizione vuota o non valutabile): il tetto prudenziale
    passa da "non superiore a 3" a "non superiore a 6".
- `apps/jobs/scoring.py`, `_apply_score_result`: il clamp passa da
  `min(5, …)` a `min(10, …)`.

### Frontend
- Nuovo `src/components/MultiSelectFilter.jsx`: tendina con checkbox che si
  chiude al click esterno. Nessuna nuova dipendenza.
- `src/pages/JobListPage.jsx`: `SCORES` passa da 1–5 a 1–10 e il filtro
  score usa `MultiSelectFilter`.
- Nuovo `src/utils/scoreStyle.js` (`scoreStyle(score)`, fascia =
  `ceil(score/2)` limitata a 1–5). Sostituisce le due mappe `SCORE_STYLE`
  duplicate in `JobCard.jsx` e `JobDetailPage.jsx`.

### Specifiche e documentazione
- Aggiornati, nel commit stesso, `01-specifiche-funzionali-v4.md` (§4.4,
  §4.5 filtri, §7 criteri di accettazione), `02-specifiche-tecniche-v3.md`
  (§3.5, §4.4, §5.1, §10) e `CLAUDE.md` (punteggio 1–10).
- Non aggiornati: `Docs/01-specifiche-funzionali-v5.md` e
  `Docs/02-specifiche-tecniche-v4.md`, che restano su 1–5.

## Verifica
- Il messaggio di commit dichiara una validazione su un campione reale: la
  distribuzione dei punteggi passa da 3 valori accorpati a 5 valori
  distinti. Non risultano i dettagli del campione.
- Nessun test automatico aggiunto o modificato nel commit.

## Note / cosa manca
- **Numerazione incoerente:** i commenti nel codice
  (`ai_scoring.py`, `models.py`, `scoreStyle.js`) e la §4.4/§10 di
  `02-specifiche-tecniche-v3.md` chiamano questo cambio "Sprint 46",
  mentre il commit è "Sprint 47". Fa fede il commit.
- **Commit misto:** `d0faa0d` contiene anche il frontend del refactor "gap
  filling" di `JobDetailPage.jsx` (pannello di selezione dei gap con
  istruzioni, rimozione dell'arricchimento su esperienza esistente), che
  appartiene allo Sprint 46 (`bf9a17a`, solo backend).
- **Effetto dello storico non riscalato:** un vecchio punteggio 5 (il
  massimo su 1–5) viene mostrato con il colore della fascia 3 (5–6) e
  compare tra i "5" del filtro, insieme ai 5 della nuova scala.
- Il criterio di ordinamento della lista (`score` decrescente) mescola le
  due scale per i job precedenti allo sprint.
