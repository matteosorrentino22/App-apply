# Sprint 37 — Fix duplicazione righe profilo su salvataggio ripetuto

## Input
Il committente (utente +1) segnala che l'errore "Non siamo riusciti a
salvare il profilo. Riprova." persiste anche dopo il fix dello Sprint 36,
e che ora il salvataggio è anche più lento. Conferma di aver inserito la
data di inizio in tutte le sezioni.

## Diagnosi (2026-08-09/10)
Verificato che il fix dello Sprint 36 (`start_date` normalizzato a
`null`) era effettivamente in produzione e funzionante — confermato
ispezionando il bundle JS minificato servito dal browser. Ispezionando i
dati reali del profilo (`user_id=3`) è emerso il problema vero: **righe
duplicate multiple** — "Police of Netherlands" presente 6 volte
(invece di 1), "Technology University of Delft" e "CAMPUS EINA
Zaragoza" 4 volte ciascuna (invece di 1), tutte con contenuto identico.

Causa radice, in `saveSection` (`ProfilePage.jsx`) e nel corpo
equivalente di `handleProfileSubmit` (`OnboardingPage.jsx`): una riga
appena creata con successo (`POST`) non veniva mai riportata nello stato
locale del form con l'id reale ricevuto dal server. Se un salvataggio
falliva su una sezione successiva (o l'utente cliccava di nuovo "Salva"
dopo aver visto l'errore, comportamento naturale), al tentativo
successivo quella riga aveva ancora una `_key` locale (stringa) e veniva
quindi ricreata da capo — duplicandola — invece di essere riconosciuta
come "già esistente" e aggiornata. Ogni salvataggio ripetuto aggiungeva
un'altra copia: spiega sia i duplicati sia il rallentamento percepito
(sempre più righe da inviare ad ogni tentativo).

## Esito
- `ProfilePage.jsx`: `saveSection` ora ritorna le righe salvate con
  l'id reale del server sostituito alla `_key` locale per ogni riga
  creata; `handleSubmit` aggiorna `companies`/`educations`/`sections` (e
  i corrispondenti `initial*Ids`) con questi valori subito dopo ogni
  sezione salvata, non solo a fine form — così un secondo tentativo,
  anche se una sezione successiva fallisce, riconosce le righe già
  create e le aggiorna invece di duplicarle.
- `OnboardingPage.jsx`: stessa protezione (`isCreatedRow`) applicata al
  ciclo di creazione di esperienze/istruzione/competenze in
  `handleProfileSubmit` — una riga con id reale (già creata in un
  tentativo precedente) viene saltata invece di essere rimandata come
  nuova.
- Dati duplicati già presenti sul profilo dell'utente +1 rimossi
  manualmente dopo conferma esplicita dell'utente (5 esperienze e 6
  istruzioni duplicate eliminate, mantenuta una sola copia di ciascuna).

### Verifica eseguita
- `npm run build`: pulito.
- Verificata la causa radice riproducendo la sequenza di richieste reali
  della pagina (Django test client) sui dati duplicati esistenti,
  confermando che tutte venivano accettate individualmente dal server —
  escludendo un problema di validazione e isolando il bug al codice
  frontend che decide se creare o aggiornare una riga.
- Non è stato possibile riprodurre in questo sprint l'errore generico
  "Non siamo riusciti a salvare" stesso (nessuna richiesta fallita
  trovata sui dati reali dell'utente dopo la pulizia): resta da
  verificare con l'utente se, dopo il redeploy di questo fix, il
  salvataggio va a buon fine in condizioni normali.

### Cosa manca
- Nessuna correzione ha ancora una causa "confermata" al 100% per
  l'errore generico originale (il messaggio non riportava mai il
  dettaglio del campo prima dello Sprint 36): la duplicazione era di
  sicuro un problema reale e ora corretto, ma se l'errore dovesse
  ripresentarsi il messaggio più parlante introdotto nello Sprint 36
  aiuterà a identificare la causa esatta senza dover ispezionare i log
  del server.
