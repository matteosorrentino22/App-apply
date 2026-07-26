from django.core.files.base import ContentFile

from .ai_content import generate_cv_content
from .models import CVDocument
from .rendering import render_cv


def _format_date(value):
    return value.strftime("%Y-%m") if value else ""


def _build_contact_line(user, profile):
    parts = [user.email, profile.phone, profile.city, profile.linkedin_url]
    return " · ".join(part for part in parts if part)


def _build_full_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


def _build_educations(profile):
    return [
        {
            "institution": edu.institution,
            "title": edu.title,
            "location": edu.location,
            "dates": edu.dates,
            "notes": edu.notes,
        }
        for edu in profile.educations.all()
    ]


def _build_languages(profile):
    return [{"language": lang.language, "level": lang.level} for lang in profile.languages.all()]


def _build_photo_url(user, profile):
    if not user.cv_include_photo or not profile.photo:
        return ""
    return f"file://{profile.photo.path}"


def _filter_grounded_skills(ai_skills, profile):
    """Le competenze mostrate nel CV devono restare un sottoinsieme di quelle
    reali del profilo, mai di invenzione dell'AI (grounding, §6.2 tecniche)."""
    profile_skill_names = {skill.name for skill in profile.skills.all()}
    return [name for name in ai_skills if name in profile_skill_names]


def _build_render_context(user, profile, job, content):
    return {
        "html_lang": "en" if user.cv_language_mode == "english" else "it",
        "full_name": _build_full_name(user),
        "contact_line": _build_contact_line(user, profile),
        "photo_url": _build_photo_url(user, profile),
        "summary": content["summary"],
        "key_achievements": content["key_achievements"],
        "experiences": content["experiences"],
        "educations": _build_educations(profile),
        "skills": _filter_grounded_skills(content["skills"], profile),
        "certifications": [cert.name for cert in profile.certifications.all()],
        "languages": _build_languages(profile),
    }


def generate_cv(job, generation_type, enrichment=""):
    """Genera un CV per `job` sul profilo del suo utente: contenuti via
    Claude, composizione del template HTML, conversione PDF con WeasyPrint,
    salvataggio in `CVDocument` (02-specifiche-tecniche-v3.md §6.2).

    Solleva l'eccezione a chi chiama in caso di fallimento (chiamata Claude,
    rendering): la gestione (stato Job, quota/credito, RunLog) è
    responsabilità di chi orchestra la generazione — automatica (Sprint 11)
    o manuale (Sprint 12) — non di questo servizio riusabile.
    """
    user = job.user
    profile = user.profile

    content = generate_cv_content(profile, job, user.cv_language_mode, enrichment)
    context = _build_render_context(user, profile, job, content)
    html, pdf_bytes, _page_count = render_cv(context)

    cv_document = CVDocument.objects.create(
        job=job,
        user=user,
        html_source=html,
        generation_type=generation_type,
        enrichment_used=enrichment,
    )
    cv_document.pdf_file.save(
        f"cv_{job.pk}_{cv_document.pk}.pdf", ContentFile(pdf_bytes), save=True
    )
    return cv_document
