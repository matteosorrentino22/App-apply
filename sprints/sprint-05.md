# Sprint 05 — Import CV esistente (parsing)

## Input
- Sprint 04 completato (API profilo disponibile).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.1; `02-specifiche-tecniche-v3.md` §3.5, §5.4.

## Obiettivo
Endpoint di upload CV (PDF/Word): estrazione testo lato server (`pdfplumber`/`pypdf`, `python-docx`), chiamata a Claude per strutturare il testo nelle sezioni del profilo master, con pre-popolamento modificabile prima del salvataggio; gestione del fallback per testo vuoto/irrisorio (PDF scansione/immagine).

## Risultato atteso
Caricando un CV leggibile, la risposta API contiene un profilo pre-popolato coerente col contenuto del file, non ancora salvato come definitivo; caricando un PDF scansione/immagine, l'utente riceve il messaggio di fallback e nessun profilo vuoto viene creato.

## Criteri di verifica
- Upload di un CV PDF testuale di prova → risposta con sezioni pre-popolate (sommario, almeno un'esperienza, istruzione) coerenti col file.
- Upload di un CV `.docx` di prova → stesso comportamento.
- Upload di un PDF scansione/immagine senza testo estraibile → risposta con messaggio di fallback dedicato; nessuna scrittura di profilo vuoto in DB.
- Il payload inviato a Claude contiene solo testo estratto, non il file binario (verificabile via log/mock della chiamata).
- I dati pre-popolati restano modificabili: una successiva chiamata di salvataggio con campi alterati sovrascrive correttamente i valori proposti.

## Output per lo sprint successivo
Pipeline di estrazione testo riusabile; profilo popolabile sia manualmente sia da upload, pronto per la creazione delle ricerche (Sprint 06).

---

## Esito (2026-07-26)

**Stato: completato**, con una riserva sulla chiamata reale a Claude (vedi Criticità — stesso tipo di limite ambientale già segnalato per Docker e Google OAuth negli sprint precedenti).

### Cosa è stato fatto
- `apps.profiles.cv_import` — modulo di servizio con la pipeline in due passi di §3.5/§5.4 tecniche:
  - `extract_text(uploaded_file)` — instrada per `content_type`/estensione a `_extract_pdf_text` (`pdfplumber`) o `_extract_docx_text` (`python-docx`); formato non riconosciuto → `ValueError` (400). Un file corrotto/non decodificabile dalla libreria (non solo il caso "testo vuoto") solleva `CVUnreadableError` invece di propagare l'eccezione della libreria, così un PDF malformato non fa mai crashare la richiesta (bug trovato e corretto durante la verifica manuale, vedi sotto).
  - `has_sufficient_text(text)` — soglia minima (40 caratteri non whitespace) per distinguere un CV leggibile da un PDF scansione/immagine senza testo estraibile.
  - `structure_with_claude(raw_text)` — **unico punto che chiama l'API Anthropic**: passa **solo la stringa di testo estratta** (mai il file), con `output_config.format` a `json_schema` (schema esplicito con le sezioni del profilo: `summary`, `key_achievements`, `experiences[]`, `educations[]`, `skills[]`, `certifications[]`, `languages[]`) così la risposta è JSON garantito, senza bisogno di parsing euristico. Thinking disattivato ed effort `medium`: compito di mappatura testo→struttura, non di ragionamento complesso, quindi non serve la spesa di token di un adaptive thinking di default (accettabile perché `thinking: disabled` è ammesso a effort ≤ `high`, §skill Claude API). Modello configurabile via `ANTHROPIC_CV_PARSING_MODEL` (default `claude-opus-5`), chiave da `ANTHROPIC_API_KEY` — entrambe da environment, mai hardcoded.
- `POST /api/profile/import-cv/` (`CVImportView`, multipart, autenticato) — orchestration: estrazione → controllo soglia (422 col messaggio di fallback se insufficiente o file illeggibile) → strutturazione con Claude → risposta 200 col profilo proposto. **Non scrive nulla su database**: la pre-popolazione resta nella risposta HTTP, il salvataggio effettivo avviene con le chiamate già esistenti dello Sprint 04 (`PATCH /api/profiles/me/`, `POST /api/experiences/`, ecc.), che sovrascrivono correttamente campi alterati dall'utente prima di salvare — nessun endpoint aggiuntivo necessario per il criterio "dati modificabili prima del salvataggio".
- Aggiunte a `requirements.txt`: `anthropic`, `pdfplumber`, `python-docx`. Aggiunte a `config/settings.py` e `.env.example`: `ANTHROPIC_API_KEY`, `ANTHROPIC_CV_PARSING_MODEL`.
- **Suite di test automatici** (`apps/profiles/tests.py`, `CVImportApiTests`): copre i criteri con un `.docx` reale generato al volo (`python-docx`) e un PDF mockato via `pdfplumber.open` (per non introdurre una dipendenza di solo-test per generare PDF binari), con `Anthropic` mockato per verificare **esplicitamente** che il payload inviato (`messages[0]["content"]`) sia una stringa di solo testo — non contiene la firma binaria `.docx` (`PK\x03\x04`) né alcun blocco `document`/base64. Copre anche: formato non supportato (400), PDF senza testo estraibile (422 + nessun `Profile` creato).

### Bug trovato e corretto durante la verifica manuale
La verifica manuale (vedi sotto) con un PDF **realmente corrotto** (non un semplice "scansione senza testo", ma un file non valido per il parser) ha fatto emergere che `pdfplumber.open` solleva un'eccezione propria (`PdfminerException`) non gestita, con conseguente **500** invece del fallback atteso. Questo non emergeva dai test automatici perché mockano `pdfplumber.open` direttamente. Corretto avvolgendo l'estrazione in un try/except che rilancia come `CVUnreadableError`, gestito dalla view con lo stesso messaggio di fallback (422) del caso "testo vuoto" — un file illeggibile per qualunque motivo porta sempre l'utente alla compilazione manuale, mai a un errore server generico.

### Verifica eseguita
Automatica (`python manage.py test apps.profiles` — 7/7, incluse le 3 dello Sprint 04) e manuale via `runserver` + `curl`: un `.txt` → 400; un PDF non valido → 422 (dopo la correzione del bug sopra); un **PDF reale con testo estraibile**, costruito a mano nel formato PDF minimo (oggetti + stream `BT/Tj`), verificato con `pdfplumber` per confermare l'estrazione del testo (`"Mario Rossi\nProject Manager con 8 anni di esperienza..."`) — la richiesta arriva correttamente fino alla chiamata a Claude, che fallisce solo per l'assenza di una vera `ANTHROPIC_API_KEY` in questo ambiente (errore di autenticazione del SDK, non un bug del codice).

| Criterio | Esito |
|---|---|
| Upload PDF testuale → sezioni pre-popolate coerenti | ✅ pipeline verificata fino alla chiamata a Claude (estrazione + soglia + payload); ⚠️ risposta strutturata completa non verificabile end-to-end senza una chiave Anthropic reale in questo ambiente (vedi Criticità) |
| Upload `.docx` → stesso comportamento | ✅ (test automatico end-to-end con `Anthropic` mockato: 200, sezioni popolate) |
| PDF scansione/immagine senza testo → messaggio di fallback, nessun profilo vuoto creato | ✅ (422, `Profile.objects.filter(user=...).exists()` → `False`) |
| Payload a Claude contiene solo testo estratto, non il file binario | ✅ (verificato via mock: `messages[0]["content"]` è una stringa, non contiene la firma binaria `.docx`) |
| Dati pre-popolati restano modificabili, salvataggio successivo sovrascrive correttamente | ✅ (per costruzione: l'endpoint di import non salva nulla; il salvataggio usa le API profilo dello Sprint 04, già testate per l'overwrite) |
| `makemigrations --check` nessuna differenza (nessun modello nuovo in questo sprint) | ✅ |

### Criticità riscontrate
1. **Verifica end-to-end reale della strutturazione Claude non eseguibile in questo ambiente.** Non è disponibile una `ANTHROPIC_API_KEY` reale nella sandbox: la pipeline è stata verificata fino al punto massimo raggiungibile (estrazione testo corretta su PDF e `.docx` reali, soglia di sufficienza, forma esatta del payload) tramite test automatici con `Anthropic` mockato, più una verifica manuale che conferma che l'unico punto di fallimento residuo è l'autenticazione SDK mancante. Il completamento del round-trip reale (risposta di Claude strutturata secondo lo schema) va verificato manualmente impostando `ANTHROPIC_API_KEY`/`ANTHROPIC_CV_PARSING_MODEL` in `.env` in un ambiente con accesso reale all'API Anthropic.
2. **`docker compose up` reale non eseguibile**, stessa causa (policy di rete della sandbox) degli sprint precedenti; `docker compose config` con un `.env` di prova conferma che il file resta sintatticamente valido dopo le nuove dipendenze.

### Cosa manca
- Verifica manuale del round-trip Claude completo con credenziali reali (vedi Criticità §1).
- Riutilizzo della stessa pipeline di estrazione/strutturazione per lo scoring e la generazione CV (Sprint 07+), fuori scope per questo sprint.
- Un vero smoke test di `docker compose up -d` (stessa riserva degli sprint precedenti).