# Parametri di configurazione della pipeline di generazione del CV
# (Docs/03-specifiche-funzionali-contenuto-cv-v4.md §12). Valori indicativi,
# da calibrare in test (§14 del documento) — modificabili qui senza toccare
# la logica, stessa natura dei prezzi del credito in config/settings.py.

# Soglia oltre la quale il budget bullet applica il valore più stretto
# della tabella sotto (nessun limite al numero di voci di istruzione
# effettivamente mostrate nel CV — tutte compaiono, richiesto
# esplicitamente dal committente).
EDU_MAX_SHOWN = 3

# Budget bullet totale (B) in funzione del numero di voci di istruzione
# mostrate: più istruzione mostrata, meno spazio per i bullet (§5.4).
# Valori rialzati (Sprint 43): con la tabella originale (12/10/9) un profilo
# reale con 4 esperienze e 3+ voci di istruzione risultava con metà pagina
# vuota ed esperienze molto pertinenti tagliate da 9 bullet reali a 2 —
# osservato in produzione (CV per EY, esperienza "Digital Transformation
# Specialist" gonfiata a torto).
BULLET_BUDGET_BY_EDU_COUNT = {1: 18, 2: 16, 3: 14}

# Numero massimo di esperienze mostrate nel CV, con eventuale swap singolo
# per rilevanza (§5.4).
MAX_EXPERIENCES_SHOWN = 5

# Bullet minimi garantiti a un'esperienza vecchia ma marcata "altamente
# rilevante" che altrimenti risulterebbe senza bullet dopo il taglio al
# budget globale (§5.4).
MIN_GUARANTEED_BULLETS_FOR_RELEVANT_EXPERIENCE = 2

# Numero di voci di Areas of Expertise (§5.3): mai sotto il minimo, il
# modello sintetizza per raggiungerlo anche con un profilo scarno.
AREAS_OF_EXPERTISE_MIN = 4
AREAS_OF_EXPERTISE_MAX = 6

# Tetto massimo di iterazioni del loop di ripiego per overflow: rimozione di
# un bullet alla volta con rirenderizzazione, oltre il quale si accetta il
# caso residuale (PDF multi-pagina, nessun errore mostrato — §6, §11.6).
MAX_OVERFLOW_ITERATIONS = 4

# Lingue di output supportate per le etichette fisse del CV (Sprint 41):
# usate sia dal modello (per riportare in che lingua ha scritto il contenuto,
# vedi CONTENT_JSON_SCHEMA in ai_content.py) sia da SECTION_LABELS in
# generation.py. Se la job description è in una lingua diversa da queste,
# il contenuto testuale viene comunque generato in quella lingua reale (come
# da prompt), ma le etichette fisse ricadono su "en" per mancanza di una
# traduzione dedicata.
SUPPORTED_CV_LANGUAGES = ["it", "en", "fr", "de", "es"]
FALLBACK_CV_LANGUAGE = "en"
