# Sprint 84 — Ricerche su più città, modalità di lavoro, lavoro dei desideri, dimensione del testo

> **Periodo:** 2026-11-17 · **Branch:** `sprint-84-ricerche-desiderio` (da `main` al commit 9a4055e, mai su `main`) · **Stato:** **progettato e approvato (mockup), da implementare**; merge e deploy non fatti.

## Input
Richieste del committente nel tracking: ID 15 (filtro remote/ibrido nella lista), ID 16 (ricerca più ampia di una città), ID 18 (ricerca "a parole" del lavoro desiderato), ID 27 (modalità di lavoro come opzione Pro della ricerca), ID 28 (testo troppo piccolo nell'app aggiunta alla Home dell'iPhone, dove non c'è lo zoom di Safari).

Numero: `git log` e `ls sprints/` arrivano a 83.

Decisioni prese col committente il 2026-11-17: `Docs/design/SPEC-DELTA.md` **A17–A20** (B12 chiuso). Mockup approvati in `Docs/design/mockups/` (vedi `SCREENS.md`): `ricerca-nuova-citta-pro`, `ricerca-nuova-citta-free`, `ricerche-citta`, `desiderio-pro`, `desiderio-free`, `impostazioni-voci-nuove`, `jobs-card-desiderio`, `detail-desiderio-modalita`, `jobs-filtri-desiderio-modalita`, `settings-dimensione-testo`, `jobs-lista-testo-grande`.

**Deroghe a `CLAUDE.md`, approvate dal committente:** il vincolo "Non introdurre filtri di ricerca oltre keywords, location e tipo ricerca" va aggiornato in questo sprint: si aggiungono la **modalità di lavoro** (solo Pro) e la ricerca nascosta del **lavoro dei desideri** (solo Pro). Ogni altro filtro di ricerca resta escluso.

## Parte 1 — Ricerche su più città (ID 16)
**Cosa deve fare**
- Nella ricerca si sceglie prima il **paese** (elenco), poi le **città**, come chip: **Free 1, Pro fino a 5**.
- La località verso la fonte è sempre in inglese, nel formato "City, Country" (risolve le raccolte finite negli USA per località scritte in italiano).
- Ogni città è cercata in un raggio di **circa 40 km**.
- **Ogni città di una ricerca in uso conta come una ricerca attiva:** Pro al massimo 50 città attive, Free 1 per tipo (come oggi). Restano i massimali di ricerche salvate (Pro 100, Free 10). Il pannello mostra "Ogni città conta come una ricerca attiva: ne usi n di 50"; la pagina Ricerche salvate mostra "Città attive n di 50"; la scheda di ogni ricerca elenca città e paese.
- Il filtro "Ricerca" della lista resta per ricerca (non per città).

**Indicazioni per chi implementa (non vincolanti)**
- La fonte accetta un raggio (`distance`, in miglia: 5, 10, 15, 25, 50): usare 25.
- La raccolta raggruppa già per tipo e località (una chiamata per gruppo, `MAX_ITEMS_PER_CALL` 150): con più città per ricerca il raggruppamento va fatto per città (e per modalità, Parte 2). I doppioni tra città vicine sono già eliminati dalla deduplica.
- Le ricerche esistenti (una città, paese testuale) vanno migrate a "paese + 1 città" senza perderle; verificare i paesi scritti in italiano.
- Al downgrade Pro → Free valgono le regole di oggi (tutte disattivate); una ricerca con più città oltre il limite Free non si può attivare finché non resta una città.

## Parte 2 — Modalità di lavoro (ID 15 + 27)
**Cosa deve fare**
- **Solo Pro:** nella ricerca, segmenti **Qualsiasi / Remoto / Ibrido / In sede** (predefinito Qualsiasi). Per i Free il controllo è visibile ma bloccato con il badge PRO e il testo "Scegliere remoto, ibrido o in sede è incluso nel piano Pro."
- **Per tutti i job raccolti**, l'AI ricava la modalità dalla descrizione durante lo scoring: Remoto, Ibrido, In sede o Non indicata. Se l'AI non la trova e il job viene da una ricerca con modalità, vale quella della ricerca.
- **Dettaglio:** chip con la modalità accanto ad "azienda · località"; con "Non indicata" il chip non compare.
- **Filtri della lista:** gruppo **Modalità** a scelta multipla (Remoto, Ibrido, In sede, Non indicata), in AND con gli altri gruppi; incluso nel conteggio dei filtri attivi e in "Azzera filtri".
- La card di lista non cambia. I job raccolti prima dello sprint non hanno la modalità.

**Indicazioni per chi implementa**
- La fonte accetta `workType` come filtro di ricerca, ma **non** la restituisce nell'output (campo vuoto nel campione di 122 annunci): per questo la modalità del job viene dall'AI. Con il motore di ricerca "AI" di LinkedIn la fonte aggiunge la modalità al testo della query invece di filtrare: non è garantita.
- Aggiungere la modalità all'output dello scoring esistente (nessuna chiamata AI in più); nuovo campo sul `Job` con migrazione, serializer, parametro di filtro in `GET /api/jobs/`.

## Parte 3 — Lavoro dei desideri (ID 18)
**Cosa deve fare**
- **Solo Pro**, uno per utente, in **Impostazioni → Ricerca job → Lavoro dei desideri**, con interruttore Attivo.
- L'utente scrive una **descrizione** (fino a 1000 caratteri) e sceglie **paese** e **fino a 5 città**; le città contano come ricerche attive (Parte 1).
- L'AI ricava dalla descrizione **1–2 keyword molto mirate** (meglio pochi job ma pertinenti). Le keyword diventano una ricerca **nascosta**: **non vengono mostrate all'utente** (decisione del committente: l'utente non deve pensare che sia una ricerca normale) e non compaiono tra le ricerche salvate. Si ricavano di nuovo solo quando cambia la descrizione.
- Durante lo scoring **ogni job**, da qualunque ricerca arrivi (anche da quella nascosta), riceve l'etichetta **Desiderio** solo se l'AI lo giudica **molto affine** alla descrizione: un giudizio sì/no severo, non una soglia di punteggio. Un job della ricerca nascosta non è "desiderio" per il solo fatto di provenire da lì.
- **Card e dettaglio:** etichetta con stellina ("Desiderio" sulla card, "Lavoro dei desideri" nel dettaglio), prima delle altre etichette.
- **Filtri:** "Lavoro dei desideri" è il **primo chip del gruppo Ricerca**, se l'utente ha il desiderio (anche spento, finché ci sono job etichettati); filtra i job con l'etichetta, non quelli che vengono dalla ricerca nascosta.
- **Free:** pagina bloccata con spiegazione e "Scopri Pro". Al downgrade il desiderio viene spento, come le ricerche.
- Testo della pagina: "Ogni giorno cerchiamo lavori in linea con la tua descrizione. Durante la valutazione l'AI segna con Desiderio i job, da qualunque ricerca arrivino, molto vicini a ciò che hai descritto. Le città contano come ricerche attive."

**Indicazioni per chi implementa**
- Costi: una chiamata AI quando la descrizione viene salvata o cambiata; pochi token in più per job nello scoring (la descrizione va nel prompt solo per gli utenti con il desiderio attivo); 1–2 keyword × città chiamate alla fonte in più per raccolta.
- La descrizione è un nuovo dato personale: va in informativa (se serve), export e cancellazione (`CLAUDE.md` → Sicurezza e privacy).

## Parte 4 — Dimensione del testo (ID 28)
**Cosa deve fare**
- Nuovo gruppo **Aspetto** in Impostazioni con **Dimensione del testo** (e Lingua, spostata qui): **Come il telefono** (predefinito), **Normale**, **Grande** (circa +20 %), con un'anteprima.
- Ingrandisce **tutta l'app**: testo, pulsanti, icone, spazi; la pagina si ridispone sulla larghezza dello schermo, senza scorrimento laterale.
- "Come il telefono" segue la dimensione del testo impostata nel sistema (su iPhone anche nell'app aggiunta alla Home).

**Indicazioni per chi implementa**
- Le misure sono in `rem` (Tailwind v4): cambiare la dimensione base del documento ingrandisce tutto. Su iOS "Come il telefono" si può ottenere con il font di sistema dinamico (`-apple-system-body`). La scelta è del dispositivo (non serve salvarla sul server, da confermare).
- Verificare con `layout.spec.js` a 360/390 px in modalità Grande (nessuna pagina più larga dello schermo).

## Da aggiornare nello stesso commit dell'implementazione
`CLAUDE.md` (vincolo sui filtri di ricerca), specifiche 01 (§4.2, §4.4, §4.5, §4.6, §4.22) e 02 (modello dati, raccolta, scoring, API §12, test §13), questa scheda, `CHANGELOG.md`, test backend e e2e (`job-list.spec.js`, `account.spec.js`, `layout.spec.js`). Nessuna dipendenza nuova. Nessun dato personale nei file (repository pubblico).

## Punti da verificare in revisione
1. **Costi Apify e AI:** un Pro al massimo (50 città, modalità diverse, desiderio) può fare molte chiamate al giorno; misurare il costo reale dopo il rilascio.
2. **Raggio:** 25 miglia (~40 km) fisso; valutare se renderlo configurabile.
3. **Elenco dei paesi:** quali paesi offrire e con che nomi inglesi verso la fonte.
4. **Modalità dalla fonte:** con il motore "AI" di LinkedIn il filtro `workType` non è garantito; l'etichetta del job viene comunque dall'AI.
5. **Severità del "Desiderio":** se le etichette sono troppo poche o troppe, il prompt va tarato.
6. **Desiderio spento:** se i job già etichettati mantengono l'etichetta (proposta: sì).
7. **Dimensione del testo:** se salvarla per utente (su più dispositivi) o solo sul dispositivo.
8. **Filtri salvati:** se includono Modalità e il chip Desiderio (da decidere insieme alla domanda aperta dello Sprint 82).
