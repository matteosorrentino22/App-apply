# Sprint 83 — Anteprima PDF degli editor su iPhone e Android

> **Periodo:** 2026-11-17 · **Branch:** `sprint-83-anteprima-header` (da `main` al commit cd6d59a, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato; build e lint OK, `editor.spec.js` 7/7; da provare dal telefono sull'anteprima; **merge e deploy non fatti**.

## Input
Dopo lo Sprint 82 in produzione l'anteprima PDF degli editor (CV e cover letter) restava bianca su iPhone (Safari, app dalla Home) e su Android (Chrome); su Chrome desktop funzionava. L'iframe deve restare.

Numero: `git log` e `ls sprints/` arrivano a 82.

## Diagnosi (prova a mano del committente, 2026-11-17)
- **Codice:** richiesta del PDF (`fetch` + `response.blob()`), tipo del Blob (`application/pdf`), creazione e revoca del blob URL identici allo Sprint 69; il blob non viene revocato prima del caricamento (solo quando arriva un PDF nuovo o all'uscita dall'editor; lo Strict Mode raddoppia gli effetti solo in sviluppo). Diversi solo montaggio (scheda Anteprima) e altezza dell'iframe.
- **Header:** CSP identica dallo Sprint 66 (`frame-src blob:`, `object-src blob:`, `frame-ancestors 'none'`), `X-Frame-Options: DENY`.
- **Pagina di prova temporanea** sull'anteprima (branch `prova-anteprima-pdf`, non su `main`): lo stesso PDF campione in sei modi (A iframe da blob, B iframe con URL normale, C `<object>`, D `<embed>`, E link "Apri il PDF", F `navigator.pdfViewerEnabled`), con header allentati; in più due varianti con gli header della produzione ("rigida") e con la modifica proposta ("self"); e la versione di prima del redesign (tag `pre-redesign`) sotto `/v1/`.
- **Esito su iPhone (iOS 18, Safari):** `pdfViewerEnabled` vero; A e B visibili con header allentati; C e D no; E apre il PDF; **A bianco con gli header della produzione, visibile con `frame-ancestors 'self'`**; anche la versione di prima del redesign è bianca.
- **Esito su Android (Chrome):** `pdfViewerEnabled` **falso**; A bianco; E scarica il file.
- **Conclusione:** su iPhone il documento del PDF in blob eredita la CSP della pagina che lo crea e `frame-ancestors 'none'` gli vieta di stare nell'iframe (presente dallo Sprint 66, per questo anche il vecchio design era bianco); Chrome per Android non ha un visualizzatore PDF incorporato, quindi nessun iframe può mostrarlo.

## Decisioni del committente
- iPhone: cambiare gli header.
- Android: al posto dell'iframe un avviso ("L'anteprima del PDF non è disponibile in questo browser. Il PDF finale si scarica con «Genera PDF finale»."), senza pulsante di download (scaricare un file non è un'anteprima).

## Implementazione
- `docker/caddy/Caddyfile.prod` (e il modello `docker/preview/Caddyfile.preview`): CSP `frame-ancestors 'self'` e `X-Frame-Options: SAMEORIGIN` (prima `'none'` / `DENY`). L'app resta non incorniciabile da altri siti; Django mantiene `XFrameOptionsMiddleware` (Caddy ne sostituisce il valore).
- `components/editor/EditorPreview.jsx`: se `navigator.pdfViewerEnabled === false` avviso `cvEditor.previewNoViewer` (it/en) al posto dell'iframe; l'indicatore delle pagine resta. Vale per CV e cover letter.
- Nessun cambio di API, backend, PDF o dipendenze.

## Verifica
- `caddy validate` del Caddyfile di produzione e di quello dell'anteprima: validi.
- `npm run build` OK; `npx oxlint src e2e` 0 errori, 9 warning (gli stessi); tutte le chiavi usate esistono in it ed en (632).
- `editor.spec.js` sullo stack usa e getta (un worker, runner limitato): primo giro 5/6, il fallimento era un'asserzione da aggiornare (il Chromium headless dei test non ha un visualizzatore PDF e ora mostra l'avviso); dopo l'aggiornamento e il test del caso opposto **7/7**. Backend non toccato.
- Pulizia della prova: anteprima spenta, Caddyfile e compose dell'istanza ripristinati, volume `/v1` e copia temporanea cancellati; il branch `prova-anteprima-pdf` resta su GitHub finché il committente non decide.

## Da provare (anteprima, poi produzione dopo il rilascio)
- iPhone (Safari e app dalla Home): "Modifica CV" e "Modifica Cover Letter" → scheda Anteprima: il PDF si vede.
- Android (Chrome): stessa scheda: compare l'avviso, nessun riquadro bianco.

## Cosa manca / note
- Il rilascio cambia il Caddyfile di produzione: il file è montato come file singolo; dopo il fast-forward va ricreato il container `caddy` (pochi secondi), come nel rilascio del redesign (`Docs/design/RELEASE.md` §4).
- Cancellare il branch `prova-anteprima-pdf` dopo la conferma.
