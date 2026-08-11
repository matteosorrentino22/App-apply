# Sprint 38 — Date stesso anno collassate, istruzione sempre mostrata per intero

## Input
Due fix richieste dal committente:
1. se un'esperienza (lavorativa o formativa) inizia e finisce nello
   stesso anno, non ripetere l'anno due volte (es. "Rome, IT | 2022 -
   2022" → "Rome, IT | 2022");
2. le voci di istruzione vanno sempre mostrate **tutte**, secondo quanto
   scritto dall'utente, senza escluderne alcuna per limite di conteggio.

## Nota sulla deviazione dalla specifica
Il punto 2 cambia esplicitamente una regola documentata in
`Docs/03-specifiche-funzionali-contenuto-cv-v4.md` §3.2 ("limite di voci
di istruzione mostrate nel CV: le 3 più recenti", parametro
`EDU_MAX_SHOWN`): su richiesta diretta del committente, questo limite è
stato rimosso — l'istruzione non viene più selezionata/troncata, sempre
mostrata per intero. Segnalato qui secondo CLAUDE.md ("non modificare
l'architettura delle specifiche tecniche senza segnalarlo
esplicitamente").

## Esito (2026-08-11)

### 1 — Anno unico quando inizio e fine coincidono
`_format_date_range` (`generation.py`): se `start.year == end.year` (ed
`end` non è "in corso"), ritorna il solo anno invece del range. Si
applica identicamente a esperienze e istruzione, essendo la stessa
funzione di formattazione condivisa.

### 2 — Istruzione sempre completa
`select_educations_to_show` (`selection.py`): rimossa la troncatura
`[:EDU_MAX_SHOWN]` — ritorna tutte le voci di istruzione del profilo,
ordinate per data di fine decrescente (stesso tie-break di prima: durata
minore, poi casuale), senza escluderne alcuna. Il parametro
`EDU_MAX_SHOWN` resta usato in `compute_bullet_budget` (`selection.py`)
solo per limitare l'indice nella tabella budget bullet
(`BULLET_BUDGET_BY_EDU_COUNT`, che ha solo le chiavi 1-3): con più di 3
voci di istruzione mostrate si applica comunque il budget più stretto
previsto per 3+ voci, invece di un `KeyError` — non è più un limite al
numero di voci mostrate.

### Verifica eseguita
- `python manage.py test`: 169/169 passati; test aggiornato
  (`test_selection.py`) per riflettere il nuovo comportamento (tutte le
  voci ritornate, ordinate, non più troncate a 3).
- `makemigrations --check --dry-run`: pulito (nessuna modifica ai
  modelli in questo sprint).
- Verifica end-to-end con generazione reale di un CV (solo
  `generate_cv_content` mockato): esperienza con inizio/fine nello stesso
  anno → "2022" (non "2022 - 2022"); profilo con 4 voci di istruzione
  (una delle quali a cavallo di un solo anno) → tutte le 4 mostrate nel
  PDF, inclusa "2016" per la voce a anno unico.

### Cosa manca
- Con l'istruzione ora senza limite di conteggio, un profilo con molte
  voci di istruzione può occupare più spazio del previsto nel calcolo
  originale del budget bullet — il loop di ripiego per overflow (§6,
  già esistente) resta l'unica salvaguardia per il vincolo "1 pagina" in
  questo scenario: se un domani si osservano CV multi-pagina frequenti
  per questo motivo, va rivalutato.
