# Sprint 82 — Anteprima PDF degli editor su mobile

> **Periodo:** 2026-11-16 · **Branch:** `sprint-82-anteprima-pdf` (da `main` al commit 811e1e2, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** correzione implementata, build e lint OK, **da confermare a mano su iPhone e Android** nell'anteprima; merge e deploy non fatti.

## Input
Segnalazione del committente dopo il rilascio del redesign: nell'editor del CV e della cover letter la scheda "Anteprima" resta **bianca** su iPhone (Safari) e Android (Chrome); su Chrome desktop funziona; con il vecchio design (Sprint 69) funzionava anche da mobile. Indicazione: ripristinare un'altezza esplicita e tenere la proporzione A4 solo da desktop; se non basta, montare l'iframe anche fuori dalla scheda attiva. L'iframe resta; nessuna dipendenza, nessun cambio di API, CSP o PDF.

Numero: `git log` e `ls sprints/` arrivano a 81.

## Analisi
- **Sprint 69:** `<iframe className="h-[70vh] w-full …">` sempre montato (su mobile sotto l'editor).
- **Sprint 76 → 81 (`components/editor/EditorPreview.jsx`):** `aspect-[210/297] w-full max-w-[640px]` dentro `flex flex-col items-center`, senza altezza; l'iframe esiste solo con la scheda "Anteprima" attiva (`EditorShell`: `mode === 'edit' ? editor : preview`).
- **Server:** sull'anteprima (DEPLOY §10), con l'utente di prova, `POST /api/jobs/<id>/cv-draft/preview/` e `/cover-letter-draft/preview/` rispondono `200 application/pdf` (15 KB e 9 KB, intestazione `%PDF-`): il PDF arriva, il problema è nella visualizzazione.
- **Ipotesi:** i visualizzatori PDF incorporati dei browser mobili dimensionano il documento sull'altezza dell'iframe al momento del caricamento; con un'altezza ricavata solo da `aspect-ratio` dentro un contenitore flex centrato il calcolo può risultare nullo o tardivo e la pagina resta bianca. Non verificabile in Playwright (Chromium headless e WebKit non visualizzano PDF).

## Correzione (prima opzione)
- `EditorPreview.jsx`: iframe `h-[70vh] min-h-[420px] w-full max-w-[640px]` centrato con `mx-auto block`; `lg:h-auto lg:min-h-0 lg:aspect-[210/297]` (da 1024 px la proporzione A4 di prima, dove funzionava). Contenitore non più `items-center`.
- **Non fatto (seconda opzione, solo se la prima non basta):** montare l'iframe anche quando la scheda attiva è "Modifica". Rimandata perché un iframe nascosto (`display: none`) caricato a dimensione zero può peggiorare proprio sui visualizzatori mobili; si decide dopo la prova a mano.

## Verifica
- `npm run build` OK; `npx oxlint src e2e` 0 errori, 9 warning (gli stessi).
- Anteprima (DEPLOY §10) aggiornata al branch; il CSS servito contiene la nuova regola; PDF di anteprima generati dal server per CV e cover letter.
- E2e non eseguiti: le immagini dello stack di prova non sono più sul server e la modifica è solo di stile su un componente; `editor.spec.js` verifica l'anteprima come "iframe o avviso", invariato. Da eseguire alla prossima suite completa (un worker, runner con limite di memoria, DEPLOY §4.4).
- **Nota operativa:** `preview.sh` usa l'immagine `appapply-e2e-frontend-build`, non più presente; per questo aggiornamento le è stato dato quel nome sull'immagine `app-apply-frontend-build:latest` della produzione (stesso `package.json`, i sorgenti vengono copiati dal branch). Solo un tag, la produzione non è toccata.

## Da provare a mano (anteprima, dal telefono)
iPhone (Safari e app dalla Home) e Android (Chrome): job con CV → "Modifica CV" → scheda "Anteprima"; stesso per "Modifica Cover Letter". Atteso: PDF visibile (almeno la prima pagina) in un riquadro alto circa 2/3 dello schermo; tornando a "Modifica", cambiando un campo e riaprendo "Anteprima" il PDF si aggiorna.

## Cosa manca / note
- Se l'anteprima resta bianca su uno dei due telefoni: seconda opzione (iframe montato sempre) o, su Android, un link "Apri il PDF" al blob URL come ripiego (aggiunta di interfaccia da decidere col committente).
