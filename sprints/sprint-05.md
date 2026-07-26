# Sprint 05 — Import CV esistente (parsing)

## Input
- Sprint 04 completato (API profilo disponibile).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.1; `02-specifiche-tecniche-v3.md` §3.5, §5.4.

## Obiettivo
Endpoint di upload CV (PDF/Word): estrazione testo lato server (`pdfplumber`/`pypdf`, `python-docx`), chiamata a Claude per strutturare il testo nelle sezioni del profilo master, con pre-popolamento modificabile prima del salvataggio; gestione del fallback per testo vuoto/irrisorio (PDF scansione/immagine).

## Risultato atteso
Caricando un CV leggibile, la risposta API contiene un profilo pre-popolato coerente col contenuto del file, non ancora salvato come definitivo; caricando un PDF scansione/immagine, l'utente riceve il messaggio di fallback e nessun profilo vuoto viene creato.

## Criteri di verifica
- Upload di un CV PDF testuale di prova → risposta con sezioni pre-popolate (sommario, almeno un'esperienza, istruzione) coerenti col file.
- Upload di un CV `.docx` di prova → stesso comportamento.
- Upload di un PDF scansione/immagine senza testo estraibile → risposta con messaggio di fallback dedicato; nessuna scrittura di profilo vuoto in DB.
- Il payload inviato a Claude contiene solo testo estratto, non il file binario (verificabile via log/mock della chiamata).
- I dati pre-popolati restano modificabili: una successiva chiamata di salvataggio con campi alterati sovrascrive correttamente i valori proposti.

## Output per lo sprint successivo
Pipeline di estrazione testo riusabile; profilo popolabile sia manualmente sia da upload, pronto per la creazione delle ricerche (Sprint 06).