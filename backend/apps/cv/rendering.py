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


def render_cv(context):
    """Renderizza HTML e PDF, applicando progressivamente i livelli di
    compattamento finché il PDF non entra in 1 pagina (o si esaurisce
    l'ultimo livello disponibile). Ritorna (html, pdf_bytes, page_count)."""
    html = None
    pdf_bytes = None
    page_count = None
    for level in COMPACT_LEVELS:
        html = render_to_string("cv/cv_template.html", {**context, **level})
        document = HTML(string=html).render()
        page_count = len(document.pages)
        pdf_bytes = document.write_pdf()
        if page_count <= 1:
            break
    return html, pdf_bytes, page_count
