# Editor interattivo del CV (Sprint 51): la bozza (`CVDraft`) parte sempre
# dall'ultimo `CVDocument` già generato (mai da zero — generare resta il
# compito di "Genera CV"/`generation.py`) e produce il PDF finale senza
# richiamare Claude né applicare taglio automatico al budget: le scelte di
# cosa mostrare sono già quelle dell'utente, fatte nell'editor.
# Sprint 69: la bozza ricorda il documento di riferimento
# (`source_document`); se nel frattempo è stato generato un CV più recente
# l'editor chiede se riseminare (`seed_draft_for_job`) o continuare
# (`keep_cv_draft`).
import copy

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.translation import gettext as _

from apps.profiles.language_options import LANGUAGE_LEVEL_LABELS, LANGUAGE_NAME_LABELS

from .cv_parameters import FALLBACK_CV_LANGUAGE, SUPPORTED_CV_LANGUAGES
from .draft_ids import ensure_cv_bullet_ids, normalize_cv_draft
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


def latest_cv_document(job):
    return job.cv_documents.order_by("-generated_at", "-id").first()


def load_cv_draft(job):
    """Bozza del job, normalizzata (id dei bullet) se salvata prima dello
    Sprint 69. Solleva `CVDraft.DoesNotExist`."""
    return normalize_cv_draft(CVDraft.objects.get(job=job))


def is_cv_draft_outdated(job, latest=None):
    """Vero se esiste una bozza e l'ultimo CV del job non è il suo documento
    di riferimento (es. "Rigenera CV" dopo l'apertura dell'editor)."""
    draft = CVDraft.objects.filter(job=job).only("source_document_id").first()
    if draft is None:
        return False
    latest = latest or latest_cv_document(job)
    return bool(latest and latest.content_json and latest.pk != draft.source_document_id)


def seed_draft_for_job(job):
    """Apre la bozza per `job` dall'ultimo CVDocument, o la risemina
    sovrascrivendo contenuto e chat (scelta "riparti dal nuovo documento")."""
    latest = latest_cv_document(job)
    if latest is None or not latest.content_json:
        raise NoCvDocumentToEdit(_("Genera prima un CV per questo job."))

    content = copy.deepcopy(latest.content_json)
    ensure_cv_bullet_ids(content)
    draft, _created = CVDraft.objects.update_or_create(
        job=job,
        defaults={
            "user": job.user,
            "content_json": content,
            "chat_history": [],
            "source_document": latest,
        },
    )
    return draft


def keep_cv_draft(job):
    """Scelta "continua la bozza": il CV più recente diventa il riferimento
    della bozza, che resta com'è (contenuto e chat)."""
    draft = load_cv_draft(job)
    latest = latest_cv_document(job)
    if latest is not None and latest.pk != draft.source_document_id:
        draft.source_document = latest
        draft.save(update_fields=["source_document", "updated_at"])
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
    """Rendering economico per la preview live nell'editor: stesso
    `render_cv` (dimensione fissa) della generazione, nessuna chiamata AI né
    loop di ripiego per overflow — se eccede 1 pagina lo si segnala
    (`page_count`), cosa tagliare resta una scelta dell'utente."""
    context = render_context_from_draft(user, profile, draft_content)
    _html, pdf_bytes, page_count = render_cv(context)
    return pdf_bytes, page_count


def finalize_cv_draft(job, content=None):
    """Produce il PDF finale a partire dalla bozza: stessa pipeline di
    rendering di `generate_cv`, ma senza richiamare Claude. Nessun consumo
    di quota/credito. `content` (Sprint 69, già validato): contenuto
    corrente dell'editor, salvato nella bozza prima del rendering — così le
    modifiche non ancora salvate dall'autosave non restano fuori. Il nuovo
    documento diventa il riferimento della bozza (nessun avviso "bozza
    superata" per un PDF nato dalla bozza stessa)."""
    try:
        draft = load_cv_draft(job)
    except CVDraft.DoesNotExist as exc:
        raise NoDraftToFinalize(_("Apri prima l'editor per questo CV.")) from exc

    if content is not None:
        draft.content_json = content
        draft.save(update_fields=["content_json", "updated_at"])

    user = job.user
    profile = user.profile
    context = render_context_from_draft(user, profile, draft.content_json)
    html, pdf_bytes, page_count = render_cv(context)

    with transaction.atomic():
        cv_document = CVDocument.objects.create(
            job=job,
            user=user,
            html_source=html,
            generation_type=CVDocument.GenerationType.MANUAL,
            content_json=draft.content_json,
            page_count=page_count,
        )
        cv_document.pdf_file.save("cv.pdf", ContentFile(pdf_bytes), save=True)
        draft.source_document = cv_document
        draft.save(update_fields=["source_document", "updated_at"])
    return cv_document
