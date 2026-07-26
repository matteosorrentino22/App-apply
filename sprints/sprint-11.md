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

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.jobs.tasks._generate_automatic_cv(job)` — invoca `apps.cv.generation.generate_cv(job, CVDocument.GenerationType.AUTOMATIC)` (Sprint 10) per un singolo Job. In caso di successo imposta `job.status = cv_generated` e `job.date_cv_generated = now()`; in caso di eccezione registra un `RunLog` (`task_type=cv_generation`, `status=failure`) e lascia il Job invariato (`new`, senza `CVDocument`), senza propagare l'errore — stesso pattern di isolamento fallimenti già usato per lo scoring (Sprint 08).
- `apps.jobs.tasks.run_nightly_cycle_for_user` esteso: dopo il cap di intake, itera i Job **tenuti** con `score >= 4` e chiama `_generate_automatic_cv` per ciascuno; il conteggio `cv_generati` è aggiunto sia al messaggio del `RunLog` di riepilogo sia al dizionario di ritorno (`cv_generated`). I Job con score 1–3 non vengono toccati: restano `new` con lo `status` di default, nessuna chiamata a `generate_cv`.
- Nessuna interazione con `DailyQuota`: la generazione automatica non incrementa `manual_cv_count` (che resta un contatore esclusivamente per la generazione manuale, Sprint 12) — coerente con §4.11 funzionali ("la generazione automatica non ha un contatore proprio").

### Verifica eseguita
`python manage.py test apps.jobs` (18/18, incluse le 4 nuove di `AutomaticCvGenerationInNightlyCycleTests`, con `generate_cv` mockato per isolare l'orchestrazione dalla pipeline di generazione già testata a sé nello Sprint 10) e `python manage.py test` sull'intero progetto (39/39, nessuna regressione); `makemigrations --check` pulito (nessuna modifica ai modelli in questo sprint).

| Criterio | Esito |
|---|---|
| Job con score 1–5 misto: tutti e soli i Job 4–5 hanno un `CVDocument` con `generation_type='automatic'` e Job in stato `cv_generated` | ✅ |
| Job con score 1–3 restano `new`, nessun `CVDocument` | ✅ |
| Fallimento simulato su un Job 4–5 specifico → quel Job resta `new` (non `cv_generated`), senza `CVDocument`, senza bloccare la generazione degli altri Job del batch | ✅ (verificato anche il `RunLog` di fallimento associato) |
| La generazione automatica non consuma `DailyQuota.manual_cv_count` | ✅ (verificato che nessun `DailyQuota` viene creato dal ciclo notturno) |

### Cosa manca
- Nessuna verifica end-to-end reale della generazione CV (dipende da Claude/WeasyPrint reali, già verificati singolarmente nello Sprint 10) — qui l'orchestrazione è testata con `generate_cv` mockato, stesso schema di mocking già adottato per raccolta/scoring.
- Guardia di concorrenza (`cv_generation_in_progress`), quota/credito e riserva all'accodamento per la generazione manuale, incluso il "riprova" su un fallimento automatico: Sprint 12.
