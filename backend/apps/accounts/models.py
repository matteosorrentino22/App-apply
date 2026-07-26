from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Placeholder custom user model.

    Empty for now: AUTH_USER_MODEL must point here from the first migration,
    since swapping it later requires a fresh database. Fields from
    02-specifiche-tecniche-v3.md §4.1 (plan, timezone, extra_credit, ...)
    are added in Sprint 02.
    """
