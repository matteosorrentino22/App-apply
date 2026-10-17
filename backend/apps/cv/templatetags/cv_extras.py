import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

# Marcatore "**parola**" (Sprint 58): stesso formato prodotto da Claude in
# ai_content.py per il grassetto nei bullet delle esperienze, e stesso
# formato scritto manualmente dall'editor (RichBulletInput.jsx) quando
# l'utente seleziona testo e preme il pulsante/Ctrl+B — un solo filtro di
# rendering per entrambe le origini. Non greedy: marcatori non bilanciati
# (un solo "**" senza chiusura) restano semplicemente testo letterale.
_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")


@register.filter(name="bold_markup")
def bold_markup(text):
    """Converte i marcatori in <strong> reale, scappando il resto del testo
    come HTML normale: l'unico markup che questo filtro può produrre sono
    tag <strong> attorno a porzioni letterali del testo stesso, mai altro."""
    if not text:
        return ""
    pieces = []
    last_end = 0
    for match in _BOLD_PATTERN.finditer(text):
        pieces.append(escape(text[last_end : match.start()]))
        pieces.append("<strong>")
        pieces.append(escape(match.group(1)))
        pieces.append("</strong>")
        last_end = match.end()
    pieces.append(escape(text[last_end:]))
    return mark_safe("".join(pieces))
