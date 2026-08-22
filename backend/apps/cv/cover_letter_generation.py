from django.core.files.base import ContentFile

from .cover_letter_content import COVER_LETTER_LABELS, generate_cover_letter_content
from .generation import _build_full_name, _format_location, _resolve_html_lang
from .models import CoverLetterDocument
from .rendering import render_cover_letter


def _build_contact_line(profile, translated_city):
    """Riga di contatti della lettera: Città, PAESE | telefono | email —
    niente LinkedIn (Sprint 42, a differenza del CV): una cover letter è più
    personale/discorsiva, il link va già nel CV allegato alla stessa
    candidatura."""
    parts = [
        _format_location(translated_city, profile.country_code),
        profile.phone,
        profile.email,
    ]
    return " | ".join(part for part in parts if part)


def generate_cover_letter(job, instructions=""):
    """Genera una cover letter per `job` sul profilo del suo utente (Sprint
    42): contenuti via Claude (paragrafi del corpo, città tradotta, lingua
    rilevata), oggetto/saluto/chiusura fissi per lingua, composizione HTML,
    conversione PDF con WeasyPrint (con loop di ripiego per overflow),
    salvataggio in `CoverLetterDocument`. Nessuna selezione/taglio lato
    server: a differenza del CV, il contenuto è già breve per costruzione
    (Docs prompt, 3-5 paragrafi).

    Solleva l'eccezione a chi chiama in caso di fallimento (chiamata Claude,
    rendering): la gestione (guardia di concorrenza, quota/credito, RunLog)
    è responsabilità di chi orchestra la generazione, non di questo
    servizio riusabile — stesso principio di `generation.generate_cv`."""
    user = job.user
    profile = user.profile

    content = generate_cover_letter_content(profile, job, user.cv_language_mode, instructions)
    html_lang = _resolve_html_lang(user, content)
    labels = COVER_LETTER_LABELS[html_lang]
    full_name = _build_full_name(user)

    context = {
        "html_lang": html_lang,
        "full_name": full_name,
        "contact_line": _build_contact_line(profile, content["translated_city"]),
        "subject_line": labels["subject_template"].format(title=job.title, company=job.company),
        "salutation": labels["salutation"],
        "paragraphs": content["paragraphs"],
        "closing": labels["closing"],
    }
    html, pdf_bytes, _page_count = render_cover_letter(context)

    document = CoverLetterDocument.objects.create(
        job=job, user=user, html_source=html, instructions_used=instructions
    )
    document.pdf_file.save(
        f"cover_letter_{job.pk}_{document.pk}.pdf", ContentFile(pdf_bytes), save=True
    )
    return document
