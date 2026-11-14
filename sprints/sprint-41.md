# Sprint 41 — CV multilingua, lingue/livelli del profilo a valori fissi, email del profilo separata dal login

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-08-19 · **Commit:** `0833bdb` (commit cumulativo di recupero del 2026-08-22 che contiene insieme Sprint 39–42, vedi `sprint-43.md`, "Nota preliminare")

## Input
Il committente segnala problemi sui CV generati per offerte in inglese con un
utente di test impostato su "lingua dell'offerta":
1. Titoli di sezione in italiano.
2. Sottotitolo "Competenze" in italiano.
3. "Presente" non tradotto sull'esperienza in corso.
4. Lingue del profilo non tradotte. Problema più ampio: né l'import da CV né
   l'inserimento manuale hanno una lista di lingue o di livelli possibili.
   Livelli richiesti: elementary, intermediate, fluent, mother tongue, da
   tradurre nella lingua del CV.

Nella stessa giornata il committente aggiunge due richieste:
- l'email sul CV veniva presa dall'account di login. Serve un campo email nel
  profilo, come il telefono, precompilato dal CV importato;
- la foto nell'intestazione disallinea il filetto sotto i contatti.

## Decisioni prese
- **Causa di 1–3 (unica):** `html_lang` era calcolato come `"en" if
  cv_language_mode == "english" else "it"`, quindi con "lingua dell'offerta" le
  etichette fisse restavano sempre in italiano. Decisione: il modello dichiara
  la lingua che ha realmente usato (`content_language`) e le etichette seguono
  quella.
- **Lingue delle etichette (risposta del committente):** etichette estese a
  **francese, tedesco e spagnolo** oltre a it/en, "per ora". Per qualunque
  altra lingua dell'offerta si usa il fallback inglese.
- **Lista lingue (risposta del committente):** lista curata di circa 30–40
  lingue, non l'elenco ISO 639-1 completo. Risultato: 36 codici ISO a due
  lettere.
- **4 livelli fissi:** `elementary`, `intermediate`, `fluent`, `mother_tongue`.
  Nell'import da CV le scale libere/CEFR vengono mappate su questi livelli; in
  caso di dubbio la voce viene omessa invece di indovinare.
- **Dati esistenti:** normalizzati con una migrazione dati best-effort per
  sinonimi; i valori non riconosciuti restano invariati.
- **Email:** un `Profile.email` separato da `user.email`, opzionale. Se è vuoto
  il CV non mostra alcuna email (nessun fallback sull'email di login).
- **Foto:** l'intestazione è allineata al fondo (`align-items: flex-end`) invece
  che al centro.

## Implementazione
### Modello dati
- `Language.language` e `Language.level` passano da testo libero a `choices`,
  definite in `apps/profiles/language_options.py`:
  - `LANGUAGE_CHOICES` (36 codici) e `LANGUAGE_LEVEL_CHOICES` (4 livelli);
  - `LANGUAGE_NAME_LABELS` e `LANGUAGE_LEVEL_LABELS` con le traduzioni
    it/en/fr/de/es, usate solo in rendering.
- Migrazioni:
  - `profiles/0006_language_choices`;
  - `profiles/0007_normalize_language_data` (RunPython: mappa nome lingua →
    codice a partire dalle traduzioni, `LEVEL_SYNONYMS` per i livelli);
  - `profiles/0008_profile_email` (`Profile.email`, `EmailField`, blank).
### Backend
- `apps/cv/cv_parameters.py`: `SUPPORTED_CV_LANGUAGES = ["it","en","fr","de","es"]`,
  `FALLBACK_CV_LANGUAGE = "en"`.
- `apps/cv/ai_content.py`: nuovo campo obbligatorio `content_language` (enum)
  nello schema, con il relativo paragrafo nel prompt.
- `apps/cv/generation.py`:
  - `SECTION_LABELS` esteso a fr/de/es;
  - `_resolve_html_lang(user, content)`: `en` se la modalità è "english",
    altrimenti `content_language` se supportato, altrimenti `en`;
  - `_build_languages(profile, html_lang)`: traduce codice lingua e livello,
    mostrando il valore grezzo se un codice non è tradotto;
  - `_build_contact_parts`: usa `profile.email`.
- `apps/profiles/cv_import.py`: lo schema e il prompt estraggono `phone` ed
  `email` (solo se scritti letteralmente nel CV) e vincolano `languages` agli
  enum dei codici. In precedenza nemmeno il telefono veniva estratto.
- `apps/profiles/serializers.py`: `email` aggiunto a `ProfileSerializer`. La
  validazione delle lingue avviene tramite le `choices` del modello.
- `apps/cv/templates/cv/cv_template.html`: `.header` con `align-items: flex-end`.
### API
- `PATCH /api/profiles/me/` accetta `email`.
- `POST/PATCH /api/languages/` rifiutano valori fuori lista (400).
- `POST /api/profile/import-cv/` restituisce anche `phone` ed `email`.
### Frontend
- `components/ListSectionEditor.jsx`: supporto `field.options`, che rende il
  campo un menu a tendina.
- Nuovo `utils/languageOptions.js`: lingue ordinate alfabeticamente nella lingua
  dell'interfaccia, livelli in ordine di progressione.
- `i18n/translations.js`: `languageNames` e `languageLevels` (solo it/en),
  chiavi `profileEmail`/`profileEmailPlaceholder` ed `email`.
- `pages/onboarding/OnboardingPage.jsx` e `pages/ProfilePage.jsx`:
  - menu a tendina per lingua e livello;
  - campo "Email da mostrare sul CV";
  - nell'onboarding il pre-fill dall'import compila `phone` ed `email`; prima
    il telefono veniva sempre azzerato.

## Verifica
Verifiche end-to-end in produzione, riportate nella sessione del 2026-08-19:
- **Migrazione 0007:** le 16 righe `Language` esistenti sono state normalizzate
  correttamente.
- **CV rigenerato** di un utente di test su un'offerta in inglese:
  - etichette in inglese;
  - `2025 - Present` sull'esperienza in corso;
  - lingue tradotte (es. "Italian: Mother tongue").
- **Import CV:** mapping verificato (madrelingua → `mother_tongue`, C1 →
  `fluent`, B1 → `intermediate`, A2 → `elementary`).
- **API:** un valore libero viene rifiutato.
- **Email e foto:** senza `profile.email` la riga contatti omette l'email; foto
  allineata al filetto, verificata con un rendering PDF→PNG.
- **Build:** frontend pulito; PDF servito via Caddy.

Nessun test automatico aggiunto o aggiornato in questo sprint. Un test di
`apps/cv` (`test_job_language_mode_is_forwarded_to_content_generation`) è
rimasto disallineato dal nuovo campo `content_language`. È stato sistemato
solo il 2026-08-22, nello Sprint 42, aggiornando la fixture `_fake_content`.

## Note / cosa manca
- Le etichette fisse del CV coprono 5 lingue. Per un'offerta in un'altra lingua
  il contenuto è scritto in quella lingua, ma le etichette sono in inglese.
- Le traduzioni dei nomi lingua e dei livelli nel frontend esistono solo in
  it/en, cioè le lingue dell'interfaccia.
- La lista delle 36 lingue è estendibile solo da codice
  (`language_options.py` + `translations.js`).
- I valori legacy non riconosciuti dalla migrazione 0007 restano nel DB. Le
  `choices` non vengono applicate alle righe già esistenti.
- **Incidente operativo:** durante la verifica del campo email un valore di
  prova è stato scritto per errore sul profilo reale di un utente in produzione.
  È stato rimosso subito ed è stato segnalato al committente nella sessione.
- `Docs/03-specifiche-funzionali-contenuto-cv-v4.md` §4 e §10.1 dice ancora che
  le etichette "seguono `cv_language_mode`" e che `Language` è "invariato". Le
  specifiche madre non menzionano `Profile.email`.
