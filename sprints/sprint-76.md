# Sprint 76 — Redesign UI: editor di CV e cover letter

> **Periodo:** 2026-11-15 · **Branch:** `sprint-76-editor` (da `sprint-75-dettaglio`, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato e verificato (e2e 43/43, screenshot a 360/390/1280 px); **merge e deploy non fatti** (in attesa dell'ok del committente).

## Input
Perimetro da `Docs/design/IMPLEMENTATION-PLAN.md` (sprint 76) e `SCREENS.md` §3. Mockup: `cv-editor`, `cv-preview`, `cv-assistant`, `cv-assistant-warn`, `cv-assistant-credit`, `cv-outdated`, `cover-editor`, `desk-editor`. Regole del committente: sezioni a fisarmonica, segmento Modifica / Anteprima, `ActionBar` con "Genera PDF finale" al posto della barra di tab; chat in `Sheet` su mobile e in colonna fissa a destra da 1024 px (400 px, gap 24, massimo 1112 px) con **una sola istanza di codice**; flusso proposta → conferma invariato; costo e saldo dall'API; stato di credito insufficiente e di avviso; "bozza superata" in `Modal`; limiti esistenti mostrati senza cambiare le regole; `RichBulletInput` ed `ExperienceGroupEditor` senza cambi di props né di comportamento; `CostConfirmDialog` dove l'editor usa oggi `window.confirm`; fuori ambito template PDF, rendering dell'anteprima, backend; nessuna dipendenza, nessun font esterno, it/en, tastiera dell'iPhone che non copre il campo della chat, nessuna pagina più larga dello schermo.

Prima di partire: `/root/App-apply` (produzione) su `main` (f6584e5), pulito; container di produzione non toccati (stesse date di creazione, tutti da `docker-compose.prod.yml`); sito 200. Numero: `git log` e `ls sprints/` arrivano entrambi a 75.

## Decisioni prese
- **Nessun `window.confirm` da sostituire.** Negli editor non c'è mai stato: "Genera PDF finale" è gratuito e la chat addebita il messaggio mostrando prima prezzo e saldo, senza conferma. Aggiungere una conferma avrebbe cambiato il comportamento, quindi non l'ho fatto. `confirmCreditCharge` (lib/usage.js), non più usata da nessuna parte dopo lo Sprint 75, è stata rimossa; corretta la frase delle specifiche (scritta nello Sprint 75) che la dava ancora in uso negli editor.
- **Una sola chat, due contenitori.** Lo stato della chat (cronologia, prezzo/saldo, testo in scrittura, decisioni, avvisi) è passato dai pannelli all'hook `useDraftChat`, chiamato dalla pagina che resta montata; il pannello `DraftChatPanel` è solo presentazione e si monta nella colonna (≥ 1024 px) o nel `Sheet` (sotto). Così chiudere e riaprire il pannello su mobile conserva tutto come prima (prima il pannello restava montato e diventava invisibile).
- **Tastiera dell'iPhone**: Safari non riduce il viewport di layout quando si apre la tastiera; il pannello della chat legge `visualViewport` (`useKeyboardInset`) e si sposta sopra la tastiera, con altezza massima pari all'area visibile. Verificato solo nel browser di prova, non su un iPhone reale.
- **Credito insufficiente** calcolato da prezzo e saldo dell'API (`balance < price`): campo e invio disattivati e il motivo nel flusso (mockup `cv-assistant-credit`); resta anche il caso 402 del server.
- **Avvisi nel flusso** della conversazione, dopo il messaggio a cui si riferiscono (mockup `cv-assistant-warn`), invece di un'unica riga di errore sotto la chat che si azzerava al messaggio successivo.
- **Proposte decise** ridotte al titolo con "Applicata" / "Rifiutata" (mockup `cv-assistant`); nelle proposte da decidere resta il "prima" barrato oltre al "dopo" (il mockup mostra solo il "dopo": tenuto per non perdere informazione).
- **"Mostra nel CV"** diventa un interruttore (`role="switch"`, mockup), stesso dato `shown`; la spunta dei punti elenco resta checkbox con l'etichetta "Visibile" (prima senza etichetta).
- **Limiti mostrati, non cambiati**: quelli del server per le bozze (`apps/cv/draft_validation.py`): 20 aree, 30 punti elenco per esperienza, 20 voci di istruzione, 30 lingue, 15 paragrafi da 3.000 caratteri; campi dell'istruzione 300 (periodo 100); messaggio della chat 2.000 (`MAX_CHAT_MESSAGE_LENGTH`). Al limite "Aggiungi …" si disattiva con il motivo; i campi semplici hanno `maxLength`; la chat ha un contatore vicino al limite. Il "15 × 400" citato nella richiesta è il limite del **Profilo** (`ExperienceGroupEditor`), che gli editor non usano: non toccato.
- **Salvataggio non riuscito**: lo stato in testata diventa "Non salvato" (prima tornava vuoto in silenzio); la logica di nuovo tentativo è la stessa (la modifica resta in attesa e parte con la successiva, con la chat o con "Genera PDF finale").
- **Anteprima** nella scheda "Anteprima" del segmento anche su desktop (mockup `desk-editor`: a destra c'è la chat); stesso meccanismo (PDF del server in un iframe da blob URL), in proporzione A4, con didascalia.
- **`RichBulletInput`**: solo stile (bordo e fuoco come gli altri campi, testo a 16 px per evitare lo zoom automatico dell'iPhone, pulsante del grassetto da 32 px). Props e comportamento invariati; il ritocco si vede anche nel Profilo, che lo usa.
- **Titoli dei paragrafi** della cover letter: "Paragrafo N", con "· Apertura" sul primo e "· Chiusura" sull'ultimo (come nel mockup), per posizione.

## Confronto funzione per funzione (prima → dopo)
### Editor del CV
| Funzione (prima) | Dopo | Note |
|---|---|---|
| "← Torna al job" | "‹ Torna al job" in testata | |
| Stato "Salvataggio… / Salvato" | uguale, con ✓; in più "Non salvato" se fallisce | |
| Titolo "Modifica CV — titolo del job" | "Modifica CV" + "titolo · azienda" | |
| Anteprima PDF sempre visibile (accanto su desktop, sotto su mobile) con "1 pagina ✓ / N pagine ⚠" | scheda "Anteprima" del segmento; indicatore delle pagine in testata; avviso multipagina come `Banner` | stesso rendering |
| Anteprima non disponibile | `Banner` con lo stesso testo | |
| Sommario, qualifica (grassetto) | fisarmoniche "Sommario" (aperta) e "Qualifica professionale" (riassunto = testo) | `RichBulletInput` |
| Aree: modifica, aggiungi, rimuovi, riordina | uguale, in "Aree di competenza" ("N aree"); "Aggiungi area" fino a 20 | |
| Esperienze: tutte, "Mostra nel CV", ruolo modificabile, azienda/località/date in sola lettura | fisarmonica "Esperienze" ("N aziende") con una fisarmonica per azienda (riassunto = ruolo); interruttore "Mostra nel CV" | |
| Bullet: spunta mostra/nascondi, testo con grassetto, aggiungi/rimuovi/riordina, ✦ contesto della chat | riquadro per bullet: testo, "Visibile", ✦ (`aria-pressed`), su/giù, elimina; "Aggiungi punto" fino a 30 | |
| Istruzione: tutti i campi, note con grassetto, aggiungi/rimuovi | fisarmonica "Istruzione" ("N voci"), campi con etichetta e `maxLength`; "Aggiungi voce" fino a 20 | |
| Competenze / certificazioni dal profilo (checkbox) | fisarmoniche con "N di M"; avviso se il profilo non ne ha | |
| Lingue: lingua e livello, aggiungi/rimuovi | fisarmonica "Lingue" ("N"); "Aggiungi lingua" fino a 30 | |
| Autosave + anteprima con un solo debounce (1,2 s) | uguale | |
| "Genera PDF finale" (con l'ultima modifica a schermo, toast, ritorno al job) | uguale, nella barra in basso | |
| Bozza superata (finestra con Riparti / Continua; chiudendo si torna al job) | `Modal` (mockup `cv-outdated`), stesse azioni e stessa chiusura | |
| Errore di apertura | `Banner` di errore + "Torna al job" | |
| Pulsante flottante "Chiedi all'AI" + pannello laterale | da 1024 px colonna fissa a destra; sotto "Assistente" nella barra → pannello dal basso | |

### Chat (CV e cover letter)
| Funzione (prima) | Dopo |
|---|---|
| Cronologia e decisioni dal server all'apertura | uguale (caricata quando la bozza esiste, come prima) |
| Invio con Invio, Shift+Invio a capo; salvataggio della bozza prima dell'invio | uguale; pulsante ↑; `maxLength` 2000 |
| Bolle utente / assistente | uguale, nuovo aspetto |
| Proposte con prima/dopo e Accetta / Rifiuta | Rifiuta / Accetta; decise → titolo + "Applicata" / "Rifiutata" |
| Elemento non più nella bozza → rifiutata con avviso | uguale, avviso nel flusso |
| Scelta non salvata dopo i tentativi → avviso | uguale, avviso nel flusso |
| Prezzo e saldo prima dell'invio | uguale, prezzo in grassetto (valori dall'API) |
| 402 → "Saldo credito insufficiente…" | uguale; in più, con saldo minore del prezzo, campo e invio disattivati prima di scrivere |
| Chip "Contesto:" dei bullet puntati | uguale, con ✕ per toglierli |
| Avviso AI sotto il campo | sotto il prezzo, sopra il campo |
| Pannello chiuso: stato conservato | uguale (stato nella pagina) |

### Editor della cover letter
| Funzione (prima) | Dopo |
|---|---|
| Paragrafi: modifica, su/giù, elimina, "+ Aggiungi paragrafo" | riquadro per paragrafo con titolo, su/giù, elimina, `maxLength` 3000; "Aggiungi paragrafo" fino a 15 |
| Anteprima, pagine, autosave, "Genera PDF finale", bozza superata, chat | come l'editor del CV |

## Implementazione
### Frontend
- Pagine riscritte nella presentazione (logica invariata): `pages/CvDraftEditorPage.jsx`, `pages/CoverLetterDraftEditorPage.jsx`.
- Nuovi: `components/editor/EditorShell.jsx` (impianto comune, colonna della chat con altezza calcolata fino alla barra azione), `editor/EditorPreview.jsx`, `editor/OutdatedDraftModal.jsx`, `editor/CvSections.jsx`; `components/DraftChatPanel.jsx`; `lib/useDraftChat.js`, `lib/draftChatApi.js`, `lib/useMediaQuery.js` (`useMediaQuery`, `useKeyboardInset`); `ui/accordion.jsx` (`AccordionSection`), `ui/switch.jsx`; `utils/draftLimits.js`.
- `CvDraftChatPanel.jsx`, `CoverLetterChatPanel.jsx`: ridotti alle etichette delle proposte e al contesto, su `DraftChatPanel`.
- `RichBulletInput.jsx`: solo classi di stile.
- `lib/usage.js`: rimossa `confirmCreditCharge` (non usata); commento di `CostConfirmDialog.jsx` aggiornato.
- `translations.js` (it/en): `cvEditor.saveError`, `modeLabel`, `modeEdit`, `previewCaption`, `previewFrameTitle`, `multiPageHint`, `assistantButton`, `chatFocusRemove`, `bulletShown`, `removeArea`, `limitAreas`, `limitBullets`, `limitEducations`, `limitLanguages`, `areasCountOne/Many`, `companiesCountOne/Many`, `entriesCountOne/Many`, `selectedCount`, `noProfileItems`; `coverLetterEditor.removeParagraph`, `limitParagraphs`, `paragraphN`, `paragraphOpening`, `paragraphClosing`, `multiPageHint`, `previewFrameTitle`. Cambiati: `backToJob` senza freccia, "Aggiungi …" senza "+" (icona), `removeBullet` / `removeLanguage` / `removeEducation` più specifici ("Rimuovi punto elenco", …).

### Backend / API
Nessun cambio.

## E2e
Nessun e2e copriva gli editor. Nuovo `e2e/editor.spec.js` (5 test; dati creati con `manage.py shell` nel DB di prova: job con CV e cover letter modificabili, competenze del profilo, cronologia della chat, CV più recente):
| Test | Cosa verifica |
|---|---|
| editor del CV (390 px) | barra azione al posto della barra di tab; Sommario aperto, Esperienze chiusa con "2 aziende"; interruttore "Mostra nel CV"; "Aggiungi punto" (3 → 4); "Salvato"; Anteprima (iframe o avviso); nessuna larghezza in eccesso |
| assistente (390 px) | ✦ su un bullet → chip "Contesto" con ✕; pannello "Assistente bozza" con prezzo e saldo dell'API e avviso AI; "Accetta" → "Applicata" e sommario aggiornato; riaperto, la decisione resta |
| credito insufficiente | banner "Saldo credito insufficiente…", campo e "Invia" disattivati |
| bozza superata | finestra con "Riparti dal nuovo CV" e "Continua la bozza"; continuando si apre l'editor |
| cover letter (1280 px) | chat in colonna larga 400 px senza pulsante "Assistente"; 4 riquadri, "Paragrafo 1 · Apertura" / "Paragrafo 4 · Chiusura", `maxlength` 3000, aggiunta e rimozione |

Nessuna asserzione esistente cambiata.

## Verifica
- `npm run build`: OK. `npx oxlint src e2e`: 0 errori, 9 warning (gli stessi di prima).
- **E2e** sullo stack usa e getta (copia `/root/App-apply-dev`, immagini `appapply-e2e-*` ricostruite, Postgres/Redis temporanei, nessun codice d'invito né email, nessun dato reale): i 5 test nuovi passati al primo giro; **suite completa 43/43** (38 di prima + 5), nessun fallimento.
- **Screenshot** (Playwright, 360/390/1280 px, utente di prova): editor del CV chiuso e aperto (Esperienze, azienda, bullet puntato), anteprima, chat normale (proposta da decidere, proposta applicata, contesto), chat con avvisi (elemento non più nella bozza, scelta non salvata simulando il fallimento della richiesta), credito insufficiente (saldo 0,10 € < 0,20 €), bozza superata, cover letter (modifica e anteprima), desktop con la chat accanto. Nel controllo corretti: colonna della chat su desktop che finiva sotto la barra azione quando in cima c'è un avviso (altezza ora misurata fino alla barra), "Genera PDF finale" che a 360 px andava a capo, campi ricchi a 14 px (zoom dell'iPhone). Larghezza del documento = schermo in tutti i 37 stati misurati; nessun errore JavaScript.
- Backend non toccato: test backend non necessari. Stack di prova abbattuto; produzione non toccata (su `main`, container invariati, sito 200).

## Cosa manca / note
- Nel browser di prova (Chromium senza visualizzatore PDF) l'iframe dell'anteprima risulta bianco negli screenshot; nei browser reali il PDF si vede come prima (meccanismo invariato).
- Spostamento sopra la tastiera dell'iPhone non verificato su un dispositivo reale.
- La finestra "bozza superata" compare sopra una pagina vuota (la bozza non è ancora caricata), non sopra l'editor come nel mockup; stesse azioni.
- Proposta nella chat: resta il "prima" barrato (il mockup mostra solo il "dopo").
- Generazione AI e invio reale dei messaggi della chat non provati negli e2e (nessuna chiave AI nell'ambiente di prova).
