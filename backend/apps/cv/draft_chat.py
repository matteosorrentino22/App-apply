"""Chat di assistenza nell'editor interattivo del CV (Sprint 59, Fase 2):
l'utente scrive un'istruzione in linguaggio naturale, Claude propone una o
più modifiche puntuali alla bozza — non le applica mai da solo. Il
frontend mostra ogni modifica come una card "prima → dopo" con
Accetta/Rifiuta; solo quando l'utente accetta, la modifica viene scritta
nel `content_json` del draft (stesse funzioni di stato già usate
dall'editor manuale di Fase 1 — vedi CvDraftEditorPage.jsx)."""

import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.ai import call_claude_structured
from apps.jobs.models import RunLog

from .models import CVDraft

# Un'azione per ogni singolo campo modificabile del draft (stessa forma di
# `apps.cv.generation.build_draft_content_json`): struttura "piatta" con un
# solo oggetto e un campo `type` a dire quali altri campi contano — niente
# `oneOf`/union nello schema, per restare nei limiti di compatibilità del
# tool-use forzato su Bedrock già documentati in `apps.common.ai`.
CHAT_ACTION_TYPES = [
    "update_summary",
    "update_qualification",
    "update_role",
    "update_bullet",
    "add_bullet",
    "hide_bullet",
    "show_bullet",
    "hide_experience",
    "show_experience",
    "update_area",
    "add_area",
    "remove_area",
    "toggle_skill",
    "toggle_certification",
    "update_education_notes",
    "update_language_level",
]

LANGUAGE_LEVEL_CODES = ["elementary", "intermediate", "fluent", "mother_tongue"]

CHAT_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": CHAT_ACTION_TYPES},
        "profile_experience_id": {"type": ["integer", "null"]},
        "bullet_index": {"type": ["integer", "null"]},
        "area_index": {"type": ["integer", "null"]},
        "education_index": {"type": ["integer", "null"]},
        "language_index": {"type": ["integer", "null"]},
        "text": {"type": ["string", "null"]},
        "name": {"type": ["string", "null"]},
        "level": {"type": ["string", "null"], "enum": LANGUAGE_LEVEL_CODES + [None]},
    },
    "required": [
        "type",
        "profile_experience_id",
        "bullet_index",
        "area_index",
        "education_index",
        "language_index",
        "text",
        "name",
        "level",
    ],
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
    "Sei l'assistente della bozza di un CV già generato, dentro un editor "
    "interattivo: l'utente ti scrive in linguaggio naturale cosa vorrebbe "
    "cambiare, tu rispondi con un breve messaggio ('reply') e un elenco "
    "('actions', può essere vuoto) di modifiche puntuali proposte — non "
    "applichi mai nulla direttamente, è l'utente che accetta o rifiuta "
    "ogni singola azione nell'interfaccia. Se il messaggio dell'utente è "
    "solo una domanda o un dubbio, rispondi senza produrre azioni.\n\n"
    "GROUNDING: per il testo narrativo (sommario, qualifica, ruolo, bullet "
    "delle esperienze, note di istruzione) puoi amplificare o estendere il "
    "contenuto oltre quanto letteralmente scritto nel profilo SOLO se "
    "l'utente te lo chiede esplicitamente in questo messaggio o in uno "
    "precedente della conversazione — mai di tua iniziativa. Se lo fai, "
    "segnalalo con naturalezza nel tuo 'reply' (es. 'ho aggiunto questo "
    "dettaglio come richiesto, verifica che sia accurato'). Per "
    "'toggle_skill'/'toggle_certification' invece NESSUNA eccezione è "
    "ammessa: 'name' deve corrispondere esattamente a una voce tra quelle "
    "elencate in 'SKILLS DISPONIBILI'/'CERTIFICATIONS DISPONIBILI' qui "
    "sotto (il profilo reale del candidato) — non puoi mai introdurne una "
    "nuova, nemmeno su richiesta esplicita.\n\n"
    "AZIONI (campo 'type', gli altri campi dell'azione non pertinenti al "
    "tipo restano null):\n"
    "- update_summary/update_qualification: 'text' = nuovo contenuto.\n"
    "- update_role: 'profile_experience_id' + 'text' = nuovo ruolo.\n"
    "- update_bullet: 'profile_experience_id' + 'bullet_index' (posizione "
    "nell'elenco bullet di quell'esperienza, come fornito sotto) + 'text'.\n"
    "- add_bullet: 'profile_experience_id' + 'text' (nuovo bullet, aggiunto "
    "in coda, visibile).\n"
    "- hide_bullet/show_bullet: 'profile_experience_id' + 'bullet_index' — "
    "nascondono/mostrano un bullet esistente senza eliminarlo.\n"
    "- hide_experience/show_experience: 'profile_experience_id'.\n"
    "- update_area: 'area_index' + 'text'. add_area: 'text' (nuova voce, "
    "deve restare riconducibile a contenuto reale del profilo, come nella "
    "generazione automatica). remove_area: 'area_index'.\n"
    "- toggle_skill/toggle_certification: 'name' esatto (vedi GROUNDING "
    "sopra) — attiva la voce se non è tra quelle mostrate, la disattiva se "
    "lo è già.\n"
    "- update_education_notes: 'education_index' + 'text'.\n"
    "- update_language_level: 'language_index' + 'level' (uno tra "
    f"{LANGUAGE_LEVEL_CODES}).\n\n"
    "Gli indici (bullet_index, area_index, education_index, "
    "language_index) si riferiscono sempre alla posizione nell'elenco così "
    "come te lo fornisco in questo messaggio, a partire da 0."
)


def _build_user_content(draft, job, profile, chat_history, user_message):
    profile_skill_names = [skill.name for skill in profile.skills.all()]
    profile_certification_names = [cert.name for cert in profile.certifications.all()]
    history_lines = [
        {"role": turn["role"], "message": turn["message"]} for turn in chat_history
    ]
    return (
        f"BOZZA CV ATTUALE (JSON):\n{json.dumps(draft.content_json, ensure_ascii=False)}\n\n"
        f"SKILLS DISPONIBILI (profilo reale, grounding stretto): "
        f"{json.dumps(profile_skill_names, ensure_ascii=False)}\n"
        f"CERTIFICATIONS DISPONIBILI (profilo reale, grounding stretto): "
        f"{json.dumps(profile_certification_names, ensure_ascii=False)}\n\n"
        f"OFFERTA:\nTitolo: {job.title}\nAzienda: {job.company}\n"
        f"Descrizione: {job.description}\n\n"
        f"CRONOLOGIA DELLA CONVERSAZIONE (dalla più vecchia):\n"
        f"{json.dumps(history_lines, ensure_ascii=False)}\n\n"
        f"NUOVO MESSAGGIO DELL'UTENTE:\n{user_message}"
    )


def _sanitize_actions(actions, profile):
    """Filtro difensivo lato server (grounding, come già per skills/
    certifications nella generazione automatica): un'azione toggle con un
    nome non letteralmente presente nel profilo reale viene scartata anche
    se il modello non ha rispettato l'istruzione del prompt."""
    profile_skill_names = {skill.name for skill in profile.skills.all()}
    profile_certification_names = {cert.name for cert in profile.certifications.all()}
    sanitized = []
    for action in actions:
        if action["type"] == "toggle_skill" and action.get("name") not in profile_skill_names:
            continue
        if (
            action["type"] == "toggle_certification"
            and action.get("name") not in profile_certification_names
        ):
            continue
        if action["type"] == "update_language_level" and action.get("level") not in LANGUAGE_LEVEL_CODES:
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
        price = settings.PRICE_CV_DRAFT_CHAT_MESSAGE
        if locked_user.extra_credit < price:
            raise ChatMessageRejected("Saldo credito insufficiente per questo messaggio.")
        locked_user.extra_credit -= price
        locked_user.save(update_fields=["extra_credit"])


def _refund_credit(user):
    with transaction.atomic():
        locked_user = type(user).objects.select_for_update().get(pk=user.pk)
        locked_user.extra_credit += settings.PRICE_CV_DRAFT_CHAT_MESSAGE
        locked_user.save(update_fields=["extra_credit"])


def send_chat_message(job, user_message):
    """Punto d'ingresso della chat (Sprint 59): riserva il credito del
    messaggio, chiama Claude con la bozza corrente come contesto, applica
    il filtro di grounding difensivo sulle azioni, e accoda sia il
    messaggio dell'utente sia la risposta alla cronologia persistita nel
    draft. Nessuna modifica al `content_json` del draft: resta compito del
    frontend applicare le azioni che l'utente accetta, con un PATCH
    separato (`CvDraftView`) — stessa autosave già esistente di Fase 1."""
    try:
        draft = job.cv_draft
    except CVDraft.DoesNotExist as exc:
        raise ChatMessageFailed("Apri prima l'editor per questo CV.") from exc

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
            task_type=RunLog.TaskType.CV_DRAFT_CHAT,
            status=RunLog.Status.FAILURE,
            message=str(exc),
            started_at=started_at,
            finished_at=timezone.now(),
        )
        raise ChatMessageFailed("L'assistente non è riuscito a rispondere.") from exc

    actions = _sanitize_actions(result["actions"], profile)
    draft.chat_history = draft.chat_history + [
        {"role": "user", "message": user_message},
        {"role": "assistant", "message": result["reply"], "actions": actions},
    ]
    draft.save(update_fields=["chat_history", "updated_at"])
    return result["reply"], actions
