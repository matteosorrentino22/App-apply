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

from .draft import load_cv_draft
from .draft_ids import cv_bullet_owners
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
        "bullet_id": {"type": ["string", "null"]},
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
        "bullet_id",
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
    "- update_bullet: 'bullet_id' (il campo 'id' del bullet nella bozza "
    "qui sotto) + 'profile_experience_id' della sua esperienza + 'text'.\n"
    "- add_bullet: 'profile_experience_id' + 'text' (nuovo bullet, aggiunto "
    "in coda, visibile).\n"
    "- hide_bullet/show_bullet: 'bullet_id' + 'profile_experience_id' — "
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
    "I bullet si indicano SEMPRE con il loro 'id' (stringa), mai con la "
    "posizione: un id che non esiste nella bozza fa scartare l'azione. Gli "
    "indici (area_index, education_index, language_index) si riferiscono "
    "alla posizione nell'elenco così come te lo fornisco in questo "
    "messaggio, a partire da 0.\n\n"
    "CRONOLOGIA: per ogni tua risposta precedente trovi anche le azioni "
    "proposte, in forma compatta, con la decisione dell'utente ('accepted' "
    "= applicata, 'rejected' = rifiutata, 'pending' = non ancora decisa). "
    "Non riproporre un'azione rifiutata se l'utente non lo chiede; lo stato "
    "reale attuale è comunque quello della BOZZA CV ATTUALE.\n\n"
    "BULLET PUNTATI: se il messaggio include un blocco 'BULLET PUNTATI "
    "DALL'UTENTE', l'utente ha selezionato esplicitamente quei singoli "
    "bullet nell'interfaccia (un pulsante su ciascuna singola attività, "
    "non sull'intera esperienza) come riferimento per questo messaggio — "
    "usali per risolvere pronomi o riferimenti generici ('questo punto', "
    "'questa attività') invece di indovinare dal solo testo. Se il "
    "messaggio nomina chiaramente un'azienda o un bullet diverso da quelli "
    "puntati, segui comunque il testo: i bullet puntati sono un aiuto per "
    "i casi ambigui, non un vincolo assoluto."
)


# Solo gli ultimi turni della cronologia vanno nel prompt (Sprint 66): la
# cronologia completa resta salvata, ma il costo di ogni messaggio non
# cresce senza limite con la lunghezza della conversazione.
MAX_HISTORY_TURNS_IN_PROMPT = 20
# Testo delle azioni passate nella cronologia del prompt (Sprint 69): basta
# a riconoscerle, il testo completo applicato è già nella bozza.
MAX_ACTION_TEXT_IN_HISTORY = 200

_COMPACT_ACTION_KEYS = (
    "profile_experience_id",
    "bullet_id",
    "area_index",
    "education_index",
    "language_index",
    "name",
    "level",
)


def compact_action(action, keys=_COMPACT_ACTION_KEYS):
    """Forma compatta di un'azione già proposta, con la decisione
    dell'utente, per la cronologia passata al modello (Sprint 69)."""
    item = {"type": action.get("type")}
    for key in keys:
        if action.get(key) is not None:
            item[key] = action[key]
    text = action.get("text")
    if text:
        item["text"] = (
            text if len(text) <= MAX_ACTION_TEXT_IN_HISTORY else text[:MAX_ACTION_TEXT_IN_HISTORY] + "…"
        )
    item["decision"] = action.get("decision") or "pending"
    return item


def history_for_prompt(chat_history, keys=_COMPACT_ACTION_KEYS):
    lines = []
    for turn in chat_history[-MAX_HISTORY_TURNS_IN_PROMPT:]:
        line = {"role": turn["role"], "message": turn["message"]}
        if turn.get("actions"):
            line["actions"] = [compact_action(action, keys) for action in turn["actions"]]
        lines.append(line)
    return lines


def _find_bullet(content, ref):
    """Bullet puntato dall'utente: per `bullet_id` (Sprint 69) o, da una
    scheda aperta prima dell'aggiornamento, per `bullet_index`."""
    for exp in content.get("experiences", []):
        if exp.get("profile_experience_id") != ref.get("profile_experience_id") and "bullet_id" not in ref:
            continue
        bullets = exp.get("bullets", [])
        if isinstance(ref.get("bullet_id"), str):
            for bullet in bullets:
                if bullet.get("id") == ref["bullet_id"]:
                    return exp, bullet
        elif isinstance(ref.get("bullet_index"), int) and 0 <= ref["bullet_index"] < len(bullets):
            return exp, bullets[ref["bullet_index"]]
    return None, None


def _build_user_content(draft, job, profile, chat_history, user_message, focus_bullets):
    profile_skill_names = [skill.name for skill in profile.skills.all()]
    profile_certification_names = [cert.name for cert in profile.certifications.all()]
    history_lines = history_for_prompt(chat_history)
    focused_bullets_info = []
    for ref in focus_bullets or []:
        exp, bullet = _find_bullet(draft.content_json, ref)
        if bullet is None:
            continue
        focused_bullets_info.append(
            {
                "profile_experience_id": exp["profile_experience_id"],
                "company": exp["company"],
                "role": exp["role"],
                "bullet_id": bullet.get("id"),
                "bullet_text": bullet["text"],
            }
        )
    focus_block = (
        f"\n\nBULLET PUNTATI DALL'UTENTE: {json.dumps(focused_bullets_info, ensure_ascii=False)}"
        if focused_bullets_info
        else ""
    )
    return (
        f"BOZZA CV ATTUALE (JSON):\n{json.dumps(draft.content_json, ensure_ascii=False)}\n\n"
        f"SKILLS DISPONIBILI (profilo reale, grounding stretto): "
        f"{json.dumps(profile_skill_names, ensure_ascii=False)}\n"
        f"CERTIFICATIONS DISPONIBILI (profilo reale, grounding stretto): "
        f"{json.dumps(profile_certification_names, ensure_ascii=False)}\n\n"
        f"OFFERTA:\nTitolo: {job.title}\nAzienda: {job.company}\n"
        f"Descrizione: {job.description}\n\n"
        f"CRONOLOGIA DELLA CONVERSAZIONE (dalla più vecchia):\n"
        f"{json.dumps(history_lines, ensure_ascii=False)}"
        f"{focus_block}\n\n"
        f"NUOVO MESSAGGIO DELL'UTENTE:\n{user_message}"
    )


_TEXT_ACTIONS = {
    "update_summary",
    "update_qualification",
    "update_role",
    "update_bullet",
    "add_bullet",
    "update_area",
    "add_area",
    "update_education_notes",
}
_EXPERIENCE_ACTIONS = {"update_role", "add_bullet", "hide_experience", "show_experience"}
_BULLET_ACTIONS = {"update_bullet", "hide_bullet", "show_bullet"}
_AREA_INDEX_ACTIONS = {"update_area", "remove_area"}


def _in_range(index, items):
    return isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(items)


def _sanitize_actions(actions, profile, content):
    """Filtro difensivo lato server sulle azioni proposte dal modello.
    Grounding (come nella generazione automatica): un toggle con un nome non
    presente nel profilo reale è scartato. Riferimenti (Sprint 69): sono
    scartate le azioni su esperienze o bullet inesistenti nella bozza
    salvata, con indici fuori range o senza il testo richiesto. Per le aree
    (ancora per indice) si allega `area_text`, il testo dell'area al momento
    della proposta, con cui la PWA ritrova l'area giusta anche se nel
    frattempo l'elenco è cambiato."""
    profile_skill_names = {skill.name for skill in profile.skills.all()}
    profile_certification_names = {cert.name for cert in profile.certifications.all()}
    experience_ids = {exp.get("profile_experience_id") for exp in content.get("experiences", [])}
    bullet_owners = cv_bullet_owners(content)
    areas = content.get("areas_of_expertise", [])
    sanitized = []
    for action in actions:
        action_type = action["type"]
        if action_type in _TEXT_ACTIONS and not isinstance(action.get("text"), str):
            continue
        if action_type == "toggle_skill" and action.get("name") not in profile_skill_names:
            continue
        if (
            action_type == "toggle_certification"
            and action.get("name") not in profile_certification_names
        ):
            continue
        if action_type == "update_language_level" and (
            action.get("level") not in LANGUAGE_LEVEL_CODES
            or not _in_range(action.get("language_index"), content.get("languages", []))
        ):
            continue
        if action_type == "update_education_notes" and not _in_range(
            action.get("education_index"), content.get("educations", [])
        ):
            continue
        if action_type in _EXPERIENCE_ACTIONS and action.get("profile_experience_id") not in experience_ids:
            continue
        if action_type in _BULLET_ACTIONS:
            if action.get("bullet_id") not in bullet_owners:
                continue
            action = {**action, "profile_experience_id": bullet_owners[action["bullet_id"]]}
        if action_type in _AREA_INDEX_ACTIONS:
            if not _in_range(action.get("area_index"), areas):
                continue
            action = {**action, "area_text": areas[action["area_index"]]}
        sanitized.append(action)
    return sanitized


class ChatMessageRejected(Exception):
    """Credito insufficiente: nessun consumo, nessuna chiamata AI."""


class ChatMessageFailed(Exception):
    """La chiamata AI è fallita: il credito riservato è già stato restituito."""


def _reserve_credit(user):
    """Ritorna il saldo dopo l'addebito."""
    with transaction.atomic():
        locked_user = type(user).objects.select_for_update().get(pk=user.pk)
        price = settings.PRICE_CV_DRAFT_CHAT_MESSAGE
        if locked_user.extra_credit < price:
            raise ChatMessageRejected("Saldo credito insufficiente per questo messaggio.")
        locked_user.extra_credit -= price
        locked_user.save(update_fields=["extra_credit"])
        return locked_user.extra_credit


def _refund_credit(user):
    with transaction.atomic():
        locked_user = type(user).objects.select_for_update().get(pk=user.pk)
        locked_user.extra_credit += settings.PRICE_CV_DRAFT_CHAT_MESSAGE
        locked_user.save(update_fields=["extra_credit"])


def send_chat_message(job, user_message, focus_bullets=None):
    """Punto d'ingresso della chat (Sprint 59, `focus_bullets` Sprint 61,
    riferimento a singoli bullet invece che a intere esperienze): riserva
    il credito del messaggio, chiama Claude con la bozza corrente come
    contesto, applica il filtro di grounding difensivo sulle azioni, e
    accoda sia il messaggio dell'utente sia la risposta alla cronologia
    persistita nel draft. Nessuna modifica al `content_json` del draft:
    resta compito del frontend applicare le azioni che l'utente accetta,
    con un PATCH separato (`CvDraftView`) — stessa autosave già esistente
    di Fase 1.
    Ritorna `(reply, actions, saldo dopo l'addebito)` (saldo: Sprint 69).
    """
    try:
        draft = load_cv_draft(job)
    except CVDraft.DoesNotExist as exc:
        raise ChatMessageFailed("Apri prima l'editor per questo CV.") from exc

    user = job.user
    profile = user.profile
    balance = _reserve_credit(user)
    started_at = timezone.now()

    try:
        result = call_claude_structured(
            model=settings.BEDROCK_CV_GENERATION_MODEL,
            system=CHAT_SYSTEM_PROMPT,
            user_content=_build_user_content(
                draft, job, profile, draft.chat_history, user_message, focus_bullets
            ),
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

    actions = _sanitize_actions(result["actions"], profile, draft.content_json)
    draft.chat_history = draft.chat_history + [
        {"role": "user", "message": user_message},
        {"role": "assistant", "message": result["reply"], "actions": actions},
    ]
    draft.save(update_fields=["chat_history", "updated_at"])
    return result["reply"], actions, balance


class InvalidChatDecision(Exception):
    """Indici fuori range o decisione non valida: nessuna scrittura."""


def record_action_decision(job, message_index, action_index, decision):
    """Persiste la scelta (accetta/rifiuta) di una singola azione proposta
    (Sprint 62): senza questo, la scelta viveva solo nello stato locale del
    pannello React — chiudendo e riaprendo la chat (o ricaricando la
    pagina) le card tornavano "in attesa", permettendo di riapplicare la
    stessa azione una seconda volta. Scrive `decision` dentro l'azione
    stessa in `chat_history`, letta dal frontend al prossimo caricamento
    per disabilitare di nuovo i pulsanti già usati. Non applica né
    disapplica nulla sul `content_json` del draft: resta responsabilità
    del frontend, qui si registra solo la scelta già fatta."""
    if decision not in ("accepted", "rejected"):
        raise InvalidChatDecision("Decisione non valida.")
    try:
        draft = job.cv_draft
    except CVDraft.DoesNotExist as exc:
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
