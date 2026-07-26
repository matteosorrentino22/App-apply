# Sprint 09 — Ciclo notturno orchestrato

## Input
- Sprint 07 (raccolta) e Sprint 08 (scoring) completati.
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.4; `02-specifiche-tecniche-v3.md` §5.1, §7.

## Obiettivo
Orchestrare raccolta → scoring → cap di intake (15 job/utente/giorno, tie-break su `published_at` più recente o casuale se mancante/pareggio persistente) come task Celery Beat schedulato alle 02:00 Europe/Rome; scarto definitivo degli eccedenti; `RunLog` completo dell'esecuzione.

## Risultato atteso
Un'esecuzione simulata del ciclo notturno, per un utente con più di 15 Job scorati, mantiene solo i 15 a punteggio più alto (con tie-break corretto) e scarta definitivamente gli altri.

## Criteri di verifica
- Eseguendo il task orchestratore su dati di test con >15 Job scorati per un utente, al termine risultano tenuti esattamente 15 Job e gli altri sono esclusi in modo da non essere riproposti in esecuzioni successive.
- Test del tie-break: con più Job a pari punteggio al confine del taglio, viene preferito quello con `published_at` più recente; con data mancante su entrambi (o pareggio persistente), la selezione avviene in modo deterministico nel test (tramite seed/mock del meccanismo casuale), senza errori.
- Celery Beat ha una entry schedulata per le 02:00 Europe/Rome (verificabile da configurazione/admin `django_celery_beat`).
- `RunLog` registra l'esecuzione con conteggio job raccolti, scorati, scartati per cap, scartati per fallimento scoring.

## Output per lo sprint successivo
Per ogni utente, al massimo 15 Job/giorno con score, pronti per la generazione automatica del CV (Sprint 11), che si innesta su questo stesso task.