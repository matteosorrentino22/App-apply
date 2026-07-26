# Sprint 14 — Import manuale di job

## Input
- Sprint 06 (concetto di quota), Sprint 08 (scoring), Sprint 02 (modello `Job`) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.9; `02-specifiche-tecniche-v3.md` §4.6, §5.2.

## Obiettivo
Endpoint API per importare un job LinkedIn tramite link (solo piano Pro), con validazione link, scoring del job importato (senza CV automatico), deduplica, quota giornaliera `import_count` (3/giorno) con estensione a credito (`PRICE_IMPORT_EXTRA`).

## Risultato atteso
Un utente Pro può importare un job valido, che viene scorato e mostrato nella sezione "Job importati" in stato `new`; un utente Free non può importare nemmeno con credito; oltre 3 import/giorno si consuma credito o si blocca.

## Criteri di verifica
- Utente Pro importa un link valido → `Job` creato con `origin='imported'`, `status='new'`, punteggio assegnato (anche se ≥4, nessun `CVDocument` automatico creato).
- Utente Free tenta l'import (anche con `extra_credit` > 0) → richiesta rifiutata.
- Link non valido → risposta con messaggio "impossibile importare quel job", nessun `Job` creato.
- Import di un job già presente nella lista dell'utente → nessun duplicato creato, risposta segnala "questo job è già nella tua lista".
- Utente Pro effettua 3 import nel giorno: il 4° senza credito sufficiente è rifiutato con messaggio di limite; con credito sufficiente, il 4° prosegue e scala `PRICE_IMPORT_EXTRA`.
- Generare poi il CV per un job importato consuma sia `import_count` (già consumato all'import) sia, separatamente, `manual_cv_count` (verificabile leggendo entrambi i contatori dopo le due operazioni).

## Output per lo sprint successivo
Job importati integrati nel modello dati unificato, pronti per essere esposti dalla vista lista (Sprint 15).