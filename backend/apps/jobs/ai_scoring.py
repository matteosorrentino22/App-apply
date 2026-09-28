from django.conf import settings

from apps.common.ai import call_claude_structured
from apps.profiles.language_options import LANGUAGE_LEVEL_LABELS, LANGUAGE_NAME_LABELS

# Ogni voce di match/gap è un'etichetta cortissima più una motivazione a
# parte (prima erano un'unica stringa con la motivazione tra parentesi): la
# UI mostra solo `label` e rivela `reason` su richiesta (pulsante "espandi
# motivazioni").
_SCORE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["label", "reason"],
    "additionalProperties": False,
}

# Verifica deterministica in scoring.py (Sprint 48): il modello identifica
# la lingua richiesta, ma il confronto con le lingue reali del profilo (e il
# conseguente cap sul punteggio) è fatto in Python, non lasciato al giudizio
# del modello — osservato in produzione che il modello, pur citando
# testualmente un requisito di lingua come gap, assegnava comunque un
# punteggio alto (media/dilutione con gli altri match positivi).
_LANGUAGE_CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "required": {"type": "boolean"},
        "language": {"type": "string"},
        "international_exception": {"type": "boolean"},
    },
    "required": ["required", "language", "international_exception"],
    "additionalProperties": False,
}

SCORE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "score_match": {"type": "array", "items": _SCORE_ITEM_SCHEMA},
        "score_gaps": {"type": "array", "items": _SCORE_ITEM_SCHEMA},
        "score_reasoning": {"type": "string"},
        "language_check": _LANGUAGE_CHECK_SCHEMA,
    },
    "required": ["score", "score_match", "score_gaps", "score_reasoning", "language_check"],
    "additionalProperties": False,
}

SCORING_SYSTEM_PROMPT = (
    "Valuti l'affinità tra il profilo master di un candidato e un'offerta di "
    "lavoro. Assegni un punteggio intero da 1 a 10 (10 = massima affinità), "
    "elenchi i punti di affinità (score_match) e le lacune principali "
    "(score_gaps) rispetto ai requisiti dell'offerta, con una breve "
    "motivazione (score_reasoning).\n"
    "Come scegliere il punteggio (Sprint 46 — scala precedente 1-5, "
    "sostituita perché troppo grezza: la maggior parte dei casi convergeva "
    "sullo stesso valore intermedio). Prima di scegliere il numero, conta "
    "esplicitamente quanti requisiti \"hard\" (competenze/esperienza/"
    "seniority dichiarati come necessari nel testo dell'offerta, non "
    "preferenziali) sono soddisfatti dal profilo e quanti mancano — il "
    "punteggio deve riflettere quel conteggio, non un giudizio complessivo "
    "a sensazione:\n"
    "- 9-10: tutti i requisiti hard sono soddisfatti, seniority e ambito "
    "coerenti, nessuna lacuna rilevante.\n"
    "- 7-8: i requisiti hard principali sono soddisfatti, manca al più un "
    "elemento secondario (una competenza preferenziale, un dettaglio di "
    "seniority) — buon match, non perfetto.\n"
    "- 5-6: manca almeno un requisito hard esplicito, oppure la seniority "
    "non è ben allineata, ma il resto del profilo è pertinente.\n"
    "- 3-4: più requisiti hard mancanti o disallineamento di ruolo/settore "
    "significativo, con qualche punto di contatto residuo.\n"
    "- 1-2: il profilo non è pertinente al ruolo (settore/funzione diversi, "
    "nessun requisito hard soddisfatto).\n"
    "Usa l'intera scala in modo differenziato: due offerte con un requisito "
    "hard mancante diverso l'una dall'altra possono avere punteggi diversi "
    "(es. 5 e 6), non lo stesso valore di default.\n"
    "Attenzione particolare alla lingua (Sprint 48): se l'offerta dichiara "
    "esplicitamente una lingua necessaria (es. \"Deutschkenntnisse\", "
    "\"fluent German required\", \"maîtrise du français\"), oppure è "
    "scritta per intero in una lingua diversa dall'inglese (segnale che "
    "quella è probabilmente la lingua di lavoro, anche senza una frase "
    "esplicita), quella lingua è un vincolo a parte, più severo di un "
    "normale requisito hard: se non è presente nel profilo candidato (Lingue) "
    "a nessun livello, il candidato non può realisticamente operare nel "
    "ruolo, indipendentemente da quanto il resto del profilo sia affine — "
    "non fare come nell'errore osservato in produzione, dove il modello ha "
    "giustificato l'assenza del tedesco richiesto scrivendo che il "
    "candidato \"mostra adattabilità linguistica\" parlando altre lingue: "
    "non è un match, è un'invenzione vietata dalla regola 3, e non deve mai "
    "comparire in score_match. Eccezione: se il testo dichiara "
    "esplicitamente un ambiente di lavoro internazionale o in inglese (es. "
    "\"international team\", \"English-speaking environment\", \"no German "
    "required\"), il vincolo non si applica.\n"
    "Regole vincolanti:\n"
    "1. Ogni voce di score_match e di score_gaps deve corrispondere a un "
    "requisito o un'informazione esplicita e individuabile nel testo "
    "dell'offerta (sezione OFFERTA). Non elencare punti di forza o lacune "
    "generiche del candidato che non siano riferiti a un requisito "
    "realmente presente nel testo.\n"
    "2. Se la descrizione dell'offerta è vuota, segnaposto (es. lorem "
    "ipsum), troppo generica o comunque priva di requisiti valutabili, "
    "score_match e score_gaps devono essere entrambi array vuoti: non "
    "riversarci il profilo del candidato. In questo caso assegna un "
    "punteggio prudenziale (non superiore a 6) e spiega la non "
    "valutabilità in score_reasoning.\n"
    "3. Non inventare competenze non presenti nel profilo (score_match).\n"
    "4. Non citare in score_gaps una competenza, esperienza, certificazione "
    "o lingua che è già presente nel profilo candidato riportato sopra: "
    "verifica il profilo per intero (esperienze, competenze, "
    "certificazioni, lingue, istruzione) prima di segnalarla come lacuna.\n"
    "5. score_reasoning deve essere brevissima: massimo due frasi, circa 40 "
    "parole in totale — va letta in pochi secondi in una lista di offerte, "
    "non deve ripetere il contenuto di score_match/score_gaps.\n"
    "6. Ogni voce di score_match e score_gaps è un oggetto con due campi: "
    "`label`, cortissima (poche parole, solo il fatto, senza spiegazioni — "
    "es. \"5 anni di esperienza PM\"), e `reason`, una frase che motiva "
    "quella voce collegandola al requisito preciso dell'offerta (il "
    "dettaglio che altrimenti andrebbe tra parentesi dopo l'etichetta).\n"
    "7. Non elencare mai in score_match una lingua assente dal profilo "
    "candidato: se una lingua richiesta (secondo il criterio sopra) non è "
    "nel profilo, può comparire solo in score_gaps, mai in score_match con "
    "giustificazioni indirette (\"adattabilità linguistica\", \"lingue "
    "simili\", \"può impararla velocemente\").\n"
    "8. Compila sempre language_check: `required` (true se hai individuato "
    "una lingua necessaria secondo il criterio sopra, false altrimenti), "
    "`language` (nome della lingua individuata, stringa vuota se required è "
    "false), `international_exception` (true se hai trovato un'esplicita "
    "dichiarazione di ambiente internazionale/inglese che esclude il "
    "vincolo)."
)


def _build_profile_summary(profile):
    if profile is None:
        return "Profilo non ancora compilato."
    experiences = "\n".join(
        f"- {exp.role} presso {exp.company}: {', '.join(exp.bullets)}"
        for exp in profile.experiences.all()
    ) or "Nessuna esperienza in profilo."
    skills = ", ".join(skill.name for skill in profile.skills.all()) or "Nessuna competenza in profilo."
    educations = "\n".join(
        f"- {edu.title} presso {edu.institution}" for edu in profile.educations.all()
    ) or "Nessuna istruzione in profilo."
    certifications = ", ".join(
        cert.name for cert in profile.certifications.all()
    ) or "Nessuna certificazione in profilo."
    languages = ", ".join(
        f"{LANGUAGE_NAME_LABELS.get(lang.language, {}).get('it', lang.language)}"
        f" ({LANGUAGE_LEVEL_LABELS.get(lang.level, {}).get('it', lang.level)})"
        if lang.level
        else LANGUAGE_NAME_LABELS.get(lang.language, {}).get("it", lang.language)
        for lang in profile.languages.all()
    ) or "Nessuna lingua in profilo."
    return (
        f"Sommario: {profile.summary}\n"
        f"Esperienze:\n{experiences}\n"
        f"Competenze: {skills}\n"
        f"Istruzione:\n{educations}\n"
        f"Certificazioni: {certifications}\n"
        f"Lingue: {languages}"
    )


def score_job_with_claude(job, profile):
    """Chiama Claude per lo scoring di un singolo Job. Solleva l'eccezione a
    chi chiama in caso di errore/timeout — la gestione del fallimento (Job
    scartato per la notte, traccia in RunLog) è responsabilità di
    `apps.jobs.scoring.score_job` (02-specifiche-tecniche-v3.md §5.1)."""
    profile_summary = _build_profile_summary(profile)
    job_summary = f"Titolo: {job.title}\nAzienda: {job.company}\nDescrizione: {job.description}"

    return call_claude_structured(
        model=settings.BEDROCK_SCORING_MODEL,
        system=SCORING_SYSTEM_PROMPT,
        user_content=f"PROFILO CANDIDATO:\n{profile_summary}\n\nOFFERTA:\n{job_summary}",
        schema=SCORE_JSON_SCHEMA,
        max_tokens=2000,
    )
