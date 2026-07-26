# Sprint 11 — Generazione automatica nel ciclo notturno

## Input
- Sprint 09 (ciclo notturno) e Sprint 10 (servizio di generazione CV) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.7 ("Generazione automatica"); `02-specifiche-tecniche-v3.md` §5.1 punto 4.

## Obiettivo
Collegare il servizio di generazione CV al ciclo notturno: per ogni Job con punteggio 4–5 tenuto dopo il cap, generare automaticamente il CV; impostare lo stato Job risultante (`new` per 1–3, `cv_generated` per 4–5 con generazione riuscita); in caso di fallimento, il Job torna a `new`.

## Risultato atteso
Al termine di un'esecuzione simulata del ciclo notturno con Job a punteggio misto, i Job 4–5 hanno un `CVDocument` associato e stato `cv_generated`; i Job 1–3 restano `new` senza `CVDocument`; un fallimento simulato riporta un Job 4–5 a `new` senza `CVDocument`.

## Criteri di verifica
- Esecuzione test del ciclo notturno su un set con Job a punteggio 1–5 misto: al termine, tutti e soli i Job con score 4–5 hanno un `CVDocument` con `generation_type='automatic'`.
- Job con score 1–3 restano in stato `new`, nessun `CVDocument` creato.
- Con mock che fa fallire la generazione per un Job 4–5 specifico, quel Job risulta in stato `new` (non `cv_generated`) e senza `CVDocument`, senza bloccare la generazione degli altri Job del batch.
- La generazione automatica non consuma i contatori `DailyQuota` (`manual_cv_count` invariato dopo il ciclo notturno).

## Output per lo sprint successivo
Comportamento automatico completo del ciclo notturno; base per introdurre la generazione manuale con le sue regole di quota/credito (Sprint 12).