# Sprint 55 — Bullet più grandi e indentati di 4pt

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `779bb79`

## Input
Dopo lo Sprint 54: "ingrandisci ancora di più i bullet e indentali di 4pt".

## Decisioni prese
- Si alza solo `padding-left`, lasciando `text-indent` a −12pt: marcatore e
  testo si spostano insieme di 4pt a destra, stessa distanza tra i due.

## Implementazione

### Backend
`cv_template.html` (valgono sia per `ul.bullets li` sia per `.areas-list li`):

| Proprietà | Prima | Dopo |
|---|---|---|
| `li` padding-left | 12pt | 16pt |
| `li` text-indent | −12pt | −12pt (invariato) |
| `li::before` font-size | base+3 (12pt) | base+5 (14pt) |

## Verifica
- Rendering PDF→PNG a vista; suite `apps.cv` 49/49.

## Note / cosa manca
- Nessuna. Il committente ha confermato ("ok ci siamo") prima di passare a
  colori e formati (Sprint 56).
