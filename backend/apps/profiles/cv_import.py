import zipfile

import docx
import pdfplumber
from django.conf import settings

from apps.common.ai import call_claude_structured

from .language_options import LANGUAGE_CHOICES, LANGUAGE_LEVEL_CHOICES

# Sotto questa soglia il testo estratto è considerato "vuoto o irrisorio"
# (tipico dei PDF scansione/immagine) — si interrompe senza chiamare Claude
# (02-specifiche-tecniche-v3.md §3.5, §5.4).
MIN_TEXT_LENGTH = 40

# Limiti dell'import (Sprint 66): il parsing gira nel worker gunicorn della
# richiesta e il testo finisce intero nel prompt di Claude.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10
MAX_DOCX_UNCOMPRESSED_BYTES = 30 * 1024 * 1024
MAX_TEXT_LENGTH = 30_000

_LANGUAGE_CODES = [code for code, _ in LANGUAGE_CHOICES]
_LEVEL_CODES = [code for code, _ in LANGUAGE_LEVEL_CHOICES]

STRUCTURING_SYSTEM_PROMPT = (
    "Riorganizzi il testo grezzo di un CV nelle sezioni del profilo master di "
    "un'app di ricerca lavoro: sommario professionale, esperienze, istruzione, "
    "competenze, certificazioni, lingue. Non inventare competenze, esperienze "
    "o dati non presenti nel testo. Se una sezione non è presente nel testo, "
    "restituiscila vuota (stringa vuota o lista vuota). Le date di istruzione "
    "ed esperienza vanno restituite in formato ISO (YYYY-MM-DD); se il testo "
    "riporta solo mese/anno, usa il primo giorno del mese; se manca del tutto "
    "una data di fine istruzione ricavabile dal testo, restituisci null.\n\n"
    "CONTATTI ('phone', 'email'): estrai il numero di telefono e l'indirizzo "
    "email SOLO se scritti letteralmente nel testo del CV (mai inventarli, "
    "mai usare altri dati); restituisci stringa vuota se assenti.\n\n"
    "LINGUE ('languages'): per ciascuna lingua individuata nel testo (in "
    "qualunque lingua/grafia sia scritta nel CV originale, es. 'Italiano', "
    "'Anglais', 'Deutsch (Muttersprache)'), restituisci 'language' come "
    "codice ISO a due lettere tra quelli elencati nello schema e 'level' "
    "mappandolo al più vicino tra i 4 livelli previsti nello schema — "
    "mappa scale diverse a quei 4 livelli (es. CEFR A1/A2 → 'elementary', "
    "B1/B2 → 'intermediate', C1 → 'fluent', C2/'nativo'/'madrelingua'/"
    "'native' → 'mother_tongue'). Se una lingua o un livello nel testo non "
    "è riconducibile con sufficiente certezza a un codice ammesso, ometti "
    "quella voce piuttosto che indovinare."
)

PROFILE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "phone": {"type": "string"},
        "email": {"type": "string"},
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "role": {"type": "string"},
                    "location": {"type": "string"},
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "technologies": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "company",
                    "role",
                    "location",
                    "start_date",
                    "end_date",
                    "bullets",
                    "technologies",
                ],
                "additionalProperties": False,
            },
        },
        "educations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "title": {"type": "string"},
                    "location": {"type": "string"},
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]},
                    "notes": {"type": "string"},
                },
                "required": [
                    "institution",
                    "title",
                    "location",
                    "start_date",
                    "end_date",
                    "notes",
                ],
                "additionalProperties": False,
            },
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        "certifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "enum": _LANGUAGE_CODES},
                    "level": {"type": "string", "enum": _LEVEL_CODES},
                },
                "required": ["language", "level"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "summary",
        "phone",
        "email",
        "experiences",
        "educations",
        "skills",
        "certifications",
        "languages",
    ],
    "additionalProperties": False,
}


class CVUnreadableError(Exception):
    """File non decodificabile dalla libreria di estrazione (es. PDF corrotto)."""


def extract_text(uploaded_file):
    """Estrae il testo grezzo da un CV PDF o .docx (nessun invio del file a
    Claude), troncato a MAX_TEXT_LENGTH. Il formato si decide dai primi byte
    del file, non dal nome o dal content-type dichiarati dal client. Solleva
    ValueError per file non ammessi (formato, dimensione, pagine)."""
    if uploaded_file.size is not None and uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValueError("Il file non può superare i 5 MB.")
    uploaded_file.seek(0)
    header = uploaded_file.read(5)
    uploaded_file.seek(0)

    if header.startswith(b"%PDF-"):
        text = _extract_pdf_text(uploaded_file)
    elif header.startswith(b"PK\x03\x04"):
        text = _extract_docx_text(uploaded_file)
    else:
        raise ValueError("Formato non supportato: solo PDF e Word (.docx) sono accettati.")
    return text[:MAX_TEXT_LENGTH]


class _TooManyPages(Exception):
    pass


def _extract_pdf_text(uploaded_file):
    try:
        text_parts = []
        with pdfplumber.open(uploaded_file) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise _TooManyPages
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except _TooManyPages as exc:
        raise ValueError(f"Il CV non può superare le {MAX_PDF_PAGES} pagine.") from exc
    except Exception as exc:
        raise CVUnreadableError(str(exc)) from exc


def _extract_docx_text(uploaded_file):
    try:
        with zipfile.ZipFile(uploaded_file) as archive:
            uncompressed = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile as exc:
        raise CVUnreadableError(str(exc)) from exc
    if uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
        raise ValueError("Il file Word è troppo grande.")
    uploaded_file.seek(0)
    try:
        document = docx.Document(uploaded_file)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise CVUnreadableError(str(exc)) from exc


def has_sufficient_text(text):
    return len(text.strip()) >= MIN_TEXT_LENGTH


def structure_with_claude(raw_text):
    """Passa a Claude solo il testo estratto (mai il file binario) per la strutturazione."""
    return call_claude_structured(
        model=settings.BEDROCK_CV_PARSING_MODEL,
        system=STRUCTURING_SYSTEM_PROMPT,
        user_content=raw_text,
        schema=PROFILE_JSON_SCHEMA,
        max_tokens=8000,
        effort="medium",
    )
