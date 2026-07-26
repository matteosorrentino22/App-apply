import json

from anthropic import Anthropic
from django.conf import settings

CONTENT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_achievements": {"type": "array", "items": {"type": "string"}},
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "role": {"type": "string"},
                    "location": {"type": "string"},
                    "dates": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["company", "role", "location", "dates", "bullets"],
                "additionalProperties": False,
            },
        },
        "skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "key_achievements", "experiences", "skills"],
    "additionalProperties": False,
}

CONTENT_SYSTEM_PROMPT = (
    "Componi i contenuti testuali di un CV su misura per un'offerta di "
    "lavoro, a partire dal profilo master reale di un candidato. Puoi "
    "riformulare, riordinare per rilevanza rispetto all'offerta, tradurre "
    "nella lingua richiesta ed enfatizzare ciò che è già nel profilo. Non "
    "devi mai inventare esperienze, competenze o risultati non presenti nel "
    "profilo fornito (grounding). Restituisci esattamente una voce in "
    "'experiences' per ogni esperienza del profilo, nello stesso numero "
    "(riordinabili ma non ne aggiungere né ometterne). Seleziona solo le "
    "competenze del profilo più pertinenti all'offerta per 'skills', senza "
    "inventarne di nuove."
)


def _format_date(value):
    return value.strftime("%Y-%m") if value else ""


def _build_experiences_input(profile):
    return [
        {
            "company": exp.company,
            "role": exp.role,
            "location": exp.location,
            "dates": f"{_format_date(exp.start_date)} - {_format_date(exp.end_date) or 'presente'}",
            "bullets": exp.bullets,
            "technologies": exp.technologies,
        }
        for exp in profile.experiences.all()
    ]


def _build_profile_context(profile):
    return {
        "summary": profile.summary,
        "key_achievements": profile.key_achievements,
        "experiences": _build_experiences_input(profile),
        "skills": [skill.name for skill in profile.skills.all()],
    }


def _resolve_language(job, cv_language_mode):
    if cv_language_mode == "english":
        return "English"
    return f"la stessa lingua della seguente job description: {job.description[:200]}"


def generate_cv_content(profile, job, cv_language_mode, enrichment=""):
    """Chiama Claude per i contenuti del CV su misura per `job`. Solleva
    l'eccezione a chi chiama in caso di errore/timeout — la gestione del
    fallimento è responsabilità del servizio di generazione (§5.2 tecniche)."""
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    profile_context = _build_profile_context(profile)
    language_instruction = _resolve_language(job, cv_language_mode)

    user_content = (
        f"PROFILO CANDIDATO (JSON):\n{json.dumps(profile_context, ensure_ascii=False)}\n\n"
        f"OFFERTA:\nTitolo: {job.title}\nAzienda: {job.company}\n"
        f"Descrizione: {job.description}\n\n"
        f"ARRICCHIMENTO FORNITO DALL'UTENTE (se presente, considera anche "
        f"questo dettaglio, senza inventare oltre): {enrichment or 'Nessuno.'}\n\n"
        f"Genera i contenuti in questa lingua: {language_instruction}."
    )

    response = client.messages.create(
        model=settings.ANTHROPIC_CV_GENERATION_MODEL,
        max_tokens=4000,
        thinking={"type": "disabled"},
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": CONTENT_JSON_SCHEMA},
        },
        system=CONTENT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text_block = next(block.text for block in response.content if block.type == "text")
    return json.loads(text_block)
