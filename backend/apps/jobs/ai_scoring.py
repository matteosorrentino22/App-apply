from django.conf import settings

from apps.common.ai import call_claude_structured
from apps.profiles.language_options import LANGUAGE_LEVEL_LABELS, LANGUAGE_NAME_LABELS

SCORE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "score_match": {"type": "array", "items": {"type": "string"}},
        "score_gaps": {"type": "array", "items": {"type": "string"}},
        "score_reasoning": {"type": "string"},
    },
    "required": ["score", "score_match", "score_gaps", "score_reasoning"],
    "additionalProperties": False,
}

SCORING_SYSTEM_PROMPT = (
    "Valuti l'affinità tra il profilo master di un candidato e un'offerta di "
    "lavoro. Assegni un punteggio intero da 1 a 5 (5 = massima affinità), "
    "elenchi i punti di affinità (score_match) e le lacune principali "
    "(score_gaps) rispetto ai requisiti dell'offerta, con una breve "
    "motivazione (score_reasoning).\n"
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
    "punteggio prudenziale (non superiore a 3) e spiega la non "
    "valutabilità in score_reasoning.\n"
    "3. Non inventare competenze non presenti nel profilo (score_match).\n"
    "4. Non citare in score_gaps una competenza, esperienza, certificazione "
    "o lingua che è già presente nel profilo candidato riportato sopra: "
    "verifica il profilo per intero (esperienze, competenze, "
    "certificazioni, lingue, istruzione) prima di segnalarla come lacuna."
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
