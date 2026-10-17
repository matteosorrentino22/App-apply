# Editor interattivo del CV (Sprint 51): la bozza (`CVDraft`) parte sempre
# dall'ultimo `CVDocument` già generato (mai da zero — generare resta il
# compito di "Genera CV"/`generation.py`) e produce il PDF finale senza
# richiamare Claude né applicare taglio automatico al budget: le scelte di
# cosa mostrare sono già quelle dell'utente, fatte nell'editor.
from django.core.files.base import ContentFile

from apps.profiles.language_options import LANGUAGE_LEVEL_LABELS, LANGUAGE_NAME_LABELS

from .cv_parameters import FALLBACK_CV_LANGUAGE, SUPPORTED_CV_LANGUAGES
from .generation import (
    SECTION_LABELS,
    _build_contact_parts,
    _build_full_name,
    _build_photo_url,
)
from .models import CVDocument, CVDraft
from .rendering import render_cv


class NoCvDocumentToEdit(Exception):
    """Nessun CVDocument esistente da cui aprire un draft per questo job."""


class NoDraftToFinalize(Exception):
    """Nessuna bozza in corso per questo job: va aperta prima con
    `seed_draft_for_job` (pulsante "Modifica CV")."""


def seed_draft_for_job(job):
    """Apre (o riapre, sovrascrivendo) la bozza per `job`, a partire
    dall'ultimo CVDocument generato."""
    latest = job.cv_documents.order_by("-generated_at", "-id").first()
    if latest is None or not latest.content_json:
        raise NoCvDocumentToEdit("Genera prima un CV per questo job.")

    draft, _created = CVDraft.objects.update_or_create(
        job=job,
        defaults={"user": job.user, "content_json": latest.content_json},
    )
    return draft


def _translate_draft_languages(languages, html_lang):
    return [
        {
            "language": LANGUAGE_NAME_LABELS.get(lang["language"], {}).get(
                html_lang, lang["language"]
            ),
            "level": LANGUAGE_LEVEL_LABELS.get(lang["level"], {}).get(html_lang, lang["level"]),
        }
        for lang in languages
    ]


def render_context_from_draft(user, profile, draft_content):
    """Contesto di rendering a partire dal contenuto già deciso dall'utente
    nell'editor: a differenza di `generation._build_render_context`, nessuna
    selezione/taglio automatico — le scelte di cosa mostrare, in che ordine
    e con che testo sono già quelle dell'utente."""
    html_lang = draft_content.get("content_language")
    if html_lang not in SUPPORTED_CV_LANGUAGES:
        html_lang = FALLBACK_CV_LANGUAGE

    experiences = [
        {
            "company": exp["company"],
            "role": exp["role"],
            "location": exp["location"],
            "dates": exp["dates"],
            "technologies": exp["technologies"],
            "bullets": [bullet["text"] for bullet in exp["bullets"] if bullet["shown"]],
        }
        for exp in draft_content["experiences"]
        if exp["shown"]
    ]

    return {
        "html_lang": html_lang,
        "labels": SECTION_LABELS[html_lang],
        "full_name": _build_full_name(user),
        "contact_parts": _build_contact_parts(profile, draft_content["translated_city"]),
        "photo_url": _build_photo_url(user, profile),
        "qualification": draft_content["qualification"],
        "summary": draft_content["summary"],
        "areas_of_expertise": draft_content["areas_of_expertise"],
        "experiences": experiences,
        "educations": draft_content["educations"],
        "skills": draft_content["skills"],
        "certifications": draft_content["certifications"],
        "languages": _translate_draft_languages(draft_content["languages"], html_lang),
    }


def render_draft_preview(user, profile, draft_content):
    """Rendering economico per la preview live nell'editor: stessi 3 livelli
    di compattamento di `render_cv`, nessuna chiamata AI né loop di ripiego
    per overflow — se eccede 1 pagina lo si segnala (`page_count`), cosa
    tagliare resta una scelta dell'utente, non dell'algoritmo."""
    context = render_context_from_draft(user, profile, draft_content)
    _html, pdf_bytes, page_count = render_cv(context)
    return pdf_bytes, page_count


def finalize_cv_draft(job):
    """Produce il PDF finale a partire dal draft corrente: stessa pipeline
    di rendering di `generate_cv`, ma senza richiamare Claude — il contenuto
    è già quello scelto dall'utente. Nessun consumo di quota/credito: non è
    una nuova generazione AI, solo un secondo rendering dello stesso CV già
    pagato alla generazione iniziale."""
    try:
        draft = job.cv_draft
    except CVDraft.DoesNotExist as exc:
        raise NoDraftToFinalize("Apri prima l'editor per questo CV.") from exc

    user = job.user
    profile = user.profile
    context = render_context_from_draft(user, profile, draft.content_json)
    html, pdf_bytes, _page_count = render_cv(context)

    cv_document = CVDocument.objects.create(
        job=job,
        user=user,
        html_source=html,
        generation_type=CVDocument.GenerationType.MANUAL,
        content_json=draft.content_json,
    )
    cv_document.pdf_file.save(
        f"cv_{job.pk}_{cv_document.pk}.pdf", ContentFile(pdf_bytes), save=True
    )
    return cv_document
