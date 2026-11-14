# Sprint 57 — Testo giustificato (sommario, Certified/Skilled in, bullet, lingue)

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `7bdd330`

## Input
Il committente chiede allineamento giustificato per sommario, righe
"Certified in"/"Skilled in" e tutti i bullet delle esperienze; se possibile
anche la riga delle lingue, mantenendo la stessa distanza tra le lingue.

## Decisioni prese
- Un solo selettore `section > p` copre sia il sommario sia le righe
  Certified/Skilled in (sono gli unici `<p>` figli diretti di una
  `<section>`).
- La riga lingue è un flex, non un paragrafo: "giustificata" con
  `justify-content: space-between` (da margine a margine, spazi uguali tra
  le lingue; `gap` resta il minimo).
- Aree di competenza non toccate (non richieste).

## Implementazione

### Backend
`cv_template.html`:

| Selettore | Prima | Dopo |
|---|---|---|
| `section > p` | `margin: 0` | `margin: 0; text-align: justify` |
| `ul.bullets li` | `margin-bottom: 1pt` | + `text-align: justify` |
| `.languages-row` justify-content | flex-start | space-between (`gap: 18pt` invariato) |

## Verifica
- Rendering PDF→PNG a vista; suite `apps.cv` 49/49.

## Note / cosa manca
- Con poche lingue (es. 2) `space-between` le porta ai due estremi della
  riga: comportamento atteso della scelta, non verificato con il
  committente su quel caso.
