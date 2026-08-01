"""Selezione e taglio del contenuto del CV, lato server, dopo la chiamata AI
(Docs/03-specifiche-funzionali-contenuto-cv-v4.md §11, punto 4). Funzioni
pure: nessuna chiamata AI, nessun accesso al database — usano solo
l'ordinamento di rilevanza già restituito dal modello."""

import random

from .cv_parameters import (
    BULLET_BUDGET_BY_EDU_COUNT,
    EDU_MAX_SHOWN,
    MAX_EXPERIENCES_SHOWN,
    MIN_GUARANTEED_BULLETS_FOR_RELEVANT_EXPERIENCE,
)


def _education_duration_days(education):
    """Durata in giorni per il tie-break (§3.2): una voce senza data di
    inizio è trattata come "durata sconosciuta", meno preferibile di una
    voce esplicitamente breve (non è una "durata minore" verificabile)."""
    if education.start_date is None:
        return float("inf")
    return (education.end_date - education.start_date).days


def select_educations_to_show(educations):
    """Le `EDU_MAX_SHOWN` voci più recenti (data di fine decrescente); a
    parità di data di fine vince la durata minore; a parità anche di
    durata, la scelta è casuale (§3.2)."""
    shuffled = list(educations)
    random.shuffle(shuffled)
    ordered = sorted(
        shuffled,
        key=lambda edu: (-edu.end_date.toordinal(), _education_duration_days(edu)),
    )
    return ordered[:EDU_MAX_SHOWN]


def compute_bullet_budget(shown_education_count):
    """Budget bullet totale (B), tabella §5.4/§12: più voci di istruzione
    mostrate, meno bullet disponibili per le esperienze."""
    count = max(1, min(shown_education_count, EDU_MAX_SHOWN))
    return BULLET_BUDGET_BY_EDU_COUNT[count]


def _select_shown_experiences(experiences):
    """Cap a `MAX_EXPERIENCES_SHOWN`, con eventuale swap singolo per
    rilevanza (§5.4): se il profilo ha più esperienze del cap, si tengono le
    più recenti; al massimo una esclusa "altamente rilevante" (la più
    rilevante tra le escluse, tie-break sulla più recente) sostituisce la
    meno recente tra le selezionate. Ogni experience ha già `_order` (indice
    di input, 0 = più recente: le esperienze arrivano già ordinate
    cronologicamente inverso da chi chiama)."""
    if len(experiences) <= MAX_EXPERIENCES_SHOWN:
        return list(experiences)

    shown = experiences[:MAX_EXPERIENCES_SHOWN]
    excluded = experiences[MAX_EXPERIENCES_SHOWN:]

    highly_relevant_excluded = [exp for exp in excluded if exp.get("highly_relevant")]
    if not highly_relevant_excluded:
        return shown

    # Nessun punteggio numerico distingue le esperienze marcate "altamente
    # rilevanti" (è un booleano, §11 punto 3): a pari marcatura, vince
    # sempre la più recente tra loro (§5.4 tie-break) — `_order` più basso.
    best_excluded = min(highly_relevant_excluded, key=lambda exp: exp["_order"])
    return shown[:-1] + [best_excluded]


def _cut_bullets_to_budget(shown_experiences, budget):
    """Tiene, tra i bullet delle sole esperienze mostrate, i `budget`
    globalmente più rilevanti secondo `relevance_rank` (rank più basso =
    più rilevante). Un'esperienza altamente rilevante che finirebbe senza
    bullet riceve un minimo garantito, sottratto al taglio globale."""
    all_bullets = [
        {"experience_index": index, "bullet": bullet}
        for index, exp in enumerate(shown_experiences)
        for bullet in exp["bullets"]
    ]
    all_bullets.sort(key=lambda item: item["bullet"].get("relevance_rank", 0))

    kept_indices_by_experience = {index: [] for index in range(len(shown_experiences))}
    for item in all_bullets[:budget]:
        kept_indices_by_experience[item["experience_index"]].append(item["bullet"])

    remaining_budget = budget - sum(len(v) for v in kept_indices_by_experience.values())
    for index, exp in enumerate(shown_experiences):
        if kept_indices_by_experience[index] or not exp.get("highly_relevant"):
            continue
        if not exp["bullets"]:
            continue
        guaranteed = sorted(exp["bullets"], key=lambda b: b.get("relevance_rank", 0))
        guaranteed = guaranteed[:MIN_GUARANTEED_BULLETS_FOR_RELEVANT_EXPERIENCE]
        kept_indices_by_experience[index] = guaranteed
        remaining_budget -= len(guaranteed)

    result = []
    for index, exp in enumerate(shown_experiences):
        kept_bullets = kept_indices_by_experience[index]
        kept_texts = [b["text"] for b in sorted(kept_bullets, key=lambda b: b.get("relevance_rank", 0))]
        result.append({**exp, "bullets": kept_texts})
    return result


def select_and_cut_experiences(experiences, budget):
    """Punto 4 della pipeline (§11): cap esperienze con swap singolo, poi
    taglio bullet al budget globale. `experiences` è la lista completa
    prodotta dal modello per punto 3, in ordine cronologico inverso
    (dall'esperienza più recente)."""
    for index, exp in enumerate(experiences):
        exp["_order"] = index

    shown = _select_shown_experiences(experiences)
    return _cut_bullets_to_budget(shown, budget)
