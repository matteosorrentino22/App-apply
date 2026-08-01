# Changelog — Registro dei documenti di estensione

> **A cosa serve.** I documenti madre (`01-specifiche-funzionali-v5.md`, `02-specifiche-tecniche-v4.md`) sono **congelati**: descrivono l'MVP come è stato sviluppato e non si toccano più. Ogni nuova funzionalità o rettifica si scrive in un **documento numerato a sé** (03, 04, 05…), che contiene prima le specifiche funzionali e poi quelle tecniche, e che dichiara in apertura cosa emenda dei madre.
>
> Questo file è l'**indice**: dice quali documenti di estensione esistono, cosa toccano dei madre, e in che stato sono. Serve a capire a colpo d'occhio quali parti dei documenti madre sono ancora valide e quali sono state superate.

---

## Documenti madre (congelati)

| Documento | Contenuto | Stato |
|---|---|---|
| `01-specifiche-funzionali-v5.md` | Specifiche funzionali complete dell'MVP | **Congelato** — non modificare |
| `02-specifiche-tecniche-v4.md` | Specifiche tecniche complete dell'MVP | **Congelato** — non modificare |

---

## Documenti di estensione

### 03 — Contenuto del CV generato
**File:** `03-specifiche-funzionali-contenuto-cv-v3.md`
**Stato:** attivo
**Ambito:** selezione, quantità e struttura del contenuto del CV generato; qualifica professionale; Areas of Expertise; overflow.

**Cosa emenda dei documenti madre:**

| Doc madre | Punto | Natura | Sintesi |
|---|---|---|---|
| 01 | §4.1 | Sostituisce | Sezione "risultati chiave" eliminata dal profilo master (restano 5 sezioni) |
| 01 | §4.1 | Aggiunge | Vincoli minimi profilo: ≥1 voce di istruzione con data di fine obbligatoria; esperienze possono essere 0 |
| 01 | §4.7 | Precisa | Istruzione "invariata" → "non riformulata", ma soggetta a selezione (max 3 voci più recenti) |
| 01 | §4.7 | Aggiunge | Nuovo elemento del CV: qualifica professionale sotto il nome |
| 01 | §4.7 | Aggiunge | Quantità deterministiche: max 5 esperienze, budget bullet calcolato dal sistema |
| 01 | §4.8 | Sostituisce | Arricchimento ristretto a esperienze già presenti; priorità massima di inclusione |
| 02 | §4.2 | Sostituisce | `Profile.key_achievements` rimosso dal modello dati |
| 02 | §4.2 | Sostituisce | `Education.dates` → `start_date` (opzionale) + `end_date` (obbligatorio) |
| 02 | §6.2 | Sostituisce | Pipeline di generazione riscritta (quantità deterministiche, qualifica, loop di ripiego) |
| 02 | §11.4 | Chiude | Strategia "1 pagina" definita: 3 livelli di compattamento + loop di ripiego + residuale silenzioso |

**Decisioni principali prese in questo documento:**
- Le **quantità** le decide il sistema, i **contenuti** il modello (principio cardine).
- **Areas of Expertise:** min 4 / max 6 voci, sezione mai omessa; con profilo scarno il modello riformula lo stesso materiale da angolazioni diverse per arrivare a 4. Non è un campo del profilo: è sempre e solo calcolato a ogni generazione.
- **Overflow esaurito:** comportamento silenzioso — PDF salvato anche se multi-pagina, evento nel `RunLog`, nessun errore all'utente.
- **Qualifica professionale con profilo senza esperienze e titolo ambiguo:** si usa comunque il titolo del job "ripulito", nessun fallback sull'istruzione.
- **Nessuna migrazione dati:** i nuovi vincoli si applicano da subito, l'app è in fase di test.

---

## Convenzioni

- **Numerazione:** ogni nuovo documento di estensione prende il numero successivo (04, 05…). Il numero non si riusa.
- **Struttura di ogni documento di estensione:**
  1. Intestazione con tipo, stato, documenti madre di riferimento, regola di precedenza
  2. **§0 — Cosa emenda dei documenti madre** (tabella dichiarativa)
  3. **Parte I — Specifiche funzionali**
  4. **Parte II — Specifiche tecniche**
  5. **Punti da verificare in revisione**
- **Precedenza:** in caso di conflitto, sul proprio ambito prevale il documento di estensione; su tutto il resto prevalgono i madre.
- **Aggiornamento di questo file:** ogni volta che nasce un documento di estensione, o che uno esistente cambia in modo che tocchi punti nuovi dei madre, si aggiorna la sua voce qui.
