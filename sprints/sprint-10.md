# Sprint 10 — Generazione CV (pipeline)

## Input
- Sprint 04 completato (profilo); modello `CVDocument` (Sprint 02).
- Riferimenti: `01-specifiche-funzionali-v4.md` §4.7; `02-specifiche-tecniche-v3.md` §3.6, §6.

## Obiettivo
Servizio di generazione CV: raccolta contesto (profilo + job + arricchimento opzionale) → chiamata Claude per i contenuti → composizione template HTML flessibile (numero di esperienze variabile, sezione istruzione invariata, foto opzionale, lingua) → conversione PDF con WeasyPrint → salvataggio in `CVDocument`.

## Risultato atteso
Dati un `Profile` e un `Job`, invocando il servizio si ottiene un `CVDocument` con `html_source` e `pdf_file` popolati, rispettando 1 pagina, l'opzione foto, la lingua richiesta e la sezione istruzione identica al profilo.

## Criteri di verifica
- Invocando il servizio su un profilo di test con 3 esperienze e uno con 1 sola esperienza, l'HTML generato contiene rispettivamente 3 e 1 blocchi "esperienza" (nessun placeholder fisso).
- Il PDF generato risulta di 1 pagina per un profilo di dimensioni standard di test (verifica sul numero di pagine del PDF).
- Con `cv_include_photo=False` il PDF non contiene l'immagine anche se il profilo ha una foto caricata; con `True` la contiene.
- Il testo della sezione istruzione nel PDF/HTML corrisponde esattamente ai dati di `Education` del profilo, senza riformulazione.
- Con `cv_language_mode='english'` il contenuto è in inglese indipendentemente dalla lingua della job description di test; con `'job_language'` segue la lingua della job description di test.
- Il `CVDocument` salvato referenzia correttamente `job` e `user`.

## Output per lo sprint successivo
Servizio di generazione CV riusabile sia dal ciclo notturno automatico (Sprint 11) sia dalla generazione manuale (Sprint 12).