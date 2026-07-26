from django.apps import AppConfig


class SearchesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.searches"
    label = "searches"

    def ready(self):
        from . import signals  # noqa: F401
