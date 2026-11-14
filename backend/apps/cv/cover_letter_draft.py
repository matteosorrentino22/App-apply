# Editor interattivo della cover letter (Sprint 63): mirror di
# apps.cv.draft, molto più semplice — niente esperienze/bullet/skill da
# riflettere nel content_json, solo un elenco di paragrafi. La bozza parte
# sempre dall'ultima `CoverLetterDocument` già generata (mai da zero) e
# produce il PDF finale senza richiamare Claude. Riseminatura e "continua
# la bozza" come per il CV (Sprint 69, vedi apps.cv.draft).
import copy

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.translation import gettext as _

from .cover_letter_content import COVER_LETTER_LABELS
from .cover_letter_generation import _build_contact_line
from .cv_parameters import FALLBACK_CV_LANGUAGE, SUPPORTED_CV_LANGUAGES
from .draft_ids import (
    ensure_cover_letter_paragraph_ids,
    normalize_cover_letter_draft,
    paragraph_texts,
)
from .generation import _build_full_name
from .models import CoverLetterDocument, CoverLetterDraft
from .rendering import render_cover_letter


class NoCoverLetterDocumentToEdit(Exception):
    """Nessuna CoverLetterDocument esistente da cui aprire un draft per
    questo job."""


class NoCoverLetterDraftToFinalize(Exception):
    """Nessuna bozza in corso per questo job: va aperta prima con
    `seed_cover_letter_draft_for_job` (pulsante "Modifica Cover Letter")."""


def latest_cover_letter_document(job):
    return job.cover_letter_documents.order_by("-generated_at", "-id").first()


def load_cover_letter_draft(job):
    """Bozza del job, normalizzata (paragrafi `{id, text}`) se salvata prima
    dello Sprint 69. Solleva `CoverLetterDraft.DoesNotExist`."""
    return normalize_cover_letter_draft(CoverLetterDraft.objects.get(job=job))


def is_cover_letter_draft_outdated(job, latest=None):
    draft = CoverLetterDraft.objects.filter(job=job).only("source_document_id").first()
    if draft is None:
        return False
    latest = latest or latest_cover_letter_document(job)
    return bool(latest and latest.content_json and latest.pk != draft.source_document_id)


def seed_cover_letter_draft_for_job(job):
    """Apre la bozza per `job` dall'ultima CoverLetterDocument, o la
    risemina sovrascrivendo contenuto e chat."""
    latest = latest_cover_letter_document(job)
    if latest is None or not latest.content_json:
        raise NoCoverLetterDocumentToEdit(_("Genera prima una cover letter per questo job."))

    content = copy.deepcopy(latest.content_json)
    ensure_cover_letter_paragraph_ids(content)
    draft, _created = CoverLetterDraft.objects.update_or_create(
        job=job,
        defaults={
            "user": job.user,
            "content_json": content,
            "chat_history": [],
            "source_document": latest,
        },
    )
    return draft


def keep_cover_letter_draft(job):
    draft = load_cover_letter_draft(job)
    latest = latest_cover_letter_document(job)
    if latest is not None and latest.pk != draft.source_document_id:
        draft.source_document = latest
        draft.save(update_fields=["source_document", "updated_at"])
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
        "paragraphs": paragraph_texts(draft_content["paragraphs"]),
        "closing": labels["closing"],
    }


def render_cover_letter_draft_preview(user, profile, job, draft_content):
    """Rendering economico per la preview live nell'editor: stessi 3
    livelli di compattamento già usati dalla generazione, nessuna chiamata
    AI."""
    context = render_context_from_cover_letter_draft(user, profile, job, draft_content)
    _html, pdf_bytes, page_count = render_cover_letter(context)
    return pdf_bytes, page_count


def finalize_cover_letter_draft(job, content=None):
    """Produce il PDF finale a partire dalla bozza: stessa pipeline di
    rendering della generazione, ma senza richiamare Claude. Nessun consumo
    di quota/credito. `content` come in `apps.cv.draft.finalize_cv_draft`."""
    try:
        draft = load_cover_letter_draft(job)
    except CoverLetterDraft.DoesNotExist as exc:
        raise NoCoverLetterDraftToFinalize(_("Apri prima l'editor per questa cover letter.")) from exc

    if content is not None:
        draft.content_json = content
        draft.save(update_fields=["content_json", "updated_at"])

    user = job.user
    profile = user.profile
    context = render_context_from_cover_letter_draft(user, profile, job, draft.content_json)
    html, pdf_bytes, page_count = render_cover_letter(context)

    with transaction.atomic():
        document = CoverLetterDocument.objects.create(
            job=job,
            user=user,
            html_source=html,
            content_json=draft.content_json,
            page_count=page_count,
        )
        document.pdf_file.save("cover_letter.pdf", ContentFile(pdf_bytes), save=True)
        draft.source_document = document
        draft.save(update_fields=["source_document", "updated_at"])
    return document
