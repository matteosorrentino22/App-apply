# Sprint 35 — Fix spaziature intestazione/istruzione e date solo anno nel CV

## Input
3 difetti segnalati dal committente dopo aver ispezionato un CV
generato:
1. la linea che separa i contatti dalla descrizione del profilo è più
   spessa delle altre linee del CV, e l'interlinea fra quella linea e la
   descrizione non è uguale a quella usata altrove (es. sotto "WORK
   EXPERIENCE" prima della prima azienda);
2. interlinea fra la riga principale di un'istruzione e la nota sotto da
   ridurre, uguale a quella fra azienda e ruolo nelle esperienze;
3. tutte le date mostrate sul CV devono avere solo l'anno (es. "Rome, IT |
   2022 - 2023"), senza il mese — la data precisa resta comunque salvata
   nel profilo per usi futuri, nessuna modifica lì.

## Esito (2026-08-09)

### 1 — Linea contatti e interlinea sotto
`cv_template.html`: `.header` portato da `border-bottom: 1.5pt` a `1pt`
(stesso spessore di `h2`/`.contact-line`, entrambi già a 1pt);
`margin-bottom` della `.header` passato da `{{ section_gap }}` a
`{{ heading_gap }}` — stesso gap usato sotto ogni `h2` (es. fra la linea
sotto "WORK EXPERIENCE" e la prima azienda), invece del gap più ampio fra
sezioni.

### 2 — Interlinea nota istruzione
Il paragrafo delle note (`<p>{{ edu.notes }}</p>`) aveva margine di
default del browser (~1em), mentre `.experience-role` è a contatto
diretto col company block sopra (nessun margine). Aggiunta regola
`.education-item p { margin: 0; }` (e, per lo stesso motivo, `section > p
{ margin: 0; }` per il sommario subito sotto ai contatti, coerente col
punto 1) — il gap ora è zero come fra azienda e ruolo nelle esperienze.

### 3 — Solo anno nelle date del CV
`_format_date` in `generation.py`: `strftime("%Y-%m")` → `strftime("%Y")`.
Unico punto di formattazione condiviso da `_format_date_range` (già usato
sia per esperienze sia per istruzione), quindi la modifica si applica
automaticamente a entrambe le sezioni senza toccare altro codice. Il
modello/profilo continua a salvare la data completa (`start_date`/
`end_date` come `DateField`): la modifica è solo nella resa a video del
CV.

### Verifica eseguita
- `python manage.py test`: 169/169 passati (nessuna assert esistente
  dipendeva dal formato `%Y-%m`, nessun test da aggiornare).
- `makemigrations --check --dry-run`: pulito (nessuna modifica ai
  modelli in questo sprint).
- Verifica visiva: generato un CV reale con la pipeline completa (solo
  `generate_cv_content` mockato) — confermati tutti e 3 i punti sul PDF
  prodotto: linea contatti a 1pt con lo stesso gap delle altre sezioni,
  nota istruzione a contatto con la riga sopra, date "2022 - 2023" e
  "2010 - 2013" (solo anno).

### Cosa manca
- Nessun nuovo punto aperto sui 3 difetti segnalati.
- Resta valido quanto già segnalato negli sprint precedenti (calibrazione
  parametri, qualità reale dei contenuti con una vera `ANTHROPIC_API_KEY`,
  suite e2e da ambiente dedicato).
