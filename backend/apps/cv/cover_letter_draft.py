# Editor interattivo della cover letter (Sprint 63): mirror di
# apps.cv.draft, molto più semplice — niente esperienze/bullet/skill da
# riflettere nel content_json, solo un elenco di paragrafi. La bozza parte
# sempre dall'ultima `CoverLetterDocument` già generata (mai da zero) e
# produce il PDF finale senza richiamare Claude.
from django.core.files.base import ContentFile

from .cover_letter_content import COVER_LETTER_LABELS
from .cover_letter_generation import _build_contact_line
from .cv_parameters import FALLBACK_CV_LANGUAGE, SUPPORTED_CV_LANGUAGES
from .generation import _build_full_name
from .models import CoverLetterDocument, CoverLetterDraft
from .rendering import render_cover_letter


class NoCoverLetterDocumentToEdit(Exception):
    """Nessuna CoverLetterDocument esistente da cui aprire un draft per
    questo job."""


class NoCoverLetterDraftToFinalize(Exception):
    """Nessuna bozza in corso per questo job: va aperta prima con
    `seed_cover_letter_draft_for_job` (pulsante "Modifica Cover Letter")."""


def seed_cover_letter_draft_for_job(job):
    """Apre (o riapre, sovrascrivendo) la bozza per `job`, a partire
    dall'ultima CoverLetterDocument generata."""
    latest = job.cover_letter_documents.order_by("-generated_at", "-id").first()
    if latest is None or not latest.content_json:
        raise NoCoverLetterDocumentToEdit("Genera prima una cover letter per questo job.")

    draft, _created = CoverLetterDraft.objects.update_or_create(
        job=job,
        defaults={"user": job.user, "content_json": latest.content_json},
    )
    return draft


def render_context_from_cover_letter_draft(user, profile, job, draft_content):
    """Contesto di rendering a partire dal contenuto già deciso
    dall'utente nell'editor — oggetto/saluto/chiusura restano quelli fissi
    per lingua (mai editabili), solo i paragrafi sono quelli della bozza."""
    html_lang = draft_content.get("content_language")
    if html_lang not in SUPPORTED_CV_LANGUAGES:
        html_lang = FALLBACK_CV_LANGUAGE
    labels = COVER_LETTER_LABELS[html_lang]

    return {
        "html_lang": html_lang,
        "full_name": _build_full_name(user),
        "contact_line": _build_contact_line(profile, draft_content["translated_city"]),
        "subject_line": labels["subject_template"].format(title=job.title, company=job.company),
        "salutation": labels["salutation"],
        "paragraphs": draft_content["paragraphs"],
        "closing": labels["closing"],
    }


def render_cover_letter_draft_preview(user, profile, job, draft_content):
    """Rendering economico per la preview live nell'editor: stessi 3
    livelli di compattamento già usati dalla generazione, nessuna chiamata
    AI."""
    context = render_context_from_cover_letter_draft(user, profile, job, draft_content)
    _html, pdf_bytes, page_count = render_cover_letter(context)
    return pdf_bytes, page_count


def finalize_cover_letter_draft(job):
    """Produce il PDF finale a partire dal draft corrente: stessa pipeline
    di rendering della generazione, ma senza richiamare Claude. Nessun
    consumo di quota/credito: non è una nuova generazione AI."""
    try:
        draft = job.cover_letter_draft
    except CoverLetterDraft.DoesNotExist as exc:
        raise NoCoverLetterDraftToFinalize("Apri prima l'editor per questa cover letter.") from exc

    user = job.user
    profile = user.profile
    context = render_context_from_cover_letter_draft(user, profile, job, draft.content_json)
    html, pdf_bytes, _page_count = render_cover_letter(context)

    document = CoverLetterDocument.objects.create(
        job=job,
        user=user,
        html_source=html,
        content_json=draft.content_json,
    )
    document.pdf_file.save(
        f"cover_letter_{job.pk}_{document.pk}.pdf", ContentFile(pdf_bytes), save=True
    )
    return document
