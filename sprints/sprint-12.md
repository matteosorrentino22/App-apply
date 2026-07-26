# Sprint 12 — Generazione manuale + quote/credito

## Input
- Sprint 10 (servizio generazione CV); `DailyQuota` e `User.extra_credit` (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.7, §4.11; `02-specifiche-tecniche-v3.md` §4.6, §5.2.

## Obiettivo
Endpoint API di generazione manuale (anche per rigenerazione e per retry di un fallimento automatico) con: guardia di concorrenza (`cv_generation_in_progress`), controllo/riserva atomica del contatore `manual_cv_count` o del credito (`extra_credit` scalato secondo `PRICE_MANUAL_CV_EXTRA`), restituzione della riserva su fallimento.

## Risultato atteso
Un utente può richiedere la generazione manuale di un CV per qualsiasi job entro il proprio massimale o a credito; richieste concorrenti sullo stesso job vengono rifiutate; un fallimento non consuma budget.

## Criteri di verifica
- Utente Free: la 1ª generazione manuale nel giorno riesce e consuma `manual_cv_count`; la 2ª, con saldo credito insufficiente, è rifiutata con messaggio di limite raggiunto; con saldo sufficiente, la 2ª prosegue e scala `PRICE_MANUAL_CV_EXTRA` da `extra_credit`.
- Utente Pro: le prime 10 generazioni manuali nel giorno consumano il contatore; l'11ª (senza credito) è rifiutata.
- Due richieste ravvicinate sullo stesso Job: la seconda, inviata mentre `cv_generation_in_progress=True`, è rifiutata senza consumare quota/credito (contatore/saldo invariato dopo il rifiuto).
- Simulando un fallimento nel servizio di generazione, il contatore consumato viene decrementato o il credito scalato riaccreditato, secondo la modalità di addebito registrata; il Job torna a `new`.
- Il retry di un fallimento automatico (Job tornato a `new` da uno stato 4–5 fallito) consuma il massimale manuale tramite lo stesso endpoint/contatore, non un budget separato.
- Un job in Archivio, dopo generazione riuscita, risulta `is_archived=False` e nella sua sezione d'origine.

## Output per lo sprint successivo
Meccanismo di generazione manuale completo, riusato dall'arricchimento (Sprint 13) prima di ogni chiamata di generazione/rigenerazione.