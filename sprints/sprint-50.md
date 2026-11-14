# Sprint 50 — Messaggi di networking (LinkedIn/email) per chiedere una raccomandazione

> **Scheda retroattiva** — ricostruita il 2026-11-14 da commit, codice e storico sessioni; non redatta a fine sprint.
> **Periodo:** 2026-10-11 · **Commit:** `df7fc67`

## Input
Richiesta del committente (11/10): nel dettaglio di un job, oltre a CV e
cover letter, poter generare anche un **messaggio da inviare via LinkedIn
o email** all'hiring manager o a un'altra persona, per farsi raccomandare
o presentare per quella posizione. Struttura "molto simile alla cover
letter"; richiesta esplicita di domande e proposte prima di sviluppare.

Nel corso della discussione il committente ha proposto di leggere il
profilo del destinatario con uno scraper Apify dedicato, poi ha deciso di
partire con il resto dello sviluppo e di inserire lo scraping in un
rilascio successivo.

La sessione di lavoro di questo sprint non è più disponibile: le decisioni
qui sotto sono ricostruite dal messaggio di commit e dal codice, e non si
può dire con certezza quali siano venute dal committente e quali siano
state proposte dall'assistente e accettate.

## Decisioni prese
- **Stessa struttura della cover letter** (Sprint 42): contenuto via
  Claude → servizio di generazione → orchestratore con guardia di
  concorrenza, quota/credito e `RunLog` in caso di fallimento.
- **Nessun PDF**: il risultato è testo da copiare nel client
  (LinkedIn/email), quindi niente template HTML né WeasyPrint. Per l'email
  c'è anche un oggetto.
- **Canale selezionabile** `linkedin` | `email`: cambia tono, lunghezza e
  struttura nel prompt (un messaggio unico per entrambi i canali sarebbe
  stato mediocre su tutti e due).
- **Storico per job**, non "solo l'ultimo" come per CV e cover letter: sullo
  stesso job ha senso scrivere a più destinatari (contatto interno,
  recruiter, hiring manager), quindi ogni generazione aggiunge un messaggio
  e non ne sostituisce nessuno.
- **Regole di prompt specifiche**: niente relazione pregressa con il
  destinatario se l'utente non l'ha dichiarata (per default si tratta come
  un primo contatto, cioè cold outreach); nessuna menzione di allegati;
  firma con il nome reale del candidato, mai un placeholder.
- **Budget indipendente**: stessi tetti Free 1/giorno e Pro 10/giorno di
  CV e cover letter, ma con un contatore separato. Oltre il tetto si paga
  a credito con un prezzo dedicato (`PRICE_REFERRAL_MESSAGE_EXTRA`,
  default 1,00).
- **Link LinkedIn del destinatario**: il campo viene salvato, ma non è
  ancora usato per personalizzare il messaggio. Per leggere il profilo
  servirebbe un nuovo scraping Apify dedicato, rimandato.
- **Test scritti subito**, a differenza della cover letter, che non ne ha.

## Implementazione

### Modello dati
- Nuovo `ReferralMessageDocument` (`apps/cv/models.py`) con i campi `job`,
  `user`, `channel` (`linkedin` | `email`), `recipient_name`,
  `recipient_linkedin_url` (URLField, 500 caratteri, salvato ma inerte),
  `instructions_used`, `subject` (vuoto per LinkedIn), `content` e
  `generated_at`. Migrazione `cv/0005_referralmessagedocument`.
- `DailyQuota.referral_message_count`, `Job.referral_message_generation_in_progress`
  (guardia di concorrenza, indipendente da quelle di CV e cover letter) e
  nuovo `RunLog.TaskType.REFERRAL_MESSAGE_GENERATION`. Migrazione
  `jobs/0012_dailyquota_referral_message_count_and_more`.
- Il messaggio non tocca mai `Job.status`.

### Backend
- `apps/cv/referral_message_content.py`: `generate_referral_message_content`
  chiama `call_claude_structured` con `BEDROCK_CV_GENERATION_MODEL`,
  `max_tokens=1500` e `effort="medium"`. Lo schema è `{subject, message}`.
  Il prompt fissa questi limiti:
  - LinkedIn: al massimo 80-100 parole (3-5 frasi), nessun oggetto;
  - email: oggetto specifico di circa 60 caratteri al massimo, corpo di
    150-180 parole al massimo in 2-3 paragrafi;
  - saluto e firma stanno nel testo; se il destinatario non ha un nome si
    usa un saluto generico;
  - grounding sul profilo reale, nessun allegato menzionato, richiesta
    finale chiara e specifica.

  Il contenuto utente include il profilo (`_build_profile_context`), il
  nome del candidato (`_build_full_name`), l'offerta, il canale, il nome
  del destinatario, le indicazioni e la lingua (`_resolve_language`, la
  stessa regola del CV).
- `apps/cv/referral_message_generation.py`: `generate_referral_message`
  crea la riga `ReferralMessageDocument`. Non fa nessun rendering.
- `apps/cv/referral_message_manual_generation.py`:
  - `request_referral_message_generation` segue lo schema guardia
    (`select_for_update` sul Job) → riserva quota o credito → generazione →
    reset del flag. Se la generazione fallisce, restituisce quota o credito,
    scrive un `RunLog` FAILURE e solleva `ReferralMessageGenerationFailed`.
  - `get_recent_instructions` restituisce al massimo 20 istruzioni
    distinte, su tutti i job dell'utente, dalla più recente.
  - `get_messages_for_job` restituisce lo storico del job.
- `config/settings.py`: `PRICE_REFERRAL_MESSAGE_EXTRA` (default `1.00`).

### API
- `POST /api/jobs/<id>/generate-referral-message/`, con body `{channel,
  recipient_name?, recipient_linkedin_url?, instructions?}`:
  - 201 con il messaggio serializzato (`id, channel, recipient_name,
    recipient_linkedin_url, subject, content, generated_at`);
  - 400 se il canale non è valido;
  - 409 se il job è già in generazione, oppure se il tetto è raggiunto e il
    credito non basta;
  - 502 se la generazione fallisce.
- `GET /api/jobs/<id>/referral-messages/`: storico del job, dal più recente.
- `GET /api/referral-message-instructions/`: `{instructions: [...]}`.

### Frontend
- `api/jobs.js`: `generateReferralMessage`, `fetchReferralMessages`,
  `fetchReferralMessageInstructions`.
- `JobDetailPage.jsx`:
  - nuovo pulsante "Genera messaggio" accanto a quelli di CV e cover letter;
  - un dialog con canale (toggle LinkedIn/Email), nome del destinatario,
    link LinkedIn del destinatario, indicazioni libere e checkbox per
    riusare indicazioni precedenti (concatenate con una riga vuota);
  - la card "Messaggi di networking generati" mostra badge del canale,
    destinatario, data, oggetto, testo e un pulsante "Copia"
    (`navigator.clipboard`). Per l'email il testo copiato comincia con la
    riga "Oggetto: …";
  - lo storico si carica all'apertura della pagina, e il nuovo messaggio
    viene messo in cima senza ricaricare.
- `i18n/translations.js`: chiavi `jobs.referral*` e
  `jobs.generateReferralMessage` (it/en).

## Verifica
Dal messaggio di commit (la sessione non è disponibile, quindi non ci sono
conteggi della suite):
- Generazione reale end-to-end, LinkedIn ed email, con e senza nome del
  destinatario. Durante la prova è emerso e stato corretto un difetto: il
  modello firmava con un placeholder del tipo "[Nome]", perché il nome del
  candidato non veniva passato nel prompt. Ora viene passato.
- Test aggiunti:
  - `apps/cv/tests.py` `ManualReferralMessageGenerationTests`, 8 test:
    quota Free, più messaggi sullo stesso job, concorrenza, rifiuto senza
    credito, prosecuzione a credito, rimborso di quota e di credito in caso
    di fallimento, istruzioni recenti deduplicate;
  - `apps/jobs/tests.py` `GenerateReferralMessageApiTests`, 4 test:
    generazione, canale non valido, storico, istruzioni.

## Note / cosa manca
- **Backlog:** lo scraping del profilo LinkedIn del destinatario per
  personalizzare il messaggio non è implementato. `recipient_linkedin_url`
  viene salvato e restituito dall'API, ma non arriva al prompt e non
  compare nella card dello storico.
- `JobSerializer` non espone `referral_message_generation_in_progress`.
  Il frontend lo legge (`job.referral_message_generation_in_progress`), ma
  il valore è sempre indefinito: il pulsante si disabilita solo durante la
  richiesta locale. La guardia lato server resta comunque attiva.
- `.env.example` non elenca `PRICE_REFERRAL_MESSAGE_EXTRA`; vale il default
  di `settings.py`.
- I messaggi non si possono modificare né cancellare dall'app, e non c'è un
  messaggio di chiusura dell'email oltre a quello già nel testo.
- `ReferralMessageDocument` non è registrato nel Django Admin.
- Le specifiche funzionali e tecniche non descrivono la funzionalità.
