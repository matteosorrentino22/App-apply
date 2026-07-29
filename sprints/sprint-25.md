# Sprint 25 — Fix: raccolta notturna persa per crash su `published_at`

## Input
Ispezionando `RunLog` in produzione dopo lo Sprint 24 (non richiesto da nessuna
specifica, emerso controllando lo stato reale dei cicli notturni) si osserva,
per l'utente 3 il 2026-07-28 alle 21:46:28: `collection failure — 'str' object
has no attribute 'timestamp'`. È un bug reale, attualmente presente in
produzione, distinto dai due problemi già noti e volutamente rimandati
(selettività Apify, suite e2e Playwright).

## Causa
`ApifyLinkedInSource._normalize_item` passa `publishedAt`/`postedAt` (stringa
ISO restituita da Apify) senza convertirla in `datetime`. `collection.py`
assegna questo valore direttamente a `Job(published_at=...)` senza mai
ripassare dal database prima che `apps.jobs.intake.apply_intake_cap` lo usi
per il tie-break (`job.published_at.timestamp()`): su un oggetto Django non
ancora ricaricato dal DB, il campo resta la stringa originale in memoria —
la conversione a `datetime` avviene solo al `refresh_from_db`/refetch, non
all'assegnazione. Il risultato: `AttributeError`, che risale fino al blocco
per-utente introdotto nello Sprint 22 — la raccolta di quella notte per
l'utente colpito va **interamente persa** (l'isolamento evita che si propaghi
agli altri utenti, ma non salva i job di chi lo incontra).

## Fix
`_normalize_item` ora converte esplicitamente la data con
`django.utils.dateparse.parse_datetime` prima di restituire il dict
normalizzato, così il valore è già un `datetime` (o `None`) quando arriva a
`Job.objects.create()`. Nessun altro modulo modificato.

## Verifica eseguita
- Riprodotto lo scenario esatto del crash di produzione (creazione di un
  `Job` con `published_at` proveniente da un dict normalizzato, poi passato
  a `apply_intake_cap` senza refetch dal DB): confermato il crash pre-fix e
  la risoluzione post-fix con uno script diretto nella shell Django del
  container di produzione.
- 2 nuovi test su `ApifyLinkedInSourceTests`: `publishedAt` stringa → `datetime`
  reale; assente → `None`.
- `python manage.py test`: **141/141 passati** (139 pre-esistenti + 2 nuovi).
- `makemigrations --check --dry-run`: nessuna differenza.

## Deploy
Rebuild e riavvio di `web`/`worker`/`beat` in produzione.

## Cosa manca
Nessun elemento noto in sospeso per questo fix. Non essendo ancora passata
una notte con il fix attivo, non è stato possibile osservare direttamente in
produzione un ciclo notturno completo privo di questo errore — solo la
riproduzione diretta in shell.
