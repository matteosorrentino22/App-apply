from django.core.files.base import ContentFile
from django.utils import timezone

from apps.jobs.models import RunLog

from .ai_content import generate_cv_content
from .cv_parameters import MAX_OVERFLOW_ITERATIONS
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


# Etichette fisse di sezione: seguono `cv_language_mode` come il resto del
# contenuto del CV (Docs/03 §4), non restano fisse in una lingua.
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
}


def _format_date(value):
    return value.strftime("%Y-%m") if value else ""


def _format_date_range(start, end, ongoing_label):
    """Intervallo date per esperienza/istruzione: `end=None` è "in corso"
    (Sprint 34), non una data mancante — mostra l'etichetta tradotta invece
    di lasciare la riga tronca (es. "2017-09 -")."""
    end_text = ongoing_label if end is None else _format_date(end)
    return f"{_format_date(start)} - {end_text}".strip(" -")


def _format_location(city, country_code):
    return ", ".join(part for part in [city, (country_code or "").upper()] if part)


def _build_contact_parts(user, profile, translated_city):
    """Riga contatti nell'intestazione, ordine fisso (segnalato dal
    committente): Città, PAESE | telefono | email | LinkedIn. LinkedIn è
    l'unica parte con link ipertestuale (`is_link`), quindi il template
    compone il markup invece di ricevere una stringa già concatenata."""
    city_country = ", ".join(
        part for part in [translated_city, profile.country_code.upper()] if part
    )
    parts = []
    if city_country:
        parts.append({"text": city_country, "is_link": False})
    if profile.phone:
        parts.append({"text": profile.phone, "is_link": False})
    if user.email:
        parts.append({"text": user.email, "is_link": False})
    if profile.linkedin_url:
        parts.append({"text": "LinkedIn", "url": profile.linkedin_url, "is_link": True})
    return parts


def _build_full_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


def _build_shown_educations(profile, ongoing_label):
    """Le `EDU_MAX_SHOWN` voci più recenti (Docs/03 §3.2), copiate senza
    riformulazione — solo selezione, nessuna chiamata AI per questa sezione."""
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


def _build_languages(profile):
    return [{"language": lang.language, "level": lang.level} for lang in profile.languages.all()]


def _build_photo_url(user, profile):
    if not user.cv_include_photo or not profile.photo:
        return ""
    return f"file://{profile.photo.path}"


def _filter_grounded_skills(ai_names, profile_names):
    """Le voci mostrate nel CV devono restare un sottoinsieme di quelle
    reali del profilo, mai di invenzione dell'AI (grounding, §6.2 tecniche
    madre)."""
    return [name for name in ai_names if name in profile_names]


def _attach_facts_and_enrichment(
    ai_experiences, profile, protected_bullets, protected_experience_id, ongoing_label
):
    """`location`/`dates`/`technologies` sono dati fattuali del profilo, non
    riformulati dall'AI (grounding): il prompt garantisce stesso ordine e
    stesso numero di voci in output (Docs/03 §11 punto 3), quindi si
    riattaccano per indice invece di chiederli al modello. Stesso principio
    per i bullet di arricchimento (§5.6): iniettati letteralmente (mai
    passati alla riformulazione AI) sull'esperienza corrispondente, marcati
    `protected` per la protezione nel taglio budget/overflow."""
    ordered_profile_experiences = list(
        profile.experiences.all().order_by("-end_date", "-start_date")
    )
    result = []
    for index, exp in enumerate(ai_experiences):
        profile_experience = ordered_profile_experiences[index]
        bullets = list(exp["bullets"])
        if protected_experience_id and profile_experience.pk == protected_experience_id:
            bullets.extend(
                {"text": text, "relevance_rank": -1, "protected": True}
                for text in protected_bullets
            )
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
                "bullets": bullets,
            }
        )
    return result


def _build_shown_experiences(
    content, bullet_budget, profile, protected_bullets, protected_experience_id, ongoing_label
):
    """Applica selezione (cap 5, swap singolo) e taglio bullet al budget
    globale (Docs/03 §11 punto 4), sul contenuto già prodotto dal modello
    per punto 3. I bullet restano dict `{text, relevance_rank}` — il loop di
    ripiego per overflow (§6) deve poterli continuare a rimuovere per
    rilevanza; l'appiattimento a stringa avviene solo subito prima del primo
    rendering (`generate_cv`)."""
    with_facts = _attach_facts_and_enrichment(
        content["experiences"], profile, protected_bullets or [], protected_experience_id, ongoing_label
    )
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


def _build_render_context(user, profile, content, protected_bullets, protected_experience_id):
    html_lang = "en" if user.cv_language_mode == "english" else "it"
    ongoing_label = SECTION_LABELS[html_lang]["ongoing"]
    shown_educations, shown_education_count = _build_shown_educations(profile, ongoing_label)
    bullet_budget = compute_bullet_budget(shown_education_count)
    profile_skill_names = {skill.name for skill in profile.skills.all()}
    profile_certification_names = {cert.name for cert in profile.certifications.all()}

    return {
        "html_lang": html_lang,
        "labels": SECTION_LABELS[html_lang],
        "full_name": _build_full_name(user),
        "contact_parts": _build_contact_parts(user, profile, content["translated_city"]),
        "photo_url": _build_photo_url(user, profile),
        "qualification": content["qualification"],
        "summary": content["summary"],
        "areas_of_expertise": [area["label"] for area in content["areas_of_expertise"]],
        "experiences": _build_shown_experiences(
            content, bullet_budget, profile, protected_bullets, protected_experience_id, ongoing_label
        ),
        "educations": shown_educations,
        "skills": _filter_grounded_skills(content["skills"], profile_skill_names),
        "certifications": _filter_grounded_skills(content["certifications"], profile_certification_names),
        "languages": _build_languages(profile),
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


def generate_cv(
    job, generation_type, enrichment="", protected_bullets=None, protected_experience_id=None
):
    """Genera un CV per `job` sul profilo del suo utente (Docs/03 §11):
    contenuti via Claude (qualifica, Areas of Expertise, bullet con
    ordinamento di rilevanza per ogni esperienza), selezione/taglio
    server-side (cap esperienze con swap singolo, budget bullet dal numero
    di voci di istruzione mostrate), composizione del template HTML,
    conversione PDF con WeasyPrint (con loop di ripiego per overflow),
    salvataggio in `CVDocument`.

    `protected_bullets`/`protected_experience_id` (Docs/03 §5.6): bullet di
    arricchimento con priorità massima di inclusione per questa generazione
    — mai esclusi dal cap esperienze, dal taglio budget né dal loop di
    ripiego per overflow.

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

    content = generate_cv_content(profile, job, user.cv_language_mode, enrichment)
    context = _build_render_context(
        user, profile, content, protected_bullets, protected_experience_id
    )
    html, pdf_bytes = _render_with_overflow_retry(job, context)

    cv_document = CVDocument.objects.create(
        job=job,
        user=user,
        html_source=html,
        generation_type=generation_type,
        enrichment_used=enrichment,
        areas_of_expertise_grounding=[
            {"label": area["label"], "grounding_reference": area["grounding_reference"]}
            for area in content["areas_of_expertise"]
        ],
    )
    cv_document.pdf_file.save(
        f"cv_{job.pk}_{cv_document.pk}.pdf", ContentFile(pdf_bytes), save=True
    )
    return cv_document
