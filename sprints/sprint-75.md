# Sprint 75 — Redesign UI: dettaglio job

> **Periodo:** 2026-11-14 · **Branch:** `sprint-75-dettaglio` (da `sprint-74-lista`, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato e verificato (e2e 38/38, screenshot a 360/390/1280 px); **merge e deploy non fatti** (in attesa dell'ok del committente).

## Input
Perimetro da `Docs/design/IMPLEMENTATION-PLAN.md` (sprint 75) e `SCREENS.md` §2. Mockup: `detail-nuovo`, `detail-menu`, `detail-gap`, `detail-cover-letter`, `detail-message`, `generazione-in-corso`, `detail-cv-generato`, `detail-docs-pages`, `detail-applied`, `undo-application`, `confirm-cost`, `desk-detail`. Regole del committente: comportamento esistente con il nuovo aspetto; nessuna API né backend; nessun nuovo stato; nessuna dipendenza (menu fatto in casa); font di sistema; stringhe it/en verificate a 360 e 390 px; template PDF ed editor (Sprint 76) non toccati; confronto funzione per funzione qui sotto.

Prima di partire: `/root/App-apply` (produzione) era sul branch `sprint-73-appshell` invece che su `main`; è stato riportato su `main` (pulito) senza toccare i container. A fine sprint i container di produzione hanno le stesse date di creazione e girano tutti da `docker-compose.prod.yml`; sito 200.

## Decisioni prese
- **Barra azione al posto della barra di tab** (`DESIGN.md` §2), a ogni larghezza; da 1024 px allineata alla colonna di 640 px (`desk-detail`). Contenuto secondo lo stato: **Genera CV ▾** senza CV (▾ = Genera cover letter, Genera messaggio); **Segna candidatura fatta** con il CV; **Annulla candidatura** dopo la candidatura (`detail-applied`; `SCREENS.md` la metteva nel ⋯, il mockup nella barra: seguito il mockup).
- **"Colma i gap" si apre a ogni "Genera CV"** (A3), anche quando il job non ha gap: è il pannello in cui si vedono avviso AI e costo prima di confermare. Senza selezione si genera come prima. Un clic in più rispetto al vecchio clic diretto.
- **Stato indicativo**: chip senza freccia (il mockup ha ▾, ma per la richiesta il chip non è selezionabile); "CV in generazione" con indicatore è lo stato transitorio esistente, mostrato sia durante la generazione da questa pagina sia quando il server ha il flag acceso.
- **Generazione sincrona invariata**: durante l'attesa una finestra non chiudibile (Esc e clic fuori ignorati) con indicatore e testo; pulsanti disattivati come prima dai flag `*_generation_in_progress`; nessun cambio a flussi o guardia di concorrenza.
- **Costo**: `CostConfirmDialog` per CV, cover letter e messaggio; il piede di ogni pannello mostra "Incluso nel piano: ne restano X su Y oggi" (o prezzo e saldo); con massimale e saldo esauriti il pulsante è disattivato e il motivo è il testo del costo, sopra il pulsante.
- **Limiti dei campi** = `max_length` del server, verificati in `backend/apps/jobs/serializers.py`: indicazioni 2.000 (con contatore), nome destinatario 255, link LinkedIn 500. Cover letter e messaggio uniscono indicazioni riusate e nuove: se il totale supera 2.000 il pulsante è disattivato con il motivo (prima il server rispondeva 400 e la pagina mostrava solo "Non siamo riusciti…").
- **Motivazioni delle voci**: aprendo un contatore si vedono subito etichetta e motivo di ogni voce; il pulsante "Espandi motivazioni" non c'è più (un tocco invece di due).
- **Menu ⋯ della testata**: Archivia / Riporta dall'archivio; per un job senza CV non ancora marcato anche "Segna candidatura fatta" (consentito anche senza CV, §4.10, e la barra in quello stato mostra "Genera CV"). Archiviando si resta nella pagina, con toast "Annulla" ed etichetta "Archiviato".
- **"Nessun link di candidatura"**: senza `apply_url` il pulsante "Annuncio" non compare; il testo esplicativo è stato tolto (i mockup non hanno un posto per esso).
- **Pillole per le indicazioni passate** (mockup `detail-cover-letter`) al posto delle checkbox; testi lunghi su più righe (massimo 3, testo completo nel `title`).
- **Messaggi di networking** sotto la riga "Messaggio" della sezione Documenti (il mockup disegna solo la riga): stesse informazioni di prima (canale, destinatario, data, Copia, profilo LinkedIn, oggetto, testo), testo troncato a 4 righe con "Leggi tutto".
- **Testi**: "Genera Cover Letter" / "Scarica Cover Letter" diventano "Genera cover letter" / "Scarica cover letter" (come nei mockup); gli editor ("Modifica Cover Letter") restano allo Sprint 76.

## Confronto funzione per funzione (prima → dopo)
| Funzione (prima dello Sprint 75) | Dopo | Note |
|---|---|---|
| Link "← Torna alla lista" (filtri dell'ultima visita) | "‹ Jobs" in alto a sinistra, stessa destinazione (`jobListHref`) | |
| Badge di stato | chip indicativo, ✓ per CV generato / candidatura fatta, "CV in generazione" con indicatore | nessun nuovo stato |
| Badge ricerca di provenienza | etichetta "Trovato con: …" | va a capo se lunga |
| Badge candidati (verde sotto 25) | uguale | |
| Titolo, azienda · località · retribuzione | uguale | |
| Icona recruiter (link al profilo) | `RecruiterIcon` (come in lista) | |
| "Importato: data" | uguale, accanto alle etichette | |
| Cuoricino preferito | uguale, in alto a destra | corretto il difetto 2 sotto |
| Punteggio | `ScoreChip` 56 px, fasce di colore esistenti | |
| "Perché questo punteggio" completo | troncato a 3 righe, "Leggi tutto" / "Mostra meno" solo se serve | |
| Elenchi Corrispondenze / Da colmare + "Espandi motivazioni" | contatori "N corrispondenze" / "N gap" (numero che non va a capo, etichetta che sì; impilati se non stanno affiancati), uno aperto per volta, con motivazione | |
| Descrizione completa sempre visibile | "Descrizione annuncio" a fisarmonica, chiusa | |
| Pannello collassabile "Colma i gap" + "Genera CV" diretto | "Genera CV" apre il pannello "Genera CV" con gap numerati (1-based, stessi numeri al server), motivazioni, indicazioni con contatore, testo di default, avviso AI, costo | stessa chiamata `generateCv(id, gap, indicazioni)` |
| "Rigenera CV" | ⋯ della riga CV → "Rigenera CV" (stesso pannello, titolo "Rigenera CV") | |
| "Generazione…" disattivato | finestra di attesa + "Generazione…" disattivato nella barra | |
| Toast multipagina dopo la generazione (CV e cover letter) | uguale | |
| 409 con `detail` del server / errore generico | uguale | |
| Scarica CV (URL firmato, nome file) | icona Scarica nella riga del CV, stesso link | |
| Modifica CV (se modificabile) | matita nella riga del CV | |
| Genera Cover Letter (popup) | ▾ della barra o "Genera" / ⋯ "Rigenera cover letter" nella riga → pannello | costo corretto (difetto 1) |
| Scarica / Modifica Cover Letter | icone nella riga | |
| Genera messaggio (popup con canale, nome, link, indicazioni, riuso) | ▾ della barra o "Genera" nella riga "Messaggio" → pannello con gli stessi campi (canale a segmenti) | costo corretto (difetto 1) |
| Elenco messaggi con Copia (oggetto incluso), link profilo normalizzato | sotto la riga "Messaggio" | |
| Avvisi: CV/cover letter su più pagine, documenti non modificabili | `Banner` sotto la riga del documento | |
| "Vai all'annuncio" / "Nessun link di candidatura" | pulsante "Annuncio ↗" (nome accessibile "Vai all'annuncio"); senza link niente | testo tolto |
| "Segna candidatura fatta" (sempre, anche senza CV) | barra con il CV; menu ⋯ senza CV | |
| "Annulla candidatura" + finestra | barra + `Modal` (Sì, annulla / No, lascia com'è) | |
| Archiviazione dal dettaglio | **nuova** (A7): menu ⋯ Archivia / Riporta dall'archivio, anche da tastiera | era solo lo swipe in lista (Sprint 74) |
| `window.confirm` del costo | `CostConfirmDialog` | A11 |
| Indicazione del costo | piede di ogni pannello; pulsante disattivato se bloccato | |
| Ricaricamento del job ogni 20 min e al ritorno in primo piano (URL firmati) | uguale | |
| Caricamento / job non trovato | indicatore / `Banner` di errore + "Torna alla lista" | |

**Azioni senza collocazione nei mockup, messe nel menu ⋯** (testata): "Riporta dall'archivio" (al posto di "Archivia" per i job archiviati), "Segna candidatura fatta" per i job senza CV. Nel ⋯ delle righe documento: "Rigenera CV", "Rigenera cover letter".

## Difetti trovati e corretti (solo frontend)
1. **Costi scambiati** (dallo Sprint 70): il popup della cover letter mostrava il costo dei messaggi (`action="referral_message"`) e quello dei messaggi il costo della cover letter. Ora ogni pannello mostra la propria azione (e2e dedicato).
2. **Preferito nel dettaglio**: `favorite`/`unfavorite` (come `archive`/`unarchive`) rispondono con `JobSerializer`, senza i campi del dettaglio; la pagina sostituiva l'intero job e spariva fino al ricaricamento ciò che dipende da `cv_editable`, `cv_page_count` e simili ("Modifica CV", avvisi). Ora si aggiorna solo il campo cambiato; in caso di errore il cuoricino torna com'era.

## Implementazione
### Frontend
- `pages/JobDetailPage.jsx` riscritta (stato e chiamate API come prima); presentazione in `components/job-detail/`: `ScoreSection.jsx` (`ScoreSection`, `DescriptionSection`), `DocumentsSection.jsx`, `GapSheet.jsx`, `CoverLetterSheet.jsx`, `ReferralSheet.jsx`, `GenerationSheetParts.jsx`.
- Nuovi componenti `ui/`: `menu.jsx` (menu button WAI-ARIA senza dipendenze: fuoco sulla prima voce, ↑ apre sull'ultima, ↑ ↓ Home Fine, Esc riporta il fuoco al pulsante, Tab e clic fuori chiudono), `split-button.jsx`, `action-bar.jsx`, `counter-toggle.jsx`, `document-row.jsx`, `expandable-text.jsx`. `utils/generationLimits.js` con i limiti del server e `joinInstructions`.
- `index.css`: con `html.has-actionbar` (messa da `ActionBar`) la barra di tab (`app-tabbar`) è nascosta e `--app-bottom-bar` vale l'altezza della barra azione (contenuto e toast restano sopra). `AppShell.jsx`: classe `app-tabbar` sulla barra di tab.
- `translations.js` (it/en): `jobs.moreActions`, `generateMenuLabel`, `restoreFromArchive`, `archivedBadge`, `foundWith`, `listingButton`, `statusCvGenerating`, `readMore`, `readLess`, `matchesCountOne/Many`, `gapsCountOne/Many`, `descriptionShow/Hide`, `documentsTitle`, `docCv`, `docCoverLetter`, `docMessage`, `cvReady`, `coverLetterReady`, `docPagesOne/Many`, `cvNotGenerated`, `coverLetterNotGenerated`, `messageNotGenerated`, `messagesCountOne/Many`, `generateShort`, `cvActions`, `coverLetterActions`, `regenerateCoverLetter`, `generatingCvTitle/Text`, `generatingCoverLetterTitle/Text`, `generatingMessageTitle/Text`, `instructionsTooLong`; `generateCoverLetter` e `downloadCoverLetter` in minuscolo.

### Backend / API
Nessun cambio.

### Nota sul lavoro
Durante lo sprint una seconda sessione ha iniziato lo stesso sprint nella stessa copia (`menu.jsx`, `action-bar.jsx`, `index.css`, `AppShell.jsx` scritti da entrambe). Su indicazione del committente il lavoro è proseguito solo qui; i blocchi duplicati in `index.css` e `AppShell.jsx` sono stati eliminati e di `menu.jsx` è rimasta la versione dell'altra sessione (equivalente, con ↑ che apre sull'ultima voce e voci `destructive`).

## E2e — asserzioni cambiate e nuove
| Spec / test | Prima | Dopo |
|---|---|---|
| `job-list` › generare il CV disabilita il pulsante… | "Genera CV" → "Generazione…" disattivato | "Genera CV" della barra → pannello "Genera CV" (selezione del gap) → finestra "Generazione del CV…" che resiste a Esc → errore → "Genera CV" di nuovo attivo |
| `job-list` › apply link e "segna candidatura fatta"… senza CV | pulsante "Segna candidatura fatta" | voce del menu ⋯; poi la barra mostra "Annulla candidatura" e la voce sparisce dal menu |
| `job-list` › segnare la candidatura come fatta… | pulsante "Segna candidatura fatta" (il seed non ha il PDF del CV) | voce del menu ⋯; poi "Annulla candidatura" con finestra: "No, lascia com'è" non cambia nulla, "Sì, annulla" riporta a "Nuovo" (senza CV) |
| `job-list` › "espandi motivazioni" | pulsante "Espandi motivazioni" | rinominato "i contatori corrispondenze/gap…": contatori `aria-expanded`, uno aperto per volta, con motivazione |
| **nuovo** `job-list` › menu ⋯ da tastiera archivia e riporta dall'archivio | — | Invio apre con il fuoco su "Archivia", Esc chiude e riporta il fuoco, ↓ riapre, Invio archivia (toast, etichetta), "Riporta dall'archivio" |
| **nuovo** `job-list` › ▾ di Genera CV… | — | voci "Genera cover letter" / "Genera messaggio", Esc riporta il fuoco; ogni pannello mostra solo il proprio costo (`action-cost-cover_letter` / `action-cost-referral_message`), `maxlength` 2000, canale LinkedIn di default |
| **nuovo** `job-list` › mobile › nel dettaglio la barra azione sostituisce la barra di tab | — | a 390 px niente barra di tab, barra azione in fondo, nessuna larghezza in eccesso; tornando alla lista la barra di tab ricompare |

## Verifica
- `npm run build`: OK. `npx oxlint src e2e`: 0 errori, 9 warning (gli stessi di prima).
- **E2e** sullo stack usa e getta di `sprints/sprint-73.md` (copia `/root/App-apply-dev`, immagini `appapply-e2e-*` ricostruite, Postgres/Redis temporanei, nessun codice d'invito né email, nessun dato reale): prima esecuzione **36/38**. I 2 fallimenti erano asserzioni da aggiornare, non difetti dell'app: (1) "Generazione del CV…" trovato due volte, perché l'indicatore lo ripeteva per gli screen reader (tolto il doppione); (2) dopo "Annulla candidatura" il test si aspettava "CV generato", ma il job del seed non ha il PDF del CV e il server lo riporta correttamente a "Nuovo" (§4.10). Poi `job-list` 24/25 con "filtro preferito" fallito una volta e passato rilanciandolo (intermittente, già passato nella prima esecuzione; non toccato da questo sprint). **Esecuzione finale dell'intera suite: 38/38.**
- **Screenshot** (Playwright, 360/390/1280 px; utente Pro di prova con job seed modificati nel DB di prova: motivazione lunga, 7 corrispondenze, 1 gap, ricerca di provenienza, recruiter; CV di 2 pagine, cover letter non modificabile e un messaggio email su un job; candidatura fatta su un altro; massimale del CV esaurito con saldo 4,60 € e poi 0 €): nuovo (gap aperto), menu ▾ aperto, menu ⋯ aperto, pannello gap, cover letter (con indicazione passata), messaggio, in generazione, con documenti, menu ⋯ del CV, candidatura fatta, conferma costo, annulla candidatura, costo bloccato; in inglese documenti, nuovo (corrispondenze aperte) e pannello gap. Larghezza del documento = schermo in tutti gli stati alle tre larghezze; nessun errore JavaScript.
- Backend non toccato: test backend non necessari. Stack di prova abbattuto; produzione non toccata.

## Cosa manca / note
- Editor di CV e cover letter (Sprint 76): usano ancora `window.confirm` per i costi (`confirmCreditCharge`) e la barra di tab.
- Il seed degli e2e non crea PDF: il percorso "Segna candidatura fatta" dalla barra (con il CV) è coperto dagli screenshot, non da un e2e.
- Differenze dai mockup: chip di stato senza ▾ (non selezionabile, per richiesta); contatori impilati a 360–390 px quando "N corrispondenze" e "N gap" non stanno affiancati senza andare a capo (affiancati da tablet in su); messaggi già generati elencati sotto la riga "Messaggio" (non disegnati); "Importato: data" mantenuto.
