# Sprint 10 — Generazione CV (pipeline)

## Input
- Sprint 04 completato (profilo); modello `CVDocument` (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.7; `02-specifiche-tecniche-v3.md` §3.6, §6.

## Obiettivo
Servizio di generazione CV: raccolta contesto (profilo + job + arricchimento opzionale) → chiamata Claude per i contenuti → composizione template HTML flessibile (numero di esperienze variabile, sezione istruzione invariata, foto opzionale, lingua) → conversione PDF con WeasyPrint → salvataggio in `CVDocument`.

## Risultato atteso
Dati un `Profile` e un `Job`, invocando il servizio si ottiene un `CVDocument` con `html_source` e `pdf_file` popolati, rispettando 1 pagina, l'opzione foto, la lingua richiesta e la sezione istruzione identica al profilo.

## Criteri di verifica
- Invocando il servizio su un profilo di test con 3 esperienze e uno con 1 sola esperienza, l'HTML generato contiene rispettivamente 3 e 1 blocchi "esperienza" (nessun placeholder fisso).
- Il PDF generato risulta di 1 pagina per un profilo di dimensioni standard di test (verifica sul numero di pagine del PDF).
- Con `cv_include_photo=False` il PDF non contiene l'immagine anche se il profilo ha una foto caricata; con `True` la contiene.
- Il testo della sezione istruzione nel PDF/HTML corrisponde esattamente ai dati di `Education` del profilo, senza riformulazione.
- Con `cv_language_mode='english'` il contenuto è in inglese indipendentemente dalla lingua della job description di test; con `'job_language'` segue la lingua della job description di test.
- Il `CVDocument` salvato referenzia correttamente `job` e `user`.

## Output per lo sprint successivo
Servizio di generazione CV riusabile sia dal ciclo notturno automatico (Sprint 11) sia dalla generazione manuale (Sprint 12).

---

## Esito (2026-07-26)

**Stato: completato.**

### Cosa è stato fatto
- `apps.cv.ai_content.generate_cv_content(profile, job, cv_language_mode, enrichment)` — chiama Claude (structured output via JSON schema, `thinking` disabilitato, come già in `apps.jobs.ai_scoring`) per produrre i contenuti su misura: `summary` riformulato, `key_achievements`, un elenco `experiences` (stesso numero di quelle del profilo, riordinabili per rilevanza, mai aggiunte/omesse), `skills` selezionate. Il prompt vieta esplicitamente di inventare esperienze/competenze non presenti nel profilo (grounding, §6.2 tecniche) e istruisce la lingua richiesta (`english` fisso oppure la lingua della job description).
- `apps.cv.rendering.render_cv(context)` — compone il template Django `apps/cv/templates/cv/cv_template.html` (HTML/CSS con ciclo `{% for %}` sulle esperienze, foto opzionale, tutte le altre sezioni condizionali) e lo converte in PDF con **WeasyPrint** (nuova dipendenza, richiesta esplicitamente da CLAUDE.md/§3.6 tecniche — non arbitraria). Applica progressivamente 3 livelli di compattamento CSS (dimensione font/spaziatura) finché il PDF non risulta di 1 pagina, controllando `len(document.pages)` prima di serializzare il PDF — copre il criterio "1 pagina" senza introdurre una libreria di conteggio pagine separata.
- `apps.cv.generation.generate_cv(job, generation_type, enrichment="")` — orchestrazione completa: prende `job.user.profile`, chiama `generate_cv_content`, costruisce il contesto di rendering (nome/contatti da `User`+`Profile`, foto solo se `cv_include_photo=True` e presente, sezione istruzione presa **direttamente da `Education`** — mai passata a Claude, quindi verbatim per costruzione — competenze filtrate all'intersezione con quelle reali del profilo come ulteriore guardia di grounding), salva `CVDocument` (`html_source`, `pdf_file`, `generation_type`, `enrichment_used`) referenziando `job` e `user`. Solleva l'eccezione al chiamante in caso di fallimento: la gestione (stato Job, quota/credito, `RunLog`) resta responsabilità di chi orchestra la generazione (Sprint 11 automatico, Sprint 12 manuale), non di questo servizio.
- **Decisione tecnica non esplicitamente richiesta, da segnalare**: aggiunti a `Profile` i campi `phone`, `city`, `linkedin_url` (migrazione `profiles.0002`). Non sono un'estensione arbitraria: `02-specifiche-tecniche-v3.md` §6.3 richiede esplicitamente che "nome, contatti, città, link LinkedIn stanno in User/Profile e vengono iniettati nell'HTML", ma nessuno di questi campi (a parte nome/email, già su `User` via `AbstractUser`) era stato creato nello Sprint 04 — un'omissione di quello sprint che questo servizio di generazione rende necessario colmare ora. Esposti anche in `ProfileSerializer` per restituirli/modificarli dall'API esistente, senza nuovi endpoint.
- `ANTHROPIC_CV_GENERATION_MODEL` (default `claude-opus-5`) aggiunto in `settings.py`/`.env.example`, distinto da `ANTHROPIC_CV_PARSING_MODEL` (usato per il parsing del CV caricato in onboarding, Sprint 05): stesso default ma parametro separato, perché sono due domini di utilizzo diversi (§3.5 tecniche prevede "una famiglia più economica per lo scoring ad alto volume, una più capace per il CV" — qui si applica la famiglia più capace).

### Verifica eseguita
`python manage.py test apps.cv` (9/9, con rendering PDF reale via WeasyPrint e verifica delle immagini incorporate via `pdfplumber`, non mockati — solo la chiamata a Claude è mockata, stesso schema di mocking già adottato per scoring/raccolta) e `python manage.py test` sull'intero progetto (35/35, nessuna regressione); `makemigrations --check` pulito.

| Criterio | Esito |
|---|---|
| HTML con 3 blocchi "esperienza" per profilo a 3 esperienze, 1 per profilo a 1 esperienza (nessun placeholder fisso) | ✅ |
| PDF di 1 pagina per un profilo di dimensioni standard di test | ✅ (verificato con `pdfplumber`, conteggio pagine reale) |
| `cv_include_photo=False` → PDF senza immagine anche con foto profilo caricata; `True` → PDF con l'immagine | ✅ (verificato sia su `html_source` sia sulle immagini incorporate nel PDF via `pdfplumber`) |
| Sezione istruzione nel PDF/HTML identica ai dati di `Education`, senza riformulazione | ✅ (per costruzione: `Education` non passa mai per Claude) |
| `cv_language_mode='english'` → contenuto in inglese indipendentemente dalla lingua della job description; `'job_language'` → segue la lingua della job description | ✅ (verificato che la modalità sia inoltrata correttamente a `generate_cv_content` e che l'attributo `lang` dell'HTML rifletta la scelta; la traduzione effettiva dipende da Claude, non verificabile in sandbox — vedi "Cosa manca") |
| `CVDocument` referenzia correttamente `job` e `user` | ✅ |

### Cosa manca
- Nessuna verifica end-to-end reale della chiamata Claude (contenuti effettivamente tradotti/riformulati) — stessa riserva già registrata per scoring e parsing CV negli sprint precedenti; la logica di composizione/rendering è comunque interamente testata con contenuti mockati.
- Collegamento al ciclo notturno per i Job 4–5 (stato `cv_generated`, gestione fallimento): Sprint 11.
- Guardia di concorrenza (`cv_generation_in_progress`), quota/credito e riserva all'accodamento per la generazione manuale: Sprint 12.
