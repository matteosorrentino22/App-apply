from django.core.files.base import ContentFile
from django.utils import timezone

from apps.jobs.models import RunLog

from apps.profiles.language_options import LANGUAGE_LEVEL_LABELS, LANGUAGE_NAME_LABELS

from .ai_content import generate_cv_content
from .cv_parameters import FALLBACK_CV_LANGUAGE, MAX_OVERFLOW_ITERATIONS, SUPPORTED_CV_LANGUAGES
from .models import CVDocument
from .rendering import render_cv
from .selection import (
    compute_bullet_budget,
    flatten_bullets_to_text,
    remove_least_relevant_bullet,
    select_and_cut_experiences,
    select_educations_to_show,
)


class ProfileIncomplete(Exception):
    """Il profilo non ha almeno 1 voce di istruzione (Docs/03 §3.2, §10.2):
    non è generabile un CV finché non è completo."""


# Etichette fisse di sezione: seguono la lingua reale del contenuto generato
# (Docs/03 §4), non restano fisse in una lingua — vedi `_resolve_html_lang`.
# Stessi 5 codici di `SUPPORTED_CV_LANGUAGES` (Sprint 41: prima solo it/en,
# causa del bug delle etichette in italiano su CV generati in altre lingue).
SECTION_LABELS = {
    "it": {
        "summary": "Profilo",
        "areas_of_expertise": "Aree di competenza",
        "experience": "Esperienza lavorativa",
        "education": "Istruzione",
        "certified_in": "Certificazioni",
        "skilled_in": "Competenze",
        "languages": "Lingue",
        "technologies": "Tecnologie",
        "ongoing": "Presente",
    },
    "en": {
        "summary": "Profile",
        "areas_of_expertise": "Areas of Expertise",
        "experience": "Work Experience",
        "education": "Education",
        "certified_in": "Certified in",
        "skilled_in": "Skilled in",
        "languages": "Languages",
        "technologies": "Technologies",
        "ongoing": "Present",
    },
    "fr": {
        "summary": "Profil",
        "areas_of_expertise": "Domaines de compétence",
        "experience": "Expérience professionnelle",
        "education": "Formation",
        "certified_in": "Certifications",
        "skilled_in": "Compétences",
        "languages": "Langues",
        "technologies": "Technologies",
        "ongoing": "Aujourd'hui",
    },
    "de": {
        "summary": "Profil",
        "areas_of_expertise": "Kompetenzbereiche",
        "experience": "Berufserfahrung",
        "education": "Ausbildung",
        "certified_in": "Zertifizierungen",
        "skilled_in": "Kenntnisse",
        "languages": "Sprachen",
        "technologies": "Technologien",
        "ongoing": "Heute",
    },
    "es": {
        "summary": "Perfil",
        "areas_of_expertise": "Áreas de especialización",
        "experience": "Experiencia laboral",
        "education": "Formación",
        "certified_in": "Certificaciones",
        "skilled_in": "Habilidades",
        "languages": "Idiomas",
        "technologies": "Tecnologías",
        "ongoing": "Actualidad",
    },
}


def _resolve_html_lang(user, content):
    """Lingua reale del contenuto generato, non la sola modalità impostata
    dall'utente (Sprint 41): con `cv_language_mode="job_language"` il CV
    esce nella lingua dell'offerta, che l'AI riporta in
    `content["content_language"]` (vedi ai_content.py) — usarla è l'unico
    modo corretto di scegliere le etichette fisse, a differenza del vecchio
    `"en" if cv_language_mode == "english" else "it"` che le lasciava in
    italiano per qualunque offerta non in inglese fisso."""
    if user.cv_language_mode == "english":
        return "en"
    detected = content.get("content_language")
    return detected if detected in SUPPORTED_CV_LANGUAGES else FALLBACK_CV_LANGUAGE


def _format_date(value):
    """Solo l'anno sul CV (richiesto esplicitamente): la data precisa resta
    salvata nel profilo per usi futuri, qui si mostra solo `%Y`."""
    return value.strftime("%Y") if value else ""


def _format_date_range(start, end, ongoing_label):
    """Intervallo date per esperienza/istruzione: `end=None` è "in corso"
    (Sprint 34), non una data mancante — mostra l'etichetta tradotta invece
    di lasciare la riga tronca (es. "2017 -"). Inizio e fine nello stesso
    anno (solo l'anno viene mostrato) collassano su un anno solo invece di
    ripeterlo (es. "2022 - 2022" → "2022")."""
    if end is None:
        return f"{_format_date(start)} - {ongoing_label}".strip(" -")
    if start and start.year == end.year:
        return _format_date(end)
    return f"{_format_date(start)} - {_format_date(end)}".strip(" -")


def _format_location(city, country_code):
    return ", ".join(part for part in [city, (country_code or "").upper()] if part)


def _build_contact_parts(profile, translated_city):
    """Riga contatti nell'intestazione, ordine fisso (segnalato dal
    committente): Città, PAESE | telefono | email | LinkedIn. LinkedIn è
    l'unica parte con link ipertestuale (`is_link`), quindi il template
    compone il markup invece di ricevere una stringa già concatenata.
    L'email è `profile.email` (Sprint 41), non `user.email`: quella
    dell'account di login può essere un alias tecnico mai pensato per
    comparire su un CV (es. "nome+1@gmail.com")."""
    city_country = ", ".join(
        part for part in [translated_city, profile.country_code.upper()] if part
    )
    parts = []
    if city_country:
        parts.append({"text": city_country, "is_link": False})
    if profile.phone:
        parts.append({"text": profile.phone, "is_link": False})
    if profile.email:
        parts.append({"text": profile.email, "is_link": False})
    if profile.linkedin_url:
        parts.append({"text": "LinkedIn", "url": profile.linkedin_url, "is_link": True})
    return parts


def _build_full_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


def _build_shown_educations(profile, ongoing_label):
    """Tutte le voci di istruzione del profilo, ordinate (Docs/03 §3.2) e
    copiate senza riformulazione — nessuna esclusa per limite di conteggio,
    nessuna chiamata AI per questa sezione."""
    shown = select_educations_to_show(list(profile.educations.all()))
    return [
        {
            "institution": edu.institution,
            "title": edu.title,
            "location": _format_location(edu.location, edu.location_country_code),
            "dates": _format_date_range(edu.start_date, edu.end_date, ongoing_label),
            "notes": edu.notes,
        }
        for edu in shown
    ], len(shown)


def _build_languages(profile, html_lang):
    """Traduce lingua/livello nella lingua di output del CV (Sprint 41): i
    valori sono codici fissi (Language.language/.level, vedi
    apps.profiles.language_options), mai passati all'AI né mostrati tali e
    quali — prima venivano copiati letteralmente, senza traduzione. Se un
    codice non è tra quelli tradotti (dato legacy non normalizzato dalla
    migrazione 0007), si mostra il valore grezzo invece di perderlo."""
    return [
        {
            "language": LANGUAGE_NAME_LABELS.get(lang.language, {}).get(html_lang, lang.language),
            "level": LANGUAGE_LEVEL_LABELS.get(lang.level, {}).get(html_lang, lang.level),
        }
        for lang in profile.languages.all()
    ]


def _build_photo_url(user, profile):
    if not user.cv_include_photo or not profile.photo:
        return ""
    return f"file://{profile.photo.path}"


def _filter_grounded_skills(ai_names, profile_names):
    """Le voci mostrate nel CV devono restare un sottoinsieme di quelle
    reali del profilo, mai di invenzione dell'AI (grounding, §6.2 tecniche
    madre)."""
    return [name for name in ai_names if name in profile_names]


def _attach_facts(ai_experiences, profile, ongoing_label):
    """`location`/`dates`/`technologies` sono dati fattuali del profilo, non
    riformulati dall'AI (grounding): il prompt garantisce stesso ordine e
    stesso numero di voci in output (Docs/03 §11 punto 3), quindi si
    riattaccano per indice invece di chiederli al modello."""
    ordered_profile_experiences = list(
        profile.experiences.all().order_by("-end_date", "-start_date")
    )
    result = []
    for index, exp in enumerate(ai_experiences):
        profile_experience = ordered_profile_experiences[index]
        result.append(
            {
                **exp,
                "location": _format_location(
                    profile_experience.location, profile_experience.location_country_code
                ),
                "dates": _format_date_range(
                    profile_experience.start_date, profile_experience.end_date, ongoing_label
                ),
                "technologies": profile_experience.technologies,
            }
        )
    return result


def _build_shown_experiences(content, bullet_budget, profile, ongoing_label):
    """Applica selezione (cap 5, swap singolo) e taglio bullet al budget
    globale (Docs/03 §11 punto 4), sul contenuto già prodotto dal modello
    per punto 3. I bullet restano dict `{text, relevance_rank}` — il loop di
    ripiego per overflow (§6) deve poterli continuare a rimuovere per
    rilevanza; l'appiattimento a stringa avviene solo subito prima del primo
    rendering (`generate_cv`)."""
    with_facts = _attach_facts(content["experiences"], profile, ongoing_label)
    selected = select_and_cut_experiences(with_facts, bullet_budget)
    return [
        {
            "company": exp["company"],
            "role": exp["role"],
            "location": exp["location"],
            "dates": exp["dates"],
            "bullets": exp["bullets"],
            "technologies": exp["technologies"],
        }
        for exp in selected
    ]


def _build_render_context(user, profile, content):
    html_lang = _resolve_html_lang(user, content)
    ongoing_label = SECTION_LABELS[html_lang]["ongoing"]
    shown_educations, shown_education_count = _build_shown_educations(profile, ongoing_label)
    bullet_budget = compute_bullet_budget(shown_education_count)
    profile_skill_names = {skill.name for skill in profile.skills.all()}
    profile_certification_names = {cert.name for cert in profile.certifications.all()}

    return {
        "html_lang": html_lang,
        "labels": SECTION_LABELS[html_lang],
        "full_name": _build_full_name(user),
        "contact_parts": _build_contact_parts(profile, content["translated_city"]),
        "photo_url": _build_photo_url(user, profile),
        "qualification": content["qualification"],
        "summary": content["summary"],
        "areas_of_expertise": [area["label"] for area in content["areas_of_expertise"]],
        "experiences": _build_shown_experiences(content, bullet_budget, profile, ongoing_label),
        "educations": shown_educations,
        "skills": _filter_grounded_skills(content["skills"], profile_skill_names),
        "certifications": _filter_grounded_skills(content["certifications"], profile_certification_names),
        "languages": _build_languages(profile, html_lang),
    }


def _render_with_overflow_retry(job, context):
    """Controllo "1 pagina" e loop di ripiego (Docs/03 §6, §11 punto 6):
    `render_cv` applica già i 3 livelli di compattamento; se il risultato
    resta multi-pagina, si rimuove un bullet alla volta (il globalmente
    meno rilevante, sugli stessi dati già selezionati/tagliati al budget)
    e si rirenderizza, fino a `MAX_OVERFLOW_ITERATIONS`. Esaurito il tetto,
    si accetta il caso residuale: si salva comunque il PDF multi-pagina,
    senza errore mostrato, con l'evento tracciato in `RunLog` per diagnosi."""
    raw_experiences = context["experiences"]
    context["experiences"] = flatten_bullets_to_text(raw_experiences)
    html, pdf_bytes, page_count = render_cv(context)

    iterations = 0
    while page_count > 1 and iterations < MAX_OVERFLOW_ITERATIONS:
        if not remove_least_relevant_bullet(raw_experiences):
            break
        context["experiences"] = flatten_bullets_to_text(raw_experiences)
        html, pdf_bytes, page_count = render_cv(context)
        iterations += 1

    if page_count > 1:
        RunLog.objects.create(
            user=job.user,
            job=job,
            task_type=RunLog.TaskType.CV_GENERATION,
            status=RunLog.Status.SUCCESS,
            message=f"CV generato multi-pagina ({page_count} pagine) dopo {iterations} iterazioni di ripiego.",
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
    return html, pdf_bytes


def generate_cv(job, generation_type, extra_instructions=""):
    """Genera un CV per `job` sul profilo del suo utente (Docs/03 §11):
    contenuti via Claude (qualifica, Areas of Expertise, bullet con
    ordinamento di rilevanza per ogni esperienza), selezione/taglio
    server-side (cap esperienze con swap singolo, budget bullet dal numero
    di voci di istruzione mostrate), composizione del template HTML,
    conversione PDF con WeasyPrint (con loop di ripiego per overflow),
    salvataggio in `CVDocument`.

    `extra_instructions` (Sprint 44): testo opzionale per colmare i gap
    rilevati per questa specifica offerta — vedi `apps.cv.gap_filling` per
    come viene composto da gap selezionati + indicazioni dell'utente, e il
    system prompt in `ai_content.py` per le regole di quando è permesso
    amplificare un'esperienza reale per farvi emergere un gap.

    Solleva l'eccezione a chi chiama in caso di fallimento (profilo
    incompleto, chiamata Claude, rendering): la gestione (stato Job,
    quota/credito, RunLog) è responsabilità di chi orchestra la generazione
    — automatica (Sprint 11) o manuale (Sprint 12) — non di questo servizio
    riusabile.
    """
    user = job.user
    profile = user.profile
    if not profile.is_complete:
        raise ProfileIncomplete("Il profilo non ha ancora almeno un titolo di studio.")

    content = generate_cv_content(profile, job, user.cv_language_mode, extra_instructions)
    context = _build_render_context(user, profile, content)
    html, pdf_bytes = _render_with_overflow_retry(job, context)

    cv_document = CVDocument.objects.create(
        job=job,
        user=user,
        html_source=html,
        generation_type=generation_type,
        extra_instructions_used=extra_instructions,
        areas_of_expertise_grounding=[
            {"label": area["label"], "grounding_reference": area["grounding_reference"]}
            for area in content["areas_of_expertise"]
        ],
    )
    cv_document.pdf_file.save(
        f"cv_{job.pk}_{cv_document.pk}.pdf", ContentFile(pdf_bytes), save=True
    )
    return cv_document
