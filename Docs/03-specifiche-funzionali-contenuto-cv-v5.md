# Contenuto del CV generato: selezione, quantità, impaginazione, rifinitura

> **Documento:** 03
> **Tipo:** documento di dettaglio sul contenuto e sull'impaginazione del CV generato
> **Versione:** 5. Descrive l'**as-is al 2026-11-14** (HEAD `a181e90`, Sprint 64), verificato sul codice.
> **Stato:** attivo
> **Documenti di riferimento:** `Docs/01-specifiche-funzionali-v6.md`, `Docs/02-specifiche-tecniche-v5.md`
> **Precedenza:** su contenuto, quantità, selezione, impaginazione e rifinitura manuale (editor/chat) del CV prevale questo documento. Su ogni altro tema prevalgono 01 e 02.
> **Ambito:** *cosa* compare nel CV generato per un job, *con quali regole* si decidono quantità e selezione, *come* la pipeline lo realizza, *che aspetto* ha il template unico e *cosa* l'utente può cambiare dopo, con l'editor e con la chat AI.
>
> **Struttura:** **Parte I**: specifiche funzionali (cosa fa). **Parte II**: specifiche tecniche (come è realizzato). In fondo, **§14**: punti aperti e limiti noti.
>
> **Numerazione.** I paragrafi §1–§14 tengono la numerazione della v4, perché i commenti nel codice (`selection.py`, `generation.py`, `cv_parameters.py`, `profiles/models.py`…) citano ancora quei `§`. Le sezioni nuove partono da §15: §15 (editor e chat, funzionale) sta nella Parte I, §16 (template e stile) e §17 (bozza e `content_json`) nella Parte II. §14 è l'ultima sezione del documento.

### Nota di versione (v5)

La v5 riscrive il documento come **descrizione dell'as-is**, non come progetto. Cambia rispetto alla v4:

1. **Istruzione mostrata per intero** (Sprint 38). Nessun limite di voci. `EDU_MAX_SHOWN = 3` serve solo come soglia per il budget bullet (§3.2, §12).
2. **Budget bullet 18/16/14** al posto di 12/10/9. Il commento nel codice dice "Sprint 43", ma la modifica è entrata nel commit dello Sprint 45 (vedi `sprints/sprint-45.md`). Il minimo garantito è fisso a **2** (§5.4).
3. **Arricchimento rimosso, sostituito da "colma i gap"** (Sprint 44). Niente salvataggio sul profilo e niente priorità protetta dal taglio (§5.6).
4. **Nessuna generazione automatica** (rimossa nel commit dello Sprint 45). Il CV si genera **sempre su richiesta** dell'utente (§1).
5. **Lingua di output** (Sprint 41). Le etichette fisse seguono la lingua reale del contenuto, in 5 lingue (it/en/fr/de/es) con fallback `en`. Lingue e livelli del profilo diventano codici tradotti. L'email nei contatti è quella del profilo, non quella di login (§5.7, §5.10).
6. **Un solo livello di rendering a dimensione fissa** (Sprint 52). Il font non si riduce mai. Se il loop di ripiego non basta, il CV può uscire su più pagine (§6).
7. **Ordine delle sezioni reale**: "Certified in / Skilled in" sta **prima** delle esperienze; il sommario non ha titolo (§4).
8. **Template e stile** (Sprint 52–57): Cambria/Caladea, nero con un solo colore d'accento, testo giustificato, azienda stampata una volta sola per ruoli consecutivi (§7, §16).
9. **Grassetto automatico sulle keyword** dei bullet (Sprint 58) (§5.11).
10. **Editor in-app e chat AI** (Sprint 51, 59–62): la rifinitura manuale prima esclusa ora esiste (§15, §17).
11. **Vincoli di input al profilo**: i limiti "8 bullet per esperienza / 200 caratteri" della v4 **non sono implementati**. La data di fine dell'istruzione **non è obbligatoria**: vuota significa "in corso" (Sprint 34) (§3).

### Storico condensato

- **v1–v2**: prima formulazione. Cap di 5 esperienze, budget bullet calcolato dall'istruzione, qualifica professionale sotto il nome, Areas of Expertise al posto dei "risultati chiave", istruzione non riformulata.
- **v3**: formula di peso "recenza + durata" per ripartire i bullet, swap multipli, 3 livelli di compattamento.
- **v4**: una sola chiamata AI su tutte le esperienze. Swap singolo e taglio dopo la risposta, con un unico criterio di rilevanza. Loop di ripiego con tetto di 4 iterazioni. Eliminata la formula di peso. Budget 12/10/9, istruzione max 3 voci, arricchimento con priorità.
- **v5**: as-is al 2026-11-14 (vedi nota sopra).

---

## 0. Rapporto con 01 e 02

`01-specifiche-funzionali-v6.md` e `02-specifiche-tecniche-v5.md` hanno già recepito le modifiche che la v4 di questo documento dichiarava come emendamenti: niente "risultati chiave" nel profilo, `Education` con `start_date`/`end_date`, pipeline a una sola chiamata, qualifica, Areas of Expertise. Per **regole di contenuto, quantità, selezione, impaginazione del CV e rifinitura con editor e chat** 01 e 02 rimandano a questo documento. Su questi temi, in caso di conflitto, **prevale questo documento**. Flussi di quota e credito, stati del job, endpoint e modello dati generale restano descritti in 01/02. Qui sono richiamati solo quando servono a capire il contenuto.

---

# PARTE I — SPECIFICHE FUNZIONALI

## 1. Obiettivo e contesto

Il CV generato combina il **profilo master** dell'utente con la **job description** di un'offerta. L'obiettivo è **1 pagina A4**, che però non è garantita in assoluto (§6). Il CV si genera **sempre su richiesta**: pulsante "Genera CV" / "Rigenera CV" nel dettaglio del job. Il ciclo notturno fa solo raccolta e scoring, e nessun punteggio fa partire una generazione da solo. Ogni generazione o rigenerazione consuma la quota giornaliera o il credito secondo le regole di 01/02. Il PDF scaricato è sempre quello dell'ultimo `CVDocument` del job: una generazione oppure un PDF finalizzato dall'editor (§15).

**Vincoli confermati:**
- **Grounding.** Il modello non inventa esperienze, competenze o risultati assenti dal profilo. Può riformulare, riordinare, enfatizzare e tradurre. Ci sono due eccezioni controllate: la sintesi per astrazione delle Areas of Expertise (§5.3) e l'amplificazione di esperienze reali per i gap selezionati dall'utente (§5.6). Nell'editor si aggiunge la richiesta esplicita dell'utente in chat (§15.3).
- **Template unico.** Esiste un solo template, e l'utente non può scegliere un template diverso. Il contenuto (quante esperienze, quanti bullet, quali voci) dipende solo da profilo, job ed eventuali indicazioni sui gap.

## 2. Principio cardine: le quantità le decide il sistema, i contenuti il modello

- **Il sistema** fissa con regole deterministiche i **tetti**: budget totale di bullet B (dal numero di voci di istruzione), massimo 5 esperienze, minimo garantito, numero di iterazioni del ripiego.
- **Il modello AI** produce i **contenuti** in una sola chiamata: sommario, qualifica, Areas of Expertise, bullet riformulati per **ogni** esperienza del profilo, scelta di skills e certificazioni. Restituisce anche un **ordinamento di rilevanza** (`relevance_rank` per ogni bullet) e una marcatura booleana `highly_relevant` per esperienza.
- **Il sistema applica quell'ordinamento** dopo la risposta, senza altre chiamate AI. Prima il cap delle esperienze con swap singolo, poi il taglio dei bullet al budget, poi il loop di ripiego per overflow. Il criterio di taglio è uno solo (la rilevanza) e serve in due momenti.

Nessuna domanda preliminare all'utente per dimensionare il CV: le quantità si calcolano dai dati reali del profilo.

## 3. Vincoli di input al profilo master

### 3.1 Esperienze lavorative
- Numero **libero** di esperienze, anche **zero** (caso neolaureato, §8).
- Nel profilo le esperienze sono **raggruppate per azienda**: più ruoli nella stessa azienda stanno sotto la stessa scheda. Ogni ruolo è un'esperienza a sé, con proprie date, località, attività e tecnologie.
- Data di fine vuota = esperienza **in corso**.
- Con **più di 5 esperienze** il profilo (e l'onboarding) mostra l'avviso *"Hai inserito più di 5 esperienze: il CV generato ne mostrerà al massimo 5, le più pertinenti per ciascuna offerta."* Il testo non descrive con esattezza la regola reale, che tiene le 5 più recenti con al massimo uno swap (§5.4, §14).
- **Nessun limite** al numero di bullet per esperienza né alla loro lunghezza: i valori "8 bullet / 200 caratteri" della v4 non esistono né nel backend né nel frontend. I soli limiti di lunghezza sono i `max_length` dei campi testuali del modello (es. azienda e ruolo 255 caratteri). I bullet sono una lista JSON senza vincoli.

### 3.2 Istruzione
- **Almeno 1 voce di istruzione** rende il profilo completo, quindi generabile (`Profile.is_complete`). Senza istruzione la generazione è rifiutata.
- La **data di fine non è obbligatoria**: vuota significa "in corso" (Sprint 34) e la voce conta come la più recente. Le traduzioni contengono ancora un messaggio "La data di fine è obbligatoria…", ma nessuna pagina lo usa.
- **Tutte** le voci compaiono nel CV, senza alcun limite di conteggio (Sprint 38, richiesta del committente).
- **Ordinamento:** data di fine decrescente, con "in corso" in testa. A pari data di fine viene prima la voce di **durata minore**; una voce senza data di inizio conta come durata sconosciuta, quindi va dopo. Se anche la durata è pari, l'ordine è **casuale**.
- **Nessuna chiamata AI:** titolo, istituto, località e note si copiano dal profilo senza riformularli né tradurli. Le date si formattano come in §5.4.
- Nessun limite di caratteri specifico per i campi oltre ai `max_length` del modello (istituto e titolo 255; note testo libero).

### 3.3 Testi di guida alla compilazione
Oggi nel profilo esistono l'indicazione sul raggruppamento per azienda e l'avviso sulle 5 esperienze (§3.1). Non c'è una guida più ampia sulla sintesi di bullet e istruzione.

## 4. Struttura del CV generato

Il template è uno solo, A4, e le sezioni compaiono in questo ordine:

1. **Intestazione**: nome, **qualifica professionale**, riga contatti, foto facoltativa (§5.7, §5.1).
2. **Sommario**: un paragrafo **senza titolo di sezione** (§5.2).
3. **Areas of Expertise**: elenco puntato su due colonne (§5.3).
4. **Certified in / Skilled in**: due righe, senza titolo di sezione (§5.5).
5. **Esperienza lavorativa** (§5.4).
6. **Istruzione** (§3.2, §5.8).
7. **Lingue** (§5.9).

Una sezione vuota non compare: niente esperienze → niente sezione Esperienze; niente skills né certificazioni → niente righe.

**Etichette fisse.** Seguono la **lingua reale del contenuto** generato (§5.10), non la sola impostazione `cv_language_mode`:

| Codice | Areas of Expertise | Esperienze | Istruzione | Certified in | Skilled in | Lingue | Tecnologie | In corso |
|---|---|---|---|---|---|---|---|---|
| it | Aree di competenza | Esperienza lavorativa | Istruzione | Certificazioni | Competenze | Lingue | Tecnologie | Presente |
| en | Areas of Expertise | Work Experience | Education | Certified in | Skilled in | Languages | Technologies | Present |
| fr | Domaines de compétence | Expérience professionnelle | Formation | Certifications | Compétences | Langues | Technologies | Aujourd'hui |
| de | Kompetenzbereiche | Berufserfahrung | Ausbildung | Zertifizierungen | Kenntnisse | Sprachen | Technologien | Heute |
| es | Áreas de especialización | Experiencia laboral | Formación | Certificaciones | Habilidades | Idiomas | Tecnologías | Actualidad |

Nel codice esiste anche un'etichetta "Profilo/Profile…" per il sommario, ma il template non la usa.

## 5. Regole di generazione, sezione per sezione

### 5.1 Qualifica professionale
- Calcolata dal modello **a ogni generazione**, non è un campo del profilo. Compare sotto il nome.
- Il modello estrae dal **titolo del job** il **nome del ruolo**, senza tecnologie, progetto o contesto (es. *"Software Engineer for SSH/AWS and ERP systems"* → *"Software Engineer"*). Tiene la **seniority** se c'è (Senior, Junior, Lead…). Se il titolo è già pulito, lo usa così com'è.
- **Titolo ambiguo o multi-ruolo** → ruolo dell'esperienza più recente del profilo. **Senza esperienze** → titolo del job ripulito, senza ricorrere all'istruzione.
- È scritta nella lingua del CV (§5.10).

### 5.2 Sommario
- Il modello parte dal sommario del profilo come **base indicativa, non vincolante**. Può riorganizzarlo, tagliarlo o riscriverlo quasi per intero per aprirlo sulle **3–5 priorità chiave dell'offerta**, che il modello individua prima di scrivere qualunque contenuto. La figura professionale reale deve restare riconoscibile.
- Usa la terminologia dell'offerta **solo** dove corrisponde a contenuto reale del profilo.
- Lunghezza: un breve paragrafo di **alcune righe piene**, né una frase isolata né un'ultima riga di poche parole. È un'indicazione nel prompt, non un controllo del sistema.
- Le stesse priorità dell'offerta devono orientare in modo coerente sommario, aree e bullet: una priorità supportata dal profilo può comparire in più punti.

### 5.3 Areas of Expertise
- **Soft skill / aree funzionali-trasversali** (leadership, stakeholder management, problem solving…), distinte dalle hard skill di "Skilled in".
- **Da 4 a 6 voci** (`AREAS_OF_EXPERTISE_MIN/MAX`). Il vincolo sta solo nel prompt, non nello schema di output, quindi il sistema non lo controlla. Il template le dispone su **due colonne**.
- **Licenza di astrazione:** il modello può coniare il nome di un'area raggruppando competenze ed esperienze **realmente presenti** nel profilo, ma non può dedurle dalla sola job description. Con un profilo scarno guarda gli stessi contenuti da angolazioni diverse per arrivare comunque a 4.
- Ogni area ha un **riferimento interno di grounding** (bullet o esperienza d'origine). Viene salvato per diagnosi e non compare mai nel CV (§13).

### 5.4 Esperienze lavorative

**Input al modello.** Il modello riceve **tutte** le esperienze del profilo in ordine cronologico inverso (data di fine decrescente, quelle in corso in testa, poi data di inizio decrescente). Per ognuna riceve azienda, ruolo, attività (bullet) e tecnologie, non località né date. Restituisce una voce per ogni esperienza, nello stesso ordine e numero, con:
- bullet **riformulati**, mai più di quelli presenti nel profilo per quell'esperienza;
- un `relevance_rank` intero per bullet (0 = il più rilevante), univoco solo all'interno dell'esperienza;
- `highly_relevant` = vero solo per esperienze "pur non recentissime, particolarmente pertinenti" all'offerta.

Regole di scrittura dal prompt:
- ogni bullet occupa **1 o 2 righe piene**: se sfora di poco su una seconda riga, va accorciato oppure arricchito con un dettaglio reale;
- una competenza dell'offerta presente nel profilo solo come skill isolata, ma riconducibile a un'esperienza, può diventare esplicita in un bullet di quell'esperienza;
- grassetto sulle keyword (§5.11).

**Cap: massimo 5 esperienze** (`MAX_EXPERIENCES_SHOWN`).
- Con ≤ 5 esperienze compaiono tutte.
- Con più di 5 si tengono le **5 più recenti**, più uno **swap singolo**. Se tra le escluse c'è almeno un'esperienza marcata `highly_relevant`, la **più recente tra quelle marcate** prende il posto della **meno recente** tra le 5. La marcatura è un sì/no, senza punteggio: a parità di marcatura vince sempre la più recente. Mai più di uno swap.
- **Ordine nel CV:** sempre cronologico inverso. La rilevanza decide quanti bullet ha ogni esperienza e lo swap, non la posizione.

**Budget di bullet B** (`BULLET_BUDGET_BY_EDU_COUNT`) in funzione del numero di voci di istruzione:

| Voci di istruzione | B |
|---|---|
| 1 | 18 |
| 2 | 16 |
| 3 o più | 14 |

**Taglio.**
- Tra i bullet delle sole esperienze mostrate si tengono i **B globalmente più rilevanti**, ordinati per `relevance_rank`. Il rank è univoco solo dentro ogni esperienza, quindi il confronto mette sullo stesso piano i rank 0, 1, 2… di esperienze diverse (vedi §14).
- **Minimo garantito:** un'esperienza `highly_relevant` rimasta senza bullet ne riceve **2** (`MIN_GUARANTEED_BULLETS_FOR_RELEVANT_EXPERIENCE`), i suoi più rilevanti. I bullet garantiti si **aggiungono** a quelli già tenuti, quindi il totale può superare B.
- Dentro ogni esperienza i bullet rimasti compaiono **in ordine di rilevanza**, dal più rilevante, non nell'ordine del profilo.
- Un'esperienza mostrata senza bullet compare come **riga singola** (ruolo, località, date, tecnologie).

**Dati fattuali, mai dal modello.** Località, date e tecnologie arrivano dal profilo e si riattaccano a ogni esperienza per posizione:
- **Località**: "Città, XX" (codice paese ISO in maiuscolo).
- **Date: solo l'anno**. Esperienza in corso → "AAAA - Present" (etichetta tradotta). Inizio e fine nello stesso anno → un anno solo (Sprint 35, 38).
- **Tecnologie**: riga "Tecnologie: a, b, c" sotto i bullet, se presenti.
- **Ruolo**: è quello restituito dal modello, che di norma lo copia dal profilo. Il prompt non vieta di riformularlo.
- **Azienda**: per ruoli **consecutivi** nella stessa azienda il nome compare **una volta sola**, sopra il primo.

### 5.5 Certified in / Skilled in
- **Hard skill e certificazioni** prese **alla lettera** dal profilo. Il modello sceglie quali e in che ordine, per rilevanza rispetto all'offerta.
- Un **filtro del sistema** scarta qualunque voce che non coincida esattamente con una skill o certificazione del profilo.
- Due righe, **prima delle esperienze**: "**Certificazioni:** …" (en "Certified in") e poi "**Competenze:** …" (en "Skilled in"), voci separate da virgola. Una riga vuota non compare.
- Nessun vincolo di "una riga": con molte voci la riga va a capo, giustificata.
- Una competenza già messa in evidenza in un bullet può comparire anche qui.

### 5.6 Colma i gap (sostituisce l'arricchimento)

> L'arricchimento della v4 (dettaglio agganciato a un'esperienza, salvabile nel profilo, con priorità protetta) **non esiste più** (Sprint 44).

- **Dove:** nel dettaglio del job, sotto la descrizione, c'è un pannello **espandibile e facoltativo**: "Colma i gap trovati per questa offerta prima di generare". Contiene:
  - l'elenco **numerato** dei gap trovati dallo scoring, ciascuno con una casella di spunta;
  - una casella di testo facoltativa "Indicazioni su come inserire i gap selezionati" (es. "per il gap 2, …");
  - un avviso quando ci sono gap selezionati ma nessuna indicazione.

  Il pulsante "Genera CV" / "Rigenera CV" sta fuori dal pannello e invia comunque gap e indicazioni presenti.
- **Cosa arriva al modello:**
  - nessun gap e nessuna indicazione → nulla;
  - solo indicazione → "INDICAZIONI DEL CANDIDATO PER QUESTA GENERAZIONE: …". È un'indicazione generica e **non** autorizza eccezioni al grounding;
  - gap selezionati → elenco numerato "GAP DA COLMARE PER QUESTA OFFERTA" (per ogni gap "etichetta (motivo)"), più le indicazioni dell'utente. Senza indicazioni si usa un testo predefinito: per ogni gap, amplificare con buon senso l'esperienza reale più plausibile.
- **Cosa l'AI può fare**, **solo** per i gap elencati: amplificare o estendere il contenuto di un'esperienza **reale** del profilo (stessa azienda, ruolo e periodo), anche oltre i bullet documentati. Deve seguire le indicazioni dell'utente; senza indicazioni sceglie l'esperienza più plausibile. Il bullet così creato deve avere `relevance_rank` basso, cioè molto rilevante.
- **Cosa l'AI non può fare**, nemmeno per un gap:
  - creare datori di lavoro, ruoli o periodi mai avuti;
  - aggiungere a skills/certifications voci non presenti nel profilo (qui vale il filtro del sistema, §5.5).
- **Nessun salvataggio sul profilo.** Il testo usato resta solo sul `CVDocument` (`extra_instructions_used`), per tracciabilità.
- **Nessuna protezione dal taglio.** Un bullet nato da un gap segue le regole normali del budget e del ripiego. La sola differenza è il rank basso chiesto al modello.
- Colmare i gap non ricalcola il punteggio del job.

### 5.7 Intestazione e contatti
- **Nome**: nome e cognome dell'account. Se mancano, al loro posto compare l'**email dell'account** (§14).
- **Qualifica** sotto il nome (§5.1).
- **Riga contatti**, separata da un filetto, ordine fisso: **Città tradotta, PAESE** | **telefono** | **email del profilo** | **LinkedIn**. La città è tradotta dal modello nella lingua del CV (es. "Roma" → "Rome"); il paese è il codice ISO a 2 lettere. L'email è il campo dedicato del profilo (Sprint 41), **non** quella di login. LinkedIn è un link con testo fisso "LinkedIn". Le parti vuote si omettono.
- **Foto**: rotonda, a destra, solo se l'utente ha attivato l'opzione "includi foto" **e** il profilo ha una foto. Di default è spenta.

### 5.8 Istruzione
Tutte le voci, nell'ordine di §3.2, una per riga:
- prima riga: "**Titolo** — Istituto" a sinistra, "Località | **date**" a destra (date solo anno, "in corso" tradotto, stesso anno collassato);
- sotto, le note se presenti.

Nessuna riformulazione né traduzione.

### 5.9 Lingue
**Tutte** le lingue del profilo, su una riga, nel formato "Lingua: Livello". Lingua e livello sono **codici fissi** del profilo (Sprint 41), tradotti nella lingua del CV. Livelli: elementare, intermedio, fluente, madrelingua. Un codice non riconosciuto (dato vecchio) compare così com'è.

### 5.10 Lingua di output
- Impostazione utente `cv_language_mode`:
  - `english` → tutto in **inglese**;
  - `job_language` (default) → tutto nella **lingua della job description**.
- Nel secondo caso il modello dichiara in quale lingua ha scritto (`content_language`) e da quella dipendono le etichette fisse (§4). Lingue supportate per le etichette: **it, en, fr, de, es** (`SUPPORTED_CV_LANGUAGES`).
- Offerta in un'altra lingua: il testo esce comunque in quella lingua, ma etichette fisse, nomi delle lingue e livelli sono in **inglese** (`FALLBACK_CV_LANGUAGE = "en"`).
- Qualifica, sommario, aree, bullet e città sono tradotti dal modello. Istruzione, skills e certificazioni restano come nel profilo. Le tecnologie restano come nel profilo.

### 5.11 Grassetto sulle keyword
- Il modello può marcare con `**…**`, in ogni bullet di esperienza, **al massimo 1–2 brevi parole o espressioni**: le più rilevanti per l'offerta (tool richiesto, competenza chiave, risultato numerico). Devono essere testo letterale del bullet, mai frasi intere, e il grassetto non va forzato se nessuna parola spicca.
- Nel PDF i marcatori diventano grassetto reale. Il modello li usa **solo nei bullet delle esperienze**, ma dallo Sprint 69 sono interpretati in tutti i testi liberi del CV che utente e chat possono modificare: qualifica, sommario, Areas of Expertise, ruolo, note dell'istruzione. Restano testo letterale solo i campi presi così come sono dal profilo (azienda, località, date, titolo e istituto, competenze, lingue). Un marcatore senza chiusura resta testo.
- Nell'editor lo stesso grassetto si mette e si toglie a mano (§15.2), con lo stesso campo in tutti questi testi: editor, anteprima e PDF mostrano la stessa cosa.

## 6. Overflow: ripiego e caso multi-pagina

1. **Dimensione fissa.** Il CV si impagina sempre con **un solo set di parametri** (corpo 9 pt, §16). Font e margini non si riducono mai: i 3 livelli di compattamento della v4 sono stati eliminati (Sprint 52, scelta del committente).
2. **Loop di ripiego.** Se il PDF supera 1 pagina, il sistema toglie il **bullet globalmente meno rilevante** (rank più alto) tra quelli rimasti e reimpagina. Ripete fino a **4 volte** (`MAX_OVERFLOW_ITERATIONS`) o finché il CV entra in una pagina o finiscono i bullet. Il loop può togliere anche bullet del minimo garantito o nati da un gap. Un'esperienza che perde tutti i bullet diventa riga singola.
3. **Caso residuale.** Se dopo il ripiego il CV supera ancora 1 pagina, si salva **comunque il PDF multi-pagina**, senza errore. Il sistema registra l'evento nel `RunLog` per diagnosi e, dallo Sprint 69, il numero di pagine nel documento (`page_count`): l'utente vede un avviso dopo la generazione e nel dettaglio del job, e può accorciare il CV con l'editor. Il multi-pagina è quindi un esito possibile e accettato.

Nell'editor (§15) non c'è alcun ripiego automatico: il numero di pagine si segnala e decide l'utente.

## 7. Template: contratto e aspetto

- **Template unico**, nessuna scelta per l'utente e nessun campo per sceglierlo nel modello utente.
- **Nessuna influenza sul contenuto:** il template impagina ciò che la pipeline (o la bozza dell'editor) ha già deciso e non cambia il numero di esperienze, bullet o voci.
- **Casi scarni gestiti:**
  - foto assente;
  - zero esperienze (sezione omessa);
  - poche aree (griglia a due colonne con l'ultima riga incompleta);
  - certificazioni assenti (sola riga "Skilled in");
  - lingue assenti.
- **Aspetto in sintesi:**
  - font serif Cambria; nel container di rendering il font effettivo è **Caladea**, con le stesse metriche;
  - tutto nero, salvo un **blu ardesia** per titoli di sezione e filetti;
  - titoli di sezione in maiuscolo;
  - intestazione centrata;
  - **testo giustificato** per sommario, righe Certified/Skilled in e bullet;
  - riga delle lingue distribuita su tutta la larghezza;
  - aree e bullet con lo stesso pallino e lo stesso rientro.

  Valori esatti in §16.
- **Collaudo:** non ci sono profili di collaudo "worst case" automatici. La v4 prevedeva due worst case A/B con garanzia di 1 pagina: oggi la garanzia non esiste (§6) e quei test non sono implementati.

## 8. Casi limite

- **Profilo molto ricco** (>5 esperienze, molti bullet): 5 esperienze (al massimo uno swap), bullet limitati da B e dal ripiego, avviso a monte. Ciò che non entra nel CV resta nel profilo e nella bozza dell'editor, come esperienze e bullet nascosti (§15).
- **Profilo scarno**: CV visivamente leggero, accettato. Nessun riempimento. Le Areas of Expertise restano comunque 4–6.
- **Profilo senza esperienze**: ammesso. La sezione Esperienze è omessa e B resta inutilizzato. La qualifica è il titolo del job ripulito.
- **Molta istruzione** (≥3 voci): tutte mostrate, B = 14. Con molte voci aumenta la probabilità di multi-pagina.
- **Stesso profilo, job diversi**: B, istruzione e lingue sono identici. Cambiano testi, bullet scelti, eventuale swap, skills e certificazioni scelte.
- **Variabilità del modello**: a parità di input testi, rank e marcature possono cambiare tra due generazioni.
- **Nessuna certificazione**: sola riga "Skilled in".
- **Lingua dell'offerta non supportata**: testo nella lingua dell'offerta, etichette in inglese (§5.10).

## 9. Fuori scope

1. **Formato Word**: solo PDF.
2. **Scelta di più template** o personalizzazioni grafiche da parte dell'utente.
3. **CV volutamente su 2 pagine** come opzione: oggi il multi-pagina è solo un esito residuale (§6) o una scelta fatta nell'editor (§15).
4. **Sincronizzazione bozza → profilo**: nulla di quanto si modifica nell'editor o nella chat torna nel profilo master.
5. **OCR** e ogni altra esclusione già a verbale in 01/02.

## 15. Rifinitura manuale: editor e chat AI

> Sezione nuova (Sprint 51, 59–62). Dettagli tecnici in §17.

### 15.1 Accesso e ciclo di vita della bozza
- Il pulsante **"Modifica CV"** compare nel dettaglio del job quando esiste un CV scaricabile e apre l'editor.
- **Prima apertura**: si crea una **bozza** (una per job) copiando il contenuto strutturato dell'ultimo CV del job. I CV generati prima dello Sprint 51 non hanno questo contenuto: il pulsante "Modifica CV" non compare e il dettaglio spiega di rigenerare il CV (Sprint 69).
- **Aperture successive**: si riapre la bozza esistente, con modifiche e conversazione. Se nel frattempo è stato generato un CV più recente (es. "Rigenera CV"), l'editor chiede prima *"ripartire dal nuovo documento (le modifiche precedenti e la chat si perdono) o continuare la bozza?"* (Sprint 69). "Riparti" ricrea la bozza dal nuovo CV e svuota la chat; "Continua" la lascia com'è e la domanda non si ripete per quel CV.
- **"Genera PDF finale"** produce un **nuovo CV del job** dalla bozza, compresa l'ultima modifica a schermo anche se l'autosave non è ancora partito (Sprint 69); il nuovo CV diventa quello scaricato e non conta come "CV più recente" per la domanda sopra. Non chiama l'AI e **non consuma quota né credito**. Lo stato del job non cambia. La bozza resta.

### 15.2 Cosa l'utente può cambiare rispetto alle regole automatiche

| Elemento | Regola automatica (§5) | Nell'editor |
|---|---|---|
| Qualifica, sommario | Scritti dal modello | Testo libero, con grassetto (Sprint 69) |
| Areas of Expertise | 4–6 voci dal modello | Modifica (con grassetto), aggiunta, rimozione, riordino; nessun minimo o massimo |
| Esperienze mostrate | Cap 5 + swap singolo | **Tutte** le esperienze del profilo sono in bozza, con la spunta "Mostra nel CV" (le escluse partono spente); nessun cap. L'ordine non si cambia |
| Ruolo | Dal modello | Modificabile, con grassetto |
| Azienda, località, date | Dal profilo | Solo lettura |
| Tecnologie | Dal profilo | Né visibili né modificabili; compaiono comunque nel PDF |
| Bullet | Taglio a B, minimo garantito, ripiego | **Tutti** i bullet prodotti dall'AI, ciascuno con spunta mostra/nascondi; all'inizio la spunta riflette la selezione automatica (bullet tagliati dal budget o dal ripiego spenti). Testo modificabile, aggiunta, rimozione, riordino. **Nessun taglio automatico al budget** |
| Grassetto nei bullet | Dal modello, 1–2 keyword | Selezione del testo + pulsante **B** o Ctrl/Cmd+B; nessun limite |
| Istruzione | Tutte le voci, copiate dal profilo | Tutti i campi modificabili (periodo come testo libero; note con grassetto), aggiunta e rimozione. **Solo nel CV** |
| Certified/Skilled in | Scelte dal modello con filtro di grounding | Caselle di spunta sulle **sole** voci del profilo |
| Lingue | Tutte dal profilo | Lingua e livello da elenchi fissi, aggiunta e rimozione. Solo nel CV |
| Una pagina | Ripiego di 4 iterazioni, poi multi-pagina | **Nessun ripiego**: l'anteprima mostra "1 pagina ✓" o "N pagine ⚠" e decide l'utente |

- **Anteprima**: il PDF reale, impaginato dal server con lo stesso template, nella colonna destra.
- **Salvataggio**: automatico. Bozza e anteprima si aggiornano insieme circa 1,2 s dopo l'ultima modifica, con stato "Salvataggio… / Salvato".
- Accendere un'esperienza esclusa dal cap mostra **tutti** i suoi bullet: le esperienze escluse non sono passate dal taglio, quindi i loro bullet partono tutti accesi.

### 15.3 Chat AI dell'editor
- **Apertura**: pulsante flottante "Chiedi all'AI" in basso a destra. Si apre un pannello laterale ("Assistente bozza") che non blocca l'editor e si chiude con la X.
- **Proposta → conferma.** L'utente scrive in linguaggio naturale. Il modello risponde con un breve testo e zero o più **azioni puntuali**, ciascuna mostrata come una card "prima" (rosso barrato) / "dopo" (verde) con **Accetta / Rifiuta**. Nulla si applica in automatico. "Accetta" applica la modifica come se l'utente l'avesse fatta a mano, quindi seguono salvataggio e anteprima.
- **Azioni possibili:**
  - modifica di sommario, qualifica e ruolo di un'esperienza;
  - modifica e aggiunta di bullet; nascondere o mostrare un bullet;
  - nascondere o mostrare un'esperienza;
  - modifica, aggiunta e rimozione di un'area;
  - accendere o spegnere una skill o una certificazione;
  - modifica delle note di una voce di istruzione;
  - modifica del livello di una lingua.

  **Non** previste: riordino, eliminazione di bullet, modifica di titolo/istituto/date dell'istruzione, aggiunta o rimozione di lingue o voci di istruzione.
- **Riferimento ai bullet**: il pulsante ✦ su ogni bullet lo aggiunge al "Contesto" del messaggio. Si possono puntare più bullet, anche di esperienze diverse. Il modello li usa per risolvere riferimenti generici ("questo punto"), ma se il testo nomina chiaramente altro segue il testo. Dallo Sprint 69 bullet puntati e proposte si riferiscono al bullet per il suo identificativo, non per la posizione: riordini, eliminazioni o più proposte accettate nello stesso turno non spostano mai una modifica su un altro bullet; una proposta su un elemento che non esiste più non viene applicata.
- **Memoria delle proposte** (Sprint 69): il modello vede, per i turni precedenti, anche le proposte fatte e la scelta dell'utente (accettata, rifiutata, in sospeso), e non ripropone ciò che è stato rifiutato se l'utente non lo chiede.
- **Grounding in chat:**
  - per il testo narrativo (sommario, qualifica, ruolo, bullet, note di istruzione) il modello può andare oltre il profilo **solo su richiesta esplicita** dell'utente nella conversazione, e deve segnalarlo nella risposta;
  - le nuove aree devono restare riconducibili al profilo;
  - skills e certificazioni: **nessuna eccezione**, solo nomi esatti del profilo. Il sistema scarta comunque le azioni con nomi non presenti nel profilo e i livelli di lingua non validi.
- **Persistenza**: conversazione e decisioni (Accetta/Rifiuta) restano salvate con la bozza. Riaprendo l'editor, le card già decise compaiono come "Applicata" o "Rifiutata".
- **Costo**: **ogni messaggio** costa 0,20 € di credito extra (default di `PRICE_CV_DRAFT_CHAT_MESSAGE`), senza quota gratuita né massimale; prezzo e saldo sono mostrati sopra il campo di testo prima dell'invio (Sprint 69). Senza credito il messaggio è rifiutato; se l'AI fallisce, il credito torna all'utente.

---

# PARTE II — SPECIFICHE TECNICHE

> Riferimenti di codice relativi a `backend/apps/cv/` salvo diversa indicazione.

## 10. Modello dati coinvolto

### 10.1 Profilo (`apps/profiles/models.py`)
- **`Profile`**: `user`, `summary`, `photo`, `phone`, `email` (email da mostrare sul CV, Sprint 41), `city`, `country_code` (ISO alpha-2), `linkedin_url`. Proprietà `is_complete` = esiste almeno un `Education`.
- **`Experience`**: `company`, `role` (255), `location`, `location_country_code`, `start_date` e `end_date` entrambi nullable (`end_date` nullo = in corso), `bullets` (JSON list, senza limiti), `technologies` (JSON list).
- **`Education`**: `institution`, `title` (255), `location`, `location_country_code`, `start_date` e `end_date` **entrambi nullable** (`end_date` nullo = in corso), `notes`.
- **`Skill`, `Certification`**: `name` (255). **`Language`**: `language` e `level` a scelte fisse (`apps/profiles/language_options.py`); livelli `elementary`, `intermediate`, `fluent`, `mother_tongue`.
- Sull'utente: `cv_language_mode` (`english` | `job_language`, default `job_language`), `cv_include_photo` (default falso).

### 10.2 Validazione
Generabile solo se `profile.is_complete`; altrimenti `ProfileIncomplete`. Nessun minimo di esperienze. Nessuna validazione su numero o lunghezza dei bullet, né sulla data di fine dell'istruzione.

### 10.3 CV
- **`CVDocument`**: `job`, `user`, `html_source`, `pdf_file` (cartella `cv_documents/`), `generated_at`, `generation_type` (`automatic` | `manual`; `automatic` resta nel modello ma non è più usato), `extra_instructions_used` (testo gap/indicazioni), `areas_of_expertise_grounding` (`[{label, grounding_reference}]`), `content_json` (§17).
- **`CVDraft`**: `job` OneToOne (`related_name="cv_draft"`), `user`, `content_json`, `chat_history`, `created_at`, `updated_at`.

## 11. Pipeline di generazione del CV

Punto d'ingresso: `request_manual_cv_generation` (`manual_generation.py`). Fa guardia di concorrenza, controllo del profilo e riserva di quota o credito, poi chiama `generate_cv(job, MANUAL, extra_instructions)` (`generation.py`). Gira in modo **sincrono** nella richiesta HTTP `POST /api/jobs/<id>/generate-cv/` con `{gaps, gap_instructions}`. Prima della chiamata, `gap_filling.build_extra_instructions` trasforma gap e indicazioni nel testo `extra_instructions` (§5.6).

1. **Controllo profilo**: `profile.is_complete`, altrimenti `ProfileIncomplete`.
2. **Chiamata AI per i contenuti**: `ai_content.generate_cv_content`. Una sola chiamata `call_claude_structured` (`apps/common/ai.py`: Claude via AWS Bedrock, schema imposto con tool-use forzato, fino a 3 tentativi). Modello `BEDROCK_CV_GENERATION_MODEL`, `max_tokens=4000`, `effort="medium"`.
   - **Input:** profilo (`summary`, `city`, `experiences[{company, role, bullets, technologies}]` ordinate `-end_date, -start_date`, `skills`, `certifications`), offerta (titolo, azienda, descrizione completa), `extra_instructions` (o "Nessuna."), istruzione di lingua, range delle Areas of Expertise.
   - **Istruzione di lingua:** "English" se `cv_language_mode == "english"`, altrimenti "la stessa lingua della seguente job description: <primi 200 caratteri>".
3. **Contesto e selezione** (`_build_render_context`):
   - lingua delle etichette (`_resolve_html_lang`): `en` se modalità inglese, altrimenti `content_language` se supportata, altrimenti `en`;
   - istruzione ordinata (`select_educations_to_show`) e budget `compute_bullet_budget(n)`;
   - `_attach_facts`: per **indice di posizione**, aggiunge a ogni esperienza dell'AI `profile_experience_id`, località, date formattate e tecnologie del profilo;
   - `select_and_cut_experiences(experiences, B)`;
   - filtro di grounding su skills e certificazioni;
   - lingue tradotte.
4. **Rendering e ripiego** (`_render_with_overflow_retry`): i bullet si appiattiscono a stringhe e si impagina con `render_cv` (WeasyPrint; numero di pagine da `document.pages`). Se le pagine sono più di 1 parte il loop `remove_least_relevant_bullet` (§11.6).
5. **`content_json`**: `build_draft_content_json` (§17).
6. **Salvataggio**: `CVDocument` con HTML, PDF, `generation_type`, `extra_instructions_used`, `content_json`, `areas_of_expertise_grounding`. Stato del job (`cv_generated`, `date_cv_generated`), quota, credito e rimborsi sono gestiti da `manual_generation.py` (vedi 02).

### 11.1 Schema JSON di output del modello (`CONTENT_JSON_SCHEMA`)

```
{
  summary: str,
  qualification: str,
  translated_city: str,
  content_language: "it"|"en"|"fr"|"de"|"es",
  areas_of_expertise: [{label: str, grounding_reference: str}],
  experiences: [{company: str, role: str, highly_relevant: bool,
                 bullets: [{text: str, relevance_rank: int}]}],
  skills: [str],
  certifications: [str]
}
```
Tutti i campi sono obbligatori e `additionalProperties: false` vale a ogni livello. Lo schema non ha `minItems`/`maxItems`: il range 4–6 delle aree e "una voce per esperienza, mai più bullet del profilo" stanno solo nel prompt.

### 11.2 Sezioni del system prompt (`CONTENT_SYSTEM_PROMPT`)
1. Grounding con due eccezioni controllate.
2. Priorità dell'offerta (3–5).
3. Sommario (§5.2).
4. Qualifica (§5.1).
5. Città tradotta (solo città, senza paese).
6. `content_language`.
7. Areas of Expertise (§5.3).
8. Esperienze: stesso ordine e numero, rank, `highly_relevant`, skill isolata → bullet, 1–2 righe piene (§5.4).
9. Grassetto (§5.11).
10. Gap da colmare (§5.6).
11. Skills e certificazioni letterali.

### 11.3 Selezione e taglio (`selection.py`, funzioni pure)
- `select_educations_to_show`: rimescolamento casuale e poi ordinamento stabile per (`-fine`, `durata`). La fine nulla vale `+inf`; l'inizio nullo dà durata `+inf`; una voce in corso usa la data odierna come fine provvisoria per la durata.
- `compute_bullet_budget(n)` = `BULLET_BUDGET_BY_EDU_COUNT[max(1, min(n, EDU_MAX_SHOWN))]`.
- `_select_shown_experiences`: se le esperienze sono più di 5, prende `shown = prime 5` ed `excluded = resto`. Se esiste un'esclusa `highly_relevant`, quella con `_order` minimo (la più recente) sostituisce l'ultima di `shown`.
- `_cut_bullets_to_budget`:
  - ordina tutti i bullet delle esperienze mostrate per `relevance_rank` crescente (ordinamento stabile, quindi a pari rank vince l'esperienza più recente) e tiene i primi B;
  - poi, a ogni esperienza `highly_relevant` con zero bullet tenuti (ma con bullet disponibili), assegna i suoi 2 migliori **in aggiunta**;
  - infine riordina i bullet di ogni esperienza per rank.
- `remove_least_relevant_bullet`: toglie il bullet con il rank **massimo** tra tutti quelli rimasti (a pari rank il primo trovato, quindi quello dell'esperienza più recente). Restituisce `False` se non ce ne sono.
- `flatten_bullets_to_text`: da `{text, relevance_rank}` a stringa, appena prima del rendering.

### 11.4 Formattazione dei dati fattuali (`generation.py`)
- `_format_date` → `%Y`.
- `_format_date_range(start, end, ongoing)`:
  - fine nulla → "AAAA - <ongoing>";
  - stesso anno → "AAAA";
  - altrimenti "AAAA - AAAA";
  - trattini e spazi in eccesso rimossi se manca un estremo.
- `_format_location(city, cc)` → "Città, CC".
- `_build_contact_parts`: `[{text, is_link, url?}]` nell'ordine città+paese, `profile.phone`, `profile.email`, LinkedIn.
- `_build_full_name`: `first_name last_name`, oppure `user.email`.
- `_build_photo_url`: `file://` del file foto, solo con `cv_include_photo` e foto presente.
- `_build_languages`: `LANGUAGE_NAME_LABELS` / `LANGUAGE_LEVEL_LABELS` nella lingua del CV, con il valore grezzo come fallback.
- `SECTION_LABELS`: le 5 lingue (§4).

### 11.5 Grounding lato server
- Skills e certificazioni: `_filter_grounded_skills` tiene solo i nomi presenti esattamente nel profilo.
- Località, date e tecnologie non passano mai dal modello. Istruzione e lingue non passano mai dal modello. Il ruolo invece è quello restituito dal modello.
- Il resto del grounding (aree, bullet, gap) si affida al prompt; il sistema non lo verifica.

### 11.6 Loop di overflow
```
html, pdf, pages = render_cv(context)          # un solo livello (COMPACT_LEVELS)
iter = 0
while pages > 1 and iter < MAX_OVERFLOW_ITERATIONS (4):
    if not remove_least_relevant_bullet(experiences): break
    rirenderizza; iter += 1
if pages > 1: RunLog(task_type=cv_generation, status=SUCCESS,
                     message="CV generato multi-pagina (N pagine) dopo K iterazioni di ripiego.")
```
`render_cv` passa per `_render_with_compact_retry`, che con un solo livello impagina una volta sola. La generazione riuscita in 1 pagina non scrive nessun `RunLog`.

## 12. Parametri di configurazione

`cv_parameters.py`, salvo diversa indicazione. Si modificano senza toccare la logica.

| Parametro | Valore | Dove agisce |
|---|---|---|
| `EDU_MAX_SHOWN` | 3 | Solo come soglia del budget (3+ voci → valore più stretto). **Non** limita le voci mostrate (§3.2) |
| `BULLET_BUDGET_BY_EDU_COUNT` | `{1: 18, 2: 16, 3: 14}` | Budget B (§5.4) |
| `MAX_EXPERIENCES_SHOWN` | 5 | Cap esperienze con swap singolo (§5.4) |
| `MIN_GUARANTEED_BULLETS_FOR_RELEVANT_EXPERIENCE` | 2 | Esperienza `highly_relevant` rimasta senza bullet (§5.4) |
| `AREAS_OF_EXPERTISE_MIN` / `MAX` | 4 / 6 | Solo nel prompt (§5.3) |
| `MAX_OVERFLOW_ITERATIONS` | 4 | Loop di ripiego (§6, §11.6) |
| `SUPPORTED_CV_LANGUAGES` | `["it", "en", "fr", "de", "es"]` | Enum `content_language`, `SECTION_LABELS` (§5.10) |
| `FALLBACK_CV_LANGUAGE` | `"en"` | Etichette per lingue non supportate (§5.10) |
| `COMPACT_LEVELS` (`rendering.py`) | 1 livello: corpo 9 pt, interlinea 1.25, margine 1cm, `section_gap` 8pt, `heading_gap` 4pt, `item_gap` 6pt, foto 65pt | Impaginazione (§6, §16) |
| `max_tokens` / `effort` generazione (`ai_content.py`) | 4000 / `medium` | Chiamata AI dei contenuti |
| `max_tokens` / `effort` chat (`draft_chat.py`) | 2000 / `medium` | Chat dell'editor |
| `PRICE_CV_DRAFT_CHAT_MESSAGE` (`config/settings.py`, env) | 0.20 € | Costo per messaggio di chat (§15.3) |

Non esistono parametri per "max bullet per esperienza", "lunghezza max bullet" o "limiti caratteri istruzione".

## 13. Grounding verificabile delle Areas of Expertise

Il `grounding_reference` di ogni area si salva su `CVDocument.areas_of_expertise_grounding` come `[{label, grounding_reference}]`. Serve alla diagnosi (consultabile da Django Admin o dal DB). Non si mostra mai all'utente né si stampa nel CV. Sui `CVDocument` creati da "Genera PDF finale" il campo è **vuoto**, perché la bozza non conserva i riferimenti.

## 16. Template e stile (`templates/cv/cv_template.html`)

Un solo file. I parametri `{{ … }}` arrivano dall'unico livello di `COMPACT_LEVELS`; tra parentesi il valore effettivo.

| Elemento | Stile |
|---|---|
| Pagina | A4, margine `page_margin` (1cm) |
| Font | `"Cambria", "Caladea", "DejaVu Serif", serif`. Nell'immagine è installato `fonts-crosextra-caladea` (`backend/Dockerfile`), quindi il font effettivo è **Caladea**, con le metriche di Cambria |
| Corpo | `base_font_size` (9pt), interlinea 1.25, colore `#000`, letter-spacing 0.2pt |
| Intestazione | flex, testo **centrato**, foto allineata in basso; filetto inferiore 1pt `#2f4a63`; padding e margine inferiore 4pt |
| Nome (h1) | base+9 (18pt), grassetto |
| Qualifica | base+5 (14pt), normale |
| Riga contatti | 9pt, filetto superiore 1pt `#2f4a63` (padding/margine 3pt); separatore " \| "; link LinkedIn sottolineato, colore ereditato |
| Foto | 65pt × 65pt, rotonda, `object-fit: cover`, margine sinistro 14pt |
| Sezioni | margine inferiore `section_gap` (8pt) |
| Titoli di sezione (h2) | 11pt fisso, grassetto, MAIUSCOLO, letter-spacing 0.5pt, `#2f4a63`, filetto inferiore 1pt `#2f4a63`, padding 2pt, margine inferiore 4pt |
| Sommario, righe Certified/Skilled in | `section > p`, **giustificato**; le righe Certified/Skilled hanno l'etichetta in grassetto e margine 1pt |
| Areas of Expertise | griglia a 2 colonne, gap 1pt (righe) / 16pt (colonne) |
| Bullet (esperienze e aree) | nessun pallino nativo; "•" via `::before` a base+5 (14pt), `vertical-align: -1pt`, `padding-right` 5pt; `padding-left` 16pt, `text-indent` −12pt. Bullet esperienze **giustificati**, margine superiore lista 2pt, 1pt tra un bullet e l'altro |
| Esperienza | blocchi separati da `item_gap` (6pt). Azienda grassetto MAIUSCOLO (`{% ifchanged %}`); riga ruolo in flex: ruolo **corsivo** a sinistra, "località \| **date**" a destra senza a capo |
| Tecnologie | base−1 (8pt), corsivo, "Tecnologie: …" |
| Istruzione | riga flex: "**Titolo** — Istituto" a sinistra, "località \| **date**" a destra; note sotto |
| Lingue | riga flex `justify-content: space-between`, gap minimo 18pt; "Lingua: Livello" |
| Grassetto keyword | filtro `bold_markup` (`templatetags/cv_extras.py`): regex non greedy `\*\*(.+?)\*\*` → `<strong>`, resto in escape HTML; applicato ai bullet delle esperienze e, dallo Sprint 69, a qualifica, sommario, aree, ruolo e note dell'istruzione |

Colori: solo `#000` e `#2f4a63`. I grigi precedenti di qualifica, contatti e tecnologie sono stati rimossi nello Sprint 56.

## 17. Bozza dell'editor: `content_json`, rendering, chat

### 17.1 Struttura di `content_json` (uguale su `CVDocument` e `CVDraft`)
```
{
  summary, qualification, translated_city,
  content_language,                       # lingua delle etichette già risolta
  areas_of_expertise: [str],
  experiences: [{profile_experience_id, company, role, location, dates,
                 technologies: [str], shown: bool,
                 bullets: [{id, text, shown: bool}]}],   # TUTTE le esperienze del profilo, TUTTI i bullet dell'AI; id stabile (Sprint 69)
  educations: [{institution, title, location, dates, notes}],   # stringhe già formattate
  skills: [str], certifications: [str],   # selezione corrente (filtrata sul profilo)
  languages: [{language: code, level: code}]
}
```
Costruzione (`build_draft_content_json`):
- `shown` dell'esperienza vale vero se l'esperienza è tra quelle finali, dopo cap, taglio e ripiego;
- `shown` di un bullet vale vero se il suo testo è tra i bullet finali di quell'esperienza. Per le esperienze escluse dal cap tutti i bullet hanno `shown = true`;
- i bullet compaiono nell'**ordine restituito dall'AI**, non nell'ordine per rank del PDF generato (§14);
- ogni bullet riceve un `id` di 12 caratteri esadecimali (`apps/cv/draft_ids.py`, Sprint 69). Gli id mancanti (contenuti precedenti, bullet aggiunti da una scheda non aggiornata) sono assegnati dal server alla lettura della bozza, al seed, in PATCH, anteprima e finalizzazione; la PWA assegna l'id ai bullet che l'utente aggiunge.

### 17.2 Rendering dalla bozza (`draft.py`)
- `seed_draft_for_job`: `update_or_create` del `CVDraft` dall'ultimo `CVDocument` (`-generated_at, -id`), con chat azzerata e `source_document` = quel documento. Se manca `content_json` solleva `NoCvDocumentToEdit` (409).
- `is_cv_draft_outdated` / `keep_cv_draft` (Sprint 69): la bozza è superata se l'ultimo CV del job non è il suo `source_document`; "continua la bozza" aggiorna solo il riferimento.
- `render_context_from_draft`:
  - prende solo esperienze e bullet con `shown`, nell'ordine della bozza, **senza cap, budget né ripiego**;
  - etichette da `content_language`, con fallback `en`;
  - intestazione (nome, contatti, foto) **riletta dal profilo e dall'utente al momento del rendering**: le modifiche a telefono, email o foto del profilo si riflettono anche su un CV finalizzato dopo;
  - lingue tradotte dai codici.
- `render_draft_preview`: un rendering con il contenuto inviato dal client (anche non salvato). Restituisce il PDF con l'header `X-Page-Count`.
- `finalize_cv_draft`: salva nella bozza il contenuto corrente inviato dalla PWA (se presente, già validato), impagina e crea un `CVDocument` (`generation_type=manual`, `content_json` = bozza, `page_count`, senza `extra_instructions_used` né `areas_of_expertise_grounding`), che diventa il `source_document` della bozza. Nessuna chiamata AI, nessun consumo.

### 17.3 Chat (`draft_chat.py`)
- **Endpoint:** `GET/POST/PATCH /api/jobs/<id>/cv-draft/chat/`.
  - GET → `{history, price, balance}` (Sprint 69).
  - POST `{message, focus_bullets: [{profile_experience_id, bullet_id}]}` → `{reply, actions, balance}`.
  - PATCH `{message_index, action_index, decision: accepted|rejected}` salva la decisione sull'azione.
- **Input al modello:** la **bozza salvata** (JSON completo, bullet nascosti inclusi, con gli id; la PWA salva prima l'eventuale modifica in attesa), skills e certificazioni del profilo, l'offerta, la cronologia degli ultimi 20 turni con, per l'assistente, le azioni proposte in forma compatta e la decisione `accepted`/`rejected`/`pending` (Sprint 69), i "BULLET PUNTATI DALL'UTENTE" (riferimenti non validi ignorati) e il nuovo messaggio.
- **Schema `CHAT_SCHEMA`:** `{reply: str, actions: [azione]}`. Ogni azione ha **tutti** i campi `type`, `profile_experience_id`, `bullet_id` (Sprint 69, al posto di `bullet_index`), `area_index`, `education_index`, `language_index`, `text`, `name`, `level` (nullable), senza `oneOf`. `type` ∈ `CHAT_ACTION_TYPES` (16 tipi, §15.3); `level` ∈ `elementary|intermediate|fluent|mother_tongue|null`. Gli indici partono da 0 e si riferiscono alla bozza inviata.
- **Filtro `_sanitize_actions`:** scarta i `toggle_skill`/`toggle_certification` con nomi non presenti nel profilo e gli `update_language_level` con livello non valido; dallo Sprint 69 anche le azioni su esperienze o bullet inesistenti, con indici di aree/istruzione/lingue fuori range o senza il testo richiesto. Allega `area_text` (testo dell'area al momento della proposta) alle azioni sulle aree.
- **Applicazione:** solo nel frontend (`applyChatAction` in `CvDraftEditorPage.jsx`), con le stesse funzioni dell'editor manuale, ritrovando bullet per `id` e aree per `area_text`; se l'elemento non c'è più l'azione non viene applicata e la decisione registrata è "rifiutata". Il server non scrive mai un'azione nel `content_json`. Le azioni salvate prima dello Sprint 69 ricevono alla prima lettura il `bullet_id` del bullet che occupa la loro posizione.
- **Persistenza:** `chat_history = [{role:"user", message}, {role:"assistant", message, actions:[{…, decision?}]}]`.
- **Costo e errori:** addebito di `PRICE_CV_DRAFT_CHAT_MESSAGE` in transazione prima della chiamata. Credito insufficiente → 402. Errore AI → rimborso, `RunLog` `cv_draft_chat` FAILURE e risposta 502.

---

## 14. Punti aperti e limiti noti

Osservazioni sul comportamento attuale del codice. Qui sono solo descritte, senza decisioni.

1. **Numerazione dei gap sfasata.** *Risolto nello Sprint 69: il prompt usa numeri e testo del pannello.* L'interfaccia numera i gap sull'elenco completo, mentre il prompt rinumera i soli gap selezionati, nell'ordine di clic. "Per il gap 2…" può indicare al modello un gap diverso da quello che l'utente vede come n. 2.
2. **Bozza non riseminata dopo "Rigenera CV".** *Risolto nello Sprint 69 (§15.1); docstring di `CVDraft` corretta.* La rigenerazione crea un nuovo `CVDocument`, ma "Modifica CV" riapre la bozza precedente, con chat e decisioni, perché il frontend crea la bozza solo se non esiste e nessun codice la aggiorna alla generazione. Il docstring di `CVDraft` descrive il contrario. Effetto: modifiche e finalizzazione partono dal contenuto vecchio.
3. **"Genera PDF finale" non attende il salvataggio automatico.** *Risolto nello Sprint 69, anche per la chat.* Il PDF finale usa la bozza salvata sul server: le modifiche dell'ultimo ~1,2 s (salvataggio non ancora partito) possono restare fuori. Allo stesso modo la chat lavora sulla bozza salvata, non sullo stato a schermo.
4. **Avviso ">5 esperienze" impreciso.** *Risolto nello Sprint 69.* Il testo dice "le più pertinenti per ciascuna offerta"; la regola reale tiene le 5 più recenti con al massimo uno swap (§5.4).
5. **Ordine dei bullet tra CV generato e bozza.** Nel PDF generato i bullet di ogni esperienza sono ordinati per rilevanza. In `content_json` restano nell'ordine restituito dall'AI. La prima anteprima dell'editor può quindi mostrare un ordine diverso dal PDF generato.
6. **`shown` dei bullet calcolato sul testo.** Due bullet con testo identico nella stessa esperienza risultano entrambi accesi o entrambi spenti. Le esperienze escluse dal cap hanno tutti i bullet accesi: accenderle nell'editor le mostra senza alcun taglio.
7. **Rank univoco solo per esperienza.** Il taglio globale e il ripiego confrontano rank di esperienze diverse come se fossero sulla stessa scala. A pari rank l'ordinamento stabile favorisce le esperienze più recenti nel taglio e toglie per primi i bullet delle più recenti nel ripiego.
8. **Minimo garantito additivo.** I 2 bullet garantiti si aggiungono al budget, quindi il totale può superare B. Il loop di ripiego può poi toglierli.
9. **Swap senza graduatoria.** `highly_relevant` è un sì/no: tra più escluse marcate vince sempre la più recente, non "la più rilevante".
10. **Allineamento per posizione AI ↔ profilo.** Località, date, tecnologie e `profile_experience_id` si riattaccano per indice. Se il modello restituisse meno esperienze del profilo, le ultime sparirebbero senza errore; se ne restituisse di più, la generazione fallirebbe. Lo schema non impone il numero.
11. **Vincoli solo nel prompt.** Il numero di aree (4–6), "mai più bullet del profilo", 1–2 keyword in grassetto e la lunghezza del sommario non sono controllati dal sistema. Anche il ruolo dell'esperienza è restituito dal modello, senza un vincolo esplicito di copia letterale.
12. **Multi-pagina silenzioso.** *Risolto nello Sprint 69: `page_count` e avviso all'utente.* Dopo 4 iterazioni il PDF può restare su più pagine. Lo segnala solo un `RunLog` con stato SUCCESS: l'utente se ne accorge solo aprendo il PDF o l'editor.
13. **Nome di ripiego = email dell'account.** Senza nome e cognome l'intestazione mostra l'email di login, che lo Sprint 41 aveva tolto apposta dalla riga contatti.
14. **Intestazione riletta dal profilo nella bozza.** Contatti e foto di un PDF finalizzato riflettono il profilo al momento della finalizzazione, non quello della generazione. La città resta quella tradotta salvata in bozza.
15. **Grounding non salvato per i PDF finalizzati.** `areas_of_expertise_grounding` è vuoto e le aree modificate a mano o via chat non hanno un riferimento di grounding.
16. **Indici della chat non validati lato server.** *Risolto nello Sprint 69 per i bullet (id stabili) e con validazione lato server di tutti i riferimenti; aree, istruzione e lingue restano per indice (§17.3).* Il riferimento ai bullet e gli indici delle azioni sono posizionali: riordinare o rimuovere bullet dopo una proposta può far applicare l'azione a un elemento diverso.
17. **Commenti e docstring superati nel codice.** `GenerationType.AUTOMATIC` mai usato; chiave di traduzione "data di fine obbligatoria" mai usata; `cv_parameters.py` cita ancora la v4 di questo documento.
18. **Test automatici dell'editor parziali.** Dallo Sprint 69 `apps/cv/test_sprint69.py` copre seed, risemina, finalizzazione, id stabili, filtro e contesto della chat, `bold_markup`; restano senza test l'anteprima e `record_action_decision`.
19. **Variabilità del modello.** A parità di profilo e job, testi, rank, marcature (quindi swap e taglio) possono cambiare tra due generazioni. È accettato.
20. **Costo e tempi per profili ricchi.** Il modello produce bullet per tutte le esperienze, anche quelle che il cap escluderà. Ogni iterazione di ripiego è un rendering WeasyPrint in più, dentro una richiesta HTTP sincrona. Impatto da monitorare.

---

*Fine del documento.*
