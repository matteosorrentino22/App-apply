# Sprint 04 — Profilo master

## Input
- Sprint 03 completato (autenticazione funzionante).
- Riferimenti: `01-specifiche-funzionali-v4.md` §3, §4.1; `02-specifiche-tecniche-v3.md` §4.2.

## Obiettivo
API REST CRUD per il profilo master e le sue sezioni (`summary`, `key_achievements`, `Experience`, `Education`, `Skill`/`Certification`, `Language`) e upload della foto profilo.

## Risultato atteso
Un utente autenticato può creare, leggere e modificare tutte le sezioni del proprio profilo e caricare una foto; i dati sono isolati per utente.

## Criteri di verifica
- Creare più `Experience` (numero variabile) per un profilo e verificare che vengano tutte restituite in lettura.
- Upload foto profilo (endpoint dedicato o campo multipart) restituisce un riferimento al file salvato, rileggibile successivamente.
- Test di isolamento: una richiesta autenticata come utente A verso il profilo di utente B restituisce 403/404.
- La suite di test automatici del modulo profilo passa (`python manage.py test` o equivalente).

## Output per lo sprint successivo
API profilo completa, riusata dal parsing CV (Sprint 05) per il pre-popolamento e dal servizio di generazione CV (Sprint 10+) come sorgente dati.