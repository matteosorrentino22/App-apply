from django.core.files.base import ContentFile

from .ai_content import generate_cv_content
from .models import CVDocument
from .rendering import render_cv
from .selection import compute_bullet_budget, select_and_cut_experiences, select_educations_to_show


class ProfileIncomplete(Exception):
    """Il profilo non ha almeno 1 voce di istruzione (Docs/03 §3.2, §10.2):
    non è generabile un CV finché non è completo."""


def _format_date(value):
    return value.strftime("%Y-%m") if value else ""


def _build_contact_line(user, profile):
    parts = [user.email, profile.phone, profile.city, profile.linkedin_url]
    return " · ".join(part for part in parts if part)


def _build_full_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


def _build_shown_educations(profile):
    """Le `EDU_MAX_SHOWN` voci più recenti (Docs/03 §3.2), copiate senza
    riformulazione — solo selezione, nessuna chiamata AI per questa sezione."""
    shown = select_educations_to_show(list(profile.educations.all()))
    return [
        {
            "institution": edu.institution,
            "title": edu.title,
            "location": edu.location,
            "dates": f"{_format_date(edu.start_date)} - {_format_date(edu.end_date)}".strip(" -"),
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


def _build_shown_experiences(content, bullet_budget):
    """Applica selezione (cap 5, swap singolo) e taglio bullet al budget
    globale (Docs/03 §11 punto 4), sul contenuto già prodotto dal modello
    per punto 3. Ritorna la lista pronta per il template."""
    selected = select_and_cut_experiences(content["experiences"], bullet_budget)
    return [
        {
            "company": exp["company"],
            "role": exp["role"],
            "location": exp["location"],
            "dates": exp["dates"],
            "bullets": exp["bullets"],
        }
        for exp in selected
    ]


def _build_render_context(user, profile, content):
    shown_educations, shown_education_count = _build_shown_educations(profile)
    bullet_budget = compute_bullet_budget(shown_education_count)
    profile_skill_names = {skill.name for skill in profile.skills.all()}
    profile_certification_names = {cert.name for cert in profile.certifications.all()}

    return {
        "html_lang": "en" if user.cv_language_mode == "english" else "it",
        "full_name": _build_full_name(user),
        "contact_line": _build_contact_line(user, profile),
        "photo_url": _build_photo_url(user, profile),
        "qualification": content["qualification"],
        "summary": content["summary"],
        "areas_of_expertise": [area["label"] for area in content["areas_of_expertise"]],
        "experiences": _build_shown_experiences(content, bullet_budget),
        "educations": shown_educations,
        "skills": _filter_grounded_skills(content["skills"], profile_skill_names),
        "certifications": _filter_grounded_skills(content["certifications"], profile_certification_names),
        "languages": _build_languages(profile),
    }


def generate_cv(job, generation_type, enrichment=""):
    """Genera un CV per `job` sul profilo del suo utente (Docs/03 §11):
    contenuti via Claude (qualifica, Areas of Expertise, bullet con
    ordinamento di rilevanza per ogni esperienza), selezione/taglio
    server-side (cap esperienze con swap singolo, budget bullet dal numero
    di voci di istruzione mostrate), composizione del template HTML,
    conversione PDF con WeasyPrint, salvataggio in `CVDocument`.

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
    context = _build_render_context(user, profile, content)
    html, pdf_bytes, _page_count = render_cv(context)

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
