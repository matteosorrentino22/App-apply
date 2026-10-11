import json

from django.conf import settings

from apps.common.ai import call_claude_structured

from .ai_content import _build_profile_context, _resolve_language
from .generation import _build_full_name

REFERRAL_MESSAGE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "message": {"type": "string"},
    },
    "required": ["subject", "message"],
    "additionalProperties": False,
}

REFERRAL_MESSAGE_SYSTEM_PROMPT = (
    "Scrivi un messaggio di networking con cui un candidato chiede a "
    "qualcuno — un contatto, un dipendente dell'azienda, un recruiter o "
    "l'hiring manager — di essere raccomandato o presentato per una "
    "specifica offerta di lavoro. Lo scopo è ottenere una risposta: deve "
    "catturare l'interesse del destinatario in poche righe, non essere un "
    "riassunto del CV.\n\n"
    "CANALE (indicato nel contenuto utente, 'linkedin' oppure 'email'):\n"
    "- linkedin: messaggio molto breve (massimo 80-100 parole, 3-5 frasi), "
    "informale ma professionale, nessun oggetto (restituisci 'subject' "
    "come stringa vuota) — su LinkedIn un messaggio lungo non viene letto.\n"
    "- email: oggetto breve e specifico (campo 'subject', max 60 caratteri "
    "circa, mai generico tipo 'Candidatura'), corpo di massimo 150-180 "
    "parole, 2-3 paragrafi brevi, leggermente più strutturato di un "
    "messaggio LinkedIn ma comunque conciso.\n"
    "In entrambi i casi saluto iniziale e firma finale fanno parte del "
    "testo di 'message' stesso (nessuna formattazione esterna aggiunta "
    "dopo): firma sempre con il nome del candidato fornito nel contenuto "
    "utente, mai con un placeholder come '[Nome]' o '[Name]'.\n\n"
    "DESTINATARIO: usa il nome fornito per il saluto, se presente; se non "
    "è fornito nessun nome, apri con un saluto generico senza inventarne "
    "uno. Non assumere mai una relazione pregressa col destinatario (es. "
    "'come discusso', 'come ci eravamo lasciati') a meno che non sia "
    "esplicitamente indicata nelle indicazioni dell'utente: per default il "
    "tono è quello di un primo contatto professionale (cold outreach), "
    "rispettoso e diretto, mai presuntuoso.\n\n"
    "GROUNDING: per ogni affermazione sul candidato (esperienze, ruoli, "
    "competenze) resta ancorato solo a ciò che è realmente nel profilo "
    "fornito — non inventare mai un'azienda, un ruolo o un risultato che "
    "il candidato non ha avuto. Non menzionare mai un allegato (CV, "
    "resume): non sappiamo se l'utente allegherà davvero qualcosa dopo "
    "aver copiato questo testo nel suo client.\n\n"
    "OBIETTIVO: collega in modo specifico il profilo del candidato al "
    "ruolo e all'azienda dell'offerta (mai un testo generico riusabile su "
    "qualunque offerta), e chiudi con una richiesta chiara e specifica "
    "(es. 'mi faresti sapere se pensi che il mio profilo sia adatto?', "
    "'potresti metterti in contatto con chi si occupa di questa "
    "posizione?') — non vaga ('ti scrivo per questa opportunità').\n\n"
    "INDICAZIONI DELL'UTENTE: se fornite, usale per orientare contenuto e "
    "tono — possono riguardare la relazione con il destinatario, dettagli "
    "da menzionare, o enfasi particolari. Se non fornite, scrivi comunque "
    "un messaggio efficace basandoti solo su profilo e offerta.\n\n"
    "LINGUA: scrivi nella lingua indicata nel contenuto utente."
)


def generate_referral_message_content(
    profile, job, cv_language_mode, channel, recipient_name="", instructions=""
):
    """Chiama Claude per il testo del messaggio di networking (Sprint 50):
    stesso profilo/offerta della cover letter, stesso principio di
    grounding, ma output pensato per essere copiato in un messaggio
    LinkedIn o in un'email, non per un documento PDF."""
    profile_context = _build_profile_context(profile)
    language_instruction = _resolve_language(job, cv_language_mode)

    user_content = (
        f"PROFILO CANDIDATO (JSON):\n{json.dumps(profile_context, ensure_ascii=False)}\n\n"
        f"NOME DEL CANDIDATO (usalo per firmare il messaggio, mai un "
        f"placeholder): {_build_full_name(job.user)}\n\n"
        f"OFFERTA:\nTitolo: {job.title}\nAzienda: {job.company}\n"
        f"Descrizione: {job.description}\n\n"
        f"CANALE: {channel}\n"
        f"NOME DESTINATARIO: {recipient_name or 'Non fornito.'}\n\n"
        f"INDICAZIONI FORNITE DALL'UTENTE (se presenti, usale come "
        f"descritto sopra): {instructions or 'Nessuna.'}\n\n"
        f"Genera i contenuti in questa lingua: {language_instruction}."
    )

    return call_claude_structured(
        model=settings.BEDROCK_CV_GENERATION_MODEL,
        system=REFERRAL_MESSAGE_SYSTEM_PROMPT,
        user_content=user_content,
        schema=REFERRAL_MESSAGE_JSON_SCHEMA,
        max_tokens=1500,
        effort="medium",
    )
