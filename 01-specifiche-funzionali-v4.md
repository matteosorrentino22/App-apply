# Specifiche Funzionali — App di ricerca lavoro e generazione CV

> **Documento:** 01 — Specifiche funzionali
> **Versione:** 4 — integra le decisioni della chat di revisione criticità (luglio 2026)
> **Stato:** revisionato
> **Ambito:** definisce *cosa* deve fare l'applicazione (non *come* è costruita).
> Le scelte tecniche (integrazione LinkedIn, struttura template CV, prompt AI, infrastruttura) sono demandate al documento di specifiche tecniche (`02-specifiche-tecniche-v3.md`).
>
> **Nota di versione (v2).** Rispetto alla v1, quella revisione recepiva: due massimali separati (import e generazione manuale); generazione manuale come unico meccanismo di (ri)generazione, disponibile a tutti i piani; retry di una generazione automatica fallita = generazione manuale; barra di ricerca confinata alla sezione corrente; tie-break del cap per data più recente; regole di downgrade con >10 ricerche; credito caricato manualmente nell'MVP; uscita automatica dall'archivio; massimale manuale Pro = 10/giorno.
>
> **Nota di versione (v3).** Recepiva due decisioni emerse nella stesura delle tecniche: foto nel CV come opzione on/off dell'utente; credito extra come pool unico generico.
>
> **Nota di versione (v4).** Questa revisione recepisce le decisioni della chat di revisione criticità:
> 1. **Credito extra come saldo in denaro (€).** Il credito non è più un contatore di "unità" generiche ma un **saldo in euro** caricato sull'account. Ogni azione oltre i massimali del piano ha un **prezzo unitario** (es. indicativo: 0,50 € per una generazione manuale extra; valori **da definire**) che viene scalato dal saldo. Vale indifferentemente per Free e Pro. **Eccezione:** l'**import manuale resta riservato al piano Pro** — un utente Free non può importare nemmeno pagando a credito. *(Vedi §4.11.)*
> 2. **Formato Word eliminato dall'MVP.** Il CV generato si scarica **solo in PDF**. Il download Word è spostato tra le evoluzioni future. Decade la garanzia "1 pagina in Word" (punto §8.12 della v3, ora chiuso). *(Vedi §4.7, §5.)*
> 3. **Limite di raccolta per utente per notte.** La fonte restituisce al massimo **50 job/notte per utente Free** e **100 job/notte per utente Pro**, sommando tutte le ricerche attive. Su questi job avviene lo scoring; poi si applica il cap di intake dei 15. *(Vedi §4.4.)*
> 4. **Tie-break del cap con data mancante.** La data di pubblicazione può mancare: il job è comunque ammesso. In caso di pareggio di punteggio al taglio dei 15, si preferisce il job più recente; se la data manca o il pareggio persiste, la scelta è **casuale**. *(Vedi §4.4.)*
> 5. **Definizione di "nuovi job" per la notifica mattutina.** Sono "nuovi" i job raccolti **dopo l'ultima notifica mattutina inviata** a quell'utente. Copre correttamente anche i fusi orari a est dell'Europa ed evita doppi invii. *(Vedi §4.12.)*
> 6. **Generazione concorrente bloccata.** Mentre un CV è in generazione per un job, il comando "genera" su quello stesso job è disabilitato (indicatore di caricamento) e una seconda richiesta viene rifiutata. *(Vedi §4.7.)*
> 7. **Fallimento dello scoring notturno.** Un'offerta il cui scoring fallisce durante il ciclo notturno viene **scartata per quella notte** (non entra nel cap, non viene ritentata). *(Vedi §4.4.)*
> 8. **"Apertura lista immediata" = reattività.** Chiarito che il requisito di apertura immediata della lista (§6) indica semplice reattività dell'applicazione, **non** una cache offline dei dati sul dispositivo.
> 9. *(Recepimento tecnico, senza effetto funzionale visibile)* Il reset dei massimali giornalieri è allineato alla **mezzanotte Europe/Rome**, stesso riferimento del ciclo notturno. Per l'utente resta valida la descrizione del §4.11: i tetti si azzerano una volta al giorno.

---

## 1. Obiettivo del prodotto e problema che risolve

L'applicazione centralizza e automatizza il lavoro ripetitivo della ricerca di impiego. Oggi ogni candidato affronta manualmente lo stesso ciclo: cercare posizioni, capire quali sono davvero adatte al proprio profilo, e riscrivere il CV su misura per ognuna. Il prodotto elimina questo lavoro ripetitivo raccogliendo le offerte, valutandone l'affinità con il profilo dell'utente e generando automaticamente un CV personalizzato per le offerte più promettenti.

L'utente definisce una volta il proprio profilo e le proprie ricerche; da lì in poi l'app lavora in background e ogni mattina presenta una lista curata di opportunità, con i CV già pronti per le più affini. Il valore centrale è *"svegliarsi con il lavoro già fatto"*: non cercare, non filtrare, non riscrivere il CV ogni volta.

**Confine del problema risolto (MVP):** il prodotto arriva fino alla produzione del CV pronto e al link di candidatura. La candidatura vera e propria resta manuale (l'utente si candida sul portale di origine). L'app offre però un tracciamento minimo dello stato di ogni offerta, così l'utente ha un punto unico da cui vedere a che punto è ciascuna. L'automazione della fase di candidatura è un'evoluzione futura, esplicitamente fuori dall'MVP.

**Cadenza:** il ciclo è giornaliero. I nuovi job vengono raccolti durante la notte e sono già disponibili in app dal mattino; alle 10:00 (ora locale dell'utente) l'utente riceve una notifica che lo avvisa della presenza di nuove offerte da valutare.

---

## 2. Utenti target e bisogni principali

Il prodotto serve chi cerca lavoro — in modo attivo o passivo — e vuole massimizzare le candidature di qualità minimizzando il tempo manuale.

**Utente primario (MVP): la persona in transizione di carriera.** È l'utente su cui, in caso di conflitto tra esigenze, si decide a suo favore.

**Utenti supportati ma non prioritari:**
- il **professionista occupato / passivo**, che valuta il mercato pur avendo già un lavoro e vuole poche segnalazioni ma molto rilevanti;
- il **candidato ad alto volume**, che cerca attivamente e vuole molte offerte con CV pronti.

**Bisogno n.1 dell'utente primario:**
1. non dover mai riscrivere il CV a mano;
2. capire a colpo d'occhio, già nella lista, se un job può interessargli — senza dover leggere l'intera descrizione — grazie a titolo, azienda, località e soprattutto alla scomposizione di *cosa è affine* e *cosa manca* rispetto al proprio profilo. Da lì decide se approfondire il dettaglio o archiviare il job (con uno swipe).

**Nota sull'affinità e la persona in transizione.** Lo scoring misura l'affinità rispetto al **profilo master** (l'esperienza reale attuale dell'utente), non il *gradimento* né l'affinità rispetto a un obiettivo futuro. Poiché la persona in transizione cerca per definizione ruoli diversi dal proprio passato, questa scelta implica che il suo scoring sarà spesso strutturalmente basso proprio sui ruoli desiderati. L'app la asseconda **a valle**, tramite la **generazione manuale del CV** — disponibile anche in Free (1 al giorno, estendibile a credito) e utilizzabile su *qualsiasi* job, compresa la rigenerazione con arricchimento di un job già generato — e l'**arricchimento mirato del profilo** in fase di generazione (vedi §4.7 e §4.8), non modificando la definizione di scoring. *(Vedi anche §8.)*

---

## 3. User stories / casi d'uso principali

Formato: *come [utente], voglio [azione], per [beneficio]*.

### Setup e onboarding
- Come utente, voglio **registrarmi e dichiarare la mia situazione/obiettivo**, per impostare il mio punto di partenza. *(Nell'MVP è un dato salvato, senza effetti su raccolta o scoring — vedi §5.)*
- Come utente, voglio **costruire il mio profilo master in sezioni** (sommario professionale, risultati chiave, esperienze, istruzione, competenze e certificazioni, lingue), per avere un'unica fonte di verità per i miei CV.
- Come utente, voglio **pre-popolare il profilo caricando un CV esistente** e poi correggerlo, per non compilarlo da zero.
- Come utente, voglio **caricare una foto profilo**, per includerla nei CV generati.
- Come utente, voglio **scegliere se includere o meno la foto nel CV** (opzione on/off), per adattare il documento ai template e ai mercati che non gradiscono la foto.
- Come utente, voglio **scegliere il template del CV e la lingua di generazione** durante l'onboarding, per definire l'aspetto e la lingua dei documenti prodotti.

### Ricerche
- Come utente, voglio **creare una o più ricerche salvate con filtri di *keywords* e *location***, per raccogliere solo le offerte pertinenti.
- Come utente, voglio **attivare o disattivare una ricerca senza cancellarla**, per controllare quali ricerche girano ogni notte.
- Come utente Free, voglio **capire che attivando una nuova ricerca quella precedentemente attiva si disattiva** (posso tenerne attiva 1 sola), per non avere sorprese su cosa gira di notte.

### Ciclo quotidiano
- Come utente, voglio **ricevere una notifica al mattino (ore 10:00 locali)** quando ci sono nuovi job, per sapere che c'è materiale nuovo da valutare.
- Come utente, voglio **vedere la lista dei job di oggi ordinati per punteggio**, con titolo, azienda, località, punteggio e scomposizione affinità/lacune, per decidere rapidamente cosa approfondire.
- Come utente, voglio **filtrare la lista per periodo** (oggi, ultima settimana, ultimo mese, tutti), per rivedere anche i job dei giorni precedenti.
- Come utente, voglio **filtrare la lista per score e per stato del job**, per isolare rapidamente ciò che mi interessa.
- Come utente, voglio **cercare tra i miei job con una barra testuale** (per titolo, azienda, località), per ritrovare velocemente un'offerta.
- Come utente, voglio **aprire il dettaglio di un job** con la descrizione completa, per approfondire quando l'anteprima mi interessa.
- Come utente, voglio **archiviare un job con uno swipe**, per togliere dalla vista ciò che non mi interessa senza cancellarlo.
- Come utente, voglio **annullare uno swipe di archiviazione accidentale**, per non perdere un job archiviato per errore.
- Come utente, voglio **rimuovere un job dall'archivio con uno swipe** (azione disponibile solo dentro l'archivio), per riportarlo tra i job attivi.

### CV e candidatura
- Come utente, voglio **ricevere automaticamente un CV personalizzato per i job raccolti ad alta affinità (punteggio 4–5)**, per candidarmi senza riscrivere nulla.
- Come utente, voglio **generare manualmente un CV per un job** — sotto soglia (1–3), importato, oppure già dotato di CV automatico (4–5) — entro il massimale giornaliero del mio piano o, oltre, a credito, per candidarmi anche a offerte meno affini o per migliorare un CV già prodotto.
- Come utente, voglio **arricchire il profilo con un dettaglio di esperienza reale prima di generare (o rigenerare) il CV**, per colmare una lacuna evidenziata; e voglio poter scegliere se salvare quel dettaglio anche nel profilo master.
- Come utente, voglio **scaricare il CV generato in PDF**, per allegarlo dove serve.
- Come utente, voglio **aprire il link della candidatura originale e marcare il job come "candidatura fatta"** (possibile solo dopo aver generato un CV per quel job), per tenere traccia di dove mi sono candidato.

### Import manuale
- Come utente Pro, voglio **importare un job incollando il suo link LinkedIn**, per farlo valutare e trattare dall'app anche se non è stato raccolto automaticamente.

### Gestione account
- Come utente, voglio **modificare il profilo master in qualsiasi momento**, con effetto sulle generazioni future.
- Come utente, voglio **gestire il mio piano e caricare credito extra (saldo in €)**, per operare oltre i limiti del mio piano. *(Nell'MVP il checkout non è attivo: il credito viene caricato manualmente — vedi §4.11 e §5.)*

---

## 4. Funzionalità incluse nel perimetro (MVP)

### 4.1 Account e profilo
- Registrazione e onboarding. In onboarding l'utente: dichiara la propria situazione/obiettivo (dato salvato, inerte), sceglie il template CV, sceglie la lingua di generazione del CV, **sceglie se includere la foto profilo nel CV** (opzione on/off), imposta le prime ricerche.
- Profilo master strutturato in sezioni: sommario professionale, risultati chiave, esperienze lavorative, istruzione, competenze e certificazioni, lingue.
- Pre-popolamento del profilo tramite upload di un CV esistente (**PDF o Word**); caricamento di una foto profilo. Se il file caricato non è leggibile automaticamente (es. PDF scannerizzato/immagine, senza testo estraibile), l'app avvisa l'utente e lo invita a **compilare il profilo manualmente**, anziché produrre un profilo vuoto o incompleto. *(Nota: l'upload in Word riguarda solo la lettura del CV di partenza; il CV generato si scarica solo in PDF — §4.7.)*
- **Inclusione della foto nel CV:** scelta dall'utente in onboarding e modificabile in ogni momento. Se disattivata, i CV generati non riportano la foto anche se una foto profilo è stata caricata.
- Profilo modificabile in ogni momento, con effetto sulle generazioni future. **I CV già generati non vengono modificati** da una successiva modifica del profilo master.

### 4.2 Ricerche
- Una o più ricerche salvate, ognuna definita da due soli filtri: **keywords** e **location**.
  - Esempi: *keywords = "IT Project Manager", location = "Rome, Italy"* — oppure — *keywords = "Enel", location = "Milan, Italy"*.
- Ogni ricerca è attivabile/disattivabile senza essere cancellata. Solo le ricerche **attive** producono job nella raccolta notturna.
- **Limiti per piano:**
  - **Free:** fino a **10 ricerche salvate**, di cui **1 sola attiva** alla volta. Attivandone una nuova, l'app **disattiva automaticamente** quella precedentemente attiva e **avvisa l'utente** del cambio.
  - **Pro:** fino a **100 ricerche salvate**, di cui fino a **50 attive** contemporaneamente.
- **Downgrade Pro→Free:** al passaggio da Pro a Free **tutte le ricerche vengono disattivate**. Non c'è alcuna selezione automatica: l'utente dovrà rientrare nell'app e attivarne una (entro il limite Free di 1 attiva).
  - Le ricerche salvate **restano tutte**, anche se superano le 10. In questo stato di eccedenza l'utente **non può aggiungere nuove ricerche** finché non ne elimina abbastanza da **scendere sotto la soglia di 10**. Le ricerche esistenti restano comunque attivabili/disattivabili (entro il limite Free di 1 attiva). *(Vedi §8.)*

### 4.3 Fonte delle offerte
- Unica fonte nell'MVP: **LinkedIn**.
- La fonte è concepita come componente sostituibile, per aggiungerne altre in futuro senza riscrivere il resto (requisito da tradurre nell'architettura — vedi specifiche tecniche).
- **Campi obbligatori** per mostrare un'offerta: *job title, company, location, job description, link di candidatura*. Se manca anche uno solo, l'offerta non viene mostrata.
- La **data di pubblicazione non è un campo obbligatorio**: un'offerta priva di data viene comunque ammessa (con effetto solo sul tie-break del cap — §4.4).
- Campi opzionali (es. retribuzione): mostrati se presenti, ignorati se assenti.
- **Deduplica per ID job, per utente:** un job già mostrato in precedenza allo stesso utente non viene rimostrato nei giorni successivi. Se lo stesso job è restituito da più ricerche attive dello stesso utente, viene mostrato una sola volta. *(Attribuzione del job alla ricerca in caso di match multiplo: vedi §8.)*

### 4.4 Ciclo quotidiano
- Raccolta notturna dei job pubblicati nelle 24 ore precedenti, per le ricerche attive dell'utente. Il vincolo delle 24 ore è applicato **alla fonte** (filtro nella richiesta di raccolta — dettaglio nelle tecniche).
- **Limite di raccolta per piano:** la fonte restituisce al massimo **50 job/notte per l'utente Free** e **100 job/notte per l'utente Pro**, sommando tutte le ricerche attive. Questi limiti contengono i costi di valutazione a monte del cap di intake.
- **Scoring** di ogni offerta raccolta (entro il limite di cui sopra): punteggio di affinità da 1 a 5 rispetto al profilo master, con breve motivazione e scomposizione *match/gap* (cosa è affine, cosa manca). Lo scoring non inventa competenze non presenti. Se lo scoring di una singola offerta **fallisce** durante il ciclo notturno, l'offerta è **scartata per quella notte** (non entra nel cap, non viene ritentata); la diagnosi resta lato backend.
- **Cap giornaliero di intake:** dopo lo scoring, vengono acquisiti al massimo **15 job al giorno per utente**, scelti come i **15 a punteggio più alto** sommando tutte le ricerche attive. In caso di **pareggio di punteggio** al confine (es. più job con lo stesso score al 15°/16° posto), si tiene il job **pubblicato più di recente** secondo la data restituita da LinkedIn; se la data manca o il pareggio persiste, la scelta tra i job a pari merito è **casuale**. I job eccedenti vengono **scartati** per quel giorno e **non** riproposti nei giorni successivi.
- Notifica alle 10:00 (ora locale dell'utente) **solo se** ci sono nuovi job (definizione di "nuovi": §4.12). Nessun job nuovo → nessuna notifica.

### 4.5 Vista lista e navigazione

**Sezioni.** L'app organizza i job in **tre sezioni**:
- **Principale** — i job raccolti automaticamente, non archiviati.
- **Job importati** — i job importati manualmente via link (§4.9), non archiviati.
- **Archivio** — tutti i job archiviati, qualunque sia la loro origine.

La sezione in cui un job appare dipende dall'archiviazione e dall'origine, **non** dallo stato del job (vedi §4.6).

**Ordinamento.** In tutte le viste con filtro temporale, i job sono ordinati per **punteggio decrescente** (non cronologico).

**Filtri temporali.** Sotto la barra di ricerca, filtri preimpostati: **oggi (default)**, **ultima settimana**, **ultimo mese**, **tutti**.

**Filtri aggiuntivi** (raggiungibili da un pulsante "filtri" che apre il pannello completo, per non affollare la pagina):
- **Score** — multiselect sui valori **1–5**.
- **Stato** — multiselect sui tre stati stabili: **nuovo**, **CV generato**, **candidatura fatta** (il transitorio *CV in generazione* **non** è selezionabile).

**Ambito dei filtri.** Tutti i filtri sopra (temporale, score, stato) valgono in **tutte e tre le sezioni**.

**Barra di ricerca testuale.** Cerca per keyword tra *job title, company, location* (non nella descrizione), su tutto lo storico a database **della sezione corrente**. La ricerca **resta confinata alla sezione da cui è avviata** (es. cercando dalla Principale non compaiono job archiviati o importati). **Quando la barra di ricerca è attiva, tutti gli altri filtri (temporale, score, stato) vengono ignorati.**

**Riga di lista.** Ogni riga mostra: titolo, azienda, località, punteggio, scomposizione affinità/lacune.

**Dettaglio job.** Job description completa.

**Archiviazione e swipe:**
- Nelle sezioni Principale e Job importati, lo **swipe archivia** il job (lo sposta in Archivio).
- È previsto l'**undo** dello swipe di archiviazione accidentale.
- Nella sezione Archivio, lo **swipe "rimuovi da archivio"** riporta il job alla sua sezione d'origine (Principale o Job importati) con lo stato che aveva.
- **Uscita automatica dall'archivio.** Se l'utente **genera, rigenera o arricchisce** un CV per un job che si trova in Archivio, il job **esce automaticamente dall'archivio** e torna alla sua **sezione d'origine** (Principale se raccolto, Job importati se importato), mantenendo lo stato risultante dall'operazione. *(Vedi §4.7 e §8.)*

### 4.6 Stati e sezioni del job

Lo **stato** e la **sezione** sono due dimensioni indipendenti.

**Stati stabili (tre):**
- **nuovo** — stato iniziale delle offerte raccolte con punteggio 1–3, e di **tutti** i job importati manualmente (a prescindere dal punteggio); è inoltre lo stato in cui **torna** un job 4–5 la cui generazione automatica sia fallita (§4.7);
- **CV generato** — stato iniziale delle offerte raccolte con punteggio 4–5 (CV prodotto automaticamente), o stato di qualsiasi job dopo la generazione (manuale) del CV;
- **candidatura fatta** — assegnato manualmente dall'utente, **possibile solo dopo che è stato generato un CV** per quel job.

> **Nota.** Un job con punteggio 4–5 **nasce** in stato "CV generato", ma **può legittimamente stazionare in "nuovo"** se la sua generazione automatica è fallita (path di errore, §4.7). Non è un difetto.

**Stato transitorio:**
- **CV in generazione** — visibile mentre un CV viene prodotto (vedi §4.7 e §6): sul job compare un indicatore di caricamento al posto dello stato, finché il documento non è pronto. **Mentre questo stato è attivo, il comando "genera" su quello stesso job è disabilitato** e un'eventuale richiesta duplicata viene rifiutata (§4.7).

**Archiviazione (dimensione ortogonale allo stato).** "Archiviato" **non è uno stato**: è un attributo che determina solo la **sezione** in cui il job appare. Archiviare un job **non cambia il suo stato**. Rimuovendolo dall'archivio, il job torna alla sua sezione d'origine con lo **stato che non ha mai perso** (nuovo / CV generato / candidatura fatta).

### 4.7 Generazione del CV

**Generazione automatica.** Per i job **raccolti** con punteggio 4–5, il CV viene prodotto automaticamente durante il ciclo notturno, per **tutti i piani** (incluso Free). La generazione automatica **non ha un tetto giornaliero proprio** ed è di fatto limitata dal cap di intake di 15 job/giorno (§4.4). La generazione automatica attinge a un **budget separato** da quello della generazione manuale.

**Generazione manuale.** È l'**unico meccanismo di (ri)generazione** del CV su azione esplicita dell'utente ed è disponibile su **qualsiasi job**:
- un job raccolto **sotto soglia** (punteggio 1–3);
- un job **importato** manualmente (che non riceve mai il CV automatico — §4.9);
- un job raccolto **4–5** che **ha già** il CV automatico → in questo caso la generazione manuale funge da **rigenerazione** (tipicamente accompagnata da arricchimento — §4.8).

La generazione manuale è soggetta a un **massimale giornaliero** che dipende dal piano:
- **Free:** **1 generazione manuale al giorno**;
- **Pro:** **10 generazioni manuali al giorno**.

Ogni generazione manuale (inclusa la rigenerazione di un 4–5) **consuma un'unità** del massimale manuale del piano. **Esaurito il massimale**, l'utente può proseguire **a credito**: ogni generazione extra scala il proprio **prezzo unitario** dal saldo in € (§4.11); con saldo insufficiente, l'operazione è bloccata con un messaggio di limite raggiunto. Prima di ogni generazione manuale l'utente può **arricchire** il profilo (§4.8).

**Concorrenza.** Per un job il cui CV è **in generazione**, il comando "genera" è disabilitato nell'interfaccia (il pulsante mostra un indicatore di caricamento) e una seconda richiesta sullo stesso job viene comunque rifiutata dal sistema. Non è quindi possibile consumare due unità di massimale (o due addebiti a credito) per lo stesso job in lavorazione.

> **Nota (v2).** Non esiste un canale separato "rigenerazione Pro, una volta per job": la rigenerazione è semplicemente una generazione manuale su un job che ha già un CV, disponibile a **tutti i piani** entro il rispettivo tetto giornaliero (o oltre, a credito), senza limite di conteggio per singolo job.

**Contenuto del CV.** Il CV combina profilo master + descrizione della posizione: riformula le sezioni pertinenti per far emergere l'esperienza reale più rilevante, **mantiene invariata la sezione istruzione**, e **non aggiunge nulla che non sia nel profilo** (salvo i dettagli aggiunti dall'utente via arricchimento — §4.8).

**Template e lunghezza.** Il CV segue il template scelto dall'utente ed è di **1 pagina**.

**Foto.** La foto profilo compare nel CV **solo se** l'utente ha attivato l'opzione di inclusione (§4.1). Se l'opzione è disattivata, il CV non riporta la foto anche in presenza di una foto profilo caricata.

**Lingua del CV**, secondo la scelta dell'utente (impostata in onboarding, modificabile in ogni momento): *(1)* sempre in inglese, oppure *(2)* nella lingua della job description. Il CV può quindi uscire in una lingua diversa da quella del profilo, tramite traduzione automatica dei contenuti reali dell'utente (tradurre è permesso; aggiungere no).

**Formato di download: solo PDF.** Il download in **Word è escluso dall'MVP** (evoluzione futura — §5). Nessun editor in-app del CV generato.

**Fallimento della generazione.** La generazione **non dovrebbe** fallire: un fallimento è considerato un bug dell'app, non un flusso previsto. Se comunque il CV non viene prodotto:
- all'utente viene mostrato un messaggio del tipo *"impossibile creare CV per questo job"*;
- il job **torna allo stato "nuovo"** e l'indicatore *CV in generazione* scompare;
- compare l'azione **"riprova"**;
- il tentativo fallito **non consuma** il budget di generazione: l'unità di massimale (o l'importo scalato dal credito) viene **restituita**.
- **Retry di una generazione automatica fallita.** Quando la generazione **automatica** di un job 4–5 è fallita e il job è tornato a "nuovo", il **"riprova"** avviato dall'utente è a tutti gli effetti una **generazione manuale**: consuma il massimale manuale del piano (Free 1/g, Pro 10/g) o, esaurito quello, il credito. *(Vedi §8: possibile penalizzazione dell'utente Free per un bug, oggi mitigata dalla via d'uscita a credito.)*

### 4.8 Arricchimento mirato del profilo
- Prima di generare **o rigenerare** un CV, l'utente può aggiungere un dettaglio di **esperienza reale precedentemente omessa** dal profilo master, per colmare una lacuna evidenziata.
- Il testo mostrato inquadra l'aggiunta come esperienza reale omessa; la responsabilità di veridicità è dell'utente.
- Al momento dell'inserimento, l'app chiede se salvare il dettaglio **anche nel profilo master** (per i job futuri) o solo per quel CV.
- L'arricchimento tocca **solo il CV generato**: non ricalcola il punteggio e non sblocca la generazione automatica per job sotto soglia. Di conseguenza, un CV può contenere esperienza reale non (ancora) presente nel master.

### 4.9 Import manuale di job
- Sezione secondaria (**Job importati**) dove l'utente incolla un link job di LinkedIn per importarlo.
- Il job importato viene **scorato** come gli altri, ma **non riceve mai il CV automatico**; la generazione è sempre manuale.
- Una volta importato, si comporta come un job normale (stati, archiviazione, arricchimento, download).
- Se il link non è valido → warning: *"impossibile importare quel job"*.
- Se l'utente importa un job **già presente** nella sua lista → nessun duplicato; l'app segnala *"questo job è già nella tua lista"*.
- **Limiti:** riservato al piano **Pro**, massimo **3 import al giorno**; oltre, ogni import scala il proprio prezzo unitario dal **credito** (§4.11). L'**import resta esclusivamente Pro**: un utente Free non può importare nemmeno disponendo di credito. Questo massimale è **indipendente** da quello della generazione manuale di CV (§4.7, §4.11): importare un job consuma un'unità del tetto **import**; generarne poi il CV consumerà, separatamente, un'unità del tetto **generazione manuale**.

### 4.10 Candidatura
- La marcatura **"candidatura fatta"** è possibile **solo dopo** che è stato generato un CV per quel job (automatico o manuale).
- Per un job con CV generato, l'utente apre il link della candidatura originale e procede manualmente sul portale di origine.
- L'utente marca manualmente il job come "candidatura fatta".

### 4.11 Monetizzazione

**Livelli.**
- **Free:** CV automatico sui job raccolti 4–5 (senza tetto proprio, limitato di fatto dai 15 job/giorno di intake); **1 generazione manuale di CV al giorno**, oltre la quale può proseguire **a credito**; **10 ricerche salvate, 1 attiva**; limite di raccolta **50 job/notte**. Attivabile anche via codice sconto. **Nessun import manuale** (nemmeno a credito).
- **Pro:** tutte le funzionalità; **10 generazioni manuali di CV al giorno** (oltre, a credito); **import manuale 3/giorno** (oltre, a credito); **100 ricerche salvate, 50 attive**; limite di raccolta **100 job/notte**.
- **Credito extra:** un **saldo in denaro (€)** caricato sull'account, spendibile per operazioni oltre i massimali del piano.

**Come funziona il credito.**
- Il credito è un **saldo unico in euro** (es. l'utente carica 10 €).
- Ogni tipo di azione oltre massimale ha un **prezzo unitario** (es. indicativo: 0,50 € per una generazione manuale extra; i valori effettivi sono **da definire** — §8). L'azione oltre soglia scala dal saldo il prezzo corrispondente.
- Lo stesso saldo copre indifferentemente generazioni manuali extra (Free e Pro) e import extra (solo Pro — l'import resta precluso al Free a prescindere dal credito).
- Con **saldo insufficiente** per il prezzo dell'azione, l'operazione è bloccata con un messaggio di limite raggiunto.
- Un'azione **fallita** non consuma credito: l'importo scalato viene restituito (§4.7).

**Massimali giornalieri (due pool separati e indipendenti).**
- **Generazione CV.** Automatica e manuale attingono a **budget separati**. Il massimale **manuale** è Free 1/giorno, Pro 10/giorno; ogni generazione manuale — compresa la **rigenerazione con arricchimento** di un job 4–5 — consuma il massimale manuale (o, oltre, il credito).
- **Import job.** Massimale **a sé stante**: Pro 3/giorno (il Free non importa). Non condivide il tetto con la generazione manuale di CV. Un job importato per cui si genera poi il CV consuma **un'unità di ciascuno** dei due massimali (uno di import + uno di generazione manuale).
- I massimali si **azzerano una volta al giorno** (riferimento orario unico, allineato al ciclo notturno — dettaglio nelle tecniche).

**Vincoli operativi.** I limiti dei piani sono **operativi** nell'MVP.

**Credito e checkout nell'MVP.** Il **checkout non è attivo**: il cambio piano avviene tramite codice voucher o intervento amministrativo, e il **credito viene caricato manualmente** (via pannello amministrativo). Il checkout self-service — anche per la ricarica del credito — è previsto come evoluzione futura. Il **downgrade Pro→Free** disattiva tutte le ricerche (§4.2).

> **Conseguenza operativa (MVP).** Poiché nell'MVP il credito è caricabile solo manualmente, l'uso oltre i massimali è di fatto **raggiungibile solo se un amministratore ha pre-caricato credito**. In assenza di credito, i massimali giornalieri si comportano come **tetti rigidi**. *(Vedi §8.)*

I **prezzi** dei piani e i **prezzi unitari** delle azioni a credito restano **da definire** (vedi §8).

### 4.12 Notifiche
- **Notifica mattutina (10:00 locali):** inviata **solo se** per l'utente esistono **nuovi job**, definiti come i job **raccolti dopo l'ultima notifica mattutina inviata** a quell'utente (o dopo la registrazione, se nessuna notifica è mai stata inviata). Questa definizione garantisce che ogni batch di raccolta venga annunciato **una sola volta** e copre correttamente anche gli utenti in fusi orari per cui le 10:00 locali cadono prima o durante il ciclo notturno: la notifica riguarda i job del ciclo più recente disponibile, senza doppi invii.
- **Notifica di inattività:** il timer parte alla **registrazione** dell'utente e si azzera ogni volta che l'utente marca una candidatura come "fatta". Se **non** viene marcata alcuna candidatura come "fatta" **per 7 giorni**, l'utente riceve un promemoria del tipo *"non ti candidi da un po', entra nell'app e procedi…"*. La notifica scatta **anche** per chi non ha mai avuto un CV pronto, e **anche** per chi è attivo nell'app ma non marca mai "candidatura fatta". *(Effetto collaterale voluto, vedi §8.)*

---

## 5. Funzionalità esplicitamente escluse (fuori scope per l'MVP)

1. **Candidatura automatica** (invio diretto senza uscire dall'app). Prevista come evoluzione futura.
2. **Hub completo per candidature esterne.** L'MVP consente solo l'import manuale puntuale di singoli job LinkedIn via link (§4.9); non un tracciamento generalizzato di candidature trovate altrove.
3. **Stati post-candidatura** (in colloquio, rifiutato, offerta ricevuta, ecc.). La macchina a stati si ferma a "candidatura fatta".
4. **Checkout / pagamento reale**, incluso l'acquisto self-service di credito. I piani esistono e limitano, ma non si paga dall'app; piano e credito si gestiscono via voucher o intervento amministrativo.
5. **Fonti diverse da LinkedIn.**
6. **Effetto della dichiarazione di obiettivo/situazione (onboarding) su raccolta o scoring.** Nell'MVP è un dato salvato e inerte.
7. **Scelta della lunghezza del CV da parte dell'utente.** Nell'MVP il CV è sempre di 1 pagina, non configurabile.
8. **Ricalcolo dello score dopo l'arricchimento del profilo.**
9. **Generazione automatica del CV per i job importati manualmente** (sempre manuale, anche con punteggio ≥ 4).
10. **Filtri di ricerca oltre keywords e location.** Nell'MVP la ricerca salvata è definita solo da *keywords + location*: **tipo di contratto** e **modalità di lavoro** (e altri criteri) **non** sono filtri disponibili.
11. **Notifiche diverse** da quella mattutina e da quella di inattività (es. avvisi al cambio stato, riepiloghi settimanali via email).
12. **Editor in-app del CV generato.** Il CV si scarica com'è.
13. **Più profili master per utente.** Un solo profilo master, anche per l'utente in transizione. *(Vedi §8: tensione con l'utente primario.)*
14. **Aggiornamento automatico dei CV già prodotti.** Una modifica del profilo master **non** ritocca i CV già generati; non esiste un'azione "aggiorna tutti i CV". L'utente può però **rigenerare** manualmente il CV di un job (spendendo una generazione manuale — §4.7), che è l'unico modo per rifletterci un profilo aggiornato o un arricchimento.
15. **Feedback dell'utente sullo scoring** e qualsiasi meccanismo di apprendimento dai feedback.
16. **Gestione privacy dei dati personali** (conservazione, cancellazione account e dati). Non trattata nell'MVP. *(Vedi §8: debito da saldare prima di un pubblico reale.)*
17. **Vincoli di scala dichiarati.** L'MVP è pensato per pochi utenti (cerchia ristretta di test); nessun target di utenti concorrenti da rispettare.
18. **OCR sui CV caricati.** L'upload del CV di partenza (§4.1) si basa sull'estrazione del testo; i CV forniti come immagine/scansione senza testo estraibile non vengono letti automaticamente (l'utente compila manualmente). L'OCR è fuori dall'MVP.
19. **Download del CV in formato Word** *(nuovo, v4)*. Il CV generato si scarica **solo in PDF**; il Word è previsto come evoluzione futura. *(L'upload in Word del CV di partenza resta invece supportato — §4.1.)*
20. **Cache offline dei dati nella app** *(nuovo, v4)*. La lista si apre "senza attesa percepibile" nel senso della **reattività** dell'applicazione; non è prevista una sincronizzazione/cache dei dati sul dispositivo per l'uso offline.

---

## 6. Requisiti non funzionali rilevanti a livello utente

### Vincoli confermati
- **Multi-utenza con isolamento dei dati.** Ogni utente ha profilo, ricerche, offerte e CV isolati e privati; nessun utente vede i dati di un altro.
- **Localizzazione oraria per utente.** Le notifiche e il concetto di "oggi" nella lista seguono il fuso locale di ciascun utente (le "10:00" sono le sue 10:00). *(Il ripristino dei massimali giornalieri segue invece un riferimento orario unico — §4.11.)*
- **Freschezza dei dati.** I job mostrati al mattino sono quelli pubblicati nelle 24 ore precedenti, aggiornati durante la notte.
- **Reattività — apertura lista:** immediata, senza attesa percepibile. Il requisito indica **reattività dell'applicazione** (risposte rapide del server), **non** una cache offline dei dati sul dispositivo (§5.20).
- **Reattività — generazione CV:** attesa di circa **10–15 secondi**, durante i quali l'utente può continuare a usare l'app; sul job in lavorazione compare un indicatore di caricamento (*CV in generazione*) finché il CV non è pronto; il comando "genera" su quel job è nel frattempo disabilitato (§4.7).
- **Gestione del fallimento di generazione CV.** In caso di mancata generazione (bug), l'utente vede *"impossibile creare CV per questo job"*, il job torna a "nuovo", è disponibile "riprova" e il budget (massimale o credito) non viene consumato; il retry di una generazione automatica fallita è però una generazione manuale (§4.7).
- **Comportamento in caso di fonte non disponibile.** Se la raccolta notturna fallisce, all'utente si comunica semplicemente che oggi non sono stati trovati nuovi job; nessun messaggio d'errore tecnico. La diagnosi resta lato backend. Lo stesso principio vale per il fallimento dello scoring di singole offerte (§4.4): nessun errore mostrato, offerta scartata per quella notte.
- **Lingua dell'interfaccia.** Default = lingua del dispositivo: **italiano** se il dispositivo è in italiano, **inglese** in ogni altro caso (e inglese come fallback se la lingua non è rilevabile). Modificabile nelle impostazioni. Di fatto, interfaccia bilingue IT/EN nell'MVP.
- **Lingua del CV.** Vedi §4.7.

### Da definire (segnalati, non ipotizzati)
- **Prezzi** dei piani e **prezzi unitari** delle azioni a credito (generazione manuale extra, import extra).
- **Soglia di scala** oltre l'MVP: non dichiarata, da riprendere quando il prodotto esce dalla cerchia di test.

---

## 7. Criteri di accettazione (per funzione principale)

Formato: checklist di condizioni verificabili.

### Profilo e onboarding
- ☐ In onboarding l'utente può dichiarare situazione/obiettivo, scegliere template CV, scegliere lingua CV e creare almeno una ricerca.
- ☐ Il profilo master presenta tutte le sezioni previste (sommario, risultati chiave, esperienze, istruzione, competenze/certificazioni, lingue).
- ☐ Caricando un CV esistente (PDF o Word), le sezioni del profilo risultano pre-popolate e modificabili.
- ☐ Se il CV caricato non è leggibile automaticamente (nessun testo estraibile), l'utente riceve un avviso ed è invitato a compilare manualmente, senza che venga creato un profilo vuoto.
- ☐ È possibile caricare una foto profilo.
- ☐ In onboarding l'utente può scegliere se includere la foto nel CV, e la scelta è modificabile in seguito.
- ☐ Una modifica al profilo master si riflette sui CV generati successivamente, non su quelli già prodotti.

### Ricerche
- ☐ Una ricerca è definita solo da keywords e location.
- ☐ Free: si possono salvare fino a 10 ricerche e tenerne attiva 1 sola; attivandone una nuova, la precedente attiva si disattiva e l'utente viene avvisato.
- ☐ Pro: si possono salvare fino a 100 ricerche e tenerne attive fino a 50.
- ☐ Una ricerca può essere disattivata e riattivata senza perdere i suoi filtri.
- ☐ Solo le ricerche attive producono job nella raccolta notturna.
- ☐ Al downgrade Pro→Free tutte le ricerche risultano disattivate e nessuna viene riattivata automaticamente.
- ☐ Al downgrade Pro→Free con più di 10 ricerche salvate, tutte restano ma non se ne possono aggiungere di nuove finché non si scende sotto 10 eliminandone.

### Raccolta e fonte
- ☐ I job raccolti provengono da LinkedIn e sono pubblicati nelle 24h precedenti (vincolo applicato alla fonte in fase di raccolta).
- ☐ In una notte, la fonte restituisce al massimo 50 job per un utente Free e 100 per un utente Pro, sommando tutte le ricerche attive.
- ☐ Un'offerta priva anche di uno solo tra job title, company, location, job description, link non viene mostrata.
- ☐ Un'offerta priva della data di pubblicazione viene comunque ammessa.
- ☐ Uno stesso job (stesso ID) già mostrato a un utente non ricompare a quell'utente nei giorni successivi.
- ☐ In un giorno vengono acquisiti al massimo 15 job per utente, i 15 a punteggio più alto; gli eccedenti sono scartati e non riproposti.
- ☐ In caso di pareggio di punteggio al confine dei 15, viene preferito il job pubblicato più di recente; se la data manca o il pareggio persiste, la scelta è casuale.
- ☐ Un'offerta il cui scoring notturno fallisce viene scartata per quella notte, senza messaggi d'errore all'utente.

### Notifiche
- ☐ Se esistono job raccolti dopo l'ultima notifica mattutina inviata, l'utente riceve la notifica alle 10:00 nel proprio fuso orario.
- ☐ Se non esistono job nuovi (secondo la definizione sopra), nessuna notifica mattutina viene inviata.
- ☐ Uno stesso batch di raccolta non viene mai annunciato due volte allo stesso utente.
- ☐ Il timer di inattività parte alla registrazione e si azzera a ogni "candidatura fatta".
- ☐ Se l'utente non marca alcuna candidatura come "fatta" per 7 giorni, riceve la notifica di inattività, anche se non ha mai avuto un CV pronto e anche se è per altri versi attivo nell'app.

### Scoring
- ☐ Ogni offerta mostra un punteggio da 1 a 5.
- ☐ Ogni offerta mostra una breve motivazione e la scomposizione match/gap.
- ☐ Il punteggio non fa riferimento a competenze non presenti nel profilo master.

### Vista lista, sezioni e ricerca
- ☐ Esistono tre sezioni: Principale, Job importati, Archivio.
- ☐ All'apertura, la lista mostra i job di oggi ordinati per punteggio decrescente.
- ☐ Ogni riga mostra titolo, azienda, località, punteggio e match/gap.
- ☐ È possibile filtrare per periodo (oggi/ultima settimana/ultimo mese/tutti) e vedere job passati.
- ☐ È possibile filtrare per score (multiselect 1–5) e per stato (multiselect: nuovo, CV generato, candidatura fatta).
- ☐ I filtri temporale, score e stato valgono in tutte e tre le sezioni.
- ☐ La barra di ricerca trova job per titolo, azienda o località su tutto lo storico a database della sezione corrente, e non attraversa le altre sezioni.
- ☐ Quando la barra di ricerca è attiva, gli altri filtri (temporale, score, stato) vengono ignorati.
- ☐ L'ordinamento è per punteggio decrescente anche con i filtri temporali applicati.
- ☐ La lista si apre senza attesa percepibile.
- ☐ Uno swipe archivia il job (in Principale e Job importati); è possibile annullare uno swipe accidentale.
- ☐ Nell'archivio, uno swipe "rimuovi da archivio" riporta il job alla sua sezione d'origine con lo stato che aveva.
- ☐ Generando, rigenerando o arricchendo un CV su un job archiviato, il job esce automaticamente dall'archivio e torna alla sua sezione d'origine.

### Stati del job
- ☐ Gli stati stabili sono tre: nuovo, CV generato, candidatura fatta; "archiviato" non è uno stato.
- ☐ Un job raccolto con punteggio 4–5 nasce in stato "CV generato".
- ☐ Un job raccolto con punteggio 1–3 nasce in stato "nuovo".
- ☐ Un job importato manualmente nasce sempre in stato "nuovo", anche con punteggio ≥ 4.
- ☐ Un job 4–5 la cui generazione automatica è fallita può stazionare legittimamente in stato "nuovo".
- ☐ Archiviare un job non ne cambia lo stato; rimuoverlo dall'archivio lo riporta allo stato precedente.
- ☐ Durante la generazione (manuale o automatica), il job mostra l'indicatore transitorio "CV in generazione".

### Generazione CV
- ☐ Per un job 4–5 raccolto, il CV è prodotto automaticamente, per tutti i piani (incluso Free).
- ☐ La generazione manuale è disponibile su azione dell'utente per qualsiasi job (1–3, importato, o 4–5 già generato), entro il massimale giornaliero del piano (Free 1/g, Pro 10/g) o, oltre, a credito.
- ☐ Generazione automatica e manuale attingono a budget separati.
- ☐ Per un job importato, la generazione è sempre e solo manuale.
- ☐ Un utente (Free o Pro) può rigenerare con arricchimento il CV di un job che ha già un CV, spendendo una generazione manuale (o credito).
- ☐ Il retry di una generazione automatica fallita conta come generazione manuale e consuma il massimale manuale (o credito).
- ☐ Mentre un CV è in generazione per un job, il comando "genera" su quello stesso job è disabilitato e una richiesta duplicata viene rifiutata, senza doppio consumo di massimale o credito.
- ☐ Se la generazione fallisce, l'utente vede "impossibile creare CV per questo job", il job torna a "nuovo", è disponibile "riprova" e il tentativo fallito non consuma massimale né credito (l'eventuale importo scalato viene restituito).
- ☐ Il CV scaricato è di 1 pagina.
- ☐ Il CV rispetta il template scelto dall'utente.
- ☐ La sezione istruzione del CV coincide con quella del profilo master (invariata).
- ☐ La foto compare nel CV solo se l'utente ha attivato l'opzione di inclusione; se disattivata, il CV non riporta la foto anche con foto profilo caricata.
- ☐ Il CV non contiene voci assenti dal profilo (salvo dettagli aggiunti dall'utente via arricchimento).
- ☐ Il CV è scaricabile in PDF; non è previsto il download in Word.
- ☐ Con opzione lingua = "inglese", il CV è in inglese qualunque sia la lingua dell'annuncio.
- ☐ Con opzione lingua = "lingua della job description", il CV segue la lingua dell'annuncio, traducendo i contenuti reali dell'utente se necessario.

### Arricchimento del profilo
- ☐ Prima di generare o rigenerare un CV, l'utente può aggiungere un dettaglio di esperienza.
- ☐ Al momento dell'aggiunta, l'app chiede se salvarlo anche nel profilo master.
- ☐ Se salvato solo per il CV, il dettaglio non compare nel profilo master.
- ☐ L'aggiunta non modifica il punteggio del job.

### Import manuale
- ☐ Un utente Pro può importare un job incollando un link LinkedIn.
- ☐ Un utente non-Pro non ha accesso all'import manuale, nemmeno con credito disponibile.
- ☐ Oltre 3 import in un giorno, l'operazione scala il prezzo unitario dal credito (se il saldo è sufficiente); con saldo insufficiente è bloccata con un messaggio.
- ☐ Un link non valido produce il warning "impossibile importare quel job".
- ☐ L'import di un job già in lista non crea duplicati e segnala "questo job è già nella tua lista".
- ☐ Un job importato viene scorato ma non riceve CV automatico.

### Piani, massimali e credito
- ☐ Free, Pro e credito applicano i rispettivi limiti operativi (ricerche, CV, import, limite di raccolta 50/100).
- ☐ Il cambio piano è possibile via voucher o intervento amministrativo (nessun checkout).
- ☐ Il credito è un saldo in euro, caricabile solo manualmente (pannello amministrativo) nell'MVP.
- ☐ Ogni azione oltre massimale scala dal saldo il prezzo unitario configurato per quel tipo di azione.
- ☐ Con saldo insufficiente, l'azione oltre massimale è bloccata con un messaggio di limite raggiunto.
- ☐ Import manuale e generazione manuale del CV hanno due massimali separati e indipendenti (import: Pro 3/g; generazione manuale: Free 1/g, Pro 10/g).
- ☐ Generare un CV su un job importato consuma un'unità del massimale import (all'atto dell'import) e un'unità del massimale di generazione manuale (all'atto della generazione).
- ☐ I massimali giornalieri si azzerano una volta al giorno.

### Requisiti trasversali
- ☐ Un utente non può in alcun modo vedere dati (profilo, ricerche, job, CV) di un altro utente.
- ☐ Le notifiche rispettano il fuso orario locale dell'utente.
- ☐ In caso di raccolta fallita, l'utente vede "nessun nuovo job oggi" e non un errore tecnico.
- ☐ L'interfaccia è in italiano se il dispositivo è in italiano, altrimenti in inglese, ed è modificabile nelle impostazioni.

---

## 8. Punti da verificare in revisione

Dubbi residui e decisioni consapevoli da riesaminare nelle fasi successive. Rispetto alla v3 sono stati **chiusi**: il punto sul Word "1 pagina" (Word eliminato dall'MVP), il punto sul pool unico di credito (superato dal saldo in €), il comportamento a tetto esaurito (ora definito: prosecuzione a credito o blocco con messaggio), la definizione di "nuovi job" per la notifica, il tie-break con data mancante, la concorrenza sulla generazione e il fallimento dello scoring notturno. La numerazione è stata rifatta.

1. **Scoring vs. utente primario.** Lo scoring misura l'affinità col profilo master, ma l'utente primario (persona in transizione) cerca ruoli diversi dal proprio passato. L'MVP la serve solo *a valle* (generazione manuale — anche a credito — + arricchimento). Verificare se questo basta o se serve un secondo segnale (desiderabilità vs. gap) — attualmente escluso.

2. **Valore centrale vs. utente primario.** La promessa *"svegliarsi con il lavoro già fatto"* (§1) regge pienamente solo per chi ottiene CV automatici (job 4–5). Per la persona in transizione, spesso a basso punteggio sui ruoli desiderati, il CV richiede l'azione manuale. Decisione accettata per l'MVP; da rivalutare.

3. **Un solo profilo master.** In tensione diretta con l'utente primario, che potrebbe voler puntare a due direzioni di carriera con profili distinti. Confermato "uno solo" per l'MVP: da rivalutare presto.

4. **Dichiarazione di obiettivo inerte.** Il dato raccolto in onboarding non fa nulla nell'MVP. Verificare che questa inerzia sia accettabile e che l'onboarding non generi aspettative di un comportamento che non c'è.

5. **CV con voci non presenti nel master.** L'arricchimento "solo per questo CV" produce CV con righe assenti dal profilo. Voluto, ma segnalato perché una revisione potrebbe leggerlo come incoerenza.

6. **Scarto di offerte per campi mancanti.** Richiedere descrizione *e* link potrebbe eliminare una fetta di annunci LinkedIn reali (apply gestiti diversamente, description parziali). Scelta qualità-sopra-quantità; valutare se ammorbidire in fase di test. *(La data di pubblicazione è ora esplicitamente tollerata come assente.)*

7. **Cap di intake a 15 job/giorno.** Il tetto di 15 può scartare offerte potenzialmente rilevanti, definitivamente (non riproposte). A monte agiscono ora i limiti di raccolta 50/100 (§4.4). Resta da verificare se 15 è adeguato o va parametrizzato per piano.

8. **Limiti di raccolta 50/100 e qualità della selezione** *(nuovo, v4)*. Con Pro fino a 50 ricerche attive e un tetto complessivo di 100 job/notte, la distribuzione dei risultati tra le ricerche dipende dalla fonte: alcune ricerche potrebbero risultare "affamate" da altre più prolifiche. Da osservare in test se il tetto complessivo penalizza sistematicamente certe ricerche.

9. **Timer di inattività ancorato alla registrazione e alla sola "candidatura fatta".** Effetto voluto ("scatta comunque"), con i due casi ruvidi già confermati: (a) utente appena registrato che riceve il promemoria prima di aver mai avuto job; (b) utente attivo che non marca mai "candidatura fatta". A verbale come effetti voluti, da rivedere.

10. **"LinkedIn giù" indistinguibile da "nessun job".** Dal lato utente i due casi appaiono identici ("nessun nuovo job oggi"). Lo stesso vale per un'offerta scartata per fallimento di scoring. Voluto; verificare se in futuro serve distinguerli.

11. **Attribuzione di un job dedup-licato tra più ricerche.** Lo stesso job può risultare da più ricerche: la dedup lo mostra una volta, ma non è definito a quale ricerca sia attribuito. Rileva se in futuro si vorrà spiegare "perché ho ricevuto questo job".

12. **Ora locale + multi-utenza.** Raccolta notturna, reset dei massimali e notifiche seguono riferimenti temporali diversi (unico per raccolta e massimali, locale per notifiche e "oggi"). Registrato come requisito funzionale; dettagli nelle tecniche.

13. **Privacy / cancellazione dati (esclusione §5.16).** Accettabile per un test tra conoscenti, ma diventa quasi obbligatoria (GDPR) prima di un pubblico reale. Debito esplicito da saldare.

14. **Riduzione dei filtri di ricerca a keywords + location.** Scelta accettata per l'MVP, da verificare se sufficiente per la qualità della raccolta.

15. **Penalizzazione dell'utente Free per un bug di generazione automatica.** Il retry di un CV automatico fallito è una generazione manuale (§4.7): un utente Free il cui unico CV 4–5 della giornata è fallito deve spendere la sua sola generazione manuale/giorno (o credito) per riprovare. Coerente col modello, ma penalizza l'utente per un difetto dell'app; il credito offre ora una via d'uscita, che però nell'MVP dipende da un caricamento amministrativo. Da valutare (es. retry gratuito per fallimenti automatici).

16. **Rigenerazione senza limite per-job.** Un utente può rigenerare ripetutamente lo stesso job, limitato solo dal tetto giornaliero e dal credito (che di fatto estende il tetto per chi ne dispone). Verificare che non sia un uso indesiderato.

17. **Credito solo manuale nell'MVP.** L'uso oltre i massimali è raggiungibile solo con credito pre-caricato da un amministratore; senza, i tetti sono rigidi. Comportamento ora definito (blocco con messaggio); resta da definire il testo esatto dei messaggi.

18. **Prezzi da definire.** Prezzi dei piani e **prezzi unitari** delle azioni a credito (generazione manuale extra, import extra; il valore 0,50 € citato è solo un esempio).

19. **Freschezza dei dati per utenti fuori dall'Europa.** La raccolta è un batch unico ancorato al fuso europeo (dettaglio nelle tecniche): per un utente in un fuso lontano i job presentati al mattino possono avere ore di ritardo. Accettato per l'MVP (cerchia di test perlopiù europea); da rivalutare per utenti globali. La definizione di "nuovi job" della notifica (§4.12) garantisce comunque che ogni batch sia annunciato una sola volta, anche nei fusi a est.

20. **Giorno-quota vs giorno-visualizzazione.** Il "giorno" della lista è locale; il ripristino dei massimali segue un riferimento unico allineato al ciclo notturno (dettaglio nelle tecniche). Per un utente in un fuso lontano i tetti si azzerano a un orario locale diverso dalla mezzanotte. Scarto accettato per l'MVP.

21. **CV caricato non leggibile / assenza di OCR.** L'upload del CV di partenza si basa sull'estrazione del testo: i CV immagine/scansione non vengono letti e l'utente compila manualmente. Accettato per l'MVP; verificare in test la frequenza del caso.

22. **Scelta casuale nel tie-break** *(nuovo, v4)*. Con data mancante o pareggio persistente al taglio dei 15, la scelta è casuale: due esecuzioni sugli stessi dati possono selezionare job diversi. Accettato (il caso è marginale); segnalato perché rende il taglio non perfettamente riproducibile.

---

*Fine del documento. Prossima fase prevista: revisione di semplicità/manutenibilità.*
