# Sprint 54 — Spaziatura lettere uniforme e pallino bullet unificato

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `597aef7`

## Input
Il committente chiede quale spaziatura lettere abbiano le sezioni diverse
dai titoli (risposta: nessuna, `normal`) e poi: 0.2pt su tutto il resto;
elenchi puntati di "Areas of Expertise" ed esperienze non uguali e non
allineati → stesso stile di quello delle esperienze, con pallino un po'
più grande in entrambi.

## Decisioni prese
- `letter-spacing` impostato su `body`; i titoli di sezione (h2) restano a
  0.5pt perché dichiarano la proprietà esplicitamente.
- Un unico marcatore per i due elenchi: carattere "•" via `::before` (prima
  le esperienze usavano il pallino nativo del motore di rendering, le aree
  un "•" via `::before` con rientro proprio).

## Implementazione

### Backend
`cv_template.html`:

| Elemento | Prima | Dopo |
|---|---|---|
| `body` letter-spacing | non impostato (normal) | 0.2pt |
| `h2` letter-spacing | 0.5pt | 0.5pt (invariato) |
| `ul.bullets` | `margin: 2pt 0 0 0; padding-left: 12pt`, pallino nativo | `margin: 0` + `margin-top: 2pt`, `padding: 0`, `list-style: none` |
| `ul.bullets li` rientro | (da `padding-left` della lista) | `padding-left: 12pt; text-indent: -12pt` (come `.areas-list li`) |
| marcatore `::before` | solo `.areas-list li`, `content "•"`, `padding-right 5pt` | `ul.bullets li` e `.areas-list li`: `content "•"`, `font-size: base+3` (12pt), `line-height: 0`, `vertical-align: -1pt`, `padding-right: 5pt` |

## Verifica
- Rendering PDF→PNG a vista; suite `apps.cv` 49/49.

## Note / cosa manca
- Nessuna.
