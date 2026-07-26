# Sprint 13 — Arricchimento profilo

## Input
- Sprint 12 completato (generazione manuale).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.8; `02-specifiche-tecniche-v3.md` §5.2 (nota), §6.2.

## Obiettivo
Endpoint per aggiungere un dettaglio di esperienza reale prima di una generazione/rigenerazione manuale, con scelta se salvarlo anche nel profilo master o solo per quel CV; il dettaglio viene passato al servizio di generazione come contesto aggiuntivo.

## Risultato atteso
Generando un CV con un dettaglio di arricchimento "solo per questo CV", il PDF risultante riflette quel dettaglio ma il profilo master resta invariato; con l'opzione "salva anche nel master", il profilo risulta aggiornato.

## Criteri di verifica
- Invio di un dettaglio di arricchimento con `save_to_profile=False`, seguito da generazione CV → il `CVDocument` risultante referenzia l'arricchimento (`enrichment_used`) e il contenuto generato lo riflette (verificabile tramite mock della chiamata Claude); il `Profile` dell'utente non contiene il nuovo dettaglio.
- Stesso test con `save_to_profile=True` → il `Profile` risulta aggiornato con il nuovo dettaglio (verificabile in lettura API profilo).
- L'aggiunta dell'arricchimento non modifica `Job.score` (score invariato prima/dopo).

## Output per lo sprint successivo
Arricchimento disponibile come step opzionale prima di ogni generazione manuale; profilo e generazione CV completi per l'uso da frontend.