"""Selezione e taglio del contenuto del CV, lato server, dopo la chiamata AI
(Docs/03-specifiche-funzionali-contenuto-cv-v4.md §11, punto 4). Funzioni
pure: nessuna chiamata AI, nessun accesso al database — usano solo
l'ordinamento di rilevanza già restituito dal modello."""

import random

from django.utils import timezone

from .cv_parameters import (
    BULLET_BUDGET_BY_EDU_COUNT,
    EDU_MAX_SHOWN,
    MAX_EXPERIENCES_SHOWN,
    MIN_GUARANTEED_BULLETS_FOR_RELEVANT_EXPERIENCE,
)


def _education_end_ordinal(education):
    """Data di fine come intero ordinabile: un'istruzione ancora in corso
    (`end_date=None`, "Present" sul CV — Sprint 34) è per definizione la più
    recente possibile, quindi vince il confronto con qualunque data di fine
    passata (valore massimo, non un caso da escludere)."""
    if education.end_date is None:
        return float("inf")
    return education.end_date.toordinal()


def _education_duration_days(education):
    """Durata in giorni per il tie-break (§3.2): una voce senza data di
    inizio è trattata come "durata sconosciuta", meno preferibile di una
    voce esplicitamente breve (non è una "durata minore" verificabile). Una
    voce ancora in corso usa la data odierna come fine provvisoria."""
    if education.start_date is None:
        return float("inf")
    end = education.end_date or timezone.localdate()
    return (end - education.start_date).days


def select_educations_to_show(educations):
    """Tutte le voci di istruzione, ordinate per data di fine decrescente
    (a parità vince la durata minore, poi la scelta è casuale) — nessuna
    esclusa per limite di conteggio: a differenza delle esperienze, che
    vengono tagliate per rilevanza/spazio, l'istruzione riflette
    interamente quanto scritto dall'utente."""
    shuffled = list(educations)
    random.shuffle(shuffled)
    return sorted(
        shuffled,
        key=lambda edu: (-_education_end_ordinal(edu), _education_duration_days(edu)),
    )


def compute_bullet_budget(shown_education_count):
    """Budget bullet totale (B), tabella §5.4/§12: più voci di istruzione
    mostrate, meno bullet disponibili per le esperienze. La tabella ha solo
    le chiavi 1-3: con più istruzione mostrata (nessun limite di conteggio,
    tutte le voci del profilo compaiono) si applica comunque il budget più
    stretto previsto per 3+ voci, invece di un `KeyError`."""
    count = max(1, min(shown_education_count, EDU_MAX_SHOWN))
    return BULLET_BUDGET_BY_EDU_COUNT[count]


def _has_protected_bullet(experience):
    return any(b.get("protected") for b in experience["bullets"])


def _select_shown_experiences(experiences):
    """Cap a `MAX_EXPERIENCES_SHOWN`, con eventuale swap singolo per
    rilevanza (§5.4): se il profilo ha più esperienze del cap, si tengono le
    più recenti; al massimo una esclusa "altamente rilevante" (la più
    rilevante tra le escluse, tie-break sulla più recente) sostituisce la
    meno recente tra le selezionate. Ogni experience ha già `_order` (indice
    di input, 0 = più recente: le esperienze arrivano già ordinate
    cronologicamente inverso da chi chiama).

    Priorità assoluta (Docs/03 §5.6): un'esperienza con almeno un bullet di
    arricchimento `protected` per il CV corrente non può mai finire esclusa
    — se il cap la escluderebbe, la si include comunque (sostituendo la
    meno recente tra le altre selezionate), a prescindere da rilevanza o
    marcatura del modello."""
    if len(experiences) <= MAX_EXPERIENCES_SHOWN:
        return list(experiences)

    shown = experiences[:MAX_EXPERIENCES_SHOWN]
    excluded = experiences[MAX_EXPERIENCES_SHOWN:]

    protected_excluded = [exp for exp in excluded if _has_protected_bullet(exp)]
    protected_orders = {exp["_order"] for exp in protected_excluded}
    for protected_exp in protected_excluded:
        non_protected_in_shown = [exp for exp in shown if not _has_protected_bullet(exp)]
        if not non_protected_in_shown:
            break
        least_recent = max(non_protected_in_shown, key=lambda exp: exp["_order"])
        shown[[exp["_order"] for exp in shown].index(least_recent["_order"])] = protected_exp

    excluded = [exp for exp in excluded if exp["_order"] not in protected_orders]

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
    bullet riceve un minimo garantito, sottratto al taglio globale.

    I bullet marcati `protected` (arricchimento per il CV corrente, Docs/03
    §5.6) sono sempre tenuti, a prescindere dal rank: contano nel budget
    consumato ma non sono mai tra gli eleggibili all'esclusione.

    I bullet superstiti restano dict `{text, relevance_rank, protected}`
    (non ancora appiattiti a stringa): il loop di ripiego per overflow (§6,
    in `remove_least_relevant_bullet`) deve poter continuare a rimuovere
    per rilevanza dopo questo taglio, quindi il rank va preservato oltre
    questa funzione — l'appiattimento a stringa avviene solo appena prima
    del rendering finale (`generation.py`)."""
    kept_by_experience = {index: [] for index in range(len(shown_experiences))}
    remaining_budget = budget

    for index, exp in enumerate(shown_experiences):
        protected = [b for b in exp["bullets"] if b.get("protected")]
        kept_by_experience[index].extend(protected)
        remaining_budget -= len(protected)

    all_other_bullets = [
        {"experience_index": index, "bullet": bullet}
        for index, exp in enumerate(shown_experiences)
        for bullet in exp["bullets"]
        if not bullet.get("protected")
    ]
    all_other_bullets.sort(key=lambda item: item["bullet"].get("relevance_rank", 0))

    for item in all_other_bullets[: max(0, remaining_budget)]:
        kept_by_experience[item["experience_index"]].append(item["bullet"])

    for index, exp in enumerate(shown_experiences):
        if kept_by_experience[index] or not exp.get("highly_relevant"):
            continue
        if not exp["bullets"]:
            continue
        guaranteed = sorted(exp["bullets"], key=lambda b: b.get("relevance_rank", 0))
        kept_by_experience[index] = guaranteed[:MIN_GUARANTEED_BULLETS_FOR_RELEVANT_EXPERIENCE]

    result = []
    for index, exp in enumerate(shown_experiences):
        kept_bullets = sorted(kept_by_experience[index], key=lambda b: b.get("relevance_rank", 0))
        result.append({**exp, "bullets": kept_bullets})
    return result


def select_and_cut_experiences(experiences, budget):
    """Punto 4 della pipeline (§11): cap esperienze con swap singolo, poi
    taglio bullet al budget globale. `experiences` è la lista completa
    prodotta dal modello per punto 3, in ordine cronologico inverso
    (dall'esperienza più recente). I bullet nel risultato restano dict
    `{text, relevance_rank}` — vedi nota in `_cut_bullets_to_budget`."""
    for index, exp in enumerate(experiences):
        exp["_order"] = index

    shown = _select_shown_experiences(experiences)
    return _cut_bullets_to_budget(shown, budget)


def remove_least_relevant_bullet(experiences):
    """Loop di ripiego per overflow (§6, §11 punto 6): rimuove, tra tutti i
    bullet sopravvissuti al taglio del punto 4, quello globalmente meno
    rilevante (rank più alto) — un'unica rimozione per chiamata, così chi
    orchestra può rirenderizzare tra un tentativo e l'altro. I bullet
    `protected` (arricchimento per il CV corrente, §5.6) sono esclusi dai
    candidati e non vengono mai rimossi da questa funzione: se sono l'unico
    contenuto rimasto e il CV eccede ancora la pagina, si ricade nel caso
    residuale già previsto (multi-pagina salvato senza errore — §6). Muta
    `experiences` in place. Ritorna `True` se ha rimosso qualcosa, `False`
    se non restano bullet non protetti da rimuovere."""
    candidates = [
        (exp_index, bullet_index, bullet.get("relevance_rank", 0))
        for exp_index, exp in enumerate(experiences)
        for bullet_index, bullet in enumerate(exp["bullets"])
        if not bullet.get("protected")
    ]
    if not candidates:
        return False

    exp_index, bullet_index, _rank = max(candidates, key=lambda item: item[2])
    del experiences[exp_index]["bullets"][bullet_index]
    return True


def flatten_bullets_to_text(experiences):
    """Appiattisce i bullet da dict `{text, relevance_rank}` a semplice
    stringa, per il rendering finale nel template (nessun uso del rank oltre
    questo punto della pipeline)."""
    return [{**exp, "bullets": [b["text"] for b in exp["bullets"]]} for exp in experiences]
