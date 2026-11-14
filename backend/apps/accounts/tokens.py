import hashlib
import secrets

from .models import AuthToken


def hash_token_key(key):
    return hashlib.sha256(key.encode()).hexdigest()


def create_token(user, user_agent=""):
    """Crea un nuovo token per `user` e restituisce la chiave in chiaro:
    è l'unico momento in cui esiste fuori dal client."""
    key = secrets.token_urlsafe(32)
    AuthToken.objects.create(user=user, key_hash=hash_token_key(key), user_agent=user_agent[:200])
    return key


def revoke_all_tokens(user):
    """Disconnette l'utente da tutti i dispositivi (cambio password,
    cancellazione account)."""
    AuthToken.objects.filter(user=user).delete()
