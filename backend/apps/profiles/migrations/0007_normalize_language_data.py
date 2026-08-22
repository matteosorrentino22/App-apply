# Normalizza i 16 record esistenti di Language (creati quando 'language' e
# 'level' erano testo libero) ai codici fissi introdotti da 0006. Best-effort
# per sinonimo comune (case-insensitive): un valore non riconosciuto resta
# invariato — non blocca la migrazione, semplicemente quella riga non verrà
# tradotta nel rendering del CV finché non viene corretta a mano (Sprint 41).
from django.db import migrations

from apps.profiles.language_options import LANGUAGE_NAME_LABELS

LEVEL_SYNONYMS = {
    "elementary": "elementary", "elementare": "elementary", "basic": "elementary",
    "beginner": "elementary", "a1": "elementary", "a2": "elementary",
    "principiante": "elementary", "élémentaire": "elementary", "grundkenntnisse": "elementary",
    "elemental": "elementary",
    "intermediate": "intermediate", "intermedio": "intermediate", "b1": "intermediate",
    "b2": "intermediate", "intermédiaire": "intermediate", "gute kenntnisse": "intermediate",
    "fluent": "fluent", "fluente": "fluent", "fluido": "fluent", "advanced": "fluent",
    "c1": "fluent", "courant": "fluent", "fließend": "fluent",
    "mother tongue": "mother_tongue", "madrelingua": "mother_tongue", "native": "mother_tongue",
    "nativo": "mother_tongue", "native speaker": "mother_tongue", "c2": "mother_tongue",
    "langue maternelle": "mother_tongue", "muttersprache": "mother_tongue",
    "lengua materna": "mother_tongue",
}


def _build_name_to_code():
    name_to_code = {}
    for code, translations in LANGUAGE_NAME_LABELS.items():
        for name in translations.values():
            name_to_code[name.lower()] = code
    return name_to_code


def normalize_language_data(apps, schema_editor):
    Language = apps.get_model("profiles", "Language")
    name_to_code = _build_name_to_code()
    for row in Language.objects.all():
        new_language = name_to_code.get(row.language.strip().lower(), row.language)
        new_level = LEVEL_SYNONYMS.get(row.level.strip().lower(), row.level) if row.level else row.level
        if new_language != row.language or new_level != row.level:
            row.language = new_language
            row.level = new_level
            row.save(update_fields=["language", "level"])


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0006_language_choices"),
    ]

    operations = [
        migrations.RunPython(normalize_language_data, migrations.RunPython.noop),
    ]
