# Sprint 52 — Font Cambria (via Caladea) e dimensione fissa nel template CV

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `e2fdb30`

## Input
Dopo il test positivo della Fase 1 dell'editor (Sprint 51), il committente
avvia una serie di ritocchi grafici del template PDF "step by step" (un
rilascio per ogni modifica, da verificare a vista). Primo passo: usare
Cambria al posto dell'attuale "Calibri", e dimensione del testo **fissa**,
che non deve più diminuire se il CV supera una pagina.

## Decisioni prese
- Verificato nel container che non era installato né Calibri né Cambria
  (solo DejaVu): il CSS chiedeva `Helvetica/Arial` e WeasyPrint/Pango
  ricadeva su DejaVu Sans. Il "Calibri" percepito non lo era mai stato.
- Cambria non è redistribuibile: si installa **Caladea**, font open source
  metricamente compatibile con Cambria.
- Rimosso il restringimento progressivo: un solo livello a dimensione
  fissa. Se il contenuto non entra in 1 pagina resta solo il ripiego già
  esistente (rimozione del bullet meno rilevante, fino a
  `MAX_OVERFLOW_ITERATIONS`); oltre, si accetta un PDF multi-pagina a
  dimensione piena.
- Cover letter esplicitamente non toccata (fuori dalla richiesta).

## Implementazione

### Backend
- `backend/Dockerfile`: aggiunto il pacchetto `fonts-crosextra-caladea`.
- `cv_template.html`, `body`: `font-family: "Helvetica", "Arial",
  sans-serif` → `"Cambria", "Caladea", "DejaVu Serif", serif`.
- `rendering.py`, `COMPACT_LEVELS`: da 3 livelli a 1. Rimossi:
  - livello 2: `base_font_size 8`, `line_height 1.15`, `section_gap 6pt`,
    `heading_gap 3pt`, `item_gap 5pt`, `page_margin 1.1cm`,
    `photo_size 55pt`;
  - livello 3: `base_font_size 7`, `line_height 1.1`, `section_gap 4pt`,
    `heading_gap 2pt`, `item_gap 3pt`, `page_margin 0.9cm`,
    `photo_size 45pt`.
  Resta il solo livello `base_font_size 9`, `line_height 1.25`,
  `section_gap 9pt`, `heading_gap 4pt`, `item_gap 7pt`,
  `page_margin 1.4cm`, `photo_size 65pt` (ritoccato nello Sprint 53).
  `COVER_LETTER_COMPACT_LEVELS` invariato (3 livelli).

## Verifica
- Rendering PDF→PNG ispezionato a vista; suite `apps.cv` 49/49.
- Ricostruiti anche worker/beat (stessa immagine).

## Note / cosa manca
- Restano commenti non aggiornati che parlano ancora di "3 livelli di
  compattamento" (`generation.py`, docstring di
  `_render_with_overflow_retry`; `draft.py`, docstring di
  `render_draft_preview`).
- Il "1 pagina" non è più un vincolo garantito: il multi-pagina è il caso
  residuale accettato (tracciato in `RunLog`).
