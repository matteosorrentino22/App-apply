# Composizione del testo "indicazioni extra" per colmare i gap rilevati per
# una specifica offerta (Sprint 44 — sostituisce l'arricchimento manuale su
# esperienza esistente). Funzione pura: nessuna chiamata AI, nessun accesso
# al database — le regole su cosa il modello può fare con questo testo
# vivono nel system prompt di `ai_content.py`, non qui.

DEFAULT_GAP_INSTRUCTION = (
    "Non è stata fornita un'indicazione specifica su come colmare questi "
    "gap: individua per ciascuno l'esperienza reale del profilo più "
    "plausibile e amplificane con buon senso il contenuto per farvi "
    "emergere un riferimento credibile a quel gap, restando coerente con "
    "azienda/ruolo/periodo di quell'esperienza."
)


def _gap_label_and_reason(item):
    if isinstance(item, dict):
        return (item.get("label") or "").strip(), (item.get("reason") or "").strip()
    return str(item or "").strip(), ""


def _gap_line(number, item):
    label, reason = _gap_label_and_reason(item)
    prefix = f"{number}." if number is not None else "-"
    return f"{prefix} {label}" + (f" (motivo: {reason})" if reason else "")


def resolve_selected_gaps(score_gaps, gap_numbers=None, gaps=None):
    """Righe dei gap selezionati, con la stessa numerazione e lo stesso
    testo mostrati nel pannello "Colma i gap" (Sprint 69): numero = posizione
    1-based nell'elenco completo `Job.score_gaps`, nell'ordine dell'elenco
    (non di selezione), etichetta e motivo come in UI. `gap_numbers` è il
    formato attuale della PWA; `gaps` (testi liberi, formato precedente) è
    ancora accettato da una scheda aperta prima dell'aggiornamento: i testi
    riconosciuti prendono il loro numero, gli altri restano senza numero."""
    score_gaps = score_gaps or []
    if gap_numbers:
        numbers = sorted({n for n in gap_numbers if 1 <= n <= len(score_gaps)})
        return [_gap_line(n, score_gaps[n - 1]) for n in numbers]

    known = {}
    for index, item in enumerate(score_gaps):
        label, reason = _gap_label_and_reason(item)
        known.setdefault(f"{label} ({reason})" if reason else label, index + 1)
        known.setdefault(label, index + 1)
    numbered, unnumbered = set(), []
    for text in gaps or []:
        text = (text or "").strip()
        if not text:
            continue
        if text in known:
            numbered.add(known[text])
        else:
            unnumbered.append(f"- {text}")
    return [_gap_line(n, score_gaps[n - 1]) for n in sorted(numbered)] + unnumbered


def build_extra_instructions(gap_lines, instructions):
    """Compone il testo passato come `extra_instructions` a
    `generate_cv_content`. Con gap selezionati (`gap_lines`, già numerate da
    `resolve_selected_gaps`), l'elenco più l'istruzione (dell'utente o
    quella di default) autorizza l'eccezione al grounding descritta nel
    system prompt — senza gap, un'eventuale indicazione resta
    un'indicazione generica, senza quel permesso."""
    instructions = (instructions or "").strip()
    gap_lines = [line for line in (gap_lines or []) if line and line.strip()]

    if not gap_lines and not instructions:
        return ""

    if not gap_lines:
        return f"INDICAZIONI DEL CANDIDATO PER QUESTA GENERAZIONE: {instructions}"

    numbered = "\n".join(gap_lines)
    return (
        "GAP DA COLMARE PER QUESTA OFFERTA (indicati dal candidato; i numeri "
        "sono quelli che il candidato vede nell'elenco completo dei gap "
        f"dell'offerta e può usare nelle istruzioni):\n{numbered}\n\n"
        f"ISTRUZIONI DEL CANDIDATO SU COME COLMARLI: {instructions or DEFAULT_GAP_INSTRUCTION}"
    )
