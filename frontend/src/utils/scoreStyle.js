// Colore a fasce (non un colore per valore esatto): con lo score 1-10
// (Sprint 46, prima 1-5) 10 colori distinti sarebbero poco distinguibili a
// colpo d'occhio. Ogni fascia raggruppa 2 valori consecutivi sugli stessi 5
// colori (--color-score-1..5 in index.css; valori ridefiniti nello Sprint 72
// per il contrasto, DESIGN.md §3.1: 9–10 verde, 7–8 oliva, 5–6 ocra, 3–4
// arancio, 1–2 rosso). Il componente è ui/score-chip.jsx.
const BAND_STYLE = {
  1: 'bg-score-1-soft text-score-1',
  2: 'bg-score-2-soft text-score-2',
  3: 'bg-score-3-soft text-score-3',
  4: 'bg-score-4-soft text-score-4',
  5: 'bg-score-5-soft text-score-5',
}

export function scoreStyle(score) {
  const band = Math.min(5, Math.max(1, Math.ceil(score / 2)))
  return BAND_STYLE[band]
}
