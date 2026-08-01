# Sprint 28 — Nuovo template CV e loop di ripiego overflow (contenuto CV, fase 3/4)

## Input
Sprint 27 completato (pipeline contenuti AI e selezione server-side). Il
template attuale non riproduceva il layout proposto dal committente (PDF di
riferimento) — confronto fatto insieme durante la discussione: header
centrato con qualifica, "Areas of Expertise" a due colonne, esperienze con
azienda in maiuscolo e ruolo in grassetto su righe separate, riga tecnologie
in corsivo, certificazioni e competenze unite in un unico paragrafo, lingue
in riga orizzontale centrata.

## Obiettivo
- Riscrivere `cv_template.html` per riprodurre il layout di riferimento.
- Aggiungere `Experience.technologies` al contenuto del CV (già raccolto in
  onboarding, mai arrivato al template — gap segnalato da
  `02-specifiche-tecniche-v4.md` §4.2, "una riga per ogni esperienza").
- Etichette di sezione che seguono `cv_language_mode` (§4 del doc 03).
- Implementare il loop di ripiego per overflow (§6, §11 punto 6): rimozione
  di un bullet alla volta (il globalmente meno rilevante) con
  rirenderizzazione, tetto di 4 iterazioni, caso residuale silenzioso
  (PDF multi-pagina salvato, evento in `RunLog`, nessun errore utente).
- Verificare il contratto dei template (§7): due profili worst-case (A: max
  bullet, B: max istruzione) entrano in 1 pagina.

## Esito (2026-08-01)

### Nuovo template
`cv_template.html` riscritto secondo il riferimento: header centrato con
qualifica sotto il nome, contatti con separatori, sezione Areas of
Expertise a due colonne (CSS grid), esperienze con azienda/location su una
riga e ruolo/date sulla riga sotto, riga tecnologie in corsivo dopo i
bullet, certificazioni+competenze in un unico paragrafo ("Certified in" /
"Skilled in"), lingue centrate in riga. Verificato con rendering reale
(non solo test automatici): screenshot del PDF prodotto confrontato
visivamente col riferimento del committente.

### Tecnologie per esperienza
`Experience.technologies` (dato fattuale del profilo, mai riformulato
dall'AI) viene riattaccato lato server per indice dopo la chiamata Claude
(`_attach_technologies` in `generation.py`) — non richiesto al modello,
coerente col trattamento di `location`/`dates`. Mostrato nel template come
riga "Technologies: ..." per esperienza, seguendo `cv_language_mode`.

### Etichette di sezione multilingua
Nuovo dizionario `SECTION_LABELS` (it/en) in `generation.py`, iniettato nel
context come `labels`. Segue la stessa granularità it/en già usata per
`html_lang` — limite preesistente non introdotto in questo sprint: la
modalità "lingua della job description" può produrre contenuto in
qualunque lingua, ma le etichette fisse restano binarie it/en, come già
era `html_lang` prima di questo sprint.

### Loop di ripiego per overflow
- `selection.py`: i bullet restano `{text, relevance_rank}` (non più
  appiattiti a stringa) fino a un passo esplicito (`flatten_bullets_to_text`)
  subito prima del rendering — necessario perché il loop di ripiego deve
  poter continuare a rimuovere per rilevanza dopo il primo rendering.
  Nuova funzione `remove_least_relevant_bullet`: rimuove, tra tutte le
  esperienze mostrate, il bullet col rank più alto (meno rilevante); muta
  la lista in place, ritorna `False` quando non resta nulla da rimuovere.
- `generation.py`: `_render_with_overflow_retry` orchestra il loop — dopo
  il primo rendering (già con i 3 livelli di compattamento esistenti), se
  il PDF risulta multi-pagina rimuove un bullet e rirenderizza, fino a
  `MAX_OVERFLOW_ITERATIONS` (4, nuovo parametro in `cv_parameters.py`).
  Esaurite le iterazioni senza rientrare in 1 pagina, il PDF multi-pagina
  viene salvato comunque (nessun errore all'utente), con un `RunLog` di
  esito `SUCCESS` e messaggio esplicativo per diagnosi.
- Non ancora implementata la protezione "priorità massima" dei bullet di
  arricchimento (ultimi a essere rimossi, §5.6): rimandata allo Sprint 29,
  quando l'arricchimento viene ristrutturato per agganciarsi a
  un'esperienza esistente — marcare quei bullet come protetti ha senso
  farlo insieme a quella ristrutturazione, non prima.

### Verifica eseguita
- **Contratto dei template (§7), entrambi i profili worst-case**: renderizzati
  manualmente in shell — Worst case A (1 istruzione, B=12, 5 esperienze a
  budget pieno, 6 Areas of Expertise, 2 righe skills/certificazioni,
  lingue) e Worst case B (3 istruzioni, B=9, stesso resto) — **entrambi
  1 pagina**, senza nemmeno bisogno del loop di ripiego (solo i 3 livelli
  di compattamento esistenti sono bastati): buon margine di sicurezza.
- **Loop di ripiego attivato realmente**: nuovo test
  `test_overflow_is_resolved_by_removing_bullets_one_at_a_time` con
  contenuto sovradimensionato (5 esperienze, 8 bullet ciascuna, testo
  lungo) — verificato che il PDF finale sia 1 pagina grazie alle rimozioni.
- **Caso residuale**: nuovo test
  `test_residual_multi_page_case_is_saved_without_error_and_logged` — con
  contenuto fisso (sommario + note istruzione) sufficientemente grande da
  restare multi-pagina anche dopo aver esaurito le 4 iterazioni (che
  rimuovono solo bullet, non contenuto fisso): verificato che il CV venga
  comunque salvato, senza eccezione, con un `RunLog` che riporta
  "multi-pagina" nel messaggio.
- **Verifica visiva end-to-end**: generato un CV realistico completo
  (profilo con foto assente, 2 esperienze con tecnologie, istruzione,
  competenze, certificazioni, lingue) con l'intera pipeline reale (solo
  `generate_cv_content` mockato, tutto il resto — selezione, taglio,
  rendering, PDF — codice reale) e confrontato visivamente il PDF prodotto
  col riferimento del committente: layout coerente.
- `python manage.py test`: **160/160 passati** (154 pre-esistenti + 6
  nuovi: 4 su `selection.py` per le nuove funzioni di overflow, 2 di
  integrazione su `generate_cv`); `makemigrations --check --dry-run` pulito.

### Cosa manca
- Protezione "priorità massima" per i bullet di arricchimento nel taglio al
  budget e nel loop di ripiego: **Sprint 29** (va di pari passo con la
  ristrutturazione dell'arricchimento vincolato a un'esperienza esistente).
- Calibrazione reale dei valori parametrici e qualità dei contenuti (stessa
  nota degli sprint precedenti: nessuna `ANTHROPIC_API_KEY` di test isolata
  in questo ambiente).
- Testi esatti di guida alla compilazione e messaggi (già segnalato come
  punto aperto dal documento stesso, §14).
