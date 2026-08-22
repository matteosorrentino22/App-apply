import json

from apps.common.ai import call_claude_structured
from django.conf import settings

from .ai_content import _build_profile_context, _resolve_language
from .cv_parameters import FALLBACK_CV_LANGUAGE, SUPPORTED_CV_LANGUAGES

# Righe fisse per lingua (mai generate dall'AI, stesso principio di
# SECTION_LABELS in generation.py): oggetto della lettera, saluto e
# chiusura sono formule standard, più affidabili come traduzione
# deterministica che come output del modello ad ogni chiamata.
COVER_LETTER_LABELS = {
    "it": {
        "subject_template": "Candidatura per la posizione di {title} — {company}",
        "salutation": "Gentile Responsabile delle Risorse Umane,",
        "closing": "Cordiali saluti,",
    },
    "en": {
        "subject_template": "Application for {title} – {company}",
        "salutation": "Dear Hiring Manager,",
        "closing": "Sincerely,",
    },
    "fr": {
        "subject_template": "Candidature au poste de {title} — {company}",
        "salutation": "Madame, Monsieur,",
        "closing": "Cordialement,",
    },
    "de": {
        "subject_template": "Bewerbung als {title} — {company}",
        "salutation": "Sehr geehrte Damen und Herren,",
        "closing": "Mit freundlichen Grüßen,",
    },
    "es": {
        "subject_template": "Candidatura para el puesto de {title} — {company}",
        "salutation": "Estimado/a responsable de contratación,",
        "closing": "Atentamente,",
    },
}

COVER_LETTER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "content_language": {"type": "string", "enum": SUPPORTED_CV_LANGUAGES},
        "translated_city": {"type": "string"},
        "paragraphs": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["content_language", "translated_city", "paragraphs"],
    "additionalProperties": False,
}

COVER_LETTER_SYSTEM_PROMPT = (
    "Scrivi solo i paragrafi del corpo di una cover letter professionale su "
    "misura per un'offerta di lavoro, a partire dal profilo master reale di "
    "un candidato. Non scrivere intestazione, riga oggetto, saluto iniziale "
    "né formula di chiusura: sono già gestiti fuori da questa generazione, "
    "restituisci solo l'elenco dei paragrafi del corpo.\n\n"
    "GROUNDING: per ogni affermazione professionale (esperienze, ruoli, "
    "risultati, competenze) resta ancorato solo a ciò che è realmente nel "
    "profilo fornito — non inventare mai un'azienda, un ruolo o un "
    "risultato che il candidato non ha avuto.\n\n"
    "INDICAZIONI DELL'UTENTE: se fornite, usale pienamente per orientare "
    "questa generazione — possono essere indicazioni di tono/enfasi (es. "
    "'più diretta', 'enfatizza il lato commerciale') oppure dettagli reali "
    "non ancora presenti nel profilo (es. una motivazione personale per "
    "la posizione, un trasferimento, un progetto specifico da menzionare): "
    "in quest'ultimo caso includili come fatti dati per veri, la "
    "responsabilità di veridicità resta dell'utente — stesso principio "
    "dell'arricchimento mirato del CV. Se non sono fornite indicazioni, "
    "scrivi comunque una lettera efficace basandoti solo su profilo e "
    "offerta.\n\n"
    "STRUTTURA: da 3 a 5 paragrafi. Apri con l'interesse per il ruolo "
    "specifico e il motivo per cui il profilo è pertinente; prosegui con "
    "1-2 paragrafi di esperienza/risultati concreti e reali che dimostrano "
    "il fit con l'offerta; se ci sono indicazioni dell'utente da "
    "includere, dedica loro un paragrafo a parte nel punto più naturale "
    "della lettera (non forzarlo in apertura se non è quello il tono "
    "richiesto); chiudi con un breve paragrafo di ringraziamento e "
    "disponibilità a un colloquio. Ogni paragrafo deve occupare per "
    "intero lo spazio di alcune righe piene (mai un paragrafo isolato di "
    "una riga sola): l'intera lettera deve restare entro una pagina, sii "
    "concreto e mai ripetitivo.\n\n"
    "CITTÀ TRADOTTA ('translated_city'): la città del candidato (fornita nel "
    "profilo) tradotta nella lingua richiesta per questa lettera (es. "
    "'Roma' → 'Rome' in inglese). Se la città è già nella lingua richiesta "
    "o non è traducibile, restituiscila invariata. Non aggiungere il "
    "paese: solo il nome della città.\n\n"
    "LINGUA ('content_language'): il codice, tra "
    f"{SUPPORTED_CV_LANGUAGES}, che corrisponde alla lingua realmente "
    "usata per scrivere i paragrafi in questa generazione. Se ti è "
    "richiesto l'inglese fisso, è sempre 'en'. Se ti è chiesto di seguire "
    "la lingua dell'offerta, individua quella lingua e restituisci il "
    "codice corrispondente tra quelli elencati; se la lingua dell'offerta "
    "non è nessuna delle lingue elencate, scrivi comunque i paragrafi in "
    f"quella lingua reale ma imposta 'content_language' su "
    f"'{FALLBACK_CV_LANGUAGE}'."
)


def generate_cover_letter_content(profile, job, cv_language_mode, instructions=""):
    """Chiama Claude per i paragrafi del corpo della cover letter (Sprint
    42): stesso profilo/offerta della generazione CV, stesso principio di
    grounding, ma nessuna selezione/taglio lato server — la lettera è
    breve per natura, non serve un budget di spazio come per i bullet CV."""
    profile_context = _build_profile_context(profile)
    language_instruction = _resolve_language(job, cv_language_mode)

    user_content = (
        f"PROFILO CANDIDATO (JSON):\n{json.dumps(profile_context, ensure_ascii=False)}\n\n"
        f"OFFERTA:\nTitolo: {job.title}\nAzienda: {job.company}\n"
        f"Descrizione: {job.description}\n\n"
        f"INDICAZIONI FORNITE DALL'UTENTE PER QUESTA LETTERA (se presenti, "
        f"usale come descritto sopra): {instructions or 'Nessuna.'}\n\n"
        f"Genera i contenuti in questa lingua: {language_instruction}."
    )

    return call_claude_structured(
        model=settings.BEDROCK_CV_GENERATION_MODEL,
        system=COVER_LETTER_SYSTEM_PROMPT,
        user_content=user_content,
        schema=COVER_LETTER_JSON_SCHEMA,
        max_tokens=2000,
        effort="medium",
    )
