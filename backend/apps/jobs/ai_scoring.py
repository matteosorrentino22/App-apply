import json

from anthropic import Anthropic
from django.conf import settings

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
    "motivazione (score_reasoning). Non inventare competenze non presenti "
    "nel profilo."
)


def _build_profile_summary(profile):
    if profile is None:
        return "Profilo non ancora compilato."
    experiences = "\n".join(
        f"- {exp.role} presso {exp.company}: {', '.join(exp.bullets)}"
        for exp in profile.experiences.all()
    ) or "Nessuna esperienza in profilo."
    skills = ", ".join(skill.name for skill in profile.skills.all()) or "Nessuna competenza in profilo."
    return f"Sommario: {profile.summary}\nEsperienze:\n{experiences}\nCompetenze: {skills}"


def score_job_with_claude(job, profile):
    """Chiama Claude per lo scoring di un singolo Job. Solleva l'eccezione a
    chi chiama in caso di errore/timeout — la gestione del fallimento (Job
    scartato per la notte, traccia in RunLog) è responsabilità di
    `apps.jobs.scoring.score_job` (02-specifiche-tecniche-v3.md §5.1)."""
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    profile_summary = _build_profile_summary(profile)
    job_summary = f"Titolo: {job.title}\nAzienda: {job.company}\nDescrizione: {job.description}"

    response = client.messages.create(
        model=settings.ANTHROPIC_SCORING_MODEL,
        max_tokens=2000,
        output_config={
            "format": {"type": "json_schema", "schema": SCORE_JSON_SCHEMA},
        },
        system=SCORING_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"PROFILO CANDIDATO:\n{profile_summary}\n\nOFFERTA:\n{job_summary}",
            }
        ],
    )
    text_block = next(block.text for block in response.content if block.type == "text")
    return json.loads(text_block)
