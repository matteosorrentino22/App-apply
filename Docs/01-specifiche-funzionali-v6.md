# Specifiche Funzionali — App di ricerca lavoro e generazione CV

> **Documento:** 01 — Specifiche funzionali
> **Versione:** 6 — descrive l'as-is al 2026-11-14 (Sprint 66 sicurezza, Sprint 67 privacy e GDPR, Sprint 68 lista job, scoring e raccolta, Sprint 69 generazione, editor e chat, Sprint 70 account, profilo, notifiche e frontend, Sprint 71 testi del server in italiano e inglese, Sprint 73 navigazione a 3 voci, Sprint 74 lista Jobs, Sprint 75 dettaglio job e Sprint 76 editor del redesign UI)
> **Stato:** corrente. Documento vivo: va aggiornato nello stesso commit dello sprint che cambia il comportamento dell'app (regola in `CLAUDE.md` → "Workflow sprint").
> **Ambito:** descrive *cosa fa oggi* l'applicazione (non *come* è costruita).
> **Riferimenti incrociati:**
> - specifiche tecniche (modello dati, flussi, API, test): `Docs/02-specifiche-tecniche-v5.md`;
> - contenuto e impaginazione del CV (selezione delle esperienze, budget dei bullet, qualifica, Areas of Expertise, istruzione, overflow, editor e chat): `Docs/03-specifiche-funzionali-contenuto-cv-v5.md`.
>
> **Regola di prevalenza.** Per le regole di contenuto e di impaginazione del CV **prevale il documento 03**. Questo documento ne riporta solo una sintesi (§4.7, §4.16, §4.17).
>
> **Numerazione.** I paragrafi §1–§8 e §4.1–§4.12 mantengono la numerazione e il significato delle versioni precedenti, perché il codice li cita. Le funzioni nate dopo la v5 sono in coda a §4 (§4.13–§4.22). In §5 le voci non più escluse restano come segnaposto numerato; in §8 i punti risolti restano come segnaposto e i nuovi si aggiungono in coda a ciascun gruppo con numeri successivi all'ultimo usato.

---

## Nota di versione (v6)

La v6 fonde le due versioni divergenti precedenti: la v4 in radice, che aveva recepito lo sprint-39 e lo sprint-47 ma non il documento 03, e la v5 in `Docs/`, che aveva recepito il documento 03 ma non gli sprint 39 e 47. Allinea poi il testo a quanto fatto negli sprint 40–64. Novità rispetto a v4/v5:

1. **Niente più CV automatici** (Sprint 45). Il ciclo notturno fa solo raccolta e scoring. Ogni CV si genera su richiesta, per qualunque punteggio (§4.4, §4.7).
2. **Niente più limiti di raccolta** (Sprint 46): via il tetto di 50/100 job per notte e il cap di intake di 15 job al giorno. Resta solo il limite tecnico di 150 risultati per chiamata alla fonte (§4.4).
3. **Punteggio da 1 a 10** con rubrica per fascia (Sprint 47). Match e gap hanno una motivazione espandibile (Sprint 46). Il punteggio è limitato a 3 se l'offerta richiede una lingua assente dal profilo (Sprint 48) (§4.4).
4. **Ricerche di tipo Job role / Company** (sprint-39), 1 attiva per tipo sul piano Free (§4.2).
5. **"Colma i gap" al posto dell'arricchimento del profilo** (Sprint 44) (§4.8).
6. **Lista job** (Sprint 46, 63, 64):
   - quattro sezioni, con l'aggiunta di Preferiti;
   - intervallo di date al posto dei periodi preimpostati;
   - nuovi filtri: location, ricerca di provenienza (multi-selezione), candidati, recruiter;
   - filtri preferiti salvabili;
   - badge candidati e icona recruiter (§4.5, §4.21).
7. **"Candidatura fatta" marcabile anche senza CV** (Sprint 46) (§4.6, §4.10).
8. **Statistiche e raccolta manuale "Raccogli ora"**, 1 al giorno (Sprint 44; dallo Sprint 73 in un pannello della lista, la Home è eliminata) (§4.13, §4.14).
9. **Creazione manuale di un job**, Free e Pro, 3 al giorno (Sprint 43) (§4.15).
10. **Editor del CV** (Sprint 51) **con chat AI** a proposta e conferma (Sprint 59–62) (§4.16, §4.17).
11. **Cover letter in PDF** (Sprint 42), con editor e chat (Sprint 63) (§4.18, §4.19).
12. **Messaggi di networking** LinkedIn/email (Sprint 50) (§4.20).
13. **Profilo** (Sprint 41): lingue e livelli a valori fissi; email da mostrare sul CV separata da quella di login. Navigazione con le pagine Home, Jobs, Profilo e Impostazioni (Sprint 44, 46) (§4.1, §4.22).
14. **Monetizzazione**: 6 massimali giornalieri distinti più 2 azioni sempre a credito (le chat). I prezzi hanno valori di default configurati. Nessun voucher esiste (§4.11).
15. **Motore AI** (Sprint 40): Claude via AWS Bedrock. Nessun effetto funzionale visibile; dettaglio nelle tecniche.
16. Il **profilo master ha 5 sezioni**, senza "risultati chiave" (dal documento 03). Il **vincolo reale** è "almeno 1 voce di istruzione", verificato solo al momento della generazione del CV. La data di fine dell'istruzione **non** è obbligatoria (istruzione in corso ammessa).

## Storico versioni (sintesi)

- **v1 → v2:** due massimali separati (import e generazione manuale); generazione manuale come unico meccanismo di (ri)generazione, aperta a tutti i piani; ricerca testuale confinata alla sezione; uscita automatica dall'archivio; regole di downgrade con più di 10 ricerche; credito caricato manualmente.
- **v3:** foto nel CV attivabile o disattivabile; credito extra come pool unico.
- **v4** (revisione delle criticità, luglio 2026):
  - credito come saldo in €;
  - eliminato il Word;
  - limiti di raccolta 50/100 per notte e tie-break del cap;
  - definizione di "nuovi job" per la notifica;
  - generazione concorrente bloccata;
  - scoring fallito = offerta scartata;
  - "apertura immediata" intesa come reattività, non come cache offline.

  Poi aggiornata in place con sprint-39 (tipo di ricerca) e sprint-47 (punteggio 1–10).
- **v5** (agosto 2026): recepisce il documento 03 v3:
  - profilo a 5 sezioni;
  - Areas of Expertise come contenuto generato;
  - istruzione "non riformulata";
  - arricchimento ristretto alle esperienze esistenti;
  - qualifica professionale;
  - vincoli minimi del profilo.
- **v6** (14/11/2026): fusione di v4 e v5 e allineamento all'as-is degli sprint 40–64 (vedi nota sopra). Le versioni superate sono in `Docs/archivio/`. Aggiornata in place con lo Sprint 66 (sicurezza), lo Sprint 67 (privacy e GDPR: consensi in registrazione, verifica dell'email, recupero e cambio password, export e cancellazione dell'account, pagine legali, preferenza notifiche, avviso AI), lo Sprint 68 (lista, scoring, raccolta), lo Sprint 70 (contatori e prezzi visibili, fuso orario, cambio email, logout ovunque, notifiche al logout, pagina Profilo completa, avviso di nuova versione) e lo Sprint 71 (messaggi del server e notifiche nella lingua dell'interfaccia).

---

## 1. Obiettivo del prodotto e problema che risolve

L'applicazione centralizza e automatizza il lavoro ripetitivo della ricerca di impiego. Oggi ogni candidato ripete a mano lo stesso ciclo: cerca posizioni, capisce quali sono davvero adatte al suo profilo, riscrive CV e lettera su misura per ognuna e prepara i messaggi ai contatti.

Il prodotto toglie la parte ripetitiva:
- raccoglie ogni notte le offerte che corrispondono alle ricerche dell'utente;
- ne valuta l'affinità con il profilo e spiega cosa combacia e cosa manca;
- su richiesta, per ogni offerta, produce con un clic un **CV personalizzato**, una **cover letter** e **messaggi di networking**, che l'utente può rifinire in un editor con un assistente AI.

L'utente definisce una volta profilo e ricerche. Da lì l'app lavora in background e ogni mattina presenta una lista di opportunità già valutate e ordinate. Il valore centrale è *"svegliarsi con la selezione già fatta"*: non cercare, non filtrare, e avere i documenti di candidatura pronti in pochi clic, senza riscriverli da zero.

> **Rispetto alle versioni precedenti.** La promessa originale ("CV già pronti al risveglio per le offerte più affini") non vale più: dallo Sprint 45 nessun CV viene generato in automatico. Ogni documento si produce su richiesta (§4.7).

**Confine del problema risolto:** il prodotto arriva fino ai documenti pronti e al link della candidatura. La candidatura vera e propria resta manuale: l'utente si candida sul portale di origine. L'app offre un tracciamento minimo ("candidatura fatta") come punto unico da cui vedere a che punto è ciascuna offerta. L'automazione della candidatura è fuori perimetro.

**Cadenza:** il ciclo è giornaliero.
- I nuovi job vengono raccolti di notte (02:00, ora italiana) e sono disponibili dal mattino.
- Alle 10:00 locali l'utente riceve una notifica, se ci sono offerte nuove.
- Una volta al giorno l'utente può avviare anche una raccolta manuale (§4.14).

---

## 2. Utenti target e bisogni principali

Il prodotto serve chi cerca lavoro, in modo attivo o passivo, e vuole massimizzare le candidature di qualità riducendo al minimo il tempo manuale.

**Utente primario: la persona in transizione di carriera.** In caso di conflitto tra esigenze, si decide a suo favore.

**Utenti supportati ma non prioritari:**
- il **professionista occupato o passivo**, che valuta il mercato pur avendo già un lavoro e vuole poche segnalazioni, ma molto rilevanti;
- il **candidato ad alto volume**, che cerca attivamente e vuole molte offerte e documenti pronti.

**Bisogni principali dell'utente primario:**
1. non dover mai riscrivere CV e lettera a mano;
2. capire a colpo d'occhio, già nella lista, se un job può interessargli, senza leggere tutta la descrizione. Lo aiutano titolo, azienda, località, punteggio e soprattutto l'elenco di *cosa manca* rispetto al suo profilo. Da lì decide se aprire il dettaglio, salvare il job tra i preferiti o archiviarlo (con uno swipe).

**Nota sull'affinità e la persona in transizione.** Lo scoring misura l'affinità con il **profilo master**, cioè con l'esperienza reale attuale. Non misura il gradimento né l'affinità con un obiettivo futuro. Chi è in transizione cerca per definizione ruoli diversi dal proprio passato, quindi il suo punteggio sarà spesso basso proprio sui ruoli che desidera. L'app la sostiene **a valle**:
- la generazione del CV è su richiesta e disponibile su qualunque job, a prescindere dal punteggio;
- con **"colma i gap"** (§4.8) il modello può far emergere le lacune selezionate, ampliando esperienze reali;
- l'**editor con chat AI** (§4.16–§4.17) permette di rifinire il CV;
- la **cover letter** (§4.18) accetta indicazioni libere, anche su fatti non ancora presenti nel profilo.

La definizione di scoring resta invariata (vedi §8).

---

## 3. User stories / casi d'uso principali

Formato: *come [utente], voglio [azione], per [beneficio]*.

### Setup e onboarding
- Come utente, voglio **registrarmi con email e password**, per avere un account personale. *(Il login con Google è implementato ma non è configurato in produzione e il pulsante è nascosto: vedi §4.1.)*
- Come utente, voglio **leggere informativa privacy e termini di servizio e dare i consensi obbligatori** (informativa letta, termini accettati, età minima di 16 anni) al momento della registrazione, per sapere come vengono trattati i miei dati (Sprint 67).
- Come utente, voglio **confermare il mio indirizzo email** con un link, così nessuno può registrarsi a mio nome (Sprint 67).
- Come utente, voglio **dichiarare la mia situazione o il mio obiettivo** in onboarding. *(Il dato viene salvato ma non ha effetti: vedi §5.)*
- Come utente, voglio **costruire il mio profilo master in sezioni** (sommario, esperienze, istruzione, competenze e certificazioni, lingue), più i dati di contatto (telefono, email da mostrare sul CV, città, LinkedIn), per avere un'unica fonte di verità per i miei documenti.
- Come utente, voglio **pre-compilare il profilo caricando un CV esistente** (PDF o Word) e poi correggerlo, per non partire da zero.
- Come utente, voglio **caricare una foto** e **scegliere se includerla nel CV**.
- Come utente, voglio **scegliere la lingua dei documenti generati**: sempre in inglese, oppure nella lingua dell'offerta.
- Come utente, voglio **creare la prima ricerca già in onboarding**, per ricevere offerte dalla notte stessa.

### Ricerche
- Come utente, voglio **creare ricerche salvate con tipo, keywords e località**, per raccogliere solo le offerte pertinenti.
- Come utente, voglio **scegliere se una ricerca è per ruolo (*Job role keyword*) o per azienda (*Company*)**, per distinguere "voglio questo tipo di ruolo" da "voglio lavorare in questa azienda".
- Come utente, voglio **attivare o disattivare una ricerca senza cancellarla**, per decidere cosa gira ogni notte.
- Come utente Free, voglio **sapere che posso tenere attiva una sola ricerca per tipo** e che attivandone un'altra dello stesso tipo la precedente si disattiva.

### Ciclo quotidiano e lista
- Come utente, voglio **ricevere una notifica alle 10:00** quando ci sono nuovi job.
- Come utente, voglio **vedere le mie statistiche** (pannello "Raccogli nuovi job" della lista) (job trovati, CV generati, candidature fatte: oggi, ultima settimana, totali).
- Come utente, voglio **avviare una raccolta manuale ("Raccogli ora")**, al massimo una volta al giorno, per non aspettare la notte.
- Come utente, voglio **vedere la lista dei job ordinata per punteggio**, con titolo, azienda, località, punteggio, gap principali, numero di candidati e presenza di un recruiter, per decidere rapidamente cosa approfondire.
- Come utente, voglio **filtrare la lista** per intervallo di date, località, ricerca di provenienza, punteggio, stato, numero di candidati e presenza di un recruiter.
- Come utente, voglio **salvare una combinazione di filtri con un nome** e riapplicarla con un clic.
- Come utente, voglio **cercare tra i miei job con una barra testuale** (titolo, azienda, località).
- Come utente, voglio **aprire il dettaglio di un job**, con descrizione completa, motivazione del punteggio e match/gap con le relative motivazioni.
- Come utente, voglio **segnare un job come preferito** e ritrovarlo nella sezione Preferiti.
- Come utente, voglio **archiviare un job con uno swipe**, **annullare** un'archiviazione accidentale e **riportare** un job fuori dall'archivio.

### CV
- Come utente, voglio **generare (o rigenerare) un CV personalizzato per qualunque job**, entro il massimale giornaliero del mio piano o, oltre, a credito.
- Come utente, voglio **scegliere uno o più gap rilevati dallo scoring e farli colmare nel CV** ("colma i gap"), con indicazioni facoltative su come inserirli.
- Come utente, voglio **modificare il CV generato in un editor** (testi, bullet visibili, ordine, grassetti, istruzione e lingue del solo CV) con anteprima live, e **produrre il PDF finale** senza costi aggiuntivi.
- Come utente, voglio **chiedere modifiche a un assistente AI dentro l'editor**, vedere ogni proposta come "prima → dopo" e **accettarla o rifiutarla**, anche puntando singoli bullet come contesto.
- Come utente, voglio **scaricare il CV in PDF** con un nome di file leggibile.

### Cover letter e networking
- Come utente, voglio **generare una cover letter in PDF** per un job, con indicazioni facoltative e la possibilità di riusare quelle date in passato.
- Come utente, voglio **modificare la cover letter in un editor con chat AI** e produrre il PDF finale.
- Come utente, voglio **generare un messaggio LinkedIn o un'email** per chiedere una raccomandazione o una presentazione per un job, indicando destinatario e contesto, e **copiarlo** con un clic.

### Candidatura
- Come utente, voglio **aprire il link originale della candidatura** e **segnare il job come "candidatura fatta"**, anche senza aver generato un CV, per tenere traccia di dove mi sono candidato.

### Import e creazione manuale
- Come utente Pro, voglio **importare un job incollando il suo link LinkedIn**, per farlo valutare anche se non è stato raccolto in automatico.
- Come utente (Free o Pro), voglio **inserire a mano un job** (titolo, azienda, località, descrizione, data, link facoltativo), per farlo valutare e trattare come gli altri.

### Gestione account
- Come utente, voglio **modificare il profilo master in qualsiasi momento**, con effetto sulle generazioni future.
- Come utente, voglio **vedere il mio piano e il saldo del credito extra**. *(Piano e credito sono gestiti dall'amministratore: vedi §4.11.)*
- Come utente, voglio **scegliere la lingua dell'interfaccia** (italiano/inglese) e **attivare le notifiche push**.
- Come utente, voglio **disattivare le notifiche** su tutti i miei dispositivi, per non riceverne più finché non le riattivo (Sprint 67).
- Come utente, voglio **cambiare la password** e, se l'ho dimenticata, **recuperarla via email**, venendo disconnesso da tutti i dispositivi (Sprint 67).
- Come utente già registrato, voglio **prendere visione delle versioni aggiornate di informativa e termini** prima di continuare a usare l'app, oppure, se non le accetto, esportare i miei dati o eliminare l'account (Sprint 67).
- Come utente, voglio **esportare tutti i miei dati** in un archivio scaricabile, per conservarli o portarli altrove (Sprint 67).
- Come utente, voglio **eliminare il mio account** e tutti i dati collegati, con effetto immediato e un'email di conferma (Sprint 67).

---

## 4. Funzionalità incluse nel perimetro

### 4.1 Account e profilo

**Registrazione e accesso.**
- **Registrazione** con email e password (l'email è l'identificativo). Senza verifica dell'email (vedi sotto) al termine l'utente entra nell'onboarding.
- **Consensi obbligatori** (Sprint 67): il modulo ha **tre caselle, mai pre-selezionate**: "Ho letto l'informativa privacy", "Accetto i termini di servizio" (i due link aprono le pagine in una nuova scheda, senza perdere il modulo) e "Dichiaro di avere almeno 16 anni". Senza tutte e tre la registrazione è rifiutata ("Per registrarti devi selezionare tutte e tre le caselle."); il controllo è fatto anche dal server. Per ogni documento restano registrate sull'account la versione accettata e la data.
- **Registrazione su invito** (Sprint 66): durante la fase di test il modulo chiede anche un **codice di invito**, comunicato dall'amministratore. Senza il codice corretto la registrazione è rifiutata con un messaggio generico. Se l'amministratore non imposta un codice la registrazione è aperta e il campo può restare vuoto.
- **Verifica dell'email** (Sprint 67), attiva solo quando l'invio di email è configurato dall'amministratore:
  - dopo la registrazione l'app mostra "Controlla la tua email" e invia un **link di conferma valido 3 giorni**; l'account esiste ma non è utilizzabile finché l'indirizzo non è confermato;
  - il link apre la pagina "Conferma dell'email": a conferma riuscita "Indirizzo confermato. Ora puoi accedere." e il pulsante per andare al login (la conferma non fa entrare direttamente nell'app). Con un link scaduto o non valido la stessa pagina permette di chiederne uno nuovo;
  - il login di un account non confermato è rifiutato con un messaggio dedicato ("Devi prima confermare il tuo indirizzo email…") e il pulsante **"Invia di nuovo il link"**. Il messaggio compare solo dopo una password corretta: a chi non conosce la password non rivela nulla;
  - **non enumerazione**: la registrazione risponde sempre "Controlla la tua email", anche se l'indirizzo ha già un account. In quel caso non viene creato nulla e al titolare dell'indirizzo arriva un'email che segnala il tentativo, con i link al login e al recupero password. Anche il reinvio del link risponde sempre allo stesso modo;
  - le email di servizio (verifica, tentativo di registrazione, recupero password, conferma di cancellazione) sono in italiano o in inglese secondo la lingua dell'interfaccia e non contengono dati del profilo;
  - **senza invio di email configurato** resta il comportamento precedente: i nuovi account nascono già verificati, la registrazione fa entrare subito nell'onboarding e un'email già registrata è segnalata come tale ("Un utente con questa email esiste già."). Gli account creati prima dello Sprint 67 risultano già verificati.
- **Login** con email e password. Dopo il login l'utente arriva alla lista job, anche se l'onboarding non è stato completato; dallo Sprint 70, finché il profilo non è completo (stessa regola della generazione del CV: almeno un titolo di studio), in cima a ogni pagina c'è un **banner fisso** con il link: "Completa il profilo" (all'onboarding, con l'import del CV) se il profilo è ancora vuoto, "Vai al profilo" se manca solo l'istruzione. Il banner non compare in onboarding e nella pagina Profilo e sparisce appena il profilo è completo. Si è scelto il banner invece di un rimando automatico all'onboarding per non interrompere chi usa già l'app. Con credenziali errate il messaggio è sempre lo stesso ("Credenziali non valide."), sia che l'email esista sia che non esista. Sotto il modulo c'è il link **"Password dimenticata?"** (Sprint 67).
- **Sessione** (Sprint 66): ogni accesso vale per quel dispositivo; si può essere collegati da più dispositivi contemporaneamente. La sessione **scade dopo 30 giorni senza utilizzo** su quel dispositivo (usare l'app la rinnova): a quel punto, o se la sessione viene revocata, l'app torna alla pagina di login. Con il rilascio dello Sprint 66 tutti gli utenti hanno dovuto rifare il login una volta.
- **Tentativi limitati** (Sprint 66): troppi tentativi di login o di registrazione ravvicinati vengono bloccati per qualche minuto con il messaggio "Troppi tentativi. Attendi qualche minuto e riprova.". Dallo Sprint 67 sono limitati anche le richieste di email (reinvio del link, recupero password: poche all'ora per dispositivo e per indirizzo), i tentativi di password nel cambio password e nell'eliminazione dell'account, e l'export dei dati (3 al giorno).
- **Recupero della password** (Sprint 67), dalla pagina "Recupera la password" (link "Password dimenticata?"):
  - l'utente inserisce l'email e la risposta è sempre la stessa ("Se l'indirizzo corrisponde a un account, ti abbiamo inviato un link…"), che l'account esista o no;
  - il link (valido **3 giorni**, utilizzabile **una sola volta**) apre la pagina "Scegli una nuova password"; dopo il salvataggio l'utente è **disconnesso da tutti i dispositivi** e accede con la nuova password. Un link scaduto o già usato mostra "Il link non è valido o è scaduto: chiedine uno nuovo." Usare il link conferma anche l'indirizzo email;
  - senza invio di email configurato la pagina mostra "Il recupero della password via email non è al momento disponibile. Scrivi al titolare indicato nell'informativa privacy."
- **Cambio della password** dalle Impostazioni (§4.22, Sprint 67).
- **Cambio dell'email di accesso** dalle Impostazioni (§4.22, Sprint 70), solo con l'invio di email configurato: password + nuovo indirizzo, link di conferma (3 giorni) al nuovo indirizzo e avviso a quello attuale; l'email di accesso cambia solo alla conferma.
- **Login con Google.** È implementato ma **non è configurato in produzione**; dallo Sprint 67 il pulsante "Accedi con Google" **compare solo quando l'amministratore lo configura**, quindi oggi non si vede e l'unico accesso è email e password. Il percorso non è comunque completo (§8).
- **Logout:** dallo Sprint 73 (redesign UI, decisione A9) il pulsante **"Esci"** è in fondo alla pagina **Impostazioni** e chiede conferma in una finestra ("Vuoi uscire?", Esci / Annulla); non è più nella barra di navigazione. Resta anche nella schermata di accettazione dei testi legali. Chiude la sessione di quel dispositivo anche sul server (gli altri dispositivi restano collegati) e **disattiva le notifiche push su quel dispositivo** (§4.12).
- **Accettazione dei testi aggiornati** (Sprint 67). Chi non ha accettato le **versioni correnti** di informativa, termini e dichiarazione d'età vede, al posto di qualunque pagina riservata agli utenti collegati, una **schermata bloccante** "Informativa privacy e termini di servizio" con le stesse tre caselle e il pulsante "Continua". È successo una volta a tutti gli utenti registrati prima dello Sprint 67 e succederà di nuovo a tutti quando un testo cambierà versione. Dalla schermata, senza accettare, si può comunque **esportare i dati**, **eliminare l'account** o **uscire**; finché non si accetta la barra di navigazione resta nascosta e nessuna altra funzione è disponibile.
- **Pagine legali** (Sprint 67): **Informativa privacy** (`/privacy`) e **Termini di servizio** (`/terms`) sono pagine pubbliche, leggibili anche senza account, in italiano o in inglese secondo la lingua dell'interfaccia, con versione e data di entrata in vigore. Un piccolo footer con i due link è presente in tutte le pagine dell'app. I dati del titolare del trattamento (nome, email e, facoltativo, indirizzo) li imposta l'amministratore nella configurazione; finché mancano nome o email le pagine mostrano l'avviso "Dati del titolare del trattamento da completare: questa pagina non è ancora nella sua versione definitiva." Una copia di riferimento dei testi è in `Docs/legal/`.
- **Export ed eliminazione dell'account**: dalle Impostazioni (§4.22) e dalla schermata di accettazione (Sprint 67).

**Onboarding (3 passi).**
1. **Preferenze:**
   - nome e cognome (obbligatori; compaiono su CV, cover letter e nomi dei file);
   - "Situazione / obiettivo attuale": dato salvato ma inerte, non usato da nessuna funzione (modificabile anche in seguito dalla pagina Profilo, Sprint 70);
   - **fuso orario** (Sprint 70): elenco dei fusi IANA; proposto quello dell'account o, se è ancora il default Europe/Rome, quello del dispositivo. Alla registrazione l'account riceve già il fuso del dispositivo;
   - template CV: campo bloccato su "Standard (unico disponibile)", perché esiste un solo template;
   - lingua dei documenti: "lingua dell'offerta" (default) oppure "sempre inglese";
   - inclusione della foto nel CV (sì/no).
2. **Profilo:**
   - **upload facoltativo di un CV esistente** (PDF o Word .docx), che pre-compila il form; nulla viene salvato finché l'utente non preme "Salva";
   - se il file non contiene testo leggibile (es. scansione), l'app avvisa "Non siamo riusciti a leggere il CV: compila il profilo manualmente" e non crea un profilo vuoto;
   - dallo Sprint 70 gli altri errori hanno un messaggio dedicato: file troppo grande (oltre 5 MB, controllato già prima dell'invio), formato non supportato (solo PDF e .docx), troppe pagine (oltre 10), limite di 5 import al giorno raggiunto, servizio di lettura del CV non disponibile ("riprova più tardi o compila il profilo a mano");
   - poi l'utente compila o corregge tutte le sezioni (vedi sotto).
3. **Prima ricerca:** tipo, keywords, città e paese. La ricerca viene creata e **attivata subito**, poi l'utente va alla lista.

La pagina di onboarding resta raggiungibile anche in seguito, ma non ha un link nella navigazione. Con la verifica dell'email attiva, la pagina di conferma porta al login e il primo accesso da lì prosegue nell'onboarding, come dopo una registrazione senza verifica.

**Profilo master.** Un solo profilo per utente. Contiene:
- **dati di contatto:** telefono, **email da mostrare sul CV**, città e paese (con autocompletamento), link LinkedIn, foto. L'email del CV è distinta da quella di login (Sprint 41): se è vuota, CV e cover letter non mostrano alcuna email;
- **sommario professionale;**
- **esperienze lavorative**, raggruppate per azienda (più ruoli nella stessa azienda): ruolo, località, data di inizio e di fine (oppure "in corso"), bullet ("attività / competenze"), **tecnologie** (modificabili da onboarding e Profilo dallo Sprint 70; compaiono sul CV come riga "Tecnologie");
- **istruzione:** istituto, titolo, località, data di inizio e di fine (oppure "in corso"), note;
- **competenze** e **certificazioni** (voci semplici);
- **lingue**, scelte da una **lista fissa di 36 lingue** con **4 livelli**: Elementary, Intermediate, Fluent, Mother tongue (Sprint 41). Sul CV nomi e livelli vengono tradotti nella lingua del documento.

La sezione "risultati chiave" **non esiste**. "Areas of Expertise" è un contenuto che il modello calcola a ogni generazione del CV, non un campo del profilo (doc 03).

**Vincoli di completezza.**
- Per generare un CV serve **almeno 1 voce di istruzione**. Il controllo avviene **solo al momento della generazione**, non al salvataggio del profilo. Se manca: "Completa il profilo (almeno un titolo di studio) prima di generare un CV."
- La data di fine dell'istruzione **non è obbligatoria**: "in corso" è ammesso.
- Le **esperienze possono essere zero** (es. neolaureato).
- Oltre 5 esperienze compare un avviso: il CV ne mostrerà al massimo 5.
- **Limiti dei testi** (Sprint 70): al massimo **15 bullet per esperienza**, ciascuno di **400 caratteri** (il campo non accetta testo più lungo; i bullet pre-compilati dal CV oltre il limite sono evidenziati); al massimo 30 esperienze, 15 voci di istruzione, 100 competenze, 50 certificazioni e 36 lingue. I limiti non sono retroattivi: un'esperienza salvata prima, con più bullet o bullet più lunghi, si può ancora salvare senza toccarli, ma non può crescere oltre e i bullet nuovi devono rispettare il limite.

**Cosa recupera il pre-compilamento da CV.**
- **Recupera:** sommario, telefono ed email (solo se scritti nel CV), aziende, ruoli, luoghi e bullet, istituti, titoli e note, competenze, certificazioni e lingue con livello. Le scale libere e quelle CEFR sono ricondotte ai 4 livelli; nel dubbio la voce viene omessa.
- **Non recupera:** le **date** di esperienze e istruzione, città e LinkedIn. Vanno inserite a mano. Dallo Sprint 70 le tecnologie estratte dal CV restano nel form.

**Opzioni dei documenti** (modificabili in seguito in Impostazioni, §4.22):
- **lingua:** vale per CV, cover letter e messaggi di networking;
- **foto:** compare nel CV solo se l'opzione è attiva **e** una foto è stata caricata.

**Effetto delle modifiche.** Il profilo è modificabile in qualunque momento e vale per le generazioni future. **I documenti già generati non cambiano.** Anche i job già valutati **non vengono rivalutati** (§5.8).

### 4.2 Ricerche

- Ogni ricerca salvata ha quattro campi: **tipo** (*Job role keyword* o *Company*), **keywords**, **città** e **paese**. Città e paese si scelgono con un autocompletamento geografico.
  - Esempi: *Job role — "IT Project Manager" — Rome, Italy*; *Company — "Nome Azienda" — Milan, Italy*.
  - Per le ricerche **Company** la fonte filtra davvero per azienda, non per corrispondenza testuale sulle keywords (sprint-39). È l'unica deviazione accettata dal vincolo "solo keywords e località" (§5.10).
- Le ricerche si gestiscono dalla pagina **Impostazioni**: si creano, si modificano, si eliminano, si attivano e si disattivano. La prima si crea in onboarding.
- Una ricerca nuova creata da Impostazioni **nasce disattivata**. Solo le ricerche **attive** producono job, sia nella raccolta notturna sia in quella manuale.
- **Limiti per piano:**
  - **Free:** fino a **10 ricerche salvate**, di cui al massimo **1 attiva per tipo** (quindi fino a 2 in totale: 1 Job role e 1 Company). Se si attiva una ricerca di un tipo che ne ha già una attiva, la precedente viene **disattivata automaticamente**; la ricerca dell'altro tipo non cambia. Un avviso indica il nome della ricerca disattivata (Sprint 68). Lo stesso vale se si **cambia il tipo** di una ricerca attiva (Job role ↔ Company): conta come un'attivazione nel nuovo tipo e spegne l'eventuale altra ricerca attiva di quel tipo, con lo stesso avviso.
  - **Pro:** fino a **100 ricerche salvate**, di cui fino a **50 attive** in totale, divisibili liberamente tra i due tipi. Oltre i limiti l'operazione è rifiutata con un messaggio.
- **Downgrade Pro→Free:** tutte le ricerche vengono **disattivate** e nessuna viene riattivata in automatico.
  - Le ricerche salvate restano tutte, anche se sono più di 10. In questo caso non se ne possono creare di nuove finché, eliminandone, non si scende sotto le 10.
  - Le ricerche esistenti restano attivabili entro il limite Free.

### 4.3 Fonte delle offerte

- **Unica fonte: LinkedIn.**
  - La raccolta (notturna e manuale) passa da un servizio di scraping esterno.
  - L'import da link (§4.9) legge invece la pagina pubblica dell'offerta.
  - La fonte è un componente sostituibile.
- **Campi obbligatori** perché un'offerta raccolta venga mostrata: *titolo, azienda, località, descrizione, link di candidatura*. Se ne manca uno, l'offerta viene scartata.
- È scartata anche un'offerta con un campo testuale **più lungo del consentito** (es. un link di candidatura lunghissimo): mai troncata, perché un link troncato non funzionerebbe (Sprint 49).
- Gli scarti sono **silenziosi** per l'utente; dallo Sprint 68 il diario tecnico della raccolta conta le offerte scartate per campi mancanti, campi troppo lunghi e duplicati.
- La **data di pubblicazione non è obbligatoria**.
- **Dati facoltativi** mostrati se presenti:
  - retribuzione;
  - **numero di candidati**: valore esatto, oppure le fasce "tra i primi 25" o "oltre 200" quando LinkedIn dà solo quelle;
  - **recruiter** che ha pubblicato l'annuncio, con nome ed eventuale link al profilo;
  - **ricerca di provenienza**.

  Candidati e recruiter esistono **solo** per i job raccolti, non per quelli importati o creati a mano.
- **Deduplica per utente.** Un'offerta LinkedIn già presente tra i job dell'utente non viene ricreata, anche se nel frattempo è stata archiviata o importata. Se più ricerche restituiscono la stessa offerta nella stessa raccolta, compare una volta sola e porta la provenienza di una sola delle ricerche. Dallo Sprint 68 il job conserva anche un riferimento stabile alla ricerca di provenienza: modificarne keywords o località non lo scollega dal filtro "Ricerca" (§4.5).

### 4.4 Ciclo quotidiano

- **Raccolta notturna** alle **02:00 (Europe/Rome)**, per tutti gli utenti con ricerche attive.
  - Riguarda le offerte pubblicate nelle **24 ore precedenti**; il vincolo è applicato alla fonte.
  - Le ricerche attive dell'utente sono raggruppate per tipo e località: una richiesta alla fonte per gruppo, con al massimo **150 risultati per richiesta** (`MAX_ITEMS_PER_CALL`).
  - **Non esiste più alcun tetto per piano o per notte**, né un cap di intake: tutte le offerte valide raccolte vengono valutate e mostrate (Sprint 46). Il piano non influisce sul volume raccolto.
- **Scoring** di ogni offerta raccolta:
  - **punteggio di affinità da 1 a 10** rispetto al profilo master (Sprint 47), con una **breve motivazione** (al massimo circa 2 frasi);
  - **corrispondenze** (*match*) e **lacune** (*gap*), ciascuna con un'etichetta breve e una motivazione di una frase.
  - Il punteggio segue una **rubrica per fascia**, basata sui requisiti "obbligatori" dell'offerta soddisfatti o mancanti:
    - 9–10: tutti soddisfatti;
    - 7–8: manca al più un elemento secondario;
    - 5–6: manca un requisito obbligatorio o la seniority non è allineata;
    - 3–4: mancano più requisiti;
    - 1–2: profilo non pertinente.
  - Con una descrizione vuota o non valutabile, match e gap sono vuoti e il punteggio non supera 6.
  - Lo scoring non inventa competenze e non segnala come gap ciò che è già nel profilo. Al modello arrivano titolo, azienda, **località** (dallo Sprint 68) e descrizione dell'offerta.
- **Limite per lingua richiesta** (Sprint 48). Se l'offerta richiede una lingua (dichiarata necessaria, oppure annuncio scritto interamente in una lingua diversa dall'inglese) che **non è nel profilo a nessun livello**, il punteggio è limitato a **3** (`LANGUAGE_MISMATCH_SCORE_CAP`).
  - La motivazione si apre con "Punteggio limitato a 3/10: lingua richiesta (…) assente dal profilo." oppure, per chi ha l'interfaccia in inglese, "Score capped at 3/10: required language (…) missing from the profile." (Sprint 71): vale la lingua dell'interfaccia del momento in cui l'offerta viene valutata, e la frase non cambia se poi l'utente cambia lingua. Il resto della motivazione è scritto dall'AI e non dipende dalla lingua dell'interfaccia.
  - Fanno eccezione le offerte che dichiarano un ambiente internazionale o di lavoro in inglese.
- **Nessuna generazione automatica di CV** (Sprint 45): il ciclo notturno è solo raccolta più scoring. Tutti i job nascono in stato "nuovo" (§4.6).
- **Fallimenti:**
  - se la richiesta alla fonte di un gruppo di ricerche (tipo × località) fallisce, si perdono solo le offerte di quel gruppo: gli altri gruppi dell'utente vengono raccolti normalmente (Sprint 68). Nessun messaggio d'errore per l'utente (§6);
  - se lo scoring di una singola offerta fallisce (o la raccolta si interrompe prima dello scoring), il job **resta in lista senza punteggio**, in fondo all'ordinamento, e viene **ritentato al ciclo notturno successivo**, fino a **3 tentativi falliti** per job (Sprint 68);
  - se è in corso una raccolta manuale dello stesso utente, il ciclo notturno lo salta per quella notte (e viceversa la raccolta manuale è rifiutata mentre gira il ciclo notturno dell'utente).
- **Storico dei punteggi:** i punteggi dati sulla vecchia scala 1–5 (prima del 24/09/2026) sono stati **riscalati ×2** (1→2 … 5→10) nello Sprint 68. Il limite per lingua non è stato applicato retroattivamente a quei job (richiederebbe una nuova valutazione AI per ciascuno).
- **Notifica** alle 10:00 locali **solo se** ci sono nuovi job (§4.12).
- In aggiunta, l'utente può avviare **una raccolta manuale al giorno** (§4.14).

### 4.5 Vista lista e navigazione

**Navigazione generale** (Sprint 73, redesign UI). Dopo il login la navigazione ha **tre voci: Jobs, Profilo, Impostazioni** (la pagina Home non esiste più: l'indirizzo `/home` porta alla lista). Su telefono e tablet (sotto i 1024 px) è una **barra di tab in basso** con icona ed etichetta, voce attiva in colore primario, che rispetta l'area sicura dell'iPhone; da 1024 px è una **barra in alto** con logo e nome dell'app, le tre voci e il selettore della lingua. Jobs resta la voce attiva anche nel dettaglio e negli editor di un job. L'app si apre sulla **lista job**. Le pagine senza navigazione (accesso, pagine legali, verifica email, schermata di accettazione) mostrano in alto logo e selettore della lingua. "Esci" è in Impostazioni (§4.1).

**Sezioni.** La lista organizza i job in **quattro sezioni** (pillole in alto):

| Sezione | Contenuto |
|---|---|
| **Raccolti** | job raccolti automaticamente, non archiviati |
| **Importati** | job importati da link (§4.9) o creati a mano (§4.15), non archiviati |
| **Preferiti** | job segnati come preferiti, non archiviati, di qualunque origine (§4.21) |
| **Archiviati** | tutti i job archiviati, di qualunque origine (anche se preferiti) |

La sezione dipende da origine, preferito e archiviazione, **non** dallo stato del job. All'apertura dal menu la lista mostra **Raccolti**. Sezione e filtri sono scritti nell'indirizzo della pagina (Sprint 68): tornando dal dettaglio di un job (link "Torna alla lista" o tasto indietro del browser) la lista riparte dalla stessa sezione con gli stessi filtri, e l'indirizzo si può condividere.

**Testata della lista** (Sprint 74, redesign UI): titolo "Jobs", pulsante **Raccogli** (icona di aggiornamento, apre il pannello della raccolta manuale, §4.14), campo di **ricerca testuale**, pulsante **Filtri** con il numero dei filtri attivi e, nella sezione Raccolti, il **riepilogo delle statistiche** (§4.13). Sotto le pillole delle sezioni, se ci sono filtri attivi, la riga **"N filtri attivi · Cancella"**: "Cancella" riporta tutti i filtri ai valori di default (date di oggi, nessun altro filtro) lasciando sezione e ricerca testuale.

Nella sezione **Importati** c'è un riquadro "Importa un job" con:
- il form di import da link per il Pro (link, "Importa", indicazione del costo della prossima richiesta), oppure il messaggio "L'import manuale di job è riservato al piano Pro" con il badge PRO per il Free;
- per tutti, il pulsante **"Aggiungi manualmente"**, che apre un pannello con il form (§4.15).

**Ordinamento.** Sempre per **punteggio decrescente**, con i job senza punteggio in fondo, e a parità di punteggio per data di raccolta decrescente. L'utente non può cambiarlo.

**Filtri** (dallo Sprint 74 in un **pannello "Filtri"** dal basso, finestra centrale da 1024 px; prima erano in linea nella pagina). Si applicano subito (restano nell'indirizzo della pagina) e "Mostra risultati" chiude il pannello; "Azzera filtri" li riporta ai valori di default. Si combinano in AND tra loro; dentro un filtro a scelta multipla le opzioni valgono in OR. Il numero di filtri attivi conta un gruppo per filtro (le date solo se diverse da oggi–oggi).
- **Intervallo di date** "Dal" / "Al", sulla data di raccolta, nel fuso dell'utente, estremi inclusi.
  - **Default: oggi–oggi**, con "oggi" nel fuso dell'utente (dallo Sprint 70; prima era la data del dispositivo).
  - Il link "Tutte le date" toglie il limite e mostra tutto lo storico.
  - Sostituisce i vecchi periodi preimpostati (Sprint 46).
- **Location:** testo libero, cercato come sottostringa nella località del job.
- **Ricerca** (di provenienza): scelta multipla tra tutte le ricerche salvate, attive e non, più "Nessuna ricerca" (Sprint 40, multi-selezione dallo Sprint 63). È **nascosto e ignorato nella sezione Importati**. Dallo Sprint 68 un job resta associato alla sua ricerca anche se questa viene modificata; per i job raccolti prima e non attribuibili con certezza vale ancora il confronto con i valori attuali della ricerca.
- **Punteggio:** scelta multipla sui valori **1–10** (pillole).
- **Stato:** scelta multipla tra **nuovo**, **CV generato**, **candidatura fatta**. Lo stato transitorio non è selezionabile.
- **Candidati:** scelta multipla tra le fasce **<25**, **25–50**, **51–100**, **101–200**, **>200**. I job senza questo dato (importati, manuali) non rientrano in nessuna fascia.
- **Recruiter:** tutti / con recruiter / senza recruiter (controllo a segmenti).

In cima al pannello ci sono i **filtri salvati**, come pillole cliccabili con la ✕ per eliminarli, e il pulsante "Salva filtri attuali", che apre una finestra con il nome (§4.21). Ogni ricerca di provenienza è una pillola "parole chiave · città".

**Ricerca testuale.**
- Cerca per keyword in **titolo, azienda e località** (non nella descrizione), su tutto lo storico **della sezione corrente**, senza attraversare le altre.
- **Quando è attiva, tutti gli altri filtri vengono ignorati**: il pulsante Filtri si disattiva e compare la scritta "Filtri disattivati durante la ricerca testuale". Lo stesso vale per i filtri preferiti.

**Scheda del job nella lista** (ridotta dallo Sprint 74, SPEC-DELTA A2/A7).
- **Tutta la scheda è cliccabile** e apre il dettaglio (il link è sul titolo); il cuoricino e il profilo del recruiter restano controlli separati.
- **Badge:** stato e numero di candidati (in verde se sotto i 25). La ricerca di provenienza è nel dettaglio.
- **Dati:** titolo; azienda · località con l'**icona del recruiter** in un cerchietto (con link al profilo se disponibile); data di raccolta ("Importato: …").
- **Punteggio:** riquadro del punteggio in alto a destra, colorato per fasce di 2 valori.
- **"Da colmare":** i **primi 2 gap**, solo l'etichetta, più "+N altri · vedi nel dettaglio".
- **Cuoricino** dei preferiti in basso a destra.
- **Nessun pulsante** di dettaglio, archiviazione o generazione: il CV si genera dal dettaglio (§4.7), l'archiviazione si fa con lo swipe.
- La scheda **non** mostra i match né la motivazione del punteggio.

**Stato vuoto:** icona, il messaggio della sezione e, in Raccolti, "Raccogli ora"; con filtri attivi "Nessun job con questi filtri." e "Azzera filtri".

**Dettaglio job** (ridisegnato nello Sprint 75, mockup `detail-*` e `desk-detail`; stesso comportamento di prima).
- **Riga in alto:** "‹ Jobs" (torna alla lista con i filtri dell'ultima visita), il **cuoricino** del preferito e il menu **⋯ "Altre azioni"**: **"Archivia"** oppure, per un job archiviato, **"Riporta dall'archivio"** (SPEC-DELTA A7; si usa anche da tastiera: Invio o ↓ apre, frecce, Esc chiude) e, per un job senza CV non ancora marcato, **"Segna candidatura fatta"** (§4.10). Archiviando dal dettaglio si resta nella pagina; un avviso offre "Annulla" e un'etichetta "Archiviato" lo ricorda.
- **Intestazione:**
  - **chip dello stato**, solo indicativo (non selezionabile): "Nuovo", "✓ CV generato", "✓ Candidatura fatta" o, durante la generazione del CV, "CV in generazione" con indicatore (§4.6);
  - titolo e **punteggio** a fasce di colore (§4.4);
  - azienda · località · retribuzione (se presente) con l'**icona del recruiter** (link al profilo se disponibile);
  - pulsante **"Annuncio ↗"** ("Vai all'annuncio"), solo se il job ha un link di candidatura;
  - etichette dei **candidati**, della **ricerca di provenienza** ("Trovato con: …") e la data di raccolta.
- **Documenti** (se esiste almeno un documento, se una generazione è in corso o se la candidatura è fatta): una riga per **CV**, **Cover letter** e **Messaggio**, con stato ("Pronto · N pagine", "Non ancora generato", "CV in generazione") e azioni: matita **Modifica** (solo documenti modificabili, §4.16, §4.19), **Scarica** (link firmato, §4.18), menu ⋯ con **Rigenera**; senza documento, **"Genera"**. Sotto la riga del documento gli avvisi "occupa N pagine invece di 1" e "generato prima dell'editor, rigeneralo per modificarlo" (Sprint 69). Sotto "Messaggio" i messaggi già generati (§4.20), con il testo lungo troncato e "Leggi tutto".
- **"Perché questo punteggio":** la motivazione troncata a 3 righe con **"Leggi tutto"**; sotto, i contatori **"N corrispondenze"** e **"N gap"**: toccandone uno si apre l'elenco delle voci con la motivazione di ognuna (uno aperto per volta).
- **"Descrizione annuncio"** a fisarmonica, chiusa all'apertura (Mostra / Nascondi).
- **Barra azione in basso** (al posto della barra di tab, a ogni larghezza): **"Genera CV ▾"** se il job non ha un CV (▾ apre "Genera cover letter" e "Genera messaggio"); **"Segna candidatura fatta"** se il CV c'è; **"Annulla candidatura"** se la candidatura è fatta (§4.10).
- **Generazioni:** "Genera CV" apre il pannello **"Colma i gap"** (§4.8), cover letter e messaggio i loro pannelli (§4.18, §4.20). Ogni pannello mostra l'avviso AI e, in fondo, il costo della prossima richiesta ("Incluso nel piano: ne restano N su M oggi", a credito con prezzo e saldo, oppure bloccata: in questo caso il pulsante è disattivato); oltre il massimale chiede conferma del costo (§4.11). Durante l'attesa (sincrona, anche qualche minuto) una finestra non chiudibile mostra "Generazione del CV…" (o della cover letter / del messaggio).

**Archiviazione e swipe.**
- Fuori dalla sezione Archiviati, lo **swipe a sinistra** (dito o trascinamento del mouse) archivia il job. Un avviso scuro in basso offre **"Annulla"**. Dallo Sprint 74 non c'è più il pulsante "Archivia" sulla scheda; dallo Sprint 75 si archivia (anche **da tastiera**) dal menu ⋯ del dettaglio (SPEC-DELTA A7), che per un job archiviato offre "Riporta dall'archivio".
- Nella sezione Archiviati lo swipe diventa **"Rimuovi da archivio"**: il job torna nella sua sezione d'origine con lo stato che aveva.
- **Uscita automatica dall'archivio:** se si **genera o rigenera un CV** per un job archiviato, il job esce dall'archivio. Cover letter, messaggi e modifiche dall'editor invece **non** lo fanno uscire.

### 4.6 Stati e sezioni del job

Stato e sezione sono dimensioni **indipendenti**. Preferito e archiviazione sono attributi, non stati.

**Stati stabili (tre):**
- **nuovo**: stato iniziale di **tutti** i job (raccolti, importati, creati a mano), con qualunque punteggio. Un job torna "nuovo" solo annullando la candidatura di un job senza CV (§4.10).
- **CV generato**: stato di un job dopo una generazione del CV riuscita, compresa la rigenerazione, se il job non era già "candidatura fatta" (Sprint 69). Non cambiano lo stato: una generazione fallita, la finalizzazione dall'editor, la cover letter e i messaggi di networking.
- **candidatura fatta**: impostato a mano dall'utente **in qualunque momento**, anche senza CV (Sprint 46). Non è ripetibile; una rigenerazione del CV non lo toglie. Si può **annullare** (Sprint 69, §4.10).

**Stato transitorio:**
- **CV in generazione**: mentre il CV viene prodotto, il chip dello stato del dettaglio mostra "CV in generazione" e "Genera CV" mostra "Generazione…" ed è disabilitato (Sprint 75). Una seconda richiesta sullo stesso job viene rifiutata.
- Cover letter e messaggi di networking hanno **blocchi di concorrenza propri**, indipendenti da quello del CV, visibili anche da altri dispositivi e dopo un ricaricamento (Sprint 69). **Non** sono stati del job.
- Se una generazione si interrompe senza chiudersi (es. server riavviato), il blocco decade da solo dopo **35 minuti** (Sprint 69).

**Archiviazione e preferito.**
- Archiviare non cambia lo stato. Rimuovendo un job dall'archivio, questo torna alla sezione d'origine con lo stato che non ha mai perso.
- Il **preferito** è un attributo separato: un job preferito e poi archiviato resta preferito, ma compare solo in Archiviati.

### 4.7 Generazione del CV

**Solo su richiesta.**
- La **generazione automatica non esiste più** (Sprint 45): nessun punteggio fa partire un CV da solo.
- La generazione è disponibile su **qualunque job** (raccolto, importato o creato a mano; con punteggio alto, basso o assente) **dal dettaglio** (dallo Sprint 74 la scheda in lista non ha più "Genera CV"): "Genera CV" nella barra in basso, oppure "Genera" / "Rigenera CV" nella riga del CV, aprono sempre il pannello "Colma i gap" (§4.8), dove la selezione dei gap è facoltativa.
- **Rigenerare** significa semplicemente generare un nuovo CV per un job che ne ha già uno. Non ci sono limiti per singolo job oltre al massimale giornaliero e al credito.

**Massimale e credito.**
- Ogni generazione (compresa la rigenerazione, con o senza gap) consuma un'unità del massimale giornaliero **Free 1 / Pro 10**.
- Oltre il massimale si prosegue **a credito**, scalando **1,50 €** (`PRICE_MANUAL_CV_EXTRA`).
- Senza credito sufficiente: "Hai raggiunto il limite giornaliero di generazioni manuali e il saldo credito non è sufficiente."
- Per i dettagli vedi §4.11.

**Prerequisito:** profilo con almeno 1 voce di istruzione (§4.1).

**Concorrenza.** Durante la generazione il pulsante è disabilitato e una seconda richiesta sullo stesso job viene rifiutata. Non si consumano mai due unità (o due addebiti) per lo stesso job in lavorazione.

**Esecuzione.** La generazione avviene direttamente nella richiesta, senza coda: l'utente vede l'indicatore di caricamento finché il documento non è pronto. Non c'è un tempo massimo garantito (§6).

**Esito.**
- **Riuscita:**
  - il job passa a **CV generato**, salvo che fosse già **candidatura fatta**: in quel caso resta tale (Sprint 69);
  - esce dall'archivio, se c'era;
  - il nuovo PDF diventa quello scaricabile. I CV precedenti restano nello storico interno, ma l'app mostra solo l'ultimo.
- **Fallimento:**
  - un avviso "Non siamo riusciti a generare il CV. Riprova.";
  - lo stato del job **non cambia** (Sprint 69): un job con CV resta "CV generato", una candidatura resta tale;
  - massimale o credito vengono **restituiti** (anche quando il server interrompe una generazione troppo lunga);
  - per riprovare basta premere di nuovo "Genera CV".

**Contenuto del CV** (sintesi; le regole vincolanti sono nel **doc 03**):
- **Intestazione:**
  - nome;
  - **qualifica professionale** ricavata dal titolo del job;
  - contatti: "Città, PAESE | telefono | email del profilo | LinkedIn";
  - foto, se attivata.
- **Sommario:** riscritto per mettere in primo piano le priorità dell'offerta.
- **Areas of Expertise:** 4–6 voci, ricavate per sintesi da contenuti reali.
- **Certificazioni e competenze:** scelte solo tra quelle del profilo.
- **Esperienze:**
  - al massimo **5** (`MAX_EXPERIENCES_SHOWN`);
  - bullet riformulati e selezionati per rilevanza, con 1–2 **parole chiave in grassetto** per bullet (Sprint 58). Il grassetto aggiunto a mano o dalla chat in qualifica, sommario, aree, ruolo e note dell'istruzione compare anch'esso come grassetto (Sprint 69);
  - località, date (solo l'anno) e tecnologie prese così come sono nel profilo.
- **Istruzione:** **tutte** le voci, mai riformulate.
- **Lingue:** tradotte nella lingua del CV.
- **Grounding:** il CV non aggiunge nulla che non sia nel profilo. Le uniche eccezioni sono controllate:
  - le Areas of Expertise ottenute per astrazione;
  - l'ampliamento di esperienze reali per i gap selezionati (§4.8);
  - le modifiche richieste esplicitamente in chat (§4.17);
  - le modifiche manuali fatte nell'editor (§4.16).

**Template e lunghezza.**
- **Template unico**, non selezionabile: A4, carattere compatibile con Cambria, dimensione fissa (Sprint 52–57).
- L'obiettivo è **1 pagina**: se il contenuto eccede, l'app toglie i bullet meno rilevanti per qualche tentativo.
- In casi residuali il PDF può uscire su **più pagine**: dallo Sprint 69 l'utente lo vede subito (avviso dopo la generazione e nel dettaglio del job: "Il CV occupa N pagine invece di 1…") e può accorciarlo con l'editor (doc 03).

**Foto.** Compare solo se l'opzione è attiva e una foto è caricata.

**Lingua.** Dipende dall'impostazione dell'utente:
- *sempre inglese*;
- oppure *lingua dell'offerta*: il contenuto segue la lingua dell'annuncio. Le etichette fisse (titoli di sezione, "Present", nomi delle lingue) sono tradotte in **it/en/fr/de/es**; per altre lingue restano in inglese.

Tradurre i contenuti reali dell'utente è permesso; aggiungerne no.

**Download: solo PDF**, con nome file `CV {Nome Cognome} - {Titolo del job}.pdf` (Sprint 42). Il Word non è previsto (§5.19).

**Avviso AI** (Sprint 67). Nel pannello "Colma i gap" (dallo Sprint 75; prima sotto il pannello nel dettaglio) compare l'avviso "Contenuto generato con l'AI: verificalo prima di usarlo.". Lo stesso avviso è nelle chat degli editor (§4.17, §4.19) e nei pannelli di cover letter e messaggi di networking (§4.18, §4.20).

### 4.8 "Colma i gap" (sostituisce l'arricchimento mirato del profilo)

Dallo Sprint 44 l'**arricchimento del profilo è stato eliminato** e sostituito da "colma i gap".

**Dove si trova.** Dallo Sprint 75 (SPEC-DELTA A3, mockup `detail-gap`) è un **passo facoltativo prima di ogni generazione del CV**: "Genera CV" (o "Rigenera CV") apre un pannello dal basso (finestra centrale da 1024 px) intitolato "Genera CV" / "Rigenera CV", con i gap, le indicazioni, l'avviso AI, il costo della prossima richiesta e il pulsante di generazione. Chi non seleziona nulla genera come prima senza gap. Fino allo Sprint 74 era un pannello collassabile nel dettaglio ("Colma i gap trovati per questa offerta prima di generare") e il CV si generava con un clic diretto.

**Cosa fa l'utente.**
- Seleziona con le checkbox **uno o più gap**, presi dall'elenco numerato dei gap dello scoring; sotto ogni gap compare la sua motivazione. Al modello arrivano **gli stessi numeri e lo stesso testo** (etichetta e motivazione) che l'utente vede, nell'ordine dell'elenco (Sprint 69): "per il gap 2" indica sempre il gap n. 2 del pannello.
- Se vuole, scrive **indicazioni** su come inserirli (es. "per il gap 2, collegalo alla mia esperienza in …"), al massimo 2.000 caratteri con contatore (Sprint 75). Senza indicazioni, il modello sceglie l'esperienza reale più plausibile.
- Preme **"Genera CV"**.
- Se il job non ha gap, il pannello lo segnala.

**Cosa fa il modello.**
- **Solo per i gap selezionati** può **ampliare un'esperienza reale**, mantenendo stessa azienda, stesso ruolo e stesso periodo, anche oltre i bullet documentati.
- Non può mai:
  - inventare un datore di lavoro, un ruolo o un periodo;
  - aggiungere competenze o certificazioni assenti dal profilo.
- Il contenuto creato è trattato come molto rilevante per l'offerta.
- Con **sole indicazioni** e nessun gap selezionato, le indicazioni orientano la generazione ma non autorizzano alcun ampliamento.

**Regole.**
- Il contenuto vale **solo per quella generazione**: **non viene mai salvato nel profilo master**.
- Non ricalcola il punteggio.
- Non ha un costo proprio: è una normale generazione del CV, con lo stesso massimale o credito (§4.7).

**Cosa resta e cosa no dell'arricchimento precedente.**
- **Non esistono più:**
  - l'aggiunta di dettagli agganciati a un'esperienza del profilo;
  - la domanda "salva anche nel profilo master";
  - la priorità protetta di inclusione nel CV.
- **Restano:** la generazione su richiesta di un CV più aderente alle lacune evidenziate, senza rivalutazione del punteggio, e la responsabilità dell'utente sulla veridicità di quanto chiede di far emergere.

### 4.9 Import manuale di job da link

- Nella sezione **Importati** l'utente incolla un link a un'offerta LinkedIn.
- Il job viene letto dalla **pagina pubblica dell'offerta**. Data di pubblicazione, numero di candidati e recruiter non sono disponibili.
- Il job viene **valutato subito** come gli altri e compare in Importati in stato "nuovo". Da lì si comporta come qualunque job: stati, preferiti, archiviazione, CV, cover letter, messaggi.
- **Errori:**
  - link non valido o offerta non leggibile: *"Impossibile importare quel job."*, con restituzione di massimale o credito;
  - offerta **già presente** (anche se raccolta di notte o archiviata): nessun duplicato, l'app risponde *"Questo job è già nella tua lista."*.
- **Limiti:**
  - riservato al piano **Pro**: il Free non può importare nemmeno a credito;
  - **3 import al giorno**; oltre, **0,50 €** a credito (`PRICE_IMPORT_EXTRA`);
  - il massimale è **indipendente** da quello della generazione CV e da quello della creazione manuale (§4.15).

### 4.10 Candidatura

- **"Vai all'annuncio"** (dallo Sprint 75 il pulsante "Annuncio ↗" nell'intestazione del dettaglio) apre il link di candidatura originale. Per i job senza link il pulsante non compare (fino allo Sprint 74 compariva il testo "Nessun link di candidatura").
- **"Segna candidatura fatta"**:
  - è disponibile su **qualunque job** non ancora marcato, **anche senza CV** (Sprint 46): dallo Sprint 75 nella barra in basso del dettaglio quando il CV c'è, altrimenti nel menu ⋯;
  - registra la data e azzera il timer della notifica di inattività (§4.12).
- **"Annulla candidatura"** (Sprint 69), al posto del pulsante precedente sui job già marcati (dallo Sprint 75 nella barra in basso), chiede conferma in una finestra ("Annullare "candidatura fatta"?", Sì, annulla / No, lascia com'è, mockup `undo-application`) e riporta il job a "CV generato" se ha un CV, altrimenti a "nuovo"; la data della candidatura si azzera e il job esce dal conteggio "Candidature fatte" della Home. Il timer di inattività **non** torna indietro: resta quello della candidatura annullata.
- La candidatura vera e propria si fa sul portale di origine.

### 4.11 Monetizzazione

**Piani.** Esistono due piani, **Free** e **Pro**. Le differenze sono solo nei massimali qui sotto e nelle ricerche. La raccolta notturna, lo scoring e tutte le altre funzioni sono uguali per entrambi.

**Massimali giornalieri e prezzi extra.** Ogni azione ha un **contatore giornaliero proprio**, indipendente dagli altri. Oltre il massimale si prosegue **a credito**, scalando il prezzo unitario dal saldo. Con saldo insufficiente l'azione è **bloccata con un messaggio**.

| Azione | Free | Pro | Oltre il massimale | Prezzo extra (default) |
|---|---|---|---|---|
| Generazione CV (anche rigenerazione, con o senza "colma i gap") — §4.7 | 1/giorno | 10/giorno | a credito | **1,50 €** (`PRICE_MANUAL_CV_EXTRA`) |
| Generazione cover letter — §4.18 | 1/giorno | 10/giorno | a credito | **1,50 €** (`PRICE_COVER_LETTER_EXTRA`) |
| Messaggio di networking — §4.20 | 1/giorno | 10/giorno | a credito | **1,00 €** (`PRICE_REFERRAL_MESSAGE_EXTRA`) |
| Import job da link LinkedIn — §4.9 | **non disponibile** (nemmeno a credito) | 3/giorno | a credito | **0,50 €** (`PRICE_IMPORT_EXTRA`) |
| Creazione manuale di un job — §4.15 | 3/giorno | 3/giorno | a credito | **0,50 €** (`PRICE_MANUAL_JOB_EXTRA`) |
| Raccolta manuale "Raccogli ora" — §4.14 | 1/giorno | 1/giorno | **nessuna estensione** | — (`COLLECTION_DAILY_LIMIT`) |
| Messaggio nella chat dell'editor CV — §4.17 | — | — | **sempre a credito**, nessun messaggio gratuito | **0,20 €**/messaggio (`PRICE_CV_DRAFT_CHAT_MESSAGE`) |
| Messaggio nella chat dell'editor cover letter — §4.19 | — | — | **sempre a credito**, nessun messaggio gratuito | **0,20 €**/messaggio (`PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE`) |

**Senza costo e senza contatore:**
- raccolta notturna e scoring;
- import del CV in onboarding (al massimo **5 al giorno**, senza estensione a credito; un import non riuscito per un errore del servizio AI non viene conteggiato);
- modifica, anteprima e **PDF finale** degli editor di CV e cover letter;
- preferiti, archiviazione, filtri salvati (massimo 50 per utente, §4.21);
- "candidatura fatta".

**Ricerche salvate:**

| | Free | Pro |
|---|---|---|
| Ricerche salvate | 10 | 100 |
| Ricerche attive | 1 per tipo (max 2) | 50 in totale |

**Regole del credito.**
- Il credito è un **saldo unico in euro** sull'account. Copre tutte le azioni della tabella, sia sul Free sia sul Pro, tranne l'import, che resta precluso al Free.
- Un'azione **fallita** non consuma nulla: l'unità di massimale o l'importo scalato vengono restituiti.
- **Contatori e prezzi visibili** (Sprint 70): in Impostazioni il riquadro **"I tuoi limiti di oggi"** mostra per ogni azione a massimale usate oggi / massimale del piano e prezzo oltre il massimale ("Solo piano Pro" per l'import sul Free, "Non disponibile" per raccolta manuale e import CV), più il prezzo a messaggio delle due chat e l'ora in cui i contatori ripartono. Sotto i pulsanti di import da link, "Aggiungi manualmente" (anche nel popup) e "Raccogli ora" un'indicazione dice cosa succede alla prossima richiesta: "Incluso nel piano: ne restano N su M oggi", "Massimale di oggi raggiunto: questa azione costa X € (saldo Y €)" oppure, se il saldo non basta, che l'azione è bloccata.
- **Conferma prima dell'addebito** (Sprint 70): quando la richiesta andrebbe a credito, import da link, job manuale e le generazioni di CV, cover letter e messaggi del dettaglio chiedono conferma ("questa azione costa X € e verrà scalata dal tuo saldo (Y €). Procedere?"); nei pannelli di generazione del dettaglio compare anche l'indicazione del costo della prossima richiesta. I prezzi sono valori di default configurati dall'amministratore, non "da definire". La conferma è una **finestra dell'app** ("Costo dell'azione", Procedi / Annulla, mockup `confirm-cost`, SPEC-DELTA A11): nella lista dallo Sprint 74 (import, job manuale), nel dettaglio dallo Sprint 75 (CV, cover letter, messaggi); prima era la finestra di sistema del browser. Negli editor non c'è nessuna conferma: "Genera PDF finale" è gratuito e la chat mostra prezzo e saldo prima di ogni messaggio (§4.17). Con il massimale raggiunto e il saldo insufficiente il pulsante del pannello è disattivato e il motivo è scritto sopra.
- Le **chat** degli editor sono utilizzabili **solo con credito disponibile**.
- I massimali si **azzerano a mezzanotte (Europe/Rome)**, per tutti gli utenti.

**Gestione di piano e credito.**
- Non c'è checkout né ricarica self-service.
- **Non esistono voucher né codici sconto.**
- Piano e credito si modificano **solo dall'amministratore** (pannello di amministrazione). In Impostazioni l'utente vede piano e saldo, con la nota "Piano e credito sono gestiti dall'amministratore".
- Il **downgrade Pro→Free** disattiva tutte le ricerche (§4.2).

> **Conseguenza operativa.** Senza credito caricato dall'amministratore, i massimali sono di fatto **tetti rigidi** e le chat degli editor non sono utilizzabili.

### 4.12 Notifiche

Sono **notifiche push del browser o della PWA**. Si attivano da **Impostazioni** con "Attiva notifiche": l'app chiede il permesso del browser e registra il dispositivo.
- Su iOS l'app invita prima ad aggiungerla alla schermata Home.
- **Preferenza "Ricevi notifiche push"** (Sprint 67), nello stesso riquadro, attiva di default:
  - togliendo la spunta le notifiche si spengono per l'account: l'app **elimina le registrazioni di tutti i dispositivi**, annulla quella del browser in uso e mostra "Notifiche disattivate: non riceverai notifiche su nessun dispositivo…"; nessuna notifica (mattutina o di inattività) viene più inviata;
  - per riattivarle si rimette la spunta e si preme di nuovo "Attiva notifiche" su ogni dispositivo. Anche attivare le notifiche su un dispositivo riaccende la preferenza.
- **Logout** (Sprint 70): il dispositivo da cui si esce smette di ricevere le notifiche dell'account (registrazione eliminata sul server e annullata nel browser); gli altri dispositivi restano registrati. Dopo un nuovo accesso le notifiche vanno riattivate con "Attiva notifiche".
- **Riattivazione** (Sprint 70): rimettendo la spunta, o attivando le notifiche su un dispositivo dopo averle spente, la notifica mattutina riparte da quel momento: i job creati mentre le notifiche erano spente non la fanno partire.

**Notifica mattutina.**
- Parte nella fascia **10:00–10:59 locali**, **solo se** esistono **nuovi job**: job creati **dopo l'ultima notifica mattutina** inviata a quell'utente (o dopo la registrazione).
- Contano tutti i job nuovi: raccolti di notte o con la raccolta manuale, importati, creati a mano, anche senza punteggio.
- Ogni batch viene annunciato **una sola volta**.
- Testo: "Nuovi job pronti" / "Ci sono nuove offerte da valutare nella tua lista" (in inglese: "New jobs ready" / "There are new job offers to review in your list").

**Notifica di inattività.**
- Parte se **per 7 giorni** l'utente non segna alcuna "candidatura fatta". Il timer parte dalla registrazione e si azzera a ogni candidatura.
- Viene inviata una sola volta per periodo di inattività.
- Scatta anche per chi non ha mai generato documenti e per chi usa l'app senza marcare candidature (effetto voluto, §8).
- Testo: "Non ti candidi da un po'" / "Entra nell'app e valuta le offerte in attesa" (in inglese: "You haven't applied in a while" / "Open the app and review the pending job offers").

**Valgono per entrambe:**
- un clic sulla notifica apre l'app sulla lista;
- i testi sono in italiano o in inglese secondo la **lingua dell'interfaccia** salvata sull'account al momento dell'invio (Sprint 71; prima solo in italiano);
- l'"ora locale" è quella del fuso dell'utente, impostabile in Impostazioni dallo Sprint 70 (default: il fuso del dispositivo alla registrazione; Europe/Rome per gli account precedenti).

### 4.13 Statistiche e raccolta (Sprint 44; dallo Sprint 73–74 in Jobs)

Dallo Sprint 73 la pagina Home non esiste più. Dallo Sprint 74 (mockup `jobs-lista`, `jobs-stats`) le statistiche sono un **riepilogo espandibile** nella sezione Raccolti della lista, sotto la ricerca: chiuso mostra i **job trovati oggi** ("nuovi oggi") e **negli ultimi 7 giorni** ("questa settimana"); "Statistiche ▾" lo apre su **"Le tue statistiche"**, con tre gruppi e i valori **Oggi / Settimana / Totali**:
  - **Job trovati**, con la riga "di cui manuali: N oggi · N in settimana · N in totale". Contano tutti i job dell'utente per data di raccolta, a prescindere da sezione e archiviazione. "Manuali" comprende sia i job importati da link sia quelli creati a mano.
  - **CV generati**: ogni CV prodotto, incluse le generazioni e ogni PDF finale prodotto dall'editor. Le cover letter non sono contate.
  - **Candidature fatte**: job marcati "candidatura fatta", per data di marcatura.

La raccolta manuale (§4.14) è in un pannello a parte, aperto dal pulsante Raccogli accanto al titolo.

**Definizioni dei periodi:**
- "Oggi" parte dalla mezzanotte nel fuso dell'utente;
- "Ultima settimana" sono gli **ultimi 7 giorni mobili**, non la settimana di calendario;
- "Totali" è tutto lo storico.

Le statistiche si caricano all'apertura della lista e si ricaricano dopo una raccolta manuale riuscita, insieme alla lista. Non ci sono altre metriche.

### 4.14 Raccolta manuale "Raccogli ora"

- Dal pannello **"Raccogli nuovi job"** (pulsante Raccogli accanto al titolo della lista, o "Raccogli ora" nello stato vuoto di Raccolti), il pulsante **"Raccogli ora"** esegue subito, per il solo utente, la stessa raccolta + scoring della notte, sulle sue ricerche attive (con la finestra delle 24 ore).
- Al termine l'avviso "Raccolta completata." e, nel pannello, "Ultima raccolta: N job trovati, M tenuti dopo lo scoring"; la lista e le statistiche si ricaricano. Sotto il pulsante l'indicazione del limite ("Incluso nel piano: ne restano X su 1 oggi").
- **Limite:** **1 al giorno** (azzeramento a mezzanotte Europe/Rome), uguale per tutti i piani, **senza estensione a credito**. Oltre: "Hai già usato la raccolta manuale per oggi. Massimo 1 al giorno."
- **Una sola raccolta per volta.** Se ne è già in corso una: "Raccolta già in corso per questo account." Un blocco rimasto appeso si considera scaduto dopo **2 ore**.
- **Fallimento:** "Raccolta non riuscita. Riprova più tardi.", con il tentativo giornaliero restituito. Se fallisce solo una parte dei gruppi di ricerche, la raccolta conta come riuscita con le offerte degli altri gruppi.
- **Testi del pannello** (Sprint 74, mockup `collect-free` senza il riquadro della raccolta automatica, che arriva con lo Sprint 77): avvia subito la ricerca sulle ricerche attive; un riquadro spiega che il raccoglitore prende **solo i job pubblicati nelle ultime 24 ore**; la raccolta notturna gira comunque.
- Per concedere una seconda raccolta lo stesso giorno l'amministratore usa un'azione dedicata in Django Admin (Sprint 68).
- **Attesa:** la raccolta avviene mentre l'utente aspetta sulla pagina e può durare minuti: il pannello mostra un indicatore con "Raccolta in corso…" e non si chiude finché non finisce (mockup `collect-running`).
- La raccolta manuale **non sostituisce** quella notturna, che gira comunque per tutte le ricerche attive.

### 4.15 Creazione manuale di un job (Sprint 43)

- Nella sezione **Importati**, il pulsante **"Aggiungi manualmente"** è disponibile sia sul **Free** sia sul **Pro**.
- Apre un **pannello** (Sprint 74, mockup `add-manual`) con:
  - campi obbligatori: **titolo**, **azienda**, **località** (con autocompletamento), **descrizione**, **data e ora di riferimento** (usata come data di pubblicazione);
  - campo facoltativo: **link di candidatura**.

  Gli errori di validazione sono mostrati campo per campo.
- Il job viene **valutato subito**, compare in **Importati** in stato "nuovo" e da lì si comporta come gli altri. Non ha dati su candidati e recruiter.
- Se la creazione fallisce, il massimale o il credito vengono restituiti. Se fallisce solo la valutazione, il job resta (senza punteggio) e la valutazione viene ritentata di notte come per i job raccolti, senza restituzione (Sprint 68).
- **Limite:** **3 al giorno**, con contatore separato da quello dell'import. Oltre, **0,50 €** a credito (`PRICE_MANUAL_JOB_EXTRA`). In fondo al pannello l'indicazione del costo della prossima richiesta; se il massimale è raggiunto e il saldo non basta, "Aggiungi" è disattivato (Sprint 74).
- Non c'è controllo di duplicati: lo stesso job inserito due volte crea due job.

### 4.16 Editor del CV (Sprint 51; ritocchi grafici 52–58)

**Accesso.**
- Dal dettaglio di un job con CV, pulsante **"Modifica CV"** (dallo Sprint 75 la matita nella riga del CV, sezione Documenti).
- L'editor si apre sulla **bozza** del CV, creata la prima volta a partire dall'ultimo CV generato.
- **Bozza superata** (Sprint 69): se dopo l'apertura della bozza è stato generato un CV più recente, l'editor chiede *"Vuoi ripartire dal nuovo documento (le modifiche precedenti e la chat si perdono) o continuare la bozza?"*. "Riparti dal nuovo CV" ricrea la bozza dal documento nuovo e svuota la chat; "Continua la bozza" la riapre com'è e la domanda non si ripete per quel CV. Il PDF prodotto da "Genera PDF finale" non conta come documento più recente.
- I CV generati **prima dello Sprint 51** non sono modificabili: il pulsante "Modifica CV" non compare e il dettaglio spiega di rigenerare il CV (Sprint 69).

**Aspetto** (Sprint 76, redesign UI, mockup `cv-editor`, `cv-preview`, `desk-editor`): testata con "‹ Torna al job", stato del salvataggio ("Salvataggio…", "✓ Salvato" o "Non salvato" se il salvataggio non riesce), titolo, job · azienda e indicatore delle pagine; segmento **Modifica / Anteprima**; le sezioni (Sommario, Qualifica professionale, Aree di competenza, Esperienze, Istruzione, Competenze, Certificazioni, Lingue) sono **a fisarmonica**: all'apertura è aperto solo il Sommario, le altre mostrano un riassunto ("3 aree", "2 aziende", "1 di 3"…); dentro Esperienze ogni azienda è a sua volta una fisarmonica. In basso la **barra azione** (al posto della barra di tab, a ogni larghezza) con **"Assistente"** (sotto i 1024 px) e **"Genera PDF finale"**. Se il PDF supera una pagina un avviso lo dice sotto il segmento.

**Cosa si può modificare** (le regole complete sono nel doc 03):
- **sommario** e **qualifica**, con grassetto (Sprint 69);
- **Areas of Expertise**: modifica, aggiunta, rimozione, riordino;
- **esperienze**:
  - compaiono **tutte** quelle del profilo, comprese quelle escluse dal limite di 5, con l'interruttore "Mostra nel CV" (una spunta fino allo Sprint 75);
  - il **ruolo** è modificabile (con grassetto);
  - azienda, località e date sono in sola lettura;
  - l'ordine delle esperienze non cambia;
- **bullet**:
  - compare il pool completo prodotto dall'AI, ciascuno con la spunta "Visibile" (all'inizio vale la selezione automatica);
  - testo modificabile, con **grassetto** (pulsante B o Ctrl/Cmd+B);
  - aggiunta (fino a 30 per esperienza, il limite del server: al limite "Aggiungi punto" si disattiva con il motivo, Sprint 76), rimozione, riordino;
  - pulsante ✦ per usare il bullet come contesto della chat (§4.17);
- **istruzione**: tutti i campi, con aggiunta e rimozione; le note con grassetto;
- **lingue**: lingua e livello dalla lista fissa, con aggiunta e rimozione.
- Dallo Sprint 76 i pulsanti "Aggiungi" mostrano i limiti del server già esistenti (20 aree, 20 voci di istruzione, 30 lingue) e i campi semplici dell'istruzione hanno la lunghezza massima del server (300 caratteri, 100 per il periodo).

  Le modifiche a istruzione e lingue valgono **solo per quel CV** e non toccano il profilo.
- **competenze e certificazioni**: si scelgono con le checkbox **solo tra quelle del profilo**.

**Anteprima e salvataggio.**
- L'**anteprima** è il PDF reale, aggiornato a ogni modifica, con l'indicatore "1 pagina ✓" oppure "N pagine ⚠". Dallo Sprint 76 si vede nella scheda **Anteprima** del segmento (prima accanto all'editor su desktop e sotto su mobile), in proporzione A4, con la didascalia "Anteprima del PDF reale, aggiornata a ogni modifica."
- Nell'editor **non c'è un taglio automatico**: se il CV supera una pagina lo si segnala e decide l'utente.
- **Salvataggio automatico** circa 1 secondo dopo l'ultima modifica, con lo stato "Salvataggio… / Salvato".

**PDF finale.**
- **"Genera PDF finale"** produce un nuovo CV dalla bozza, **senza AI e senza consumare massimale o credito**, includendo anche l'ultima modifica non ancora salvata (Sprint 69). Poi l'app torna al job; se il PDF supera una pagina lo segnala.
- Il nuovo PDF diventa quello scaricabile.
- Lo stato del job non cambia.
- La bozza resta disponibile.
- Il PDF finale conta tra i "CV generati" delle statistiche (§4.13).

### 4.17 Chat AI dell'editor CV (Sprint 59–62)

**Apertura.** Dallo Sprint 76 (mockup `cv-assistant`, `desk-editor`): da 1024 px la chat ("Assistente bozza") è una **colonna fissa a destra** dell'editor (400 px), sempre visibile, e l'editor resta utilizzabile accanto (anche per puntare i bullet); sotto i 1024 px il pulsante **"Assistente"** della barra in basso la apre in un **pannello dal basso**, che si chiude con la ✕ o con Esc e resta sopra la tastiera del telefono. Conversazione, decisioni e testo non ancora inviato restano chiudendo e riaprendo il pannello. Fino allo Sprint 75 era un pannello laterale aperto dal pulsante flottante "Chiedi all'AI".

**Proposta → conferma.**
- L'utente scrive una richiesta (Invio invia, Shift+Invio va a capo; al massimo 2.000 caratteri, il limite del server, con contatore vicino al limite) e la invia con il pulsante ↑.
- L'assistente risponde con un testo e con **0 o più proposte di modifica puntuali**. Ogni proposta è una scheda con "prima" (barrato) e "dopo", e i pulsanti **Rifiuta / Accetta**; una volta decisa la scheda si riduce al titolo con "Applicata" o "Rifiutata" (Sprint 76).
- **Nulla viene applicato senza conferma.** "Accetta" applica la modifica alla bozza come farebbe l'utente a mano, quindi partono salvataggio automatico e anteprima.
- Le decisioni restano registrate: riaprendo la chat, anche dopo un ricaricamento, le proposte già decise appaiono come "Applicata" o "Rifiutata" (Sprint 62).
- Una semplice domanda riceve una risposta senza proposte.

**Cosa può proporre:**
- modificare sommario, qualifica, ruolo di un'esperienza, bullet, Areas of Expertise, note dell'istruzione, livello di una lingua;
- aggiungere bullet e aree;
- mostrare o nascondere bullet ed esperienze;
- rimuovere aree;
- attivare o disattivare competenze e certificazioni del profilo.

**Cosa non può proporre:** riordini, eliminazione di bullet, modifiche a titolo, istituto o date dell'istruzione, aggiunta o rimozione di lingue o voci di istruzione.

**Contesto.** Con il pulsante ✦ sotto ogni bullet (cumulabile, anche su esperienze diverse) l'utente indica i bullet a cui si riferisce. Sopra il campo di testo compaiono come chip "Contesto:" (dallo Sprint 76 con la ✕ per toglierli) e aiutano l'assistente a capire richieste generiche (Sprint 61). Dallo Sprint 69 bullet puntati e proposte si riferiscono al bullet stesso, non alla sua posizione: riordinare o eliminare bullet, o accettare più proposte dello stesso turno, non sposta mai una modifica su un altro bullet. Se l'elemento di una proposta non esiste più, la proposta non viene applicata e il pannello lo dice. L'assistente conosce anche le proposte fatte prima e la scelta dell'utente (accettata, rifiutata, in sospeso). Prima di inviare un messaggio l'app salva l'eventuale modifica in attesa, così l'assistente vede la bozza come è a schermo.

**Grounding.**
- Il testo narrativo può essere ampliato oltre il profilo **solo su richiesta esplicita** dell'utente, e l'assistente deve dirlo nella risposta.
- Competenze e certificazioni restano **sempre** quelle del profilo, **senza eccezioni**: le proposte non conformi vengono scartate.

**Costo.** **Ogni messaggio costa 0,20 € di credito**, senza massimale gratuito. Prezzo e saldo sono mostrati sopra il campo di testo prima dell'invio ("Ogni messaggio costa 0,20 € di credito · saldo: X €", Sprint 69), con i valori dati dal server. Con credito insufficiente compare "Saldo credito insufficiente per inviare un altro messaggio."; dallo Sprint 76 lo si vede già prima di scrivere (saldo minore del prezzo): campo e invio sono disattivati e il motivo è scritto nella conversazione. Se l'assistente non risponde, il credito viene restituito. Nessuna finestra di conferma del costo (non c'era nemmeno prima).

**Persistenza.** La conversazione è conservata nella bozza del CV (e si azzera se l'utente riparte da un CV più recente, §4.16). Se la registrazione di una scelta Accetta/Rifiuta non riesce, l'app ritenta e, se non ci riesce, lo segnala; dallo Sprint 76 gli avvisi (scelta non salvata, elemento non più nella bozza, errore dell'assistente) compaiono nel flusso della conversazione, dopo il messaggio a cui si riferiscono (mockup `cv-assistant-warn`).

**Avviso AI** (Sprint 67): sotto il prezzo, sopra il campo di testo, compare "Contenuto generato con l'AI: verificalo prima di usarlo.".

### 4.18 Cover letter (Sprint 42)

**Generazione.**
- Dal dettaglio del job, **"Genera cover letter"** è disponibile su **qualunque job**, anche senza CV, e solo su richiesta: dal ▾ di "Genera CV" nella barra in basso oppure da "Genera" / "Rigenera cover letter" nella riga della cover letter (Sprint 75).
- Il pannello (dallo Sprint 75 dal basso, mockup `detail-cover-letter`; prima un popup) contiene:
  - un campo libero "Indicazioni per questa cover letter (facoltativo)";
  - **"Oppure riusa indicazioni date in precedenza"**: fino a 20 indicazioni distinte, prese da tutte le cover letter dell'utente, dalla più recente, da selezionare con un tocco (pillole; prima checkbox).

  Le indicazioni selezionate si sommano al testo nuovo; il totale non può superare 2.000 caratteri: il campo ha un contatore e, se le indicazioni scelte e il testo insieme superano il limite, il pulsante è disattivato con il motivo (Sprint 75). Dallo Sprint 69 una combinazione di indicazioni riusate non compare nello storico come voce nuova (compare solo l'eventuale testo nuovo), e due indicazioni che differiscono solo per spazi o maiuscole sono una voce sola.
- Le indicazioni possono orientare tono ed enfasi oppure introdurre **fatti reali non presenti nel profilo**, sotto la responsabilità dell'utente.
- In fondo al pannello compare l'avviso AI (Sprint 67, §4.7) e il costo della prossima cover letter (fino allo Sprint 74, per errore, il pannello mostrava quello dei messaggi).

**Struttura.**
- Nome e cognome.
- Riga contatti "Città, PAESE | telefono | email del profilo", **senza LinkedIn**.
- **Oggetto**, **saluto generico** (es. "Dear Hiring Manager,") e **chiusura** con firma: testi fissi tradotti nella lingua della lettera, mai scritti dall'AI.
- Da **3 a 5 paragrafi** scritti dall'AI:
  - apertura sul ruolo;
  - 1–2 paragrafi di esperienze reali;
  - un paragrafo per le indicazioni dell'utente, se presenti;
  - chiusura.
- Non contiene data, destinatario, foto, istruzione, lingue né grassetti.

**Lingua.** Segue la stessa impostazione del CV (§4.7).

**Impaginazione.** **1 pagina** come obiettivo: se serve, il testo si compatta fino a 3 livelli (carattere, interlinea, margini). Altrimenti la lettera esce su più pagine, e dallo Sprint 69 l'app lo segnala (dopo la generazione e nel dettaglio del job). Lo stile grafico è proprio e **diverso da quello del CV** (scelta confermata nello Sprint 69).

**Download.** **"Scarica cover letter"** (icona nella riga della cover letter) scarica l'ultima generata, con nome `Cover letter {Nome Cognome} - {Titolo del job}.pdf`.

**Effetti.**
- La cover letter **non cambia lo stato** del job e non lo toglie dall'archivio.
- Ogni generazione ne crea una nuova; l'app mostra solo l'ultima.

**Limiti.**
- Massimale **Free 1 / Pro 10 al giorno**, indipendente da quello del CV. Oltre, **1,50 €** a credito.
- Una generazione alla volta per job, indipendente da quella del CV.
- Il profilo completo non è un prerequisito.

### 4.19 Editor e chat della cover letter (Sprint 63)

**Editor.**
- Si apre con **"Modifica Cover Letter"** dal dettaglio (dallo Sprint 75 la matita nella riga della cover letter), quando esiste una lettera. Funziona come l'editor del CV, ridotto ai soli **paragrafi**:
  - modificare il testo;
  - spostare su e giù;
  - eliminare;
  - "Aggiungi paragrafo" (fino a 15, testo fino a 3.000 caratteri: i limiti del server, Sprint 76).
- Dallo Sprint 76 (mockup `cover-editor`) stesso impianto dell'editor del CV: testata, segmento Modifica / Anteprima, un riquadro per paragrafo ("Paragrafo 1 · Apertura", "Paragrafo 2", …, l'ultimo "· Chiusura") con su, giù ed elimina, barra in basso con "Assistente" e "Genera PDF finale".
- Restano fissi oggetto, saluto, chiusura, nome e contatti.
- L'anteprima PDF è live, con il conteggio delle pagine.
- Il salvataggio è automatico.
- **"Genera PDF finale"** è gratuito e senza AI. La lettera finalizzata diventa quella scaricabile, ma non entra tra le indicazioni riusabili.
- Le lettere generate **prima dello Sprint 63** non sono modificabili: il pulsante "Modifica Cover Letter" non compare e il dettaglio spiega di rigenerarle (Sprint 69).
- **Bozza superata** e "Genera PDF finale" con l'ultima modifica non salvata: come nell'editor del CV (§4.16, Sprint 69).

**Chat.**
- "Assistente cover letter" (con messaggio iniziale e segnaposto propri della lettera, Sprint 69): dallo Sprint 76 colonna fissa a destra da 1024 px e pannello dal basso sotto, come il CV (§4.17); stesso schema proposta → conferma del CV, le decisioni conservate e il prezzo con il saldo mostrati prima dell'invio.
- Azioni possibili: **modificare**, **aggiungere** (in coda) o **rimuovere** un paragrafo. Le proposte si riferiscono al paragrafo, non alla sua posizione (Sprint 69): accettare più modifiche o rimozioni dello stesso turno colpisce sempre il paragrafo giusto.
- Non esiste il puntamento di un singolo paragrafo come contesto.
- **Grounding:** l'ampliamento oltre il profilo è ammesso solo su richiesta esplicita. Non si inventano mai aziende, ruoli o risultati, e la chat non scrive oggetto, saluto o chiusura.
- **Costo:** **0,20 € di credito per messaggio**, con un listino separato da quello della chat del CV.
- Il pannello mostra l'avviso AI come la chat del CV (Sprint 67).

### 4.20 Messaggi di networking (Sprint 50)

**Generazione.**
- Dal dettaglio del job, **"Genera messaggio"** è disponibile su qualunque job: dal ▾ di "Genera CV" nella barra in basso oppure da "Genera" nella riga "Messaggio" (Sprint 75).
- Il pannello (dallo Sprint 75 dal basso, mockup `detail-message`; prima un popup) contiene:
  - **canale**: LinkedIn (default) o Email, controllo a segmenti;
  - nome del destinatario (facoltativo, al massimo 255 caratteri);
  - link al profilo LinkedIn del destinatario (facoltativo, al massimo 500 caratteri, **solo per riferimento**: l'interfaccia spiega che non viene aperto né letto e non influisce sul testo, Sprint 69);
  - indicazioni libere (relazione con il destinatario, dettagli, tono), al massimo 2.000 caratteri con contatore, insieme alle indicazioni riusate (stessa regola della cover letter, §4.18);
  - pillole per riusare fino a 20 indicazioni date in passato (stesse regole di deduplica della cover letter, §4.18);
  - in fondo, l'avviso AI (Sprint 67, §4.7) e il costo del prossimo messaggio (fino allo Sprint 74, per errore, quello della cover letter).

**Contenuto.**
- **LinkedIn:** un messaggio breve, circa 80–100 parole al massimo, senza oggetto.
- **Email:** un **oggetto** (circa 60 caratteri al massimo) e un corpo di circa 150–180 parole al massimo.
- In entrambi i casi:
  - saluto e firma con il nome reale del candidato;
  - saluto generico se manca il nome del destinatario;
  - nessuna relazione pregressa inventata (per default si tratta come un primo contatto);
  - nessuna menzione di allegati;
  - una richiesta finale chiara.
- La lingua segue la stessa impostazione del CV.
- Il **link LinkedIn del destinatario viene salvato ma non usato** (non arriva nemmeno al modello come contesto): la lettura del profilo del destinatario è in backlog (§5.21). Dallo Sprint 69 compare nello storico come link "Profilo LinkedIn".

**Storico.**
- La scheda "Messaggi di networking generati" mostra **tutti** i messaggi del job, dal più recente, con canale, destinatario, link LinkedIn se indicato, data, oggetto (email) e testo.
- Ogni generazione **aggiunge** un messaggio: sullo stesso job si può scrivere a più persone.
- Con **"Copia"** il testo va negli appunti; per l'email il testo copiato include "Oggetto: …".
- I messaggi non si possono modificare né cancellare. Non c'è un PDF.

**Effetti e limiti.**
- Il messaggio non cambia lo stato del job. Durante la generazione il pulsante "Genera messaggio" resta disabilitato anche su altri dispositivi e dopo un ricaricamento (Sprint 69).
- Massimale **Free 1 / Pro 10 al giorno**, indipendente da CV e cover letter. Oltre, **1,00 €** a credito.

### 4.21 Preferiti e filtri salvati (Sprint 46, 64)

**Preferiti.**
- Il **cuoricino**, a sinistra del punteggio su scheda e dettaglio, aggiunge o toglie un job dai preferiti, con effetto immediato.
- La sezione **Preferiti** (§4.5) mostra i preferiti non archiviati. Togliendo il cuore da lì, la scheda sparisce subito.
- I preferiti non hanno limiti.

**Filtri preferiti** (Sprint 64).
- **Salvataggio:** **"Salva filtri attuali"** chiede un **nome** e salva **punteggio, stato, ricerca di provenienza, location, candidati e recruiter**. **Non salva mai le date** né la sezione. Salvato dalla sezione **Importati**, non contiene il filtro "Ricerca" (lì nascosto, Sprint 68).
- **Uso:**
  - ogni filtro salvato è una **pillola**;
  - un clic **copia** i valori nei filtri correnti, che restano modificabili senza toccare il filtro salvato;
  - il filtro si applica nella sezione in cui ci si trova;
  - la × elimina il filtro; se l'eliminazione non riesce, la pillola ricompare con il messaggio "Non siamo riusciti a eliminare il filtro. Riprova." (Sprint 68).
- **Limiti:**
  - **nessuna rinomina**: per cambiare nome si ricrea il filtro;
  - massimo **50 filtri per utente** (`MAX_JOB_FILTER_PRESETS`), indipendente dal piano.
- **Ricerca eliminata:** se il filtro richiama una ricerca che non esiste più, quella parte non filtra nulla e gli altri valori continuano a valere.
- I filtri salvati sono disattivati durante la ricerca testuale.

### 4.22 Pagina Profilo e impostazioni account (Sprint 46)

**Profilo** (voce di menu "Profilo"). Pagina "Modifica profilo" con:
- nome e cognome;
- "Situazione / obiettivo attuale" (Sprint 70, con la nota che oggi non è usato nella generazione dei documenti);
- sommario, telefono, email del CV, città e paese, LinkedIn;
- **foto**: anteprima della foto attuale, caricamento di una nuova (salvata con "Salva modifiche") e, dallo Sprint 70, **"Rimuovi foto"** con conferma, che elimina subito anche il file dal server;
- tutte le sezioni del profilo master (§4.1), con le **tecnologie** di ogni ruolo (Sprint 70).

Si salva con il pulsante "Salva". Limiti della pagina:
- **non** si può importare un CV (solo in onboarding);
- caricando una nuova foto la precedente viene eliminata (Sprint 67).

**Impostazioni** (voce di menu "Impostazioni"; dallo Sprint 70 anche il titolo della pagina è "Impostazioni" / "Settings", prima era "Il tuo account"). Sette riquadri:
1. **Piano e credito:** piano (Free/Pro) e saldo del credito extra, in sola lettura (§4.11).
2. **I tuoi limiti di oggi** (Sprint 70): contatori, massimali e prezzi (§4.11).
3. **Ricerche salvate:** creazione, modifica, eliminazione, attivazione e disattivazione (§4.2).
4. **Preferenze** (prima "Impostazioni"): lingua dell'interfaccia, **fuso orario** (Sprint 70: elenco IANA; decide l'"oggi" della lista e delle statistiche e l'ora della notifica mattutina), lingua dei documenti (inglese o lingua dell'offerta), foto nel CV.
5. **Notifiche push:** preferenza "Ricevi notifiche push" (Sprint 67) e attivazione sul dispositivo (§4.12).
6. **Privacy e sicurezza** (Sprint 67):
   - **Email di accesso** (Sprint 70): email attuale e cambio con nuovo indirizzo + password. Il server invia un link di conferma (valido 3 giorni) al nuovo indirizzo e un avviso a quello attuale ("se non sei stato tu, cambia la password"); l'app mostra "Ti abbiamo inviato un link di conferma a …". L'email di accesso cambia solo quando si apre il link (pagina "Nuova email di accesso", che funziona anche da un dispositivo non collegato); il link vale una volta sola. Se il nuovo indirizzo appartiene già a un altro account la risposta è la stessa ma non parte nessuna email; se lo diventa prima della conferma, la conferma è rifiutata. Senza invio di email configurato il riquadro dice che il cambio non è disponibile. L'email mostrata sul CV (Profilo) è un dato diverso e non cambia;
   - **Cambia password:** password attuale, nuova password ripetuta due volte. Dopo il cambio gli **altri dispositivi vengono disconnessi**, quello in uso resta collegato ("Password cambiata. Gli altri dispositivi sono stati disconnessi."). Password attuale errata o nuova password troppo debole producono un messaggio d'errore;
   - **Documenti legali:** link a informativa privacy e termini di servizio, ciascuno con la versione accettata e la data ("versione 1.0 accettata il …");
   - **Esporta i miei dati:** scarica subito un **archivio ZIP** con tutti i dati dell'account in formato JSON (account, accettazioni, profilo, ricerche, offerte con punteggi e motivazioni, documenti generati, bozze e chat, messaggi di networking, filtri salvati, quote giornaliere, sessioni, dispositivi registrati per le notifiche, registri delle elaborazioni), i PDF di CV e cover letter, la foto e un file di istruzioni in italiano e inglese. La password non è inclusa. **Al massimo 3 export al giorno**; oltre: "Hai già esportato i dati 3 volte oggi: riprova domani.".
7. **Zona pericolosa** (Sprint 67): **"Elimina account"**. Un popup chiede la **password** e una **conferma esplicita** ("Ho capito che tutti i miei dati verranno eliminati e non potranno essere recuperati"); senza entrambe il pulsante "Elimina definitivamente" resta disabilitato. L'eliminazione è **immediata e non annullabile**: account, profilo, ricerche, offerte, documenti, bozze, chat, messaggi, filtri, sessioni di tutti i dispositivi, notifiche, accettazioni e file (PDF e foto). L'utente torna alla pagina di login e riceve un'**email di conferma** (se l'invio di email è configurato); le copie di backup che contengono i suoi dati vengono cancellate automaticamente **entro 7 giorni**. I registri tecnici delle elaborazioni restano solo in forma anonima.

Export ed eliminazione sono disponibili anche dalla schermata di accettazione dei testi legali (§4.1), senza dover prima accettare.

**Lingua dell'interfaccia.**
- Disponibile in italiano e inglese.
- Si cambia in Impostazioni → Preferenze, dal selettore nella barra in alto su schermi da 1024 px e, prima del login, da quello in alto nelle pagine di accesso. La scelta viene salvata sull'account e al login successivo prevale.
- Al primo accesso il default è la lingua del dispositivo: italiano se è italiano, altrimenti inglese.

---

## 5. Funzionalità esplicitamente escluse (fuori perimetro)

1. **Candidatura automatica**, cioè l'invio diretto senza uscire dall'app.
2. **Hub completo per candidature esterne.** Esistono solo l'import puntuale da link LinkedIn (§4.9) e la creazione manuale di singoli job (§4.15), non un tracciamento generalizzato.
3. **Stati post-candidatura** (in colloquio, rifiutato, offerta…). La macchina a stati si ferma a "candidatura fatta", che non è annullabile.
4. **Checkout e pagamento reale**, compresa la ricarica self-service del credito. Non esistono **voucher o codici sconto**: piano e credito li gestisce solo l'amministratore.
5. **Fonti diverse da LinkedIn.** Un job di altra origine può solo essere inserito a mano (§4.15).
6. **Effetto della dichiarazione di obiettivo/situazione** su raccolta, scoring o generazione: il dato è salvato e inerte.
7. **Scelta della lunghezza del CV.** L'obiettivo è sempre 1 pagina.
8. **Ricalcolo dello score** dopo "colma i gap", dopo una modifica del profilo o dopo modifiche nell'editor. Non c'è nemmeno la rivalutazione dello storico dopo un cambio delle regole di scoring.
9. **Generazione automatica di CV** (o di cover letter e messaggi) per qualunque job. Rimossa nello Sprint 45: tutto è su richiesta.
10. **Filtri delle ricerche salvate oltre tipo, keywords e località**: tipo di contratto, modalità di lavoro e altri criteri non sono disponibili. Il tipo (Job role/Company) è l'unica deviazione accettata (sprint-39).
11. **Notifiche diverse** da quella mattutina e da quella di inattività, come avvisi al cambio stato o riepiloghi via email. Le uniche email inviate sono quelle di servizio dello Sprint 67 (verifica dell'indirizzo, tentativo di registrazione, recupero password, conferma di cancellazione, §4.1).
12. *(Voce rimossa in v6: l'editor in-app del CV esiste dallo Sprint 51, §4.16.)*
13. **Più profili master per utente.** Il profilo è uno solo (vedi §8).
14. **Aggiornamento automatico dei documenti già prodotti** dopo una modifica del profilo. L'utente può solo rigenerarli (con consumo di massimale) o modificarli negli editor.
15. **Feedback dell'utente sullo scoring** e qualsiasi apprendimento dai feedback.
16. *(Voce rimossa con lo Sprint 67: cancellazione dell'account ed export dei dati esistono, §4.22; i tempi di conservazione sono in §6.)*
17. **Vincoli di scala dichiarati.** L'app è pensata per pochi utenti di test.
18. **OCR sui CV caricati.** I CV in formato immagine o scansione non vengono letti.
19. **Download del CV (e della cover letter) in formato Word.** Solo PDF. L'upload in Word del CV di partenza resta supportato.
20. **Cache offline dei dati** sul dispositivo. "Apertura immediata" vuol dire reattività dell'app.
21. **Lettura del profilo LinkedIn del destinatario** per personalizzare i messaggi di networking (backlog, rinviato nello Sprint 50). Il link viene salvato ma non usato.
22. *(Voce rimossa con lo Sprint 67: recupero e cambio password esistono, §4.1 e §4.22.)*
23. **Scelta del template del CV e della cover letter.** Esiste un template per ciascun documento.
24. **Personalizzazione di oggetto, saluto, destinatario e chiusura della cover letter.** Sono testi fissi per lingua.
25. **Modifica e cancellazione dei messaggi di networking** generati.
26. **Ulteriori metriche nelle statistiche** oltre alle tre esistenti (erano state chieste "altre metriche a scelta", nessuna è stata implementata).
27. *(Voce rimossa con lo Sprint 70: l'email di accesso si cambia dalle Impostazioni, §4.22.)*
28. **Gestione dei consensi oltre i tre obbligatori**: non esistono consensi facoltativi (marketing, profilazione) né la revoca di singoli consensi; chi non accetta i testi può solo esportare i dati, eliminare l'account o uscire (Sprint 67).

---

## 6. Requisiti non funzionali rilevanti a livello utente

- **Multi-utenza con isolamento dei dati.**
  - Ogni utente vede solo il proprio profilo, le proprie ricerche, i propri job, documenti, bozze, messaggi e filtri salvati.
  - **Documenti e foto privati** (Sprint 66): CV, cover letter e foto si scaricano solo dall'app, con link personali che **scadono dopo un'ora** (la pagina del job li rinnova da sola); un link copiato e inoltrato smette di funzionare. La foto caricata viene ripulita dai metadati (per esempio posizione GPS e modello del telefono) e salvata con l'orientamento corretto; formati ammessi JPEG, PNG e WebP, fino a 5 MB.
- **Limiti di dimensione** (Sprint 66), con messaggio d'errore oltre il limite:
  - descrizione di un job creato a mano: 20.000 caratteri;
  - indicazioni per cover letter, messaggi di networking e "colma i gap", messaggi nelle chat degli editor: 2.000 caratteri;
  - CV da importare: 5 MB e 10 pagine (viene letto solo il testo, fino a 30.000 caratteri);
  - contenuto delle bozze negli editor: numero massimo di voci e lunghezza dei testi ampiamente sopra l'uso normale (dettaglio nelle specifiche tecniche §5.12).
- **Privacy e GDPR** (Sprint 67). I testi completi sono l'informativa privacy e i termini di servizio (§4.1, copia di riferimento in `Docs/legal/`); in sintesi:
  - **età minima 16 anni**, dichiarata in registrazione;
  - **dati nell'Unione Europea**: il server è nell'UE e le elaborazioni AI usano la regione AWS di Francoforte con instradamento limitato alle regioni AWS dell'UE. Alcuni fornitori di servizi accessori (invio email e notifiche push, raccolta delle offerte, che riceve solo keywords e località delle ricerche) possono trattare dati anche fuori dall'UE, come indicato nell'informativa;
  - **conservazione**: dati dell'account per tutta la sua durata e cancellati subito con l'eliminazione (§4.22); **copie di backup 7 giorni**, poi cancellate automaticamente; **log di sicurezza del server** (con indirizzi IP) **14 giorni**; dati temporanei per i limiti di frequenza **al massimo 24 ore**; sessioni che scadono dopo **30 giorni** senza utilizzo o al logout; registri tecnici delle elaborazioni per la durata dell'account, poi solo in forma anonima;
  - **diritti dell'interessato** esercitabili dall'app: accesso e portabilità con l'export dei dati, cancellazione con l'eliminazione dell'account, rettifica modificando profilo e impostazioni (dallo Sprint 70 anche l'email di accesso); per il resto si scrive al titolare indicato nell'informativa;
  - **nessun cookie di profilazione, analisi o pubblicità**: sul dispositivo restano solo il token di accesso e la lingua scelta (memoria locale del browser) e i file dell'app installabile;
  - **trasparenza AI**: i punti in cui l'app genera testo con l'AI mostrano l'avviso "Contenuto generato con l'AI: verificalo prima di usarlo." (§4.7).
- **Fuso orario.**
  - Il "giorno" della lista e delle statistiche (compreso il default "oggi" del filtro date) e l'orario delle notifiche seguono il fuso dell'utente, impostabile in Impostazioni e in onboarding (Sprint 70). I nuovi account ricevono il fuso del dispositivo; quelli precedenti restano su Europe/Rome finché l'utente non lo cambia.
  - Raccolta notturna e azzeramento dei massimali seguono sempre Europe/Rome.
- **Freschezza dei dati.** Al mattino si vedono le offerte pubblicate nelle 24 ore precedenti la raccolta notturna (o quella manuale).
- **Reattività — lista:** si apre senza attesa percepibile. Si intende reattività del server, **non** cache offline (§5.20).
- **Reattività — azioni AI** (CV, cover letter, messaggi, chat):
  - avvengono mentre l'utente attende, con un indicatore di caricamento sul pulsante;
  - non c'è un tempo massimo garantito;
  - la raccolta manuale può richiedere minuti;
  - durante l'attesa il comando sullo stesso job è disabilitato.
- **Aggiornamenti dell'app** (Sprint 70). Quando viene pubblicata una nuova versione, una scheda già aperta mostra in basso "Nuova versione disponibile" con il pulsante **"Aggiorna"**, che ricarica la pagina. L'app non si ricarica mai da sola, così non si perdono modifiche non salvate; il controllo avviene ogni 30 minuti e quando si torna sulla scheda.
- **Gestione dei fallimenti.**
  - Se un'azione AI fallisce, l'utente vede un messaggio semplice ("Non siamo riusciti a generare … Riprova."), non un errore tecnico, e **non perde** massimale né credito.
  - Se la raccolta notturna fallisce, all'utente semplicemente non arrivano job nuovi.
  - Lo scoring fallito lascia il job senza punteggio, senza messaggi.
  - La diagnosi resta lato server.
- **Lingua dell'interfaccia:**
  - italiano o inglese (default dalla lingua del dispositivo), modificabile e salvata sull'account;
  - dallo Sprint 71 anche **tutti i testi del server** seguono la lingua dell'interfaccia: messaggi d'errore e di validazione (login, registrazione, massimali e credito, limiti di piano, limiti di lunghezza, troppe richieste, accettazione dei testi legali, editor e chat, import), testi delle notifiche push, email di servizio (già dallo Sprint 67) e prefisso automatico del limite per lingua nella motivazione del punteggio (nella lingua del momento della valutazione, §4.4). Con l'interfaccia in italiano i testi sono gli stessi di prima;
  - non cambiano lingua i contenuti generati dall'AI (motivazioni, match e gap del punteggio, CV, cover letter, messaggi, risposte della chat), che seguono le loro regole (§4.7), né il Django Admin, che resta in italiano.
- **Lingua dei documenti:** vedi §4.7. Le etichette fisse esistono in 5 lingue (it/en/fr/de/es).
- **Veridicità dei contenuti.**
  - Le funzioni AI non inventano aziende, ruoli, periodi, competenze o certificazioni.
  - Gli ampliamenti avvengono solo nei casi espliciti: gap selezionati, richiesta esplicita in chat, indicazioni dell'utente nella cover letter.
  - La responsabilità di ciò che chiede di far emergere resta all'utente.

---

## 7. Criteri di accettazione (per funzione principale)

Formato: checklist di condizioni verificabili sull'as-is.

### Account, onboarding e profilo
- ☐ Ci si registra e si accede con email e password. Dopo la registrazione si entra nell'onboarding, dopo il login nella lista.
- ☐ Con un codice di invito configurato, la registrazione senza il codice corretto è rifiutata; il logout chiude la sessione del dispositivo; dopo 30 giorni senza utilizzo l'app chiede di nuovo il login (Sprint 66).
- ☐ I link di download di CV, cover letter e foto funzionano solo per il proprietario e scadono dopo un'ora (Sprint 66).
- ☐ La registrazione richiede le tre caselle (informativa letta, termini accettati, almeno 16 anni), mai pre-selezionate; senza anche una sola di esse è rifiutata, anche chiamando direttamente il server. Versione e data delle accettazioni restano registrate (Sprint 67).
- ☐ Con l'invio di email configurato: dopo la registrazione arriva un link di conferma valido 3 giorni; finché non è confermato il login è rifiutato con il messaggio dedicato e "Invia di nuovo il link"; un link scaduto o manomesso è rifiutato. Registrarsi con un'email già registrata dà la stessa risposta di una registrazione nuova e non crea un secondo account (Sprint 67).
- ☐ Senza invio di email configurato la registrazione fa entrare subito nell'app e "Password dimenticata?" mostra che il recupero non è disponibile (Sprint 67).
- ☐ "Password dimenticata?" risponde allo stesso modo per email registrate e non; il link ricevuto permette una sola volta di scegliere una nuova password e disconnette tutti i dispositivi (Sprint 67).
- ☐ Il cambio password dalle Impostazioni richiede la password attuale e disconnette gli altri dispositivi, lasciando collegato quello in uso (Sprint 67).
- ☐ Il cambio dell'email di accesso richiede la password; l'email cambia solo aprendo il link ricevuto al nuovo indirizzo, l'indirizzo attuale riceve un avviso, il link non vale una seconda volta; senza invio di email il cambio non è disponibile (Sprint 70).
- ☐ "Esci" è in fondo a Impostazioni, chiede conferma (Annulla non esce) e disattiva le notifiche push del dispositivo (Sprint 73).
- ☐ La navigazione ha tre voci (Jobs, Profilo, Impostazioni): barra di tab in basso sotto i 1024 px, barra in alto con logo da 1024 px; `/home` porta alla lista; nessuna pagina è più larga dello schermo a 360 e 390 px (Sprint 73).
- ☐ Con il profilo incompleto (nessun titolo di studio) ogni pagina, tranne onboarding e Profilo, mostra il banner con il link per completarlo (Sprint 70).
- ☐ Un utente che non ha accettato le versioni correnti di informativa e termini vede solo la schermata di accettazione, da cui può accettare, esportare i dati, eliminare l'account o uscire; nessun'altra funzione risponde finché non accetta (Sprint 67).
- ☐ `/privacy` e `/terms` si aprono senza login, in italiano o in inglese; se mancano i dati del titolare mostrano l'avviso; il footer con i due link è in tutte le pagine (Sprint 67).
- ☐ Il pulsante "Accedi con Google" non compare finché il login Google non è configurato (Sprint 67).
- ☐ "Esporta i miei dati" scarica uno ZIP con tutti i dati dell'account (JSON) e i suoi file, senza password né dati di altri utenti; dopo 3 export nello stesso giorno è rifiutato (Sprint 67).
- ☐ "Elimina account" richiede password e conferma esplicita; dopo l'eliminazione non resta alcun dato né file dell'utente, la sessione non funziona più e arriva l'email di conferma (Sprint 67).
- ☐ In onboarding l'utente inserisce nome e cognome, obiettivo (inerte), lingua dei documenti, opzione foto; compila il profilo; crea e attiva la prima ricerca.
- ☐ Il profilo ha sommario, esperienze, istruzione, competenze, certificazioni e lingue, più telefono, email del CV, città/paese, LinkedIn e foto. Non c'è una sezione "risultati chiave".
- ☐ Lingue e livelli si scelgono solo da una lista fissa (36 lingue, 4 livelli).
- ☐ Caricando un CV PDF o .docx il form viene pre-compilato (senza date, città e LinkedIn) e nulla viene salvato finché l'utente non conferma.
- ☐ Un CV senza testo leggibile produce l'avviso di compilazione manuale, senza creare un profilo vuoto.
- ☐ La generazione del CV è rifiutata con un messaggio se il profilo non ha almeno una voce di istruzione. Un'istruzione "in corso" (senza data di fine) è accettata.
- ☐ Le esperienze possono essere zero.
- ☐ Un bullet nuovo oltre 400 caratteri o un'esperienza con più di 15 bullet sono rifiutati; un'esperienza salvata prima oltre i limiti si salva ancora senza modificarne i bullet in eccesso (Sprint 70).
- ☐ Dalla pagina Profilo si rimuove la foto (anche il file sul server), si modificano le tecnologie dei ruoli e l'obiettivo (Sprint 70).
- ☐ Una modifica al profilo vale per i documenti generati in seguito, non per quelli già prodotti.

### Ricerche
- ☐ Una ricerca è definita da tipo (Job role/Company), keywords, città e paese.
- ☐ Free: fino a 10 ricerche salvate e 1 attiva per tipo. Attivandone una seconda dello stesso tipo, la precedente si disattiva e quella dell'altro tipo resta attiva.
- ☐ Pro: fino a 100 ricerche salvate e 50 attive in totale.
- ☐ Una ricerca si disattiva e si riattiva senza perdere i suoi dati. Solo le ricerche attive producono job.
- ☐ Al downgrade Pro→Free tutte le ricerche risultano disattivate. Con più di 10 ricerche salvate non se ne possono creare di nuove finché non si scende sotto 10.

### Raccolta, fonte e scoring
- ☐ Le offerte raccolte provengono da LinkedIn e sono state pubblicate nelle 24 ore precedenti.
- ☐ Non esiste un tetto per piano o per notte né un cap di intake: tutte le offerte valide raccolte vengono valutate e mostrate.
- ☐ Un'offerta senza titolo, azienda, località, descrizione o link non viene mostrata. Lo stesso vale per un'offerta con un campo troppo lungo. Un'offerta senza data di pubblicazione è ammessa.
- ☐ Un'offerta già presente tra i job dell'utente non viene ricreata.
- ☐ Ogni job valutato ha un punteggio da 1 a 10, una motivazione breve e match/gap, ciascuno con una motivazione.
- ☐ Se l'offerta richiede una lingua assente dal profilo, senza eccezione internazionale, il punteggio non supera 3 e la motivazione lo dichiara.
- ☐ Il ciclo notturno non genera alcun CV.
- ☐ Se lo scoring di un job fallisce, il job resta visibile senza punteggio, in fondo alla lista.

### Statistiche e raccolta manuale
- ☐ Nella sezione Raccolti il riepilogo mostra i job trovati oggi e in settimana; aperto mostra job trovati (con "di cui manuali"), CV generati e candidature fatte, per oggi, settimana e totali (Sprint 74).
- ☐ "Raccogli ora" (pannello aperto dal pulsante Raccogli) esegue raccolta + scoring sulle ricerche attive, mostra i job trovati e quelli tenuti e ricarica lista e statistiche.
- ☐ Una seconda raccolta manuale nello stesso giorno è rifiutata con "Massimo 1 al giorno", su tutti i piani e senza estensione a credito.
- ☐ Una raccolta manuale fallita non consuma il tentativo giornaliero.

### Lista, sezioni, filtri e ricerca
- ☐ Esistono quattro sezioni: Raccolti, Importati, Preferiti, Archiviati.
- ☐ All'apertura la lista mostra la sezione Raccolti con i job di oggi, ordinati per punteggio decrescente (i job senza punteggio in fondo).
- ☐ L'intervallo di date filtra per data di raccolta, estremi inclusi; "Tutte le date" mostra tutto lo storico.
- ☐ I filtri location, ricerca (multi), punteggio (1–10, multi), stato (multi), candidati (fasce, multi) e recruiter, nel pannello "Filtri", si combinano in AND, con OR dentro ciascun filtro multiplo, e si applicano subito; il pulsante Filtri mostra quanti gruppi sono attivi e "Cancella" / "Azzera filtri" li riportano ai valori di default (Sprint 74).
- ☐ Il filtro Ricerca non compare nella sezione Importati.
- ☐ La ricerca testuale trova job per titolo, azienda o località nella sola sezione corrente e, quando è attiva, ignora tutti gli altri filtri.
- ☐ La scheda mostra stato, candidati, titolo, azienda, località, icona del recruiter, data di raccolta, preferito, punteggio e i primi 2 gap con "+N altri"; tutta la scheda apre il dettaglio e non ha pulsanti di dettaglio, archiviazione o generazione (Sprint 74).
- ☐ Il dettaglio mostra stato (solo indicativo), punteggio, motivazione troncata con "Leggi tutto", contatori di corrispondenze e gap che aprono le voci con la motivazione, descrizione a fisarmonica; la barra in basso sostituisce la barra di tab con "Genera CV ▾", "Segna candidatura fatta" o "Annulla candidatura" secondo lo stato (Sprint 75).
- ☐ Dal menu ⋯ del dettaglio si archivia e si riporta un job dall'archivio, anche da tastiera (Sprint 75).
- ☐ La sezione Documenti mostra CV, cover letter e messaggi con stato, modifica, scarica, rigenera / genera e gli avvisi su più pagine e documenti non modificabili (Sprint 75).
- ☐ Le generazioni del dettaglio oltre il massimale chiedono conferma del costo in una finestra dell'app; con saldo insufficiente il pulsante del pannello è disattivato; durante l'attesa una finestra non chiudibile mostra l'indicatore (Sprint 75).
- ☐ Lo swipe archivia, con possibilità di annullare; uno swipe non apre il dettaglio. In Archiviati lo swipe riporta il job alla sezione d'origine con il suo stato.
- ☐ Generare o rigenerare un CV per un job archiviato lo fa uscire dall'archivio.

### Preferiti e filtri salvati
- ☐ Il cuoricino aggiunge o toglie un job dai preferiti. Un preferito archiviato compare solo in Archiviati.
- ☐ "Salva filtri attuali" (nel pannello Filtri) salva, con un nome, tutti i filtri tranne le date e la sezione.
- ☐ Import e job manuale oltre il massimale chiedono conferma del costo in una finestra dell'app; con saldo insufficiente "Aggiungi" è disattivato (Sprint 74).
- ☐ Applicare un filtro salvato copia i valori nei filtri correnti, che restano modificabili senza alterare il filtro salvato.
- ☐ Una ricerca eliminata dentro un filtro salvato non filtra nulla, mentre il resto del filtro continua a valere.
- ☐ Non si possono salvare più di 50 filtri.

### Stati del job e candidatura
- ☐ Gli stati stabili sono tre (nuovo, CV generato, candidatura fatta). Archiviato e preferito non sono stati.
- ☐ Ogni job nasce "nuovo", qualunque sia l'origine e il punteggio.
- ☐ Dopo una generazione riuscita del CV il job è "CV generato", salvo che fosse "candidatura fatta" (resta tale). Una generazione fallita non cambia lo stato (Sprint 69).
- ☐ "Segna candidatura fatta" è disponibile anche senza CV, una sola volta per job, e azzera il timer di inattività.
- ☐ "Annulla candidatura", dopo conferma, riporta il job a "CV generato" (o "nuovo" senza CV) senza toccare il timer di inattività (Sprint 69).
- ☐ Durante la generazione del CV il pulsante mostra "Generazione…" ed è disabilitato.

### Generazione CV e "colma i gap"
- ☐ La generazione è disponibile su qualunque job, entro il massimale (Free 1, Pro 10 al giorno) o, oltre, a credito (1,50 €). Con saldo insufficiente è bloccata con un messaggio.
- ☐ Una seconda richiesta sullo stesso job durante la generazione è rifiutata, senza un doppio consumo.
- ☐ Una generazione fallita mostra un messaggio, riporta il job a "nuovo" e restituisce massimale o credito.
- ☐ Il CV usa l'unico template, punta a 1 pagina, riporta la foto solo se l'opzione è attiva, mostra tutte le voci di istruzione senza riformularle e al massimo 5 esperienze.
- ☐ Competenze e certificazioni del CV sono solo quelle del profilo.
- ☐ Con lingua "inglese" il CV è in inglese. Con "lingua dell'offerta" segue la lingua dell'annuncio, con le etichette tradotte in it/en/fr/de/es (altrimenti in inglese).
- ☐ Il CV si scarica in PDF come `CV {Nome Cognome} - {Titolo}.pdf`.
- ☐ Nel pannello "Colma i gap" l'utente seleziona uno o più gap e, facoltativamente, scrive indicazioni. Il modello riceve gli stessi numeri e testi mostrati nel pannello (Sprint 69).
- ☐ I gap selezionati possono ampliare solo esperienze reali, mai creare aziende, ruoli o periodi né aggiungere competenze o certificazioni.
- ☐ Il contenuto prodotto per i gap non viene salvato nel profilo e non cambia il punteggio.

### Editor e chat del CV
- ☐ "Modifica CV" apre la bozza dell'ultimo CV, con tutte le esperienze e tutti i bullet del pool, ciascuno con mostra/nascondi.
- ☐ Se esiste un CV più recente della bozza, l'editor chiede in una finestra se ripartire dal nuovo documento o continuare la bozza; "Genera PDF finale" include l'ultima modifica a schermo (Sprint 69).
- ☐ Gli editor hanno sezioni a fisarmonica (CV) o riquadri per paragrafo (cover letter), il segmento Modifica / Anteprima e la barra in basso al posto della barra di tab; la chat è una colonna a destra da 1024 px e un pannello dal basso sotto; con saldo minore del prezzo di un messaggio campo e invio sono disattivati con il motivo (Sprint 76).
- ☐ Istruzione e lingue modificate nell'editor non cambiano il profilo. Competenze e certificazioni si scelgono solo tra quelle del profilo.
- ☐ L'anteprima PDF si aggiorna a ogni modifica e indica il numero di pagine. Le modifiche si salvano da sole.
- ☐ "Genera PDF finale" produce il PDF scaricabile senza consumare massimale o credito e senza cambiare lo stato del job.
- ☐ La chat propone modifiche come "prima → dopo" e nulla si applica senza "Accetta". Le decisioni restano registrate dopo un ricaricamento.
- ☐ La chat rifiuta di aggiungere competenze o certificazioni assenti dal profilo e amplia i testi solo su richiesta esplicita.
- ☐ Ogni messaggio di chat scala 0,20 € di credito, mostrato con il saldo prima dell'invio. Con saldo insufficiente il messaggio è rifiutato; se la risposta fallisce, il credito viene restituito.

### Cover letter
- ☐ "Genera cover letter" è disponibile su qualunque job, anche senza CV, con indicazioni libere e riuso di indicazioni passate (fino a 20).
- ☐ La lettera ha nome, contatti senza LinkedIn, oggetto, saluto e chiusura fissi nella lingua della lettera, e 3–5 paragrafi generati.
- ☐ Massimale Free 1, Pro 10 al giorno, indipendente dal CV. Oltre, 1,50 € a credito.
- ☐ La cover letter non cambia lo stato del job e non lo toglie dall'archivio.
- ☐ Si scarica come `Cover letter {Nome Cognome} - {Titolo}.pdf`.
- ☐ "Modifica Cover Letter" permette di modificare, spostare, aggiungere ed eliminare paragrafi, con anteprima live e PDF finale gratuito.
- ☐ La chat della cover letter propone solo modifiche, aggiunte e rimozioni di paragrafi, a 0,20 € per messaggio.

### Messaggi di networking
- ☐ "Genera messaggio" produce un messaggio LinkedIn (senza oggetto) o un'email (con oggetto) firmato con il nome reale del candidato.
- ☐ Ogni generazione si aggiunge allo storico del job, e ogni messaggio ha "Copia".
- ☐ Massimale Free 1, Pro 10 al giorno, indipendente da CV e cover letter. Oltre, 1,00 € a credito.

### Import e creazione manuale
- ☐ Un utente Pro importa un job da un link LinkedIn. Un utente Free non può importare, nemmeno con credito.
- ☐ Oltre 3 import al giorno l'operazione scala 0,50 € dal credito, oppure è bloccata con saldo insufficiente.
- ☐ Un link non valido produce "Impossibile importare quel job." e non consuma massimale o credito.
- ☐ Un job già presente produce "Questo job è già nella tua lista." senza duplicati.
- ☐ Free e Pro possono creare un job a mano (titolo, azienda, località, descrizione e data obbligatori; link facoltativo), fino a 3 al giorno, oltre a 0,50 €.
- ☐ I job importati e creati a mano vengono valutati subito, compaiono in Importati come "nuovo" e non ricevono alcun documento automatico.

### Piani, massimali e credito
- ☐ Ogni azione della tabella di §4.11 ha un contatore giornaliero proprio, che si azzera a mezzanotte Europe/Rome.
- ☐ Il credito è un saldo in euro, visibile in Impostazioni e modificabile solo dall'amministratore. Non esistono voucher né checkout.
- ☐ "I tuoi limiti di oggi" mostra per ogni azione usate / massimale e prezzo extra, e i prezzi delle chat; import da link e job manuale indicano il costo della prossima richiesta e chiedono conferma quando andrebbero a credito (Sprint 70).
- ☐ Un'azione fallita non consuma né massimale né credito.

### Notifiche
- ☐ Le notifiche si attivano da Impostazioni.
- ☐ Togliendo la spunta "Ricevi notifiche push" l'utente non riceve più alcuna notifica e le registrazioni di tutti i suoi dispositivi vengono eliminate; riattivando le notifiche su un dispositivo la preferenza torna attiva (Sprint 67).
- ☐ Con job creati dopo l'ultima notifica mattutina, l'utente riceve la notifica tra le 10:00 e le 10:59 locali. Senza job nuovi, nessuna notifica.
- ☐ Uno stesso batch non viene annunciato due volte.
- ☐ Dopo il logout il dispositivo non riceve più notifiche dell'account; riattivando le notifiche, i job creati mentre erano spente non fanno partire la notifica mattutina (Sprint 70).
- ☐ Dopo 7 giorni senza "candidatura fatta" (a partire dalla registrazione o dall'ultima candidatura) l'utente riceve una volta il promemoria di inattività.

### Requisiti trasversali
- ☐ Un utente non vede in app dati di un altro utente.
- ☐ Se una raccolta fallisce, l'utente non vede errori tecnici.
- ☐ L'interfaccia è in italiano se il dispositivo è in italiano, altrimenti in inglese, ed è modificabile.
- ☐ Con l'interfaccia in inglese i messaggi d'errore del server, le notifiche push e il prefisso del limite per lingua sono in inglese; in italiano restano quelli di prima (Sprint 71).
- ☐ Le chat degli editor, i pannelli di generazione di CV, cover letter e messaggi mostrano l'avviso sul contenuto generato con l'AI (Sprint 67).
- ☐ L'app non usa cookie di profilazione né strumenti di analisi; i backup più vecchi di 7 giorni vengono cancellati automaticamente (Sprint 67).
- ☐ Dopo il rilascio di una nuova versione una scheda aperta mostra "Nuova versione disponibile — Aggiorna" e si ricarica solo premendo il pulsante (Sprint 70).

---

## 8. Punti aperti e limiti noti dell'as-is

Questa sezione elenca comportamenti anomali, limiti e incongruenze riscontrati nell'app al 2026-11-14 (resoconti as-is verificati sul codice), seguiti dalle decisioni di prodotto ancora da rivalutare. Non propone soluzioni.

### 8.A Comportamenti anomali e limiti rilevati

**Lista, scoring e dati storici**
1. **Job scartati dal vecchio cap ancora visibili.** *(Risolto nello Sprint 68.)* I job marcati (988 al 2026-11-14, nessuno con documenti o bozze) vengono eliminati e il marcatore rimosso. Prima dello Sprint 46 il cap dei 15 job al giorno marcava come scartati i job in eccesso. Il marcatore è rimasto sui job storici, ma né la lista né le statistiche lo considerano. I job scartati in passato (circa un migliaio, mai reintegrati) compaiono quindi in lista e nei conteggi della Home come job normali.
2. **Scoring fallito, job senza punteggio.** *(Risolto nello Sprint 68.)* I job senza punteggio sono ritentati al ciclo notturno successivo (massimo 3 fallimenti per job) e con un comando manuale; per il job creato a mano la valutazione viene ritentata, il massimale non è restituito (il job esiste). Se lo scoring di un job fallisce, il job resta in lista senza punteggio, in fondo all'ordinamento, e **non viene mai ritentato**. Non esiste un comando per rivalutarlo.
   - Lo stesso succede quando una raccolta si interrompe a metà: i job già creati restano senza punteggio.
   - Per un job creato a mano, il massimale è comunque consumato anche se la valutazione fallisce.
3. **Storico dei punteggi su scala 1–5 non riscalato.** *(Risolto nello Sprint 68.)* I punteggi storici sono riscalati ×2. Resta aperto: il limite per lingua dello Sprint 48 non è stato applicato ai job valutati prima (servirebbe una nuova valutazione AI per ognuno). I job valutati prima dello Sprint 47 conservano il punteggio su 1–5:
   - un vecchio "5" (il massimo) appare con il colore della fascia 5–6;
   - nel filtro rientra tra i "5" della nuova scala;
   - l'ordinamento mescola le due scale.

   Neanche il limite per lingua dello Sprint 48 è stato applicato ai job valutati in precedenza.
4. **Match e gap dei job vecchi.** I job valutati prima del 09/09/2026 hanno match e gap senza motivazione: per loro il pulsante "Espandi motivazioni" non compare.
5. **Filtro "Ricerca" dopo la modifica di una ricerca.** *(Risolto nello Sprint 68.)* Il job conserva il riferimento alla ricerca di provenienza. Restano associati per testo (comportamento precedente) solo i job storici non attribuibili con certezza; i job di ricerche eliminate non risultano associati a nessuna ricerca. L'associazione tra job e ricerca di provenienza si ricostruisce dai valori **attuali** della ricerca salvata. Se si cambiano keywords o località di una ricerca, i job raccolti prima non risultano più associati a lei nel filtro, anche se il badge mostra ancora la provenienza originale. Lo stesso vale per i job di ricerche eliminate.
6. **Provenienza di un job trovato da più ricerche.** Il job compare una sola volta e porta la provenienza di una sola ricerca. Non si può sapere quali altre ricerche lo avrebbero trovato.
7. **Filtri e sezione non conservati.** *(Risolto nello Sprint 68.)* Sezione e filtri sono nell'indirizzo della pagina. Tornando alla lista dal dettaglio di un job, sezione e filtri ripartono dai valori di default (Raccolti, oggi–oggi).
8. **Filtro salvato creato in Importati.** *(Risolto nello Sprint 68.)* Salva anche il filtro "Ricerca", che in quella sezione è nascosto e ignorato. Applicato da un'altra sezione, il filtro torna attivo.
9. **Eliminazione di un filtro salvato non confermata.** *(Risolto nello Sprint 68.)* Se l'eliminazione fallisce lato server, la pillola sparisce comunque fino al ricaricamento della pagina.
10. **Disattivazione automatica senza avviso (Free).** *(Risolto nello Sprint 68.)* Attivando una seconda ricerca dello stesso tipo, la precedente si spegne senza un messaggio esplicito, contrariamente a quanto previsto in origine.
11. **Modifica del tipo di una ricerca attiva.** *(Risolto nello Sprint 68.)* Cambiare il tipo (Job role ↔ Company) di una ricerca già attiva non ripassa dai limiti di piano: un utente Free può così trovarsi con 2 ricerche attive dello stesso tipo.

**Raccolta**
12. *(Risolto nello Sprint 68.)* **Un errore alla fonte faceva perdere tutta la raccolta notturna dell'utente**, non solo quella della ricerca coinvolta. Dal lato utente non si distingue da "nessun job nuovo".
13. *(Risolto nello Sprint 68.)* **Raccolta manuale e raccolta notturna potevano sovrapporsi**: non c'è un blocco comune.
14. **Seconda raccolta manuale nello stesso giorno.** *(Risolto nello Sprint 68.)* Azione dedicata in Django Admin. Quando serve, l'amministratore deve azzerare a mano il contatore: non esiste uno strumento dedicato.
15. **Testo fuorviante della raccolta manuale.** *(Risolto nello Sprint 68.)* Il testo della card dice che la raccolta manuale serve a "evitare di consumare chiamate nei giorni in cui non guarderesti i risultati". In realtà la raccolta notturna gira comunque per tutte le ricerche attive.
16. **Offerte scartate non tracciate.** *(Risolto nello Sprint 68.)* Contate nel diario tecnico della raccolta. Le offerte scartate per campi mancanti o troppo lunghi non vengono registrate: non si sa quante siano.

**Stati e generazione del CV**
17. **Rigenerare il CV toglie "candidatura fatta".** *Risolto nello Sprint 69: la candidatura resta.* Una generazione riuscita su un job già marcato "candidatura fatta" lo riporta a "CV generato", e il job esce dal conteggio "Candidature fatte" della Home.
18. **Una generazione fallita riporta sempre il job a "nuovo"**, anche se aveva già un CV scaricabile o era "candidatura fatta". In questo stato il job resta con un CV, ma con lo stato "nuovo". *Risolto nello Sprint 69: una generazione fallita non cambia più lo stato.*
19. **"Candidatura fatta" non annullabile.** *Risolto nello Sprint 69: "Annulla candidatura" con conferma (§4.10).* Un clic per errore non si può correggere dall'app.
20. **Numerazione dei gap incoerente.** *Risolto nello Sprint 69: stessi numeri e stesso testo in pannello e prompt (§4.8).* Nel pannello "Colma i gap" la numerazione mostrata è quella dell'elenco completo, mentre al modello arrivano numerati solo i gap selezionati, nell'ordine di selezione. Un'indicazione come "per il gap 2…" può così riferirsi a un gap diverso da quello che l'utente vede.
21. **CV su più pagine senza avviso.** *Risolto nello Sprint 69: avviso dopo la generazione e nel dettaglio, per CV e cover letter.* In casi residuali il CV generato può uscire su più pagine senza che l'utente lo sappia. Lo stesso vale per la cover letter.
22. **Avviso sulle esperienze impreciso.** *Risolto nello Sprint 69: il testo descrive la regola reale.* L'avviso "oltre 5 esperienze" dice che il CV mostrerà "le più pertinenti". In realtà il CV mostra le 5 più recenti, con al massimo una sostituzione per pertinenza (doc 03).

**Editor e chat (CV e cover letter)**
23. **La bozza non viene riseminata dopo una rigenerazione.** *Risolto nello Sprint 69: l'editor chiede se ripartire dal nuovo documento o continuare la bozza (§4.16).* Dopo "Rigenera CV" (o una nuova cover letter), "Modifica" riapre la **bozza precedente**, con le vecchie modifiche e la vecchia chat, non il documento appena generato. Il nuovo documento resta scaricabile, ma l'editor non lo mostra.
24. **Documenti vecchi non modificabili.** *Risolto nello Sprint 69 (in parte): restano non modificabili, ma il pulsante non compare più e il dettaglio spiega di rigenerarli.* I CV generati prima dello Sprint 51 e le cover letter generate prima dello Sprint 63 mostrano il pulsante "Modifica", ma non si aprono ("Genera prima…"): vanno rigenerati, consumando massimale o credito.
25. **"Genera PDF finale" può perdere le ultime modifiche.** *Risolto nello Sprint 69: il contenuto a schermo viaggia con la richiesta.* Se si preme il pulsante subito dopo una modifica (entro circa 1 secondo, prima del salvataggio automatico), l'ultima modifica può restare fuori dal PDF.
26. **Riferimento ai bullet fragile.** *Risolto nello Sprint 69: bullet e paragrafi hanno un riferimento stabile (§4.17, §4.19).* Il contesto ✦ della chat CV si basa sulla posizione del bullet: riordinare o eliminare bullet dopo averli indicati può spostare il riferimento su un altro bullet. Allo stesso modo, nella chat della cover letter, accettare più aggiunte o rimozioni dello stesso turno può far puntare le proposte successive al paragrafo sbagliato.
27. **Testi della chat della cover letter.** *Risolto nello Sprint 69.* Il messaggio iniziale e il segnaposto del campo parlano di "CV" e di "sommario".
28. **Grassetto solo nei bullet.** *Risolto nello Sprint 69: grassetto anche in qualifica, sommario, aree, ruolo e note, nell'editor e nel PDF.* I marcatori di grassetto sono riconosciuti solo nei bullet delle esperienze: se finiscono in altri campi (es. un sommario modificato) vengono stampati come asterischi.
29. **Prezzo della chat non visibile.** *Risolto nello Sprint 69: prezzo e saldo sopra il campo di testo. Dallo Sprint 70 il prezzo a messaggio è anche in Impostazioni, "I tuoi limiti di oggi".* Il costo per messaggio non viene mostrato prima dell'invio.

**Cover letter e networking**
30. **Pulsante "Genera messaggio" sbloccato.** *Risolto nello Sprint 69.* Il pulsante resta disabilitato solo durante la richiesta della pagina corrente: lo stato "in generazione" non viene mostrato agli altri dispositivi o dopo un ricaricamento. Il blocco lato server resta comunque attivo.
31. **Combinazioni di indicazioni nello storico.** *Risolto nello Sprint 69 (§4.18).* Le combinazioni di indicazioni riusate compaiono nello storico delle indicazioni come voci nuove, con eliminazione dei soli testi identici.
32. **Link del destinatario richiesto ma non usato.** *Chiarito nello Sprint 69: resta facoltativo e inerte, l'interfaccia dice che è solo un riferimento (§4.20).* Il link al profilo LinkedIn del destinatario viene chiesto e salvato, ma non influisce sul messaggio (§5.21).

**Account, piani e notifiche**
33. **Login con Google non completato.** Non è configurato in produzione e dallo Sprint 67 il pulsante è nascosto. Anche configurandolo, il ritorno da Google non produce una sessione dell'app e salterebbe le tre caselle dei consensi e il codice di invito: va completato prima di renderlo disponibile. Le pagine di accesso del componente usato per Google restano comunque raggiungibili dal browser; un account creato da lì non può usare l'app ed è soggetto alla schermata di accettazione.
34. *(Risolto nello Sprint 67: recupero e cambio password, cancellazione dell'account ed export dei dati esistono, §4.1 e §4.22.)*
35. **Contatori e prezzi non visibili.** *(Risolto nello Sprint 70: "I tuoi limiti di oggi" in Impostazioni; costo della prossima richiesta e conferma prima dell'addebito per import, job manuale, raccolta manuale e CV dalla lista. Resta da integrare la pagina del job: generazione di CV, cover letter e messaggi.)* L'utente non vede i massimali residui né i prezzi. Scopre il passaggio a credito solo dal saldo che cala, e il blocco solo dal messaggio d'errore.
36. **Fuso orario fisso.** *(Risolto nello Sprint 70: fuso impostabile in Impostazioni e in onboarding, default dal dispositivo alla registrazione; il default del filtro date usa il fuso dell'utente.)* Il fuso orario per utente esiste ma non si imposta da interfaccia: le "10:00 locali" e il "giorno" della lista sono di fatto quelli italiani. La data predefinita del filtro usa invece la data del dispositivo.
37. **Logout e notifiche.** *(Risolto nello Sprint 70: il logout disattiva le notifiche del dispositivo; alla riattivazione non si contano i job del periodo di silenzio.)* Il logout non disattiva le notifiche su quel dispositivo: per spegnerle si usa la preferenza in Impostazioni, che vale per tutti i dispositivi dell'account (dallo Sprint 67 le notifiche sono disattivabili).
38. **Lingua di messaggi e notifiche.** *(Risolto nello Sprint 71: messaggi del server, notifiche e prefisso del limite per lingua seguono la lingua dell'interfaccia, §6; le motivazioni con il prefisso salvate prima dello Sprint 71 restano in italiano.)* Messaggi d'errore del server, notifiche e prefisso del limite per lingua sono solo in italiano, anche con l'interfaccia in inglese.
39. **Import CV in errore.** *(Risolto nello Sprint 70: messaggi dedicati per file troppo grande, formato, pagine, limite giornaliero e servizio AI non disponibile.)* Se il servizio AI fallisce durante l'import del CV in onboarding, l'utente vede solo un errore generico (l'import non viene però conteggiato nel limite giornaliero).
40. **Limiti della pagina Profilo:** *(Risolto nello Sprint 70: foto rimovibile, tecnologie e obiettivo modificabili.)* non permette di rimuovere la foto; le tecnologie delle esperienze non sono modificabili da nessuna schermata; l'obiettivo è modificabile solo in onboarding.
41. **Onboarding saltabile.** *(Risolto nello Sprint 70: banner fisso con il link finché il profilo non è completo.)* Dopo il login non c'è alcun rimando all'onboarding se il profilo è incompleto: l'utente se ne accorge solo quando la generazione del CV viene rifiutata. Con la verifica dell'email attiva (Sprint 67) l'onboarding è proposto solo se il primo login avviene dal pulsante della pagina di conferma; un login fatto in altro modo porta alla lista.
42. **Titolo della pagina Impostazioni.** *(Risolto nello Sprint 70.)* Il titolo è ancora "Il tuo account".
43. **Logout solo dalla lista.** *(Risolto nello Sprint 70: "Esci" nella barra in alto di ogni pagina; dallo Sprint 73 in Impostazioni con conferma.)* Il logout si trova solo nella pagina della lista job (e, dallo Sprint 67, nella schermata di accettazione dei testi legali).
44. **Tab rimaste aperte dopo un aggiornamento.** *(Risolto nello Sprint 70: avviso "Nuova versione disponibile — Aggiorna", senza ricaricamenti automatici.)* Una scheda dell'app aperta prima di un aggiornamento continua a usare la versione precedente finché non viene ricaricata (es. grassetti mostrati come `**testo**` nell'editor). Non c'è un ricaricamento automatico.

**Privacy, email e backup (Sprint 67)**
60. **Email non modificabile.** *(Risolto nello Sprint 70: cambio dalle Impostazioni con conferma al nuovo indirizzo.)* L'indirizzo email di accesso non si può cambiare dall'app (§5.27).
61. **Backup solo sul server.** Le copie di backup restano sullo stesso server dell'app: un guasto del disco le perderebbe insieme ai dati. Non sono cifrate; una copia altrove si fa solo a mano.
62. **Export lento per account molto grandi.** L'archivio viene preparato al momento del download: con moltissimi PDF può richiedere qualche secondo, senza indicazione di avanzamento oltre al pulsante "Preparazione…".
63. *(Risolto nello Sprint 67: il popup di eliminazione annuncia l'email di conferma solo se l'invio di email è configurato.)*

### 8.B Decisioni di prodotto da rivalutare

46. **Scoring rispetto all'utente primario.** Lo scoring misura l'affinità con il passato reale, non con l'obiettivo della persona in transizione. Il sostegno arriva solo a valle: "colma i gap", editor e chat, cover letter con indicazioni. Resta da verificare se serve un secondo segnale (desiderabilità rispetto a gap).
47. **Valore centrale ridimensionato.** Senza CV automatici, la promessa del mattino si riduce alla selezione già valutata. Ogni documento richiede un'azione e, oltre il massimale, credito.
48. **Un solo profilo master.** È in tensione con chi punta a due direzioni di carriera.
49. **Dichiarazione di obiettivo inerte.** L'onboarding raccoglie un dato che non viene usato da nessuna funzione.
50. **Documenti con contenuti non presenti nel profilo.** "Colma i gap", la chat su richiesta esplicita, le modifiche locali nell'editor e le indicazioni della cover letter producono documenti con contenuti assenti dal profilo. È voluto, ma rende il profilo una fonte di verità non esclusiva.
51. **Scarto per campi mancanti.** Esigere descrizione **e** link può eliminare annunci reali. È una scelta di qualità sopra quantità.
52. **Volume senza tetti.** Senza cap, un utente con molte ricerche può ricevere centinaia di job per notte (fino a 150 per gruppo di ricerche). È voluto (le richieste alla fonte sono comunque pagate), ma resta da osservare il carico sulla lista e i costi di scoring.
53. **Timer di inattività ancorato alla sola "candidatura fatta".** Scatta anche per utenti appena registrati o attivi che non marcano candidature (effetto voluto, da rivedere).
54. **Fonte non disponibile indistinguibile da "nessun job".** È voluto. Resta da valutare se in futuro serva distinguerli.
55. **Riferimenti orari diversi.** Raccolta e massimali seguono Europe/Rome; lista e notifiche il fuso dell'utente (impostabile dallo Sprint 70). Per utenti lontani dall'Europa i dati arrivano con ore di ritardo e i massimali si azzerano a un orario locale diverso dalla mezzanotte.
56. **Privacy.** Dallo Sprint 67 esistono consensi in registrazione, pagine legali, export e cancellazione dell'account (§4.1, §4.22, §6). Resta da decidere cosa fare delle **copie delle email di servizio** (indirizzo del destinatario e testo, mai dati del profilo) che rimangono nella posta inviata dell'account email mittente, anche dopo l'eliminazione dell'account: cancellarle periodicamente a mano oppure dichiararne la conservazione nell'informativa.
57. **Assenza di OCR.** Per i CV in formato immagine o scansione l'utente compila a mano. Resta da verificare quanto spesso succeda.
58. **Rigenerazione senza limite per job.** È limitata solo dal massimale giornaliero e dal credito.
59. **Credito solo manuale.** Senza credito caricato dall'amministratore i massimali sono rigidi e le chat degli editor sono inutilizzabili. I prezzi di default (1,50 / 1,00 / 0,50 / 0,20 €) sono configurati ma non sono mai stati validati come listino commerciale. I prezzi dei piani non sono definiti.

---

*Fine del documento.*
