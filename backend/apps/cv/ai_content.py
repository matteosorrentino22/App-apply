import json

from anthropic import Anthropic
from django.conf import settings

from .cv_parameters import AREAS_OF_EXPERTISE_MAX, AREAS_OF_EXPERTISE_MIN

CONTENT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "qualification": {"type": "string"},
        "areas_of_expertise": {
            # Niente minItems/maxItems: l'API Anthropic per gli output
            # strutturati non supporta valori diversi da 0/1 per un array
            # (400 "minItems values other than 0 or 1 are not supported" —
            # bug reale osservato in produzione). Il vincolo 4-6 resta solo
            # nel prompt testuale, come già per experiences/bullets.
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "grounding_reference": {"type": "string"},
                },
                "required": ["label", "grounding_reference"],
                "additionalProperties": False,
            },
        },
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "role": {"type": "string"},
                    "location": {"type": "string"},
                    "dates": {"type": "string"},
                    "highly_relevant": {"type": "boolean"},
                    "bullets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "relevance_rank": {"type": "integer"},
                            },
                            "required": ["text", "relevance_rank"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["company", "role", "location", "dates", "highly_relevant", "bullets"],
                "additionalProperties": False,
            },
        },
        "skills": {"type": "array", "items": {"type": "string"}},
        "certifications": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "qualification", "areas_of_expertise", "experiences", "skills", "certifications"],
    "additionalProperties": False,
}

CONTENT_SYSTEM_PROMPT = (
    "Componi i contenuti testuali di un CV su misura per un'offerta di "
    "lavoro, a partire dal profilo master reale di un candidato. Puoi "
    "riformulare, riordinare per rilevanza rispetto all'offerta, tradurre "
    "nella lingua richiesta ed enfatizzare ciò che è già nel profilo. Non "
    "devi mai inventare esperienze, competenze o risultati non presenti nel "
    "profilo fornito (grounding), con un'unica eccezione controllata per "
    "'areas_of_expertise' (vedi sotto).\n\n"
    "QUALIFICA PROFESSIONALE ('qualification'): estrai dal titolo del job il "
    "nome del ruolo, spogliato di tecnologie/progetto/contesto (es. "
    "'Software Engineer for SSH/AWS and ERP systems' → 'Software Engineer'). "
    "Mantieni la seniority se presente nel titolo (Senior, Junior, Lead...). "
    "Se il titolo è già un nome di ruolo pulito, usalo così com'è. Se il "
    "titolo è ambiguo o multi-ruolo e non ne ricavi un ruolo univoco, usa il "
    "ruolo dell'esperienza professionale più recente del profilo; se il "
    "profilo non ha esperienze, usa comunque il titolo del job ripulito.\n\n"
    "AREAS OF EXPERTISE ('areas_of_expertise'): da 4 a 6 voci di soft skill / "
    "aree funzionali-trasversali (leadership, stakeholder management, "
    "problem solving...), distinte dalle hard skill di 'skills'. Puoi "
    "sintetizzare e coniare il nome di un'area raggruppando competenze ed "
    "esperienze REALMENTE presenti nel profilo (es. bullet su coordinamento "
    "di team cross-funzionali → 'Cross-functional Team Leadership'), ma è "
    "vietato dedurre competenze dalla sola job description: ogni area deve "
    "restare riconducibile a contenuto reale del profilo. Se il profilo è "
    "scarno, riformula gli stessi bullet/esperienze da angolazioni diverse "
    "per raggiungere comunque almeno 4 voci. Per ogni area, "
    "'grounding_reference' è un riferimento interno (mai mostrato "
    "nell'utente finale) al bullet o esperienza del profilo da cui deriva.\n\n"
    "ESPERIENZE: restituisci esattamente una voce in 'experiences' per ogni "
    "esperienza del profilo (fornite in ordine cronologico inverso, dalla "
    "più recente), nello stesso ordine e nello stesso numero — non "
    "aggiungerne né ometterne — la selezione di quali mostrare è fatta da "
    "un sistema a valle. Per ciascuna, riformula i bullet reali (mai più di "
    "quanti forniti per quella esperienza) e assegna a ciascun bullet un "
    "'relevance_rank' intero: 0 = il più rilevante per l'offerta, valori "
    "crescenti per rilevanza decrescente, univoci solo all'interno della "
    "stessa esperienza. Marca 'highly_relevant'=true solo per esperienze "
    "che, pur non recentissime, sono particolarmente pertinenti a questa "
    "offerta specifica.\n\n"
    "SKILLS e CERTIFICATIONS: seleziona solo voci letteralmente presenti nel "
    "profilo, per rilevanza rispetto all'offerta, senza inventarne di nuove."
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
        for exp in profile.experiences.all().order_by("-end_date", "-start_date")
    ]


def _build_profile_context(profile):
    return {
        "summary": profile.summary,
        "experiences": _build_experiences_input(profile),
        "skills": [skill.name for skill in profile.skills.all()],
        "certifications": [cert.name for cert in profile.certifications.all()],
    }


def _resolve_language(job, cv_language_mode):
    if cv_language_mode == "english":
        return "English"
    return f"la stessa lingua della seguente job description: {job.description[:200]}"


def generate_cv_content(profile, job, cv_language_mode, enrichment=""):
    """Chiama Claude per i contenuti del CV su misura per `job` (Docs/03
    §11 punto 3): sommario, qualifica professionale, Areas of Expertise,
    bullet con ordinamento di rilevanza per ogni esperienza del profilo,
    skills/certifications selezionate. Solleva l'eccezione a chi chiama in
    caso di errore/timeout — la gestione del fallimento è responsabilità del
    servizio di generazione (§5.2 tecniche madre)."""
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    profile_context = _build_profile_context(profile)
    language_instruction = _resolve_language(job, cv_language_mode)

    user_content = (
        f"PROFILO CANDIDATO (JSON):\n{json.dumps(profile_context, ensure_ascii=False)}\n\n"
        f"OFFERTA:\nTitolo: {job.title}\nAzienda: {job.company}\n"
        f"Descrizione: {job.description}\n\n"
        f"ARRICCHIMENTO FORNITO DALL'UTENTE (se presente, considera anche "
        f"questo dettaglio, senza inventare oltre): {enrichment or 'Nessuno.'}\n\n"
        f"Genera i contenuti in questa lingua: {language_instruction}. "
        f"Le Areas of Expertise devono essere tra {AREAS_OF_EXPERTISE_MIN} e "
        f"{AREAS_OF_EXPERTISE_MAX}."
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
