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


def build_extra_instructions(gaps, instructions):
    """Compone il testo passato come `extra_instructions` a
    `generate_cv_content`. Con gap selezionati, la lista numerata più
    l'istruzione (dell'utente o quella di default) autorizza l'eccezione al
    grounding descritta nel system prompt — senza gap, un'eventuale
    indicazione resta un'indicazione generica, senza quel permesso."""
    instructions = (instructions or "").strip()
    gaps = [gap.strip() for gap in (gaps or []) if gap and gap.strip()]

    if not gaps and not instructions:
        return ""

    if not gaps:
        return f"INDICAZIONI DEL CANDIDATO PER QUESTA GENERAZIONE: {instructions}"

    numbered = "\n".join(f"{index + 1}. {gap}" for index, gap in enumerate(gaps))
    return (
        f"GAP DA COLMARE PER QUESTA OFFERTA (indicati dal candidato):\n{numbered}\n\n"
        f"ISTRUZIONI DEL CANDIDATO SU COME COLMARLI: {instructions or DEFAULT_GAP_INSTRUCTION}"
    )
