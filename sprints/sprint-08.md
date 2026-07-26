# Sprint 08 — Scoring

## Input
- Sprint 07 completato (Job raccolti); Sprint 04 (profilo per il confronto).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.4; `02-specifiche-tecniche-v3.md` §3.5, §5.1 punto 2.

## Obiettivo
Task di scoring che, per ogni `Job` non ancora valutato, chiama Claude per ottenere `score` (1–5), `score_match`, `score_gaps`, `score_reasoning`; in caso di fallimento della singola chiamata, il Job viene scartato per quella notte e l'evento tracciato in `RunLog`.

## Risultato atteso
Eseguendo il task su un insieme di Job raccolti, ciascuno riceve un punteggio con motivazione e scomposizione match/gap, oppure viene escluso con traccia in `RunLog` se lo scoring fallisce.

## Criteri di verifica
- Con mock della risposta Claude valida, dopo l'esecuzione il Job ha `score` (1–5), `score_match`, `score_gaps`, `score_reasoning` valorizzati.
- Con mock che simula un errore/timeout per un Job specifico, quel Job resta privo di score e in `RunLog` compare una entry che lo referenzia.
- Un Job scartato per fallimento scoring non compare tra i candidati passati al cap di intake (Sprint 09).
- Eseguendo il task su un batch misto (alcuni Job che falliscono, altri no), gli altri Job del batch ricevono comunque lo score senza eccezioni non gestite.

## Output per lo sprint successivo
Job scorati (o scartati con traccia in RunLog), pronti per l'applicazione del cap di intake (Sprint 09).