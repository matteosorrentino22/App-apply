# Sprint 36 — Fix salvataggio profilo con data inizio istruzione vuota

## Input
Segnalazione del committente (utente +1): dopo aver cliccato "Salva" in
Modifica profilo, errore generico "Non siamo riusciti a salvare il
profilo. Riprova." Tre domande: cosa indica, perché non si salva, perché
il messaggio non è parlante.

## Diagnosi (2026-08-09)
Verificato lato server che tutti i dati già salvati dell'utente (6
esperienze, 6 istruzioni) vengono accettati senza errori dal backend —
il problema non era nei dati esistenti ma nel flusso di invio.

Causa isolata riproducendo direttamente la chiamata `POST/PATCH
/api/educations/`: inviare `start_date: ""` (stringa vuota, non `null`)
restituisce `400 {"start_date": ["La data è in un formato errato..."]}`.
`Education.start_date` è nullable ma non accetta una stringa vuota come
valore data — serve esplicitamente `null`.

`flattenEducations` (`ProfilePage.jsx`) normalizzava già `end_date` a
`null` se vuoto (per la spunta "in corso", Sprint 34) ma **non**
`start_date`: se l'utente lascia vuoto il campo "Data inizio" su una voce
di Istruzione — campo non obbligatorio nel form — al salvataggio viene
inviata la stringa vuota così com'è, e il backend la rifiuta. Lo stesso
problema esisteva nel payload di creazione istruzione in
`OnboardingPage.jsx` (nessuna normalizzazione delle date lì).

Il messaggio generico era dovuto a un `catch` che scartava sempre il
corpo della risposta di errore del backend (`ProfilePage.jsx` e
`OnboardingPage.jsx`), mostrando un testo fisso indipendentemente dalla
causa reale.

## Esito
- `ProfilePage.jsx`: `flattenEducations` ora normalizza anche
  `start_date` a `null` se vuoto (stesso pattern già usato per
  `end_date`).
- `OnboardingPage.jsx`: normalizzazione di `start_date`/`end_date`
  aggiunta anche al payload di creazione istruzione in
  `handleProfileSubmit` (mancava del tutto).
- Nuovo `frontend/src/utils/apiErrors.js` con `formatApiErrorDetail`:
  estrae il dettaglio dei campi non validi da un `ApiError` di DRF
  (`{campo: [messaggi]}`) e lo aggiunge tra parentesi al messaggio
  d'errore esistente in `ProfilePage.jsx`/`OnboardingPage.jsx`, invece di
  scartarlo — così un futuro errore di validazione indica il campo
  incriminato senza dover guardare i log del server.

### Verifica eseguita
- Riprodotto il bug via chiamata diretta all'API di produzione
  (`start_date: ""` → 400) e confermato che con la normalizzazione a
  `null` la stessa richiesta va a buon fine (`201`).
- `npm run build`: pulito.
- Righe/utenti di test creati per la diagnosi eliminati subito dopo la
  verifica.

### Cosa manca
- Nessun altro punto aperto su questa segnalazione. Resta valido quanto
  già segnalato negli sprint precedenti.
