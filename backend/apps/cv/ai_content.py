import json

from django.conf import settings

from apps.common.ai import call_claude_structured

from .cv_parameters import (
    AREAS_OF_EXPERTISE_MAX,
    AREAS_OF_EXPERTISE_MIN,
    FALLBACK_CV_LANGUAGE,
    SUPPORTED_CV_LANGUAGES,
)

CONTENT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "qualification": {"type": "string"},
        "translated_city": {"type": "string"},
        # Usato solo per scegliere le etichette fisse di sezione lato server
        # (apps.cv.generation.SECTION_LABELS), mai mostrato all'utente finale.
        "content_language": {"type": "string", "enum": SUPPORTED_CV_LANGUAGES},
        "areas_of_expertise": {
            # Niente minItems/maxItems: con l'output strutturato nativo
            # dell'API Anthropic (non più in uso, vedi apps.common.ai) un
            # valore diverso da 0/1 dava 400 "minItems values other than
            # 0 or 1 are not supported" — non re-introdotto per prudenza
            # dopo il passaggio al tool-use forzato su Bedrock. Il vincolo
            # 4-6 resta solo nel prompt testuale, come già per
            # experiences/bullets.
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
                "required": ["company", "role", "highly_relevant", "bullets"],
                "additionalProperties": False,
            },
        },
        "skills": {"type": "array", "items": {"type": "string"}},
        "certifications": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "qualification",
        "translated_city",
        "content_language",
        "areas_of_expertise",
        "experiences",
        "skills",
        "certifications",
    ],
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
    "PRIORITÀ DELL'OFFERTA: prima di scrivere qualsiasi contenuto, individua "
    "mentalmente le 3-5 priorità chiave dell'offerta (competenze/tool "
    "richiesti, responsabilità principali, seniority, dominio/settore) e "
    "usale per orientare in modo coerente sommario, aree di competenza e "
    "bullet delle esperienze. Le sezioni non sono compartimenti stagni: se "
    "una priorità dell'offerta è supportata da contenuto reale del profilo, "
    "può e deve riflettersi in più punti del CV (es. sia nel sommario sia "
    "nel bullet dell'esperienza pertinente), non solo in uno.\n\n"
    "SOMMARIO ('summary'): il profilo master include già un breve sommario "
    "scritto dal candidato — usalo come base indicativa, non come vincolo "
    "rigido: puoi riorganizzarlo, tagliarlo o riscriverlo quasi per intero "
    "se serve per aprirlo sulle priorità dell'offerta individuate sopra, "
    "mantenendo comunque riconoscibile la figura professionale reale che "
    "descrive. Usa la terminologia dell'offerta solo dove corrisponde "
    "realmente a qualcosa già presente nel profilo (esperienze, skill, "
    "risultati): mai per attribuire competenze che il candidato non ha. "
    "Occupa per intero lo spazio naturale di un sommario di CV (un breve "
    "paragrafo di alcune righe piene): evita sia una frase isolata troppo "
    "corta sia un'ultima riga che si esaurisce dopo poche parole.\n\n"
    "QUALIFICA PROFESSIONALE ('qualification'): estrai dal titolo del job il "
    "nome del ruolo, spogliato di tecnologie/progetto/contesto (es. "
    "'Software Engineer for SSH/AWS and ERP systems' → 'Software Engineer'). "
    "Mantieni la seniority se presente nel titolo (Senior, Junior, Lead...). "
    "Se il titolo è già un nome di ruolo pulito, usalo così com'è. Se il "
    "titolo è ambiguo o multi-ruolo e non ne ricavi un ruolo univoco, usa il "
    "ruolo dell'esperienza professionale più recente del profilo; se il "
    "profilo non ha esperienze, usa comunque il titolo del job ripulito.\n\n"
    "CITTÀ TRADOTTA ('translated_city'): la città del candidato (fornita nel "
    "profilo) tradotta nella lingua richiesta per questo CV (es. 'Roma' → "
    "'Rome' in inglese). Se la città è già nella lingua richiesta o non è "
    "traducibile, restituiscila invariata. Non aggiungere il paese: solo il "
    "nome della città.\n\n"
    "LINGUA DEL CONTENUTO ('content_language'): il codice, tra "
    f"{SUPPORTED_CV_LANGUAGES}, che corrisponde alla lingua realmente usata "
    "per scrivere summary/qualification/bullet/aree di competenza in questa "
    "generazione. Se ti è stato richiesto l'inglese fisso, è sempre 'en'. Se "
    "ti è stato chiesto di seguire la lingua dell'offerta, individua quella "
    "lingua e restituisci il codice corrispondente tra quelli elencati; se "
    "la lingua dell'offerta non è nessuna delle lingue elencate, scrivi "
    f"comunque tutto il resto del contenuto in quella lingua reale (come "
    f"richiesto) ma imposta 'content_language' su '{FALLBACK_CV_LANGUAGE}' "
    "(le etichette fisse del CV, non generate da te, non hanno una "
    "traduzione per altre lingue).\n\n"
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
    "offerta specifica. Se una competenza richiesta dall'offerta è presente "
    "nel profilo solo come voce isolata in 'skills' ma è verosimilmente "
    "riconducibile a un'esperienza specifica del candidato, valuta se "
    "renderla esplicita in un bullet reale di quella esperienza invece di "
    "lasciarla solo nell'elenco skills: la rende più contestualizzata e "
    "credibile. Ogni bullet riformulato deve occupare per intero lo spazio "
    "di 1 o 2 righe piene: mai una seconda riga che si esaurisce dopo poche "
    "parole — se un bullet rischia di sforare di poco su una seconda riga "
    "quasi vuota, accorcialo per stare su una riga sola, oppure espandilo "
    "con un dettaglio reale in più (impatto, contesto, strumento usato) per "
    "riempirla.\n\n"
    "SKILLS e CERTIFICATIONS: seleziona solo voci letteralmente presenti nel "
    "profilo, per rilevanza rispetto all'offerta, senza inventarne di nuove. "
    "Una competenza già valorizzata in un bullet di esperienza (vedi sopra) "
    "resta comunque elencabile qui: le due cose non si escludono a vicenda."
)


def _build_experiences_input(profile):
    # `location`/`dates` non sono inclusi: sono dati fattuali (come
    # `technologies`), non riformulati dall'AI — riattaccati lato server
    # dopo la chiamata (Sprint 34, stesso principio di generation.py).
    return [
        {
            "company": exp.company,
            "role": exp.role,
            "bullets": exp.bullets,
            "technologies": exp.technologies,
        }
        for exp in profile.experiences.all().order_by("-end_date", "-start_date")
    ]


def _build_profile_context(profile):
    return {
        "summary": profile.summary,
        "city": profile.city,
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

    return call_claude_structured(
        model=settings.BEDROCK_CV_GENERATION_MODEL,
        system=CONTENT_SYSTEM_PROMPT,
        user_content=user_content,
        schema=CONTENT_JSON_SCHEMA,
        max_tokens=4000,
        effort="medium",
    )
