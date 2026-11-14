# Validazione del content_json delle bozze (Sprint 66) in PATCH e preview:
# il frontend invia sempre l'intero contenuto, che finisce poi nel prompt
# della chat AI e nel rendering WeasyPrint. Senza controlli una bozza con
# migliaia di voci terrebbe occupato un worker per minuti, e chiavi
# mancanti o tipi errati producevano un 500. La forma è quella prodotta da
# apps.cv.generation.build_draft_content_json e da
# apps.cv.cover_letter_generation (chiavi sconosciute rifiutate).
import copy
import json

from django.utils.translation import gettext as _

from .draft_ids import ensure_cover_letter_paragraph_ids, ensure_cv_bullet_ids

MAX_DRAFT_JSON_CHARS = 200_000


class InvalidDraftContent(ValueError):
    pass


def _str(max_length):
    return ("str", max_length)


def _list(item, max_items):
    return ("list", item, max_items)


def _obj(fields):
    return ("obj", fields)


_BOOL = ("bool",)
_INT_OR_NULL = ("int_or_null",)

_CV_SPEC = _obj(
    {
        "summary": _str(5_000),
        "qualification": _str(300),
        "translated_city": _str(200),
        "content_language": _str(10),
        "areas_of_expertise": _list(_str(300), 20),
        "experiences": _list(
            _obj(
                {
                    "profile_experience_id": _INT_OR_NULL,
                    "company": _str(300),
                    "role": _str(300),
                    "location": _str(300),
                    "dates": _str(100),
                    "technologies": _list(_str(200), 50),
                    "shown": _BOOL,
                    "bullets": _list(
                        _obj({"id": _str(40), "text": _str(2_000), "shown": _BOOL}), 30
                    ),
                }
            ),
            30,
        ),
        "educations": _list(
            _obj(
                {
                    "institution": _str(300),
                    "title": _str(300),
                    "location": _str(300),
                    "dates": _str(100),
                    "notes": _str(3_000),
                }
            ),
            20,
        ),
        "skills": _list(_str(200), 100),
        "certifications": _list(_str(300), 50),
        "languages": _list(_obj({"language": _str(100), "level": _str(100)}), 30),
    }
)

_COVER_LETTER_SPEC = _obj(
    {
        "content_language": _str(10),
        "translated_city": _str(200),
        "paragraphs": _list(_obj({"id": _str(40), "text": _str(3_000)}), 15),
    }
)


def _check(value, spec, path):
    kind = spec[0]
    if kind == "str":
        if not isinstance(value, str):
            raise InvalidDraftContent(_("%(path)s: deve essere un testo.") % {"path": path})
        if len(value) > spec[1]:
            raise InvalidDraftContent(_("%(path)s: massimo %(max)s caratteri.") % {"path": path, "max": spec[1]})
    elif kind == "bool":
        if not isinstance(value, bool):
            raise InvalidDraftContent(_("%(path)s: deve essere vero/falso.") % {"path": path})
    elif kind == "int_or_null":
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise InvalidDraftContent(_("%(path)s: deve essere un numero intero.") % {"path": path})
    elif kind == "list":
        if not isinstance(value, list):
            raise InvalidDraftContent(_("%(path)s: deve essere una lista.") % {"path": path})
        if len(value) > spec[2]:
            raise InvalidDraftContent(_("%(path)s: massimo %(max)s elementi.") % {"path": path, "max": spec[2]})
        for index, item in enumerate(value):
            _check(item, spec[1], f"{path}[{index}]")
    elif kind == "obj":
        if not isinstance(value, dict):
            raise InvalidDraftContent(_("%(path)s: formato non valido.") % {"path": path or _("contenuto")})
        fields = spec[1]
        unknown = set(value) - set(fields)
        missing = set(fields) - set(value)
        if unknown or missing:
            raise InvalidDraftContent(_("%(path)s: campi non validi.") % {"path": path or _("contenuto")})
        for name, field_spec in fields.items():
            _check(value[name], field_spec, f"{path}.{name}" if path else name)


def _validate(content, spec):
    if not isinstance(content, dict):
        raise InvalidDraftContent(_("Formato non valido."))
    if len(json.dumps(content, ensure_ascii=False)) > MAX_DRAFT_JSON_CHARS:
        raise InvalidDraftContent(_("Contenuto troppo grande."))
    _check(content, spec, "")


def validate_cv_draft_content(content):
    _validate(content, _CV_SPEC)


def validate_cover_letter_draft_content(content):
    _validate(content, _COVER_LETTER_SPEC)


# Sprint 69: prima della validazione si assegnano gli id stabili mancanti
# (bullet aggiunti da una scheda aperta prima dell'aggiornamento, paragrafi
# ancora come stringhe), su una copia del dato ricevuto.
def clean_cv_draft_content(data):
    content = copy.deepcopy(data)
    ensure_cv_bullet_ids(content)
    validate_cv_draft_content(content)
    return content


def clean_cover_letter_draft_content(data):
    content = copy.deepcopy(data)
    ensure_cover_letter_paragraph_ids(content)
    validate_cover_letter_draft_content(content)
    return content
