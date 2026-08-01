import json

import docx
import pdfplumber
from anthropic import Anthropic
from django.conf import settings

DOCX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Sotto questa soglia il testo estratto è considerato "vuoto o irrisorio"
# (tipico dei PDF scansione/immagine) — si interrompe senza chiamare Claude
# (02-specifiche-tecniche-v3.md §3.5, §5.4).
MIN_TEXT_LENGTH = 40

STRUCTURING_SYSTEM_PROMPT = (
    "Riorganizzi il testo grezzo di un CV nelle sezioni del profilo master di "
    "un'app di ricerca lavoro: sommario professionale, esperienze, istruzione, "
    "competenze, certificazioni, lingue. Non inventare competenze, esperienze "
    "o dati non presenti nel testo. Se una sezione non è presente nel testo, "
    "restituiscila vuota (stringa vuota o lista vuota). Le date di istruzione "
    "ed esperienza vanno restituite in formato ISO (YYYY-MM-DD); se il testo "
    "riporta solo mese/anno, usa il primo giorno del mese; se manca del tutto "
    "una data di fine istruzione ricavabile dal testo, restituisci null."
)

PROFILE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
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
                    "language": {"type": "string"},
                    "level": {"type": "string"},
                },
                "required": ["language", "level"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "summary",
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
    """Estrae il testo grezzo da un CV PDF o .docx (nessun invio del file a Claude)."""
    name = (uploaded_file.name or "").lower()
    content_type = getattr(uploaded_file, "content_type", "") or ""

    if content_type == "application/pdf" or name.endswith(".pdf"):
        return _extract_pdf_text(uploaded_file)
    if content_type in DOCX_CONTENT_TYPES or name.endswith(".docx"):
        return _extract_docx_text(uploaded_file)
    raise ValueError("Formato non supportato: solo PDF e Word (.docx) sono accettati.")


def _extract_pdf_text(uploaded_file):
    try:
        text_parts = []
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception as exc:
        raise CVUnreadableError(str(exc)) from exc


def _extract_docx_text(uploaded_file):
    try:
        document = docx.Document(uploaded_file)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise CVUnreadableError(str(exc)) from exc


def has_sufficient_text(text):
    return len(text.strip()) >= MIN_TEXT_LENGTH


def structure_with_claude(raw_text):
    """Passa a Claude solo il testo estratto (mai il file binario) per la strutturazione."""
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.ANTHROPIC_CV_PARSING_MODEL,
        max_tokens=8000,
        thinking={"type": "disabled"},
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": PROFILE_JSON_SCHEMA},
        },
        system=STRUCTURING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_text}],
    )
    text_block = next(block.text for block in response.content if block.type == "text")
    return json.loads(text_block)
