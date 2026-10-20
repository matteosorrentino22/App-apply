# Chat di assistenza nell'editor della cover letter (Sprint 63): mirror di
# apps.cv.draft_chat, molto più semplice — solo paragrafi, niente
# skills/certifications da proteggere con un filtro difensivo (non esiste
# un elenco "disponibile" da cui scegliere, qui è tutto testo narrativo).
import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.ai import call_claude_structured
from apps.jobs.models import RunLog

from .ai_content import _build_profile_context
from .models import CoverLetterDraft

CHAT_ACTION_TYPES = ["update_paragraph", "add_paragraph", "remove_paragraph"]

CHAT_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": CHAT_ACTION_TYPES},
        "paragraph_index": {"type": ["integer", "null"]},
        "text": {"type": ["string", "null"]},
    },
    "required": ["type", "paragraph_index", "text"],
    "additionalProperties": False,
}

CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "actions": {"type": "array", "items": CHAT_ACTION_SCHEMA},
    },
    "required": ["reply", "actions"],
    "additionalProperties": False,
}

CHAT_SYSTEM_PROMPT = (
    "Sei l'assistente della bozza di una cover letter già generata, dentro "
    "un editor interattivo: l'utente ti scrive in linguaggio naturale cosa "
    "vorrebbe cambiare, tu rispondi con un breve messaggio ('reply') e un "
    "elenco ('actions', può essere vuoto) di modifiche puntuali proposte — "
    "non applichi mai nulla direttamente, è l'utente che accetta o "
    "rifiuta ogni singola azione nell'interfaccia. Se il messaggio "
    "dell'utente è solo una domanda o un dubbio, rispondi senza produrre "
    "azioni.\n\n"
    "GROUNDING: per ogni affermazione professionale puoi amplificare o "
    "estendere il contenuto oltre quanto letteralmente scritto nel "
    "profilo SOLO se l'utente te lo chiede esplicitamente in questo "
    "messaggio o in uno precedente della conversazione — mai di tua "
    "iniziativa. Se lo fai, segnalalo con naturalezza nel tuo 'reply' "
    "(es. 'ho aggiunto questo dettaglio come richiesto, verifica che sia "
    "accurato'). Resta comunque vietato, anche su richiesta, inventare "
    "un'azienda, un ruolo o un risultato che il candidato non ha mai "
    "avuto.\n\n"
    "AZIONI (campo 'type', gli altri campi non pertinenti restano null):\n"
    "- update_paragraph: 'paragraph_index' (posizione nell'elenco "
    "paragrafi, come fornito sotto, a partire da 0) + 'text' = nuovo "
    "contenuto del paragrafo.\n"
    "- add_paragraph: 'text' = nuovo paragrafo, aggiunto in coda "
    "all'elenco (l'utente può poi riordinarlo manualmente nell'editor).\n"
    "- remove_paragraph: 'paragraph_index'.\n\n"
    "Non scrivere mai oggetto, saluto iniziale o formula di chiusura: non "
    "fanno parte dei paragrafi editabili, sono gestiti fuori da questa "
    "chat."
)


def _build_user_content(draft, job, profile, chat_history, user_message):
    profile_context = _build_profile_context(profile)
    history_lines = [{"role": turn["role"], "message": turn["message"]} for turn in chat_history]
    return (
        f"BOZZA COVER LETTER ATTUALE (JSON, solo paragrafi editabili):\n"
        f"{json.dumps(draft.content_json, ensure_ascii=False)}\n\n"
        f"PROFILO CANDIDATO (JSON, per il grounding):\n"
        f"{json.dumps(profile_context, ensure_ascii=False)}\n\n"
        f"OFFERTA:\nTitolo: {job.title}\nAzienda: {job.company}\n"
        f"Descrizione: {job.description}\n\n"
        f"CRONOLOGIA DELLA CONVERSAZIONE (dalla più vecchia):\n"
        f"{json.dumps(history_lines, ensure_ascii=False)}\n\n"
        f"NUOVO MESSAGGIO DELL'UTENTE:\n{user_message}"
    )


def _sanitize_actions(actions, paragraph_count):
    """Scarta azioni con indice fuori dall'elenco paragrafi corrente —
    difesa minima contro un indice inventato dal modello, qui non serve
    altro filtro di grounding (nessun elenco 'disponibile' da proteggere,
    a differenza di skills/certifications nel CV)."""
    sanitized = []
    for action in actions:
        if action["type"] in ("update_paragraph", "remove_paragraph"):
            index = action.get("paragraph_index")
            if not isinstance(index, int) or index < 0 or index >= paragraph_count:
                continue
        sanitized.append(action)
    return sanitized


class ChatMessageRejected(Exception):
    """Credito insufficiente: nessun consumo, nessuna chiamata AI."""


class ChatMessageFailed(Exception):
    """La chiamata AI è fallita: il credito riservato è già stato restituito."""


def _reserve_credit(user):
    with transaction.atomic():
        locked_user = type(user).objects.select_for_update().get(pk=user.pk)
        price = settings.PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE
        if locked_user.extra_credit < price:
            raise ChatMessageRejected("Saldo credito insufficiente per questo messaggio.")
        locked_user.extra_credit -= price
        locked_user.save(update_fields=["extra_credit"])


def _refund_credit(user):
    with transaction.atomic():
        locked_user = type(user).objects.select_for_update().get(pk=user.pk)
        locked_user.extra_credit += settings.PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE
        locked_user.save(update_fields=["extra_credit"])


def send_chat_message(job, user_message):
    """Punto d'ingresso della chat (Sprint 63): riserva il credito del
    messaggio, chiama Claude con la bozza corrente come contesto, applica
    il filtro difensivo sugli indici, e accoda sia il messaggio
    dell'utente sia la risposta alla cronologia persistita nel draft.
    Nessuna modifica al `content_json` del draft: resta compito del
    frontend applicare le azioni che l'utente accetta, con un PATCH
    separato (`CoverLetterDraftView`)."""
    try:
        draft = job.cover_letter_draft
    except CoverLetterDraft.DoesNotExist as exc:
        raise ChatMessageFailed("Apri prima l'editor per questa cover letter.") from exc

    user = job.user
    profile = user.profile
    _reserve_credit(user)
    started_at = timezone.now()

    try:
        result = call_claude_structured(
            model=settings.BEDROCK_CV_GENERATION_MODEL,
            system=CHAT_SYSTEM_PROMPT,
            user_content=_build_user_content(draft, job, profile, draft.chat_history, user_message),
            schema=CHAT_SCHEMA,
            max_tokens=2000,
            effort="medium",
        )
    except Exception as exc:
        _refund_credit(user)
        RunLog.objects.create(
            user=user,
            job=job,
            task_type=RunLog.TaskType.COVER_LETTER_DRAFT_CHAT,
            status=RunLog.Status.FAILURE,
            message=str(exc),
            started_at=started_at,
            finished_at=timezone.now(),
        )
        raise ChatMessageFailed("L'assistente non è riuscito a rispondere.") from exc

    actions = _sanitize_actions(result["actions"], len(draft.content_json.get("paragraphs", [])))
    draft.chat_history = draft.chat_history + [
        {"role": "user", "message": user_message},
        {"role": "assistant", "message": result["reply"], "actions": actions},
    ]
    draft.save(update_fields=["chat_history", "updated_at"])
    return result["reply"], actions


class InvalidChatDecision(Exception):
    """Indici fuori range o decisione non valida: nessuna scrittura."""


def record_action_decision(job, message_index, action_index, decision):
    """Persiste la scelta (accetta/rifiuta) di una singola azione proposta
    (stesso principio di apps.cv.draft_chat, Sprint 62/63): senza questo
    la scelta vivrebbe solo nello stato locale del pannello, perdendosi
    chiudendo/riaprendo la chat o ricaricando la pagina."""
    if decision not in ("accepted", "rejected"):
        raise InvalidChatDecision("Decisione non valida.")
    try:
        draft = job.cover_letter_draft
    except CoverLetterDraft.DoesNotExist as exc:
        raise InvalidChatDecision("Nessuna bozza per questo job.") from exc

    history = draft.chat_history
    if (
        message_index < 0
        or message_index >= len(history)
        or history[message_index].get("role") != "assistant"
    ):
        raise InvalidChatDecision("Messaggio non valido.")
    actions = history[message_index].get("actions") or []
    if action_index < 0 or action_index >= len(actions):
        raise InvalidChatDecision("Azione non valida.")

    actions[action_index]["decision"] = decision
    draft.save(update_fields=["chat_history", "updated_at"])
