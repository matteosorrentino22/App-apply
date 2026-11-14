# Nei test la cache di default è una DummyCache (config/settings.py): chi ha
# bisogno di una cache vera (throttling, cache dell'autocomplete) usa questa.
LOCMEM_CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
