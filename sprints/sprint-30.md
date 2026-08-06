# Sprint 30 — Fix post-deploy: generazione CV e messaggi d'errore fuorvianti

## Input
Test manuali del committente dopo il deploy degli Sprint 26-29, da cui sono
emersi due bug reali in produzione.

## Esito (2026-08-02)

### Bug 1 — Generazione CV falliva sempre con 400 (bloccante)
Ogni chiamata reale a Claude falliva: `output_config.format.schema: For
'array' type, 'minItems' values other than 0 or 1 are not supported`.
Causa: `ai_content.py` (Sprint 27) aggiungeva `minItems`/`maxItems` allo
schema JSON delle Areas of Expertise per rinforzare il vincolo 4-6 voci —
vincolo non supportato dall'API Anthropic per gli output strutturati.
Rimosso dallo schema; il vincolo resta solo nel prompt testuale, come già
per `experiences`/`bullets`. Verificato con una chiamata reale a Claude
post-fix: generazione riuscita, contenuto corretto.

### Bug 2 — Messaggio d'errore fuorviante su "generazione già in corso"
Il pop-up "Generazione già in corso per questo job" compariva anche quando
la vera causa era un'altra (osservato: profilo senza titolo di studio,
Sprint 26 §10.2). Causa: `JobDetailPage.jsx` intercettava qualunque errore
HTTP 409 e mostrava sempre lo stesso testo fisso, ignorando il campo
`detail` che il backend restituisce già con il messaggio esatto (il
backend distingue correttamente tre cause dietro lo stesso codice 409:
concorrenza, profilo incompleto, massimale/credito esaurito — ma il
frontend le appiattiva tutte sullo stesso messaggio). Corretto per
mostrare `detail` quando presente, con il vecchio testo come fallback.

### Verifica eseguita
- `python manage.py test`: 166/166 passati, nessuna regressione.
- Generazione CV reale end-to-end (vera chiamata Claude) sul job che
  falliva in produzione: riuscita, PDF corretto.
- Frontend: `npm run build` e `oxlint` sul file toccato — puliti.
- Aggiornato il test e2e `job-list.spec.js` (Sprint 29) che asseriva
  ancora il vecchio messaggio fisso, mascherando la vera causa nel suo
  stesso commento.

### Cosa manca
Nessuno dei due fix introduce nuovi punti aperti. Resta valido quanto già
segnalato negli sprint precedenti (calibrazione parametri, qualità reale
dei contenuti, suite e2e da eseguire su ambiente dedicato).
