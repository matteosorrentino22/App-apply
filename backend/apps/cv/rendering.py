from django.template.loader import render_to_string
from weasyprint import HTML

# Livelli di compattamento CSS applicati in ordine finché il PDF risultante
# non entra in 1 pagina (02-specifiche-tecniche-v3.md §6.2 punto 4): il
# template è già progettato per starci con un profilo di dimensioni standard,
# questo è solo un margine di sicurezza per profili più ricchi della norma.
COMPACT_LEVELS = [
    {"base_font_size": 9, "line_height": "1.25", "section_gap": "9pt", "heading_gap": "4pt", "item_gap": "7pt", "page_margin": "1.4cm", "photo_size": "65pt"},
    {"base_font_size": 8, "line_height": "1.15", "section_gap": "6pt", "heading_gap": "3pt", "item_gap": "5pt", "page_margin": "1.1cm", "photo_size": "55pt"},
    {"base_font_size": 7, "line_height": "1.1", "section_gap": "4pt", "heading_gap": "2pt", "item_gap": "3pt", "page_margin": "0.9cm", "photo_size": "45pt"},
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
