# Contenuto del CV generato — selezione, quantità, qualifica

> **Documento:** 03
> **Tipo:** documento di estensione/rettifica dei documenti madre
> **Versione:** 4 — chiude l'ambiguità sulla pipeline di generazione (calcolo bullet ed esperienze mostrate) e semplifica il meccanismo di swap e il loop di overflow, in ottica di manutenibilità.
> **Stato:** attivo
> **Documenti madre (congelati):** `01-specifiche-funzionali-v5.md`, `02-specifiche-tecniche-v4.md`
> **Precedenza:** in caso di conflitto **sul contenuto del CV generato**, prevale il presente documento. Su ogni altro tema prevalgono i documenti madre.
> **Ambito:** definisce *cosa* compare nel CV generato per un dato job, *con quali regole* se ne determinano quantità e selezione, e *come* la pipeline lo realizza. Non tratta il layout grafico dei template, né la scelta 1 vs 2+ pagine (fuori scope, §9).
>
> **Struttura del documento:** **Parte I** — specifiche funzionali (cosa fa). **Parte II** — specifiche tecniche (come è realizzato). La sezione **§0** dichiara esattamente cosa questo documento emenda dei documenti madre.
>
> **Nota di versione (v4).** Rispetto alla v3, questa revisione risolve un'ambiguità logica identificata in fase di revisione: la v3 calcolava le quantità (incluso il budget bullet per esperienza) *prima* della chiamata AI, ma la selezione finale delle 5 esperienze mostrate dipendeva da marcature di rilevanza restituite *nella stessa chiamata* — un cerchio che non si chiudeva. Le decisioni prese:
> 1. **Il modello riceve sempre tutte le esperienze del profilo**, non solo le 5 provvisorie, e produce bullet e marcatura di rilevanza per ciascuna. Selezione (swap) e taglio al budget avvengono **dopo**, lato server, sui risultati completi. *(Vedi §5.4, §11.)*
> 2. **Eliminata la formula di peso "recenza + durata"** come calcolo separato a monte. Il taglio dei bullet — sia per rientrare nel budget B sia in caso di overflow da impaginazione — usa **un unico meccanismo**: l'ordinamento di rilevanza restituito dal modello. *(Vedi §5.4, §11, §12.)*
> 3. **Swap esperienze: singolo, non multiplo.** Se il profilo ha più di 5 esperienze, al massimo **una** esclusa (la più rilevante, se marcata "altamente rilevante") può sostituire la meno recente tra le 5 selezionate. A parità di rilevanza tra più escluse, vince la **più recente**. *(Sostituisce il meccanismo di swap multipli della v3 — vedi §5.4.)*
> 4. **Loop di ripiego per overflow: tetto massimo di 4 iterazioni.** Rimozione di un bullet alla volta (il meno rilevante), con rirenderizzazione a ogni passo, fino a un massimo di 4 tentativi; oltre, si accetta il caso residuale già previsto (PDF multi-pagina, nessun errore mostrato). *(Vedi §6, §11, §12.)*
>
> Budget B (tabella 12/10/9) e minimo bullet garantito (1–2) restano **confermati** invariati rispetto alla v3.

---

## 0. Cosa emenda dei documenti madre

Elenco dichiarativo di ciò che questo documento **modifica, sostituisce o aggiunge** rispetto a `01-specifiche-funzionali-v5.md` e `02-specifiche-tecniche-v4.md`. Dove indicato "sostituisce", il testo del documento madre va letto come superato.

| # | Doc madre | Punto | Natura | Cosa cambia |
|---|---|---|---|---|
| 1 | 01 | §4.1 (profilo master) | **Sostituisce** | La sezione "risultati chiave" **non esiste più** nel profilo master. Le sezioni sono cinque: sommario, esperienze, istruzione, competenze/certificazioni, lingue. *(Vedi §5.3.)* |
| 2 | 01 | §4.1 (completezza profilo) | **Aggiunge** | Vincoli minimi: **almeno 1 voce di istruzione** obbligatoria, con **data di fine obbligatoria**; le **esperienze possono essere 0**. *(Vedi §3.1, §3.2.)* |
| 3 | 01 | §4.7 ("mantiene invariata la sezione istruzione") | **Precisa** | L'istruzione resta **non riformulata dall'AI**, ma è soggetta a **selezione** (max 3 voci più recenti, con tie-break). "Invariata" va letto come "non riformulata". *(Vedi §3.2.)* |
| 4 | 01 | §4.7 (contenuto del CV) | **Aggiunge** | Nuovo elemento del CV: la **qualifica professionale** sotto il nome, calcolata a ogni generazione. *(Vedi §5.1.)* |
| 5 | 01 | §4.7 (contenuto del CV) | **Aggiunge** | Regole deterministiche sulle quantità: max 5 esperienze mostrate, budget bullet calcolato dal sistema, max 3 voci di istruzione. *(Vedi §5.4.)* |
| 6 | 01 | §4.8 (arricchimento) | **Sostituisce** | L'arricchimento **non** è più un dettaglio libero: può solo aggiungere attività/progetti **agganciati a un'esperienza già presente** nel profilo. Ha inoltre **priorità massima di inclusione** nel CV per cui è inserito. *(Vedi §5.6.)* |
| 7 | 02 | §4.2 (`Profile`) | **Sostituisce** | Il campo `key_achievements` è **rimosso** dal modello dati. *(Vedi §10.1.)* |
| 8 | 02 | §4.2 (`Education`) | **Sostituisce** | Il campo libero `dates` è sostituito da `start_date` (opzionale) ed `end_date` (**obbligatorio, non nullable**). *(Vedi §10.1.)* |
| 9 | 02 | §6.2 (pipeline di generazione) | **Sostituisce** | La pipeline è riscritta: il modello riceve tutte le esperienze in un'unica chiamata; selezione (swap singolo) e taglio bullet avvengono dopo, lato server, su un unico criterio di rilevanza. *(Vedi §11.)* |
| 10 | 02 | §11.4 (garanzia "1 pagina", punto aperto) | **Chiude** | La strategia di compattamento è ora definita: 3 livelli progressivi + loop di ripiego (max 4 iterazioni) + comportamento residuale silenzioso. *(Vedi §6, §11.)* |

**Nessuna migrazione dati.** L'app è in fase di test senza profili da preservare: i vincoli introdotti da questo documento (es. `end_date` obbligatorio) si applicano da subito, senza logica di retrocompatibilità.

---

# PARTE I — SPECIFICHE FUNZIONALI

## 1. Obiettivo e contesto

Il CV generato combina profilo master + job description, entro il vincolo di **1 pagina** (punto fermo per l'MVP). Con profili utente di ricchezza molto variabile, servono regole esplicite e verificabili su: quante esperienze compaiono, quanti bullet per esperienza, quanto spazio occupa l'istruzione, come si comportano i casi limite (profilo scarno, profilo molto ricco), e come si genera la riga di **qualifica professionale** sotto il nome.

**Vincoli non negoziabili confermati:**
- **Grounding.** Il modello AI non inventa mai esperienze, competenze o risultati assenti dal profilo. Riformulare, riordinare, enfatizzare, tradurre: sì. Aggiungere: no. (Unica estensione controllata: la sintesi per astrazione delle Areas of Expertise, §5.3.)
- **Indipendenza dal template.** Il contenuto del CV (numero di esperienze, numero di bullet, voci mostrate) dipende **esclusivamente** da profilo + job. Cambiare template cambia solo l'aspetto grafico, mai il contenuto. Ogni template deve ospitare in 1 pagina qualunque contenuto la pipeline possa legittimamente produrre (§7).
- **1 pagina.** Il CV resta di 1 pagina. La scelta 1 vs 2+ pagine è rimandata (§9).

## 2. Principio cardine: le quantità le decide il sistema, i contenuti il modello

Per garantire che lo stesso profilo produca CV **coerenti e riproducibili** nella struttura (non "a volte densi, a volte scarni" a discrezione del modello), la responsabilità è divisa così:

- **Il sistema** calcola, con regole deterministiche, i **tetti**: quante voci di istruzione mostrare, il budget totale di bullet (B), quante esperienze possono al massimo comparire (5).
- **Il modello AI** decide i **contenuti** entro quei tetti: quali bullet selezionare e come riformularli per ciascuna esperienza del profilo, le Areas of Expertise, la qualifica professionale, il sommario — e **restituisce un ordinamento di rilevanza** per ogni esperienza e per ogni bullet rispetto al job.
- **Il sistema applica quell'ordinamento**, dopo la risposta del modello, per selezionare quali esperienze mostrare (entro il cap di 5, con eventuale swap — §5.4) e per tagliare i bullet fino al budget B. **Lo stesso ordinamento di rilevanza è anche l'unico criterio usato dal loop di ripiego in caso di overflow (§6)**: un solo meccanismo di taglio, riusato in due momenti della pipeline.

Non vengono poste domande preliminari all'utente per dimensionare il CV: il budget si calcola **dai dati reali inseriti nel profilo**. I testi di guida alla compilazione (§3.3) orientano l'utente su cosa inserire.

## 3. Vincoli di input al profilo master

Le regole di generazione si appoggiano a vincoli applicati **a monte**, in fase di compilazione del profilo. Questi vincoli garantiscono che il contenuto massimo producibile sia noto e che ogni template possa garantire la pagina singola (§7).

### 3.1 Esperienze lavorative
- L'utente può inserire nel profilo master **un numero libero di esperienze**, incluso **zero** (caso legittimo, tipicamente il neolaureato senza esperienza professionale — vedi anche §8).
- Se le esperienze inserite sono **più di 5**, l'app **avvisa l'utente** che il CV generato ne mostrerà al massimo 5 (testo esatto da definire — §14). L'avviso compare alla compilazione del profilo e resta visibile finché la condizione persiste.
- Ogni esperienza ha un numero massimo di bullet inseribili nel profilo (parametro, indicativo: **8 bullet per esperienza**) e un limite di lunghezza per bullet (parametro, indicativo: **200 caratteri**).

### 3.2 Istruzione
- La sezione istruzione **non viene riformulata dall'AI**: è un dato fattuale (istituto, titolo, date) che deve restare esatto. La sua gestione è interamente a **vincoli di input**:
  - **almeno 1 voce di istruzione è obbligatoria** per considerare il profilo master completo (a differenza delle esperienze, che possono essere zero — §3.1, §8);
  - **la data di fine di ogni voce di istruzione è un campo obbligatorio** (non può essere lasciata vuota);
  - limite di voci di istruzione mostrate nel CV: **le 3 più recenti** (parametro `EDU_MAX_SHOWN`, indicativo: 3); le eventuali voci eccedenti restano nel profilo ma sono omesse dal CV;
  - limite di caratteri per i campi di ogni voce (parametri, valori esatti da definire — §14), per impedire voci che da sole squilibrino la pagina.
- **Criterio di selezione/ordinamento delle voci più recenti (tie-break):**
  1. si ordina per **data di fine** decrescente;
  2. a parità di data di fine, si preferisce la voce di **durata minore** (tipicamente un titolo più breve e specialistico rispetto a un percorso lungo con la stessa data di fine);
  3. se anche la durata è identica, la scelta tra le voci a pari merito è **casuale**.
- Nessuna chiamata al modello AI per questa sezione: si copia dal profilo, entro i limiti sopra.

### 3.3 Testi di guida alla compilazione
In fase di compilazione del profilo, l'app mostra indicazioni del tipo:
- *"Inserisci solo le esperienze rilevanti per il tipo di lavoro che cerchi. Considera due esperienze diverse se, nella stessa azienda, hai cambiato completamente mansione. Se inserisci più di 5 esperienze, il CV ne mostrerà al massimo 5 (il CV a 2 pagine arriverà in futuro)."*
- Indicazioni analoghe sulla sintesi dei bullet e delle voci di istruzione.

I testi esatti sono da definire (§14); qui si fissa il **principio**: la guida sostituisce le domande preliminari, evitando una doppia fonte di verità tra risposte dell'utente e dati del profilo.

## 4. Struttura del CV generato

Il CV generato contiene, nell'ordine, le seguenti sezioni (il layout — posizioni, colonne, stili — è demandato ai template):

1. **Intestazione:** nome, contatti, città, link LinkedIn, foto (se opzione attiva) e **qualifica professionale** (§5.1).
2. **Sommario professionale** riformulato per il job (regola dei documenti madre, invariata).
3. **Areas of Expertise** (§5.3) — sostituisce nel CV il paragrafo finora chiamato "risultati chiave".
4. **Esperienze lavorative** (§5.4).
5. **Istruzione** (§3.2).
6. **Skills & Certificazioni** (§5.5).
7. **Lingue** — copiate dal profilo, senza selezione né riformulazione (sezione a lunghezza trascurabile).

**Lingua delle etichette di sezione.** Le etichette fisse ("Areas of Expertise", "Certified in", "Skilled in" e analoghe) **seguono `cv_language_mode`** come tutto il resto del contenuto del CV: non restano fisse in inglese quando il CV è generato nella lingua della job description.

## 5. Regole di generazione, sezione per sezione

### 5.1 Qualifica professionale (nuovo elemento, calcolato per CV)

Sotto il nome dell'utente compare una riga con la **qualifica professionale generalizzata** relativa al job.

- **Non è un campo del profilo master:** viene calcolata **a ogni generazione**, dal modello AI, con lo stesso grounding sul job usato per gli altri contenuti del CV.
- **Regola di generalizzazione:** dal titolo del job posting si estrae il **nome del ruolo**, spogliato di specifiche tecnologiche, di progetto o di contesto. Esempio: *"Software Engineer for SSH/AWS and ERP systems"* → **"Software Engineer"**.
- **Brevità:** la qualifica è il nome del ruolo, tipicamente 2–4 parole, senza parentesi, elenchi di tecnologie o dettagli dell'annuncio.
- **Seniority:** se il titolo del job la contiene (Senior, Junior, Lead, ecc.), la qualifica la **mantiene** (*"Senior Software Engineer"*).
- **Titolo già generico:** se il titolo del job è già un nome di ruolo pulito, si usa **così com'è**.
- **Titolo ambiguo o multi-ruolo:** se dal titolo non è ricavabile un ruolo univoco, la qualifica è quella dell'**esperienza professionale più recente** del profilo dell'utente. **Se il profilo non ha esperienze** (caso neolaureato), si usa comunque il titolo del job "ripulito", come nel caso non ambiguo — non si tenta un fallback sull'istruzione (§8).
- **Lingua:** la qualifica segue la **lingua del CV** (opzione utente esistente: inglese / lingua della job description).

### 5.2 Sommario professionale
Regola dei documenti madre confermata: riformulato dal modello per il job, grounding sul profilo, lunghezza controllata dal prompt. Nessuna modifica in questo documento.

### 5.3 Areas of Expertise

- **Natura: soft skill / aree funzionali-trasversali** (es. leadership, stakeholder management, problem solving) — per costruzione **distinte** dalle hard skill elencate in "Skilled in" (§5.5): le due sezioni non devono sovrapporsi.
- **Non è un campo del profilo master.** Non esiste alcuna sezione del profilo che l'utente compila per alimentarla: è **sempre e solo** contenuto calcolato dal modello a ogni generazione, da esperienze e bullet reali. *(Emenda 01 §4.1 — vedi §0, riga 1.)*
- **Formato:** tra **4 e 6 voci** (target 6, disposte dal template su due colonne da 3; con 4–5 voci il template gestisce il layout asimmetrico con grazia — §7), ciascuna di **una riga**.
- **Generazione:** il modello AI le produce dal **match tra profilo e job description**.
- **Licenza di astrazione (delimitazione del grounding):** per questa sezione il modello può **sintetizzare ed etichettare** — coniare il nome di un'area raggruppando competenze ed esperienze **realmente presenti** nel profilo (es. bullet su coordinamento di team cross-funzionali → *"Cross-functional Team Leadership"*, anche se la frase non compare testualmente nel profilo). Ogni area deve restare **riconducibile a contenuti reali del profilo**; è **vietato** dedurre competenze dalla sola job description. Il grounding resta intatto: qui il modello lavora per astrazione, non per copia.
- **Grounding verificabile.** Per ogni area prodotta, il modello restituisce anche un **riferimento interno** (non visibile nel CV finale) al bullet o all'esperienza del profilo da cui l'area deriva. Rende il grounding controllabile in fase di test/tuning (dettaglio tecnico in §13).
- **Profilo scarno:** la sezione **non è mai omessa** e non scende mai sotto **4 voci**. Se il profilo non offre materiale sufficiente a fondare 6 aree distinte, il modello sintetizza fino a raggiungere il minimo di 4, riformulando/riguardando gli stessi bullet o esperienze da angolazioni diverse (più aree possono derivare, per astrazione, dallo stesso contenuto reale). Resta vietato dedurre competenze dalla sola job description.

### 5.4 Esperienze lavorative

> **Aggiornato in v4** — vedi nota di versione in apertura. Il modello riceve e produce contenuto per **tutte** le esperienze del profilo; la selezione (cap a 5, swap) e il taglio dei bullet al budget B avvengono **dopo**, lato server, sull'ordinamento di rilevanza restituito.

**Cap: massimo 5 esperienze nel CV.**
- Se il profilo ha **≤ 5 esperienze**, compaiono tutte.
- Se il profilo ha **più di 5 esperienze**, il CV mostra le **5 più recenti**, con un'eccezione a **swap singolo**: se tra le esperienze escluse ce n'è almeno una marcata dal modello come **altamente rilevante** per il job, la **più rilevante tra le escluse** sostituisce la **meno recente** tra le 5 selezionate. **Non sono ammessi swap ulteriori**: al massimo un'esperienza esclusa entra al posto di una selezionata, indipendentemente da quante altre escluse siano marcate rilevanti.
  - **Tie-break:** se più esperienze escluse sono marcate "altamente rilevanti" con pari punteggio, vince la **più recente** tra loro.
- L'utente è stato avvisato in fase di profilo (§3.1) della possibilità che non tutte le esperienze inserite compaiano nel CV.

**Ordinamento:** sempre **cronologico inverso** (dalla più recente), qualunque sia la rilevanza. La rilevanza governa la ricchezza (bullet) e l'eventuale swap, non la posizione in lista.

**Budget complessivo di bullet.**
- Il numero totale di bullet disponibili per le esperienze mostrate (**budget B**) è calcolato dal sistema **a partire dallo spazio occupato dall'istruzione**: più voci di istruzione mostrate, meno bullet disponibili. Tabella parametrica (valori **indicativi, da calibrare** — §14):
  - 1 voce di istruzione → B = 12
  - 2 voci → B = 10
  - 3 voci → B = 9

**Come si arriva al budget effettivo per esperienza.**
- Il modello scrive bullet riformulati per **tutte** le esperienze del profilo (fino al massimo che l'utente ha inserito per ciascuna) e restituisce, per ogni bullet, un **ordinamento di rilevanza** rispetto al job.
- Il sistema, **dopo** la risposta del modello: (1) applica il cap a 5 esperienze con l'eventuale swap singolo sopra descritto; (2) tra i bullet delle sole esperienze mostrate, **tiene i B globalmente più rilevanti** secondo l'ordinamento restituito, scartando gli altri.
- **Riga singola:** un'esperienza mostrata che non riceve alcun bullet nel taglio compare come **riga singola** (azienda, ruolo, località, date, nessun bullet). È il destino tipico dell'esperienza più vecchia e poco rilevante. Se però il modello la marca come **altamente rilevante** per il job, le è garantito un minimo di bullet (parametro, indicativo: **1–2**), sottratti al taglio globale (cioè scalati dai bullet altrimenti più rilevanti di altre esperienze).
- **Grounding sulle quantità:** un'esperienza non può ricevere più bullet di quanti l'utente ne abbia scritti per essa (limite già rispettato in fase di generazione dal modello).

### 5.5 Skills & Certificazioni

- **Natura: hard skill** (strumenti, tecnologie, metodologie tecniche) — espresse **letteralmente** dal profilo, per costruzione distinte dalle Areas of Expertise (§5.3), che sono soft skill astratte.
- Paragrafo unico, **due righe**:
  - **Certified in:** — certificazioni selezionate dal profilo, una riga;
  - **Skilled in:** — competenze selezionate dal profilo, una riga.
- Se l'utente **non ha certificazioni**, compare la sola riga **Skilled in**.
- La selezione (quali voci, in che ordine) è del modello, per rilevanza rispetto al job, con grounding pieno (solo voci presenti nel profilo). Ogni riga deve restare **una riga** nel rendering (vincolo di lunghezza controllato in generazione).

### 5.6 Arricchimento mirato del profilo

> **Sostituisce §4.8 di `01-specifiche-funzionali-v5.md`** (vedi §0, riga 6).

- Prima di generare **o rigenerare** un CV, l'utente può aggiungere un dettaglio (nuove attività/progetti) **agganciato a un'esperienza già presente nel profilo master**. L'arricchimento **non può** introdurre un'esperienza (azienda/ruolo) del tutto assente dal profilo.
- Il testo mostrato inquadra l'aggiunta come attività reale precedentemente omessa; la responsabilità di veridicità è dell'utente.
- Al momento dell'inserimento, l'app chiede se salvare il dettaglio **anche nel profilo master** (agganciato alla stessa esperienza, per i job futuri) o solo per quel CV.
- **Priorità di inclusione.** Il contenuto di arricchimento inserito per il CV corrente ha **priorità massima di inclusione**: è protetto sia dal taglio al budget B (§5.4) sia dal loop di ripiego per overflow (§6) — è tra gli ultimi bullet a essere rimossi in entrambi i casi. Se l'utente lo salva anche nel profilo master, nei CV **successivi** è trattato come contenuto normale, senza priorità.
- L'arricchimento **non ricalcola il punteggio** del job e **non sblocca** la generazione automatica per job sotto soglia.

## 6. Overflow: compattamento e loop di ripiego

> **Aggiornato in v4:** il loop di ripiego ha ora un **tetto massimo di 4 iterazioni** — vedi nota di versione in apertura.

Ordine di intervento quando il contenuto eccede la pagina:

1. **Compattamento progressivo:** 3 livelli di riduzione di font/margini.
2. **Loop di ripiego:** se anche il livello 3 eccede la pagina, il sistema **rimuove il bullet globalmente meno rilevante** (secondo l'ordinamento di rilevanza restituito dal modello, §2) e rirenderizza; ripete finché il CV entra in 1 pagina, **fino a un massimo di 4 iterazioni**. Un'esperienza che perde tutti i bullet degrada a **riga singola** (§5.4).
3. **Esaurimento (caso residuale):** se dopo **4 iterazioni** del loop il CV eccede ancora la pagina — con i vincoli di input (§3) e il budget (§5.4) non dovrebbe essere il caso comune — il sistema **si ferma** e salva comunque il PDF **multi-pagina, senza errore mostrato all'utente**, con **tracciamento dell'evento nel `RunLog`** lato backend per diagnosi. Nessun messaggio di fallimento generazione per questo caso.

**Protezione dell'arricchimento:** i bullet derivanti da un arricchimento per il CV corrente (§5.6) sono **gli ultimi** a essere rimossi dal loop.

## 7. Contratto dei template

Ogni template (attuale e futuro) deve rispettare questo contratto, **verificabile**:

- **Nessuna influenza sul contenuto.** Il template riceve il contenuto già deciso dalla pipeline e lo impagina; non può alterare numero di esperienze, bullet o voci.
- **Garanzia 1 pagina sul caso peggiore — due profili di collaudo.** Non esiste un unico scenario che massimizzi contemporaneamente il budget di bullet (B) e l'ingombro dell'istruzione (le due grandezze sono inversamente legate, §5.4). Si definiscono quindi **due profili di collaudo "worst case"**, **entrambi** obbligatori come test di accettazione di ogni template:
  - **Worst case A (max bullet):** 1 voce di istruzione al limite di caratteri (B = 12), 5 esperienze con budget pieno secondo il taglio per rilevanza, 6 Areas of Expertise, 2 righe Skills & Certificazioni, sezione lingue.
  - **Worst case B (max istruzione):** 3 voci di istruzione al limite di caratteri (B = 9), 5 esperienze con budget pieno, 6 Areas of Expertise, 2 righe Skills & Certificazioni, sezione lingue.

  Un template è accettato solo se **entrambi** i profili entrano in 1 pagina, entro i 3 livelli di compattamento (§6).
- **Gestione con grazia dei casi scarni:** assenza di foto (opzione off), zero o poche esperienze (§3.1, §8), sezione Areas of Expertise ridotta a 4 voci, riga Certified in assente. Nessuno di questi casi deve produrre layout rotti o spazi anomali.

## 8. Casi limite

- **Profilo molto ricco (>5 esperienze, molti bullet).** Il CV mostra 5 esperienze (regola di selezione §5.4, con al massimo **uno** swap per rilevanza), i bullet sono limitati dal budget, l'utente è avvisato a monte. Nessun contenuto viene inventato né perso dal profilo: ciò che non entra nel CV resta nel master.
- **Profilo scarno (es. 1 esperienza, 2 bullet).** Il CV risulta **visivamente leggero**: è accettato. Il grounding vieta di "riempire"; i template devono impaginare con grazia anche questo caso (§7). Nessun contenuto di riempimento generato.
- **Profilo senza esperienze (caso neolaureato).** Ammesso esplicitamente (§3.1): il profilo master richiede solo almeno 1 voce di istruzione, non esperienze. Il CV omette semplicemente la sezione "Esperienze lavorative" (o la mostra vuota, dettaglio di template); l'intero budget B resta inutilizzato. Nessun errore, nessun contenuto generato per riempire lo spazio.
- **Stesso profilo, job diversi.** La **struttura** del CV (numero di esperienze, voci di istruzione) è **identica** a parità di profilo, perché governata da tetti calcolati deterministicamente dal sistema; varia la **selezione/riformulazione dei contenuti** (bullet inclusi, eventuale swap) in funzione della rilevanza che il modello attribuisce a quel job specifico. È il livello di coerenza richiesto.
- **Titolo del job ambiguo:** qualifica dall'esperienza più recente (§5.1). **Se non esistono esperienze (neolaureato), si usa comunque il titolo del job "ripulito"** (stessa regola del caso non ambiguo), senza tentare una generalizzazione basata su istruzione o esperienza pregressa.
- **Nessuna certificazione:** sola riga Skilled in (§5.5).

## 9. Fuori scope

1. **Scelta 1 vs 2+ pagine.** Il CV resta di 1 pagina; l'opzione a 2 pagine (che tra l'altro consentirà più di 5 esperienze mostrate) è un'evoluzione futura. Il cap a 5 e l'avviso di §3.1 sono già coerenti con quell'evoluzione.
2. **Layout grafico dei singoli template.**
3. **Modifica delle altre sezioni del profilo master.** Restano quelle dei documenti madre (sommario, esperienze, istruzione, competenze/certificazioni, lingue); questo documento tocca solo la rimozione di "risultati chiave" (§0, riga 1). Per il resto cambia solo cosa/quanto ne finisce nel CV.
4. **OCR, editor in-app, Word** e ogni altra esclusione già a verbale nei documenti madre.

---

# PARTE II — SPECIFICHE TECNICHE

> Questa parte descrive come la Parte I è realizzata. Vale solo per i punti toccati da questo documento: tutto ciò che non è qui esplicitato resta come da `02-specifiche-tecniche-v4.md`.

## 10. Modello dati — delta rispetto al documento madre

### 10.1 Modifiche a `Profile` e sezioni collegate

Rispetto a `02-specifiche-tecniche-v4.md` §4.2:

- **`Profile`** — `user`, `summary`, `photo`. **Il campo `key_achievements` è rimosso.** Non esiste alcun campo persistito corrispondente alle Areas of Expertise: sono contenuto calcolato a ogni generazione (§5.3).
- **`Experience`** — invariato nei campi (`profile`, `company`, `role`, `location`, `start_date`, `end_date`, `bullets`, `technologies`), con due vincoli applicativi espliciti: numero massimo di bullet per esperienza (parametro, indicativo 8) e lunghezza massima per bullet (parametro, indicativo 200 caratteri). **Nessun limite** al numero di esperienze inseribili (0 o più ammesse); superate le 5, l'app mostra l'avviso di §3.1.
- **`Education`** — il campo libero `dates` è **sostituito** da:
  - `start_date` — opzionale, nullable;
  - `end_date` — **obbligatorio, non nullable** (necessario per il tie-break di selezione, §3.2);
  - restano `profile`, `institution`, `title`, `location`, `notes`, con limiti di lunghezza per campo (parametri da definire — §14).
- **`Skill` / `Certification`** — invariati; alimentano rispettivamente le righe "Skilled in" e "Certified in" del CV (§5.5).
- **`Language`** — invariato.

### 10.2 Validazione del profilo

Il profilo è considerato **completo** (quindi generabile) solo se:
- esiste **almeno 1 record `Education`** con `end_date` valorizzata;
- il numero di record `Experience` è **0 o più** (nessun minimo).

La validazione è applicata in onboarding e a ogni salvataggio del profilo.

### 10.3 Migrazione

**Nessuna migrazione dati.** L'app è in fase di test senza profili da preservare: i nuovi vincoli si applicano da subito, senza logica di retrocompatibilità né gestione di dati legacy.

## 11. Pipeline di generazione del CV

> **Sostituisce `02-specifiche-tecniche-v4.md` §6.2 e la Parte II §11 della v3 di questo documento.** Riscritta per chiudere l'ambiguità sulla circolarità tra selezione delle esperienze e generazione dei contenuti (vedi nota di versione in apertura).

1. **Raccolta contesto.** Profilo master strutturato dell'utente (§10.1), **con tutte le esperienze**, indipendentemente dal fatto che superino il cap di 5 — la selezione avviene dopo (punto 4) — + descrizione del job + (opzionale) dettaglio di arricchimento (§5.6).

2. **Calcolo deterministico dei tetti (lato server, prima della chiamata AI).** Solo grandezze indipendenti dal contenuto prodotto dal modello:
   - **Voci di istruzione da mostrare:** le 3 più recenti (`EDU_MAX_SHOWN`), con tie-break su data di fine → durata minore → casuale (§3.2). Non richiede il modello.
   - **Budget bullet totale (B):** determinato dal numero di voci di istruzione mostrate secondo la tabella parametrica (1→12, 2→10, 3→9). Non richiede il modello.
   - **Nessun calcolo di budget per singola esperienza** avviene in questo passo: la ripartizione tra esperienze è governata unicamente dalla rilevanza restituita dal modello (punto 3) e applicata dopo (punto 4).

3. **Chiamata a Claude per i contenuti.** Il modello riceve i dati reali dell'utente — **tutte le esperienze del profilo**, non solo un sottoinsieme provvisorio —, il job, e i tetti calcolati al punto 2 (voci di istruzione, B). Produce:
   - sommario riformulato;
   - **qualifica professionale** (§5.1);
   - per **ciascuna esperienza** del profilo (fino al massimo di bullet che l'utente vi ha inserito): bullet riformulati e un **ordinamento di rilevanza** rispetto al job, sia a livello di esperienza sia di singolo bullet;
   - marcatura delle esperienze come **"altamente rilevanti"**, dove pertinente (usata al punto 4 per lo swap);
   - **Areas of Expertise** (4–6 voci, ciascuna con riferimento interno di grounding — §5.3, §13);
   - selezione di Skills/Certificazioni (letterali dal profilo — §5.5).

   Regole di grounding invariate rispetto ai documenti madre: non inventare nulla fuori dal profilo (eccetto la sintesi per astrazione delle Areas of Expertise), tradurre sì, rispettare i limiti di lunghezza. **Una sola chiamata AI per questi contenuti** (nessuna chiamata separata per la sola marcatura di rilevanza).

4. **Selezione e taglio (lato server, dopo la chiamata AI, senza nuova chiamata AI).**
   - **Cap esperienze:** se il profilo ha ≤5 esperienze, si tengono tutte. Se >5, si tengono le 5 cronologicamente più recenti; se tra le escluse ce n'è almeno una marcata "altamente rilevante", la **più rilevante tra le escluse** (tie-break: la più recente a parità di rilevanza) sostituisce la **meno recente** tra le 5 — **un solo swap, mai più di uno** (§5.4).
   - **Taglio bullet al budget B:** tra i bullet delle sole esperienze mostrate, si tengono i **B globalmente più rilevanti** secondo l'ordinamento del punto 3, scartando gli altri. Un'esperienza mostrata senza bullet residui diventa riga singola, salvo minimo garantito (1–2 bullet, parametro) se marcata "altamente rilevante" — sottratto al taglio globale.
   - I bullet di arricchimento (§5.6) sono **esclusi da questo taglio** (protetti, priorità massima).

5. **Composizione HTML.** I contenuti selezionati si inseriscono nel template HTML: un ciclo ripete il blocco "esperienza"; la sezione **istruzione** è copiata senza riformulazione dal profilo, limitata alle voci selezionate al punto 2; la foto è inclusa solo se l'utente ha attivato l'opzione; le etichette di sezione seguono `cv_language_mode` (§4).

6. **Controllo "1 pagina" e loop di ripiego.** WeasyPrint verifica il numero di pagine risultanti. In caso di overflow:
   - **(a)** 3 livelli di compattamento progressivo (font/margini);
   - **(b)** se ancora in overflow, **loop di ripiego**: rimozione meccanica lato server di un bullet alla volta — il globalmente meno rilevante secondo l'ordinamento del punto 3, tra quelli sopravvissuti al taglio del punto 4 —, con rirenderizzazione a ogni rimozione, **fino a un massimo di 4 iterazioni**. I bullet di arricchimento sono protetti e rimossi per ultimi (§5.6);
   - **(c)** caso residuale: se dopo 4 iterazioni il contenuto eccede ancora, si **interrompe il loop** e si salva comunque il PDF multi-pagina senza errore, con evento tracciato in `RunLog` (§6).

7. **PDF.** WeasyPrint converte l'HTML in PDF — unico formato di output nell'MVP.

8. **Salvataggio.** HTML e PDF finiscono in `CVDocument`; il job passa a `cv_generated`.

**Nota implementativa.** Qualifica professionale, Areas of Expertise, bullet e riferimenti di grounding sono prodotti **nella stessa chiamata AI** (punto 3), per coerenza di grounding sul job e per evitare round-trip aggiuntivi. Tutto ciò che segue (selezione, taglio, loop di overflow) è **meccanico lato server**, senza ulteriori chiamate AI: usa solo l'ordinamento di rilevanza già restituito al punto 3. Questo significa che, per profili con più di 5 esperienze, il modello produce bullet anche per esperienze che potrebbero risultare escluse dal cap: è un costo accettato in cambio di una pipeline a una sola chiamata (vedi nota di versione).

## 12. Parametri di configurazione

Tutti i valori seguenti sono **parametri di configurazione applicativa**, modificabili senza toccare la logica (stessa natura dei prezzi del credito in `02-specifiche-tecniche-v4.md` §8.5). Valori indicativi, da calibrare in test (§14):

| Parametro | Valore indicativo | Dove agisce |
|---|---|---|
| `EDU_MAX_SHOWN` | 3 | Voci di istruzione mostrate nel CV (§3.2) |
| Tabella budget B | 1 voce → 12; 2 → 10; 3 → 9 | Budget bullet totale (§5.4) |
| Minimo bullet garantito | 1–2 | Esperienza vecchia ma altamente rilevante (§5.4) |
| Max bullet per esperienza | 8 | Vincolo di input al profilo (§3.1) |
| Lunghezza max bullet | 200 caratteri | Vincolo di input al profilo (§3.1) |
| Limiti caratteri campi istruzione | da definire | Vincolo di input al profilo (§3.2) |
| Areas of Expertise | min 4, max 6 | Generazione (§5.3) |
| Cap esperienze mostrate | 5 | Selezione (§5.4) |
| `MAX_OVERFLOW_ITERATIONS` *(nuovo, v4)* | 4 | Tetto massimo di iterazioni del loop di ripiego (§6, §11.6) |

> **Nota (v4).** La riga "Formula peso esperienza" presente in v3 è **rimossa**: la ripartizione dei bullet tra esperienze non usa più una formula di peso calcolata a monte, ma il solo ordinamento di rilevanza restituito dal modello (§5.4, §11).

## 13. Grounding verificabile delle Areas of Expertise

Il riferimento interno di provenienza (bullet o esperienza) che il modello restituisce per ogni area (§5.3) va **salvato come dato intermedio della generazione**. Non richiede una nuova tabella: può stare nei dati di lavorazione del task Celery o in un campo JSON di servizio su `CVDocument`.

Serve alla **diagnosi in fase di tuning del prompt** — verificare che le aree prodotte siano effettivamente riconducibili a contenuto reale del profilo e non dedotte dalla job description. Non è mai esposto all'utente né stampato nel CV.

---

## 14. Punti da verificare in revisione

1. **Valori numerici dei parametri.** Tutti i valori della tabella §12 vanno calibrati in test: budget B per numero di voci di istruzione (12/10/9), max bullet per esperienza (8) e lunghezza bullet (200), `EDU_MAX_SHOWN` (3), minimo garantito all'esperienza vecchia ma rilevante (1–2), limiti di caratteri dei campi istruzione, tetto di iterazioni del loop di ripiego (4).
2. **Testi da definire:** avviso ">5 esperienze" (§3.1), testi di guida alla compilazione (§3.3).
3. **Variabilità residua del modello.** A parità di profilo+job i tetti (B, cap esperienze, voci istruzione) sono deterministici, ma i **testi** generati e l'ordinamento di rilevanza possono variare tra due chiamate (natura del modello) — con effetto anche su quale esperienza entra via swap in casi borderline. Accettato; a verbale.
4. **Rilevanza "alta" come giudizio del modello.** Lo swap singolo (§5.4) e il minimo garantito all'esperienza vecchia dipendono da una marcatura di rilevanza prodotta dal modello: il criterio va reso il più possibile stabile via prompt (es. soglia esplicita, definizione operativa di "altamente rilevante"), da mettere a punto in tuning.
5. **Costo/token per profili con più di 5 esperienze.** Con la pipeline a una sola chiamata (§11), il modello produce bullet anche per le esperienze che risulteranno escluse dal cap. Da monitorare in test l'impatto su costo e tempo di risposta per profili molto ricchi (es. 10+ esperienze), e valutare se in futuro serva un pre-filtro leggero (fuori scope in questa revisione).
6. **Costo del loop di ripiego.** Ogni iterazione richiede una rirenderizzazione WeasyPrint; il tetto di 4 (§12) limita il caso peggiore, ma resta da verificare in test che anche 4 iterazioni restino entro i 10–15 secondi di attesa dichiarati nei documenti madre.

---

*Fine del documento.*
