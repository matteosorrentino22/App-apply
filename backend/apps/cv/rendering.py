from django.template.loader import render_to_string
from weasyprint import HTML

# Un solo livello, dimensione fissa (Sprint 52): prima c'erano 3 livelli che
# rimpicciolivano progressivamente il font se il CV superava 1 pagina —
# scelta esplicita del committente di non farlo più. Se il contenuto non
# entra in 1 pagina a questa dimensione, il ripiego resta solo quello già
# esistente in `generation.py` (rimozione del bullet meno rilevante,
# ri-renderizzato sempre a questa stessa dimensione): mai un font più
# piccolo, nel caso residuo si accetta un PDF multi-pagina.
COMPACT_LEVELS = [
    {"base_font_size": 9, "line_height": "1.25", "section_gap": "8pt", "heading_gap": "4pt", "item_gap": "6pt", "page_margin": "1cm", "photo_size": "65pt"},
]

# Stessa logica di COMPACT_LEVELS, senza `photo_size` (la cover letter non ha
# foto, Sprint 42) — contenuto tipicamente più corto del CV, ma stesso
# margine di sicurezza "1 pagina".
COVER_LETTER_COMPACT_LEVELS = [
    {"base_font_size": 10.5, "line_height": "1.4", "paragraph_gap": "10pt", "page_margin": "2.2cm"},
    {"base_font_size": 10, "line_height": "1.3", "paragraph_gap": "8pt", "page_margin": "1.8cm"},
    {"base_font_size": 9, "line_height": "1.25", "paragraph_gap": "6pt", "page_margin": "1.4cm"},
]


def _render_with_compact_retry(template_name, context, compact_levels):
    """Renderizza HTML e PDF, applicando progressivamente i livelli di
    compattamento finché il PDF risultante non entra in 1 pagina (o si
    esaurisce l'ultimo livello disponibile). Ritorna (html, pdf_bytes,
    page_count)."""
    html = None
    pdf_bytes = None
    page_count = None
    for level in compact_levels:
        html = render_to_string(template_name, {**context, **level})
        document = HTML(string=html).render()
        page_count = len(document.pages)
        pdf_bytes = document.write_pdf()
        if page_count <= 1:
            break
    return html, pdf_bytes, page_count


def render_cv(context):
    return _render_with_compact_retry("cv/cv_template.html", context, COMPACT_LEVELS)


def render_cover_letter(context):
    return _render_with_compact_retry(
        "cv/cover_letter_template.html", context, COVER_LETTER_COMPACT_LEVELS
    )
