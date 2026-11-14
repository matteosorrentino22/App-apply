# Sprint 53 — Ritocco dimensioni di paragrafi e sezioni nel template CV

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `d3d815c`

## Input
Il committente approva font e dimensione fissa (Sprint 52) e chiede
l'elenco completo delle dimensioni usate nel template, sezione per sezione,
per restituirlo con i valori modificati.

## Decisioni prese
- Elenco fornito distinguendo valori **parametrici** (`COMPACT_LEVELS` in
  `rendering.py`) e valori **fissi** nel template.
- Il committente ha rimandato la lista con alcuni valori cambiati.
- Riga contatti: la lista indicava "9pt (= base−1)", incoerente con
  base = 9pt; applicato il numero esplicito (9pt = base), segnalandolo al
  committente per conferma.

## Implementazione

### Backend
`rendering.py` (`COMPACT_LEVELS`, unico livello):

| Parametro | Prima | Dopo |
|---|---|---|
| `page_margin` | 1.4cm | 1cm |
| `section_gap` | 9pt | 8pt |
| `item_gap` | 7pt | 6pt |

`cv_template.html`:

| Elemento | Prima | Dopo |
|---|---|---|
| `.qualification` font-size | base+2 (11pt) | base+5 (14pt) |
| `.contact` font-size | base−1 (8pt) | base (9pt) |
| `.areas-list li` padding-left / text-indent | 10pt / −10pt | 12pt / −12pt |

Invariati: `base_font_size` 9, `line_height` 1.25, `heading_gap` 4pt,
`photo_size` 65pt, nome (h1) base+9, titoli di sezione 11pt.

## Verifica
- Rendering PDF→PNG a vista (1 pagina confermata); suite `apps.cv` 49/49.

## Note / cosa manca
- Nessun riscontro esplicito nello storico sulla scelta 9pt vs 8pt della
  riga contatti dopo la segnalazione: il valore è rimasto 9pt.
