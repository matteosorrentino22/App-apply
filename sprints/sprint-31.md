# Sprint 31 — Pagina di modifica profilo post-onboarding

## Input
Segnalato dal committente durante i test: nessun modo di modificare il
profilo master dopo il completamento dell'onboarding. Verificato che le
specifiche funzionali lo richiedono esplicitamente (`01-specifiche-
funzionali-v5.md` righe 104, 117: "modificare il profilo master in
qualsiasi momento, con effetto sulle generazioni future") — gap reale, non
solo un problema di navigazione: l'API di aggiornamento profilo esisteva
già (usata dall'onboarding), ma non c'era alcun punto d'ingresso in UI dopo
il primo completamento.

## Obiettivo
Pagina dedicata `/profile`, separata dall'onboarding (Opzione B discussa
col committente: nessuna riscrittura dell'onboarding esistente, in modo da
poter differenziare in futuro i contenuti delle due pagine senza vincoli
di codice condiviso).

## Esito (2026-08-06)

### Nuova pagina `ProfilePage.jsx`
Carica il profilo esistente (`GET /api/profiles/me/`) e precompila tutti i
campi/sezioni; in salvataggio, ogni riga con un `id` reale (esistente sul
server) usa `PATCH`, le righe nuove (aggiunte in questa sessione) usano
`POST`, le righe rimosse rispetto al caricamento iniziale vengono
esplicitamente cancellate con `DELETE` — evita di duplicare esperienze/
istruzioni/competenze a ogni salvataggio, comportamento che si sarebbe
verificato riusando ingenuamente la logica di solo-creazione
dell'onboarding.

Riusa gli stessi componenti dell'onboarding (`ExperienceGroupEditor`,
`ListSectionEditor`) invece di duplicarli: entrambi già generici, bastava
passare dati precaricati con l'id reale come chiave di riga.

### Nuovo endpoint frontend
`updateSectionItem(section, id, payload)` in `api/profile.js` — mancava un
wrapper per `PATCH` sulle singole risorse di sezione (`create`/`delete`
esistevano già dall'onboarding).

### Testi dedicati, non condivisi con l'onboarding
Come richiesto esplicitamente dal committente (in vista di differenziare i
due flussi in futuro): nuovo namespace di traduzione `profile.*` (IT/EN)
per i testi specifici della pagina (titolo, sommario, promemoria limite
esperienze, messaggi di salvataggio/errore). Le etichette di campo generiche
(Azienda, Ruolo, Titolo di studio, Data inizio/fine...) restano condivise
sotto `onboarding.*`, essendo vere e proprie etichette di campo (non testo
di flusso) usate identicamente nei due contesti.
`ExperienceGroupEditor` reso parametrico su `titleKey`/`hintKey` (default
sulle chiavi onboarding esistenti, nessuna rottura del suo uso in
onboarding) per permettere lo stesso tipo di differenziazione futura anche
lì.

### Punto d'accesso
Link "Modifica profilo" nella pagina Account, verso `/profile` (nuova
route protetta in `App.jsx`).

### Verifica eseguita
- Backend: nessuna modifica — `python manage.py test` 166/166 passati
  (verifica di non regressione, gli endpoint `ModelViewSet` già
  supportavano PATCH/DELETE dallo Sprint 26).
- Verificato via richieste HTTP reali contro l'ambiente di produzione (non
  mock) sull'utente reale segnalato dal committente: `POST`/`PATCH`/`DELETE`
  su `/api/educations/` tutti funzionanti come attesi dalla nuova pagina.
- Frontend: `npm run build` pulito; `oxlint` sui file toccati — 0 errori (2
  warning preesistenti non introdotti in questo sprint).

### Cosa manca
- Nessun test e2e Playwright dedicato scritto per questo sprint (limite
  ambientale noto, non eseguibile in questo sandbox — vedi sprint
  precedenti).
- `ExperienceGroupEditor` non gestisce ancora `technologies`/`start_date`/
  `end_date` per le esperienze (gap preesistente allo Sprint 27, non
  introdotto né risolto qui — l'utente può comunque aggiungere/rimuovere
  esperienze con azienda/ruolo/località/bullet, sufficiente per sbloccare
  la generazione CV).
