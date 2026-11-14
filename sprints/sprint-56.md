# Sprint 56 — Nero classico, ruolo in corsivo, grassetto solo sul titolo dell'istruzione

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-17 · **Commit:** `efb1d90`

## Input
Il committente chiede l'elenco di colori, grassetti, maiuscolo, corsivo e
sottolineato del template, e lo restituisce con le modifiche: nero classico
ovunque tranne titoli di sezione e filetti (blu); ruolo non più in
maiuscolo ma come scritto nel profilo, in corsivo; nell'istruzione
grassetto solo sul titolo, non sull'istituto dopo il trattino.

## Decisioni prese
- Qualifica, contatti e riga "Tecnologie" perdono il colore proprio ed
  ereditano il nero del `body`.
- Unico colore non nero rimasto: `#2f4a63` su titoli di sezione (h2) e
  filetti separatori.
- Per il grassetto parziale dell'istruzione serve un `<strong>` solo sul
  titolo invece del `font-weight` sull'intero span.

## Implementazione

### Backend
`cv_template.html`:

| Elemento | Prima | Dopo |
|---|---|---|
| `body` color | #1a1a1a | #000 |
| `.qualification` color | #333 | (ereditato, #000) |
| `.contact` color | #444 | (ereditato, #000) |
| `.experience-technologies` color | #555 | (ereditato, #000) |
| `.experience-role` | `text-transform: uppercase` | nessun maiuscolo |
| ruolo (`span.experience-role-title`, nuova classe) | normale | `font-style: italic` |
| `.experience-role-meta` | `text-transform: none` | rimosso (non più necessario) |
| titolo istruzione | `.education-title-main { font-weight: bold }` su "titolo — istituto" | `<strong>` solo su `{{ edu.title }}`, classe rimossa |

Invariati: h2 e filetti `#2f4a63`, nome azienda in grassetto e maiuscolo,
date in `<strong>`, etichette "Certified in:/Skilled in:" in grassetto,
link LinkedIn sottolineato, riga "Tecnologie" in corsivo.

## Verifica
- Rendering PDF→PNG a vista; suite `apps.cv` 49/49.

## Note / cosa manca
- Nessuna.
