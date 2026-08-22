# Opzioni fisse per il campo lingua/livello del profilo (Sprint 41): prima
# erano testo libero sia in inserimento manuale sia in import da CV, con
# valori disomogenei ("fluent"/"Fluent"/"fluente"/"native"...) che il CV
# generato non poteva tradurre in modo affidabile. `LANGUAGE_CHOICES` e
# `LANGUAGE_LEVEL_CHOICES` sono i valori ammessi (validati da Django/DRF via
# `choices=`); le due mappe di traduzione sotto servono solo al rendering
# del CV nella lingua di output scelta (apps.cv.generation), sugli stessi
# 5 codici di `apps.cv.generation.SECTION_LABELS` (it/en/fr/de/es) — non
# tutte le lingue dell'interfaccia, che resta solo it/en.

LANGUAGE_LEVEL_CHOICES = [
    ("elementary", "Elementary"),
    ("intermediate", "Intermediate"),
    ("fluent", "Fluent"),
    ("mother_tongue", "Mother tongue"),
]

# Lista curata delle lingue più comuni in un contesto lavorativo
# europeo/internazionale (non l'elenco ISO 639-1 completo, per non avere un
# menu a tendina con ~180 voci): estendibile aggiungendo un codice qui e le
# relative traduzioni in LANGUAGE_NAME_LABELS.
LANGUAGE_CHOICES = [
    ("it", "Italian"), ("en", "English"), ("fr", "French"), ("de", "German"), ("es", "Spanish"),
    ("pt", "Portuguese"), ("nl", "Dutch"), ("ru", "Russian"), ("zh", "Chinese"), ("ja", "Japanese"),
    ("ko", "Korean"), ("ar", "Arabic"), ("pl", "Polish"), ("sv", "Swedish"), ("no", "Norwegian"),
    ("da", "Danish"), ("fi", "Finnish"), ("el", "Greek"), ("tr", "Turkish"), ("cs", "Czech"),
    ("ro", "Romanian"), ("hu", "Hungarian"), ("uk", "Ukrainian"), ("hi", "Hindi"), ("he", "Hebrew"),
    ("bg", "Bulgarian"), ("sk", "Slovak"), ("hr", "Croatian"), ("sr", "Serbian"), ("lt", "Lithuanian"),
    ("lv", "Latvian"), ("et", "Estonian"), ("th", "Thai"), ("vi", "Vietnamese"), ("id", "Indonesian"),
    ("sq", "Albanian"),
]

# Traduzione del livello nelle 5 lingue di output supportate dal CV (vedi
# apps.cv.generation.SECTION_LABELS): usata solo in fase di rendering, non
# per la validazione (che resta sui codici sopra).
LANGUAGE_LEVEL_LABELS = {
    "elementary": {"it": "Elementare", "en": "Elementary", "fr": "Élémentaire", "de": "Grundkenntnisse", "es": "Elemental"},
    "intermediate": {"it": "Intermedio", "en": "Intermediate", "fr": "Intermédiaire", "de": "Gute Kenntnisse", "es": "Intermedio"},
    "fluent": {"it": "Fluente", "en": "Fluent", "fr": "Courant", "de": "Fließend", "es": "Fluido"},
    "mother_tongue": {"it": "Madrelingua", "en": "Mother tongue", "fr": "Langue maternelle", "de": "Muttersprache", "es": "Lengua materna"},
}

# Traduzione del nome della lingua nelle 5 lingue di output supportate dal CV.
LANGUAGE_NAME_LABELS = {
    "it": {"it": "Italiano", "en": "Italian", "fr": "Italien", "de": "Italienisch", "es": "Italiano"},
    "en": {"it": "Inglese", "en": "English", "fr": "Anglais", "de": "Englisch", "es": "Inglés"},
    "fr": {"it": "Francese", "en": "French", "fr": "Français", "de": "Französisch", "es": "Francés"},
    "de": {"it": "Tedesco", "en": "German", "fr": "Allemand", "de": "Deutsch", "es": "Alemán"},
    "es": {"it": "Spagnolo", "en": "Spanish", "fr": "Espagnol", "de": "Spanisch", "es": "Español"},
    "pt": {"it": "Portoghese", "en": "Portuguese", "fr": "Portugais", "de": "Portugiesisch", "es": "Portugués"},
    "nl": {"it": "Olandese", "en": "Dutch", "fr": "Néerlandais", "de": "Niederländisch", "es": "Neerlandés"},
    "ru": {"it": "Russo", "en": "Russian", "fr": "Russe", "de": "Russisch", "es": "Ruso"},
    "zh": {"it": "Cinese", "en": "Chinese", "fr": "Chinois", "de": "Chinesisch", "es": "Chino"},
    "ja": {"it": "Giapponese", "en": "Japanese", "fr": "Japonais", "de": "Japanisch", "es": "Japonés"},
    "ko": {"it": "Coreano", "en": "Korean", "fr": "Coréen", "de": "Koreanisch", "es": "Coreano"},
    "ar": {"it": "Arabo", "en": "Arabic", "fr": "Arabe", "de": "Arabisch", "es": "Árabe"},
    "pl": {"it": "Polacco", "en": "Polish", "fr": "Polonais", "de": "Polnisch", "es": "Polaco"},
    "sv": {"it": "Svedese", "en": "Swedish", "fr": "Suédois", "de": "Schwedisch", "es": "Sueco"},
    "no": {"it": "Norvegese", "en": "Norwegian", "fr": "Norvégien", "de": "Norwegisch", "es": "Noruego"},
    "da": {"it": "Danese", "en": "Danish", "fr": "Danois", "de": "Dänisch", "es": "Danés"},
    "fi": {"it": "Finlandese", "en": "Finnish", "fr": "Finnois", "de": "Finnisch", "es": "Finlandés"},
    "el": {"it": "Greco", "en": "Greek", "fr": "Grec", "de": "Griechisch", "es": "Griego"},
    "tr": {"it": "Turco", "en": "Turkish", "fr": "Turc", "de": "Türkisch", "es": "Turco"},
    "cs": {"it": "Ceco", "en": "Czech", "fr": "Tchèque", "de": "Tschechisch", "es": "Checo"},
    "ro": {"it": "Romeno", "en": "Romanian", "fr": "Roumain", "de": "Rumänisch", "es": "Rumano"},
    "hu": {"it": "Ungherese", "en": "Hungarian", "fr": "Hongrois", "de": "Ungarisch", "es": "Húngaro"},
    "uk": {"it": "Ucraino", "en": "Ukrainian", "fr": "Ukrainien", "de": "Ukrainisch", "es": "Ucraniano"},
    "hi": {"it": "Hindi", "en": "Hindi", "fr": "Hindi", "de": "Hindi", "es": "Hindi"},
    "he": {"it": "Ebraico", "en": "Hebrew", "fr": "Hébreu", "de": "Hebräisch", "es": "Hebreo"},
    "bg": {"it": "Bulgaro", "en": "Bulgarian", "fr": "Bulgare", "de": "Bulgarisch", "es": "Búlgaro"},
    "sk": {"it": "Slovacco", "en": "Slovak", "fr": "Slovaque", "de": "Slowakisch", "es": "Eslovaco"},
    "hr": {"it": "Croato", "en": "Croatian", "fr": "Croate", "de": "Kroatisch", "es": "Croata"},
    "sr": {"it": "Serbo", "en": "Serbian", "fr": "Serbe", "de": "Serbisch", "es": "Serbio"},
    "lt": {"it": "Lituano", "en": "Lithuanian", "fr": "Lituanien", "de": "Litauisch", "es": "Lituano"},
    "lv": {"it": "Lettone", "en": "Latvian", "fr": "Letton", "de": "Lettisch", "es": "Letón"},
    "et": {"it": "Estone", "en": "Estonian", "fr": "Estonien", "de": "Estnisch", "es": "Estonio"},
    "th": {"it": "Tailandese", "en": "Thai", "fr": "Thaï", "de": "Thailändisch", "es": "Tailandés"},
    "vi": {"it": "Vietnamita", "en": "Vietnamese", "fr": "Vietnamien", "de": "Vietnamesisch", "es": "Vietnamita"},
    "id": {"it": "Indonesiano", "en": "Indonesian", "fr": "Indonésien", "de": "Indonesisch", "es": "Indonesio"},
    "sq": {"it": "Albanese", "en": "Albanian", "fr": "Albanais", "de": "Albanisch", "es": "Albanés"},
}
