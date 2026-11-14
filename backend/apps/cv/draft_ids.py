# ID stabili per i bullet del CV e i paragrafi della cover letter (Sprint 69).
# Prima chat ed editor si riferivano a bullet e paragrafi per posizione: un
# riordino, o l'accettazione di più azioni dello stesso turno, poteva far
# colpire l'elemento sbagliato. Ora ogni bullet (`{id, text, shown}`) e ogni
# paragrafo (`{id, text}`) ha un `id` breve e casuale, assegnato alla
# generazione, dalla PWA quando l'utente ne aggiunge uno, o qui in modo
# "pigro" per i contenuti salvati prima dello Sprint 69 (bullet senza `id`,
# paragrafi come semplici stringhe). Le funzioni sono difensive: toccano solo
# le parti con la forma attesa e lasciano il resto alla validazione.
import uuid


def new_item_id():
    return uuid.uuid4().hex[:12]


def _valid_id(value, seen):
    return isinstance(value, str) and 0 < len(value) <= 40 and value not in seen


def ensure_cv_bullet_ids(content):
    """Assegna un `id` ai bullet che non lo hanno (o con un id duplicato).
    Modifica `content` sul posto; ritorna True se ha cambiato qualcosa."""
    if not isinstance(content, dict) or not isinstance(content.get("experiences"), list):
        return False
    changed = False
    seen = set()
    for exp in content["experiences"]:
        if not isinstance(exp, dict) or not isinstance(exp.get("bullets"), list):
            continue
        for bullet in exp["bullets"]:
            if not isinstance(bullet, dict):
                continue
            if not _valid_id(bullet.get("id"), seen):
                bullet["id"] = new_item_id()
                changed = True
            seen.add(bullet["id"])
    return changed


def ensure_cover_letter_paragraph_ids(content):
    """Converte i paragrafi-stringa in `{id, text}` e assegna gli `id`
    mancanti o duplicati. Modifica `content` sul posto."""
    if not isinstance(content, dict) or not isinstance(content.get("paragraphs"), list):
        return False
    changed = False
    seen = set()
    paragraphs = content["paragraphs"]
    for index, paragraph in enumerate(paragraphs):
        if isinstance(paragraph, str):
            paragraphs[index] = {"id": new_item_id(), "text": paragraph}
            changed = True
        elif isinstance(paragraph, dict) and not _valid_id(paragraph.get("id"), seen):
            paragraph["id"] = new_item_id()
            changed = True
        if isinstance(paragraphs[index], dict):
            seen.add(paragraphs[index].get("id"))
    return changed


def cv_bullet_owners(content):
    """`{bullet_id: profile_experience_id}` della bozza."""
    owners = {}
    for exp in content.get("experiences", []):
        for bullet in exp.get("bullets", []):
            owners[bullet.get("id")] = exp.get("profile_experience_id")
    return owners


def _map_legacy_cv_actions(content, chat_history):
    """Azioni salvate prima dello Sprint 69 (`bullet_index`): ricevono il
    `bullet_id` del bullet che occupa oggi quella posizione, cioè lo stesso
    che avrebbero colpito con il vecchio comportamento."""
    experiences = {exp.get("profile_experience_id"): exp for exp in content.get("experiences", [])}
    changed = False
    for turn in chat_history:
        for action in turn.get("actions") or []:
            if "bullet_id" in action or "bullet_index" not in action:
                continue
            bullet_id = None
            index = action.get("bullet_index")
            exp = experiences.get(action.get("profile_experience_id"))
            if exp is not None and isinstance(index, int) and 0 <= index < len(exp.get("bullets", [])):
                bullet_id = exp["bullets"][index].get("id")
            action["bullet_id"] = bullet_id
            changed = True
    return changed


def _map_legacy_cover_letter_actions(content, chat_history):
    paragraphs = content.get("paragraphs", [])
    changed = False
    for turn in chat_history:
        for action in turn.get("actions") or []:
            if "paragraph_id" in action or "paragraph_index" not in action:
                continue
            paragraph_id = None
            index = action.get("paragraph_index")
            if isinstance(index, int) and 0 <= index < len(paragraphs):
                paragraph_id = paragraphs[index].get("id")
            action["paragraph_id"] = paragraph_id
            changed = True
    return changed


def normalize_cv_draft(draft):
    """Normalizzazione pigra di una `CVDraft` salvata prima dello Sprint 69
    (id dei bullet e azioni della chat); salva solo se serve."""
    changed = ensure_cv_bullet_ids(draft.content_json)
    if isinstance(draft.chat_history, list):
        changed = _map_legacy_cv_actions(draft.content_json, draft.chat_history) or changed
    if changed:
        draft.save(update_fields=["content_json", "chat_history", "updated_at"])
    return draft


def normalize_cover_letter_draft(draft):
    changed = ensure_cover_letter_paragraph_ids(draft.content_json)
    if isinstance(draft.chat_history, list):
        changed = _map_legacy_cover_letter_actions(draft.content_json, draft.chat_history) or changed
    if changed:
        draft.save(update_fields=["content_json", "chat_history", "updated_at"])
    return draft


def paragraph_texts(paragraphs):
    return [p["text"] if isinstance(p, dict) else p for p in paragraphs]
