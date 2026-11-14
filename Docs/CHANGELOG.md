# Changelog — Storico delle specifiche

> **A cosa serve.** Indice e storico dei documenti di specifica. Dice quali sono i documenti **correnti** (che descrivono l'as-is dell'app), quali versioni sono superate e in quale sprint è nata ogni parte dell'app.
>
> **Regola in vigore dal 2026-11-14.** Le specifiche in `Docs/` sono documenti **vivi**: descrivono sempre l'app così com'è e vanno aggiornate nello stesso commit dello sprint che cambia il comportamento (procedura in `CLAUDE.md` → "Workflow sprint"). Sostituisce la regola precedente (documenti madre congelati + documenti di estensione numerati 04, 05…), che non era stata applicata dagli sprint 40–64 e aveva prodotto due serie di specifiche divergenti. La numerazione dei paragrafi esistenti va mantenuta (il codice cita i `§`); le parti nuove si aggiungono in coda.

---

## Documenti correnti

| Documento | Versione | As-is al | Contenuto |
|---|---|---|---|
| `01-specifiche-funzionali-v6.md` | 6 | 2026-11-14 (Sprint 64) | Cosa fa l'app: funzioni, piani e massimali, criteri di accettazione, limiti noti |
| `02-specifiche-tecniche-v5.md` | 5 | 2026-11-14 (Sprint 64) | Architettura, stack, modello dati completo, flussi, generazione CV, deploy, API REST (§12), test (§13), limiti tecnici noti |
| `03-specifiche-funzionali-contenuto-cv-v5.md` | 5 | 2026-11-14 (Sprint 64) | Regole di contenuto, selezione e impaginazione del CV; editor e chat. Prevale su 01/02 per questi temi |
| `../DEPLOY.md` | — | 2026-11-14 | Deploy in produzione, variabili d'ambiente, task schedulati, backup, runbook operativo |

## Versioni superate (`archivio/`)

Conservate solo come storico: **non** usarle come riferimento.

| File | Stato al momento dell'archiviazione |
|---|---|
| `archivio/01-specifiche-funzionali-v4.md` | Era in radice e citata da `CLAUDE.md`. Aveva recepito sprint-39 (ricerche Job role/Company) e sprint-47 (score 1–10), **non** il documento 03 |
| `archivio/02-specifiche-tecniche-v3.md` | Era in radice. Come sopra (39 e 47 sì, documento 03 no) |
| `archivio/01-specifiche-funzionali-v5.md` | Era in `Docs/`, dichiarata "congelata". Aveva recepito il documento 03, **non** 39/47 (score ancora 1–5) |
| `archivio/02-specifiche-tecniche-v4.md` | Era in `Docs/`, dichiarata "congelata". Come sopra |
| `archivio/03-specifiche-funzionali-contenuto-cv-v4.md` | Documento di estensione sul contenuto del CV (sprint 26–29), poi superato da 30–38, 44, 51–62 |

Nessuna delle versioni archiviate descriveva gli sprint 40–64.

## Storico versioni

### 01 — Specifiche funzionali
- **v1–v3** (luglio 2026): perimetro MVP, massimali, credito come pool generico, foto on/off.
- **v4** (luglio 2026, revisione criticità): credito in €, niente Word, limiti di raccolta per notte, tie-break del cap, definizione "nuovi job", generazione concorrente bloccata, scoring fallito scartato. Poi aggiornata in place con sprint-39 e sprint-47.
- **v5** (01/08/2026): recepisce il documento 03 v3 (profilo a 5 sezioni, vincoli istruzione, qualifica, arricchimento ristretto).
- **v6** (14/11/2026): fusione di v4 e v5 e allineamento completo all'as-is degli sprint 40–64.

### 02 — Specifiche tecniche
- **v1–v3** (luglio 2026): architettura monolitica Django+Celery, modello dati, flussi, deploy. v3 poi aggiornata in place con sprint-39 e sprint-47.
- **v4** (01/08/2026): recepisce il documento 03 (pipeline CV riscritta, `Education.start_date/end_date`, rimozione `key_achievements`).
- **v5** (14/11/2026): fusione di v3 e v4 e allineamento completo all'as-is degli sprint 40–64; aggiunte le sezioni API REST e Test.

### 03 — Contenuto del CV
- **v1–v3** (luglio 2026): selezione e quantità del contenuto, qualifica, Areas of Expertise, overflow.
- **v4** (01/08/2026): versione implementata negli sprint 26–29.
- **v5** (14/11/2026): allineamento all'as-is (sprint 30–38, 41, 44, 51–62): budget bullet, istruzione, template a dimensione fissa, grassetto keyword, "colma i gap" al posto dell'arricchimento, editor e chat.

## Mappa sprint → documenti

Ogni sprint ha la sua scheda in `../sprints/sprint-NN.md`. Le schede 40–42 e 44–64 sono **retroattive** (ricostruite il 2026-11-14 da commit, codice e storico sessioni). Non esistono gli sprint 40–42 come commit separati: sono nel commit cumulativo `0833bdb`, vedi `sprint-43.md`. La numerazione 44–47 di commit e commenti nel codice non coincide: vedi la tabella di riconciliazione in `sprint-44.md`.

| Sprint | Tema | Dove è descritto oggi |
|---|---|---|
| 01–17 | Fondamenta backend: account, profilo, ricerche, raccolta, scoring, CV, piani, notifiche | 01 §4, 02 §2–§5 |
| 18–22 | PWA React (Tailwind + shadcn/ui), gestione account, push, deploy, QA e2e | 01 §4, 02 §3.3, §8, `DEPLOY.md` |
| 23–25 | Modifica ricerche, città/paese, import diretto da LinkedIn (API guest), fix raccolta | 01 §4.2, §4.9; 02 §5.3, §5.7 |
| 26–38 | Contenuto del CV: modello dati, pipeline, template, overflow, arricchimento vincolato, pagina Profilo, fix layout/date | 03; 01 §4.1, §4.7; 02 §6 |
| 39 | Ricerche Job role / Company, chiamate Apify raggruppate | 01 §4.2; 02 §5.3 |
| 40 | Filtro per ricerca di provenienza; migrazione AI ad AWS Bedrock | 01 §4.5; 02 §3.5 |
| 41 | CV multilingua (5 lingue), lingue/livelli a valori fissi, email del profilo | 03; 01 §4.1; 02 §4.2 |
| 42 | Cover letter (PDF, quota/credito dedicati) | 01 §4.18; 02 §5.10 |
| 43 | Creazione manuale di un job | 01 §4.15; 02 §5.8 |
| 44 | Home con statistiche e navigazione; "colma i gap" al posto dell'arricchimento | 01 §4.8, §4.13; 03 |
| 45 | Scoring più accurato e parallelo; fix raccolta manuale; rimozione CV automatici | 01 §4.4, §4.14; 02 §5.1, §5.6 |
| 46 | Filtri lista, Preferiti, pagine Profilo/Impostazioni, candidati/recruiter; rimozione cap di intake | 01 §4.5, §4.21, §4.22; 02 §4.4 |
| 47–49 | Score 1–10 con rubrica, cap sulla lingua richiesta, scarto campi oltre `max_length` | 01 §4.4; 02 §5.9 |
| 50 | Messaggi di networking (LinkedIn/email) | 01 §4.20; 02 §5.11 |
| 51 | Editor del CV (bozza manuale) | 01 §4.16; 03; 02 §5.12 |
| 52–58 | Template CV (Cambria/Caladea, dimensioni, colori, giustificato), grassetto keyword | 03 |
| 59–62 | Chat AI nell'editor CV (proposta → conferma, riferimento ai bullet, decisioni persistite) | 01 §4.17; 03; 02 §5.13 |
| 63 | Filtro "Ricerca" multi-selezione; editor e chat della cover letter | 01 §4.5, §4.19; 02 §5.12–§5.13 |
| 64 | Filtri preferiti salvabili | 01 §4.21; 02 §4.13 |
