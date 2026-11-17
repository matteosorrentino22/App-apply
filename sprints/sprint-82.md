# Sprint 82 — Anteprima PDF degli editor, attività come chip, stipendio e contratto

> **Periodo:** 2026-11-16 · **Branch:** `sprint-82-anteprima-pdf` (da `main` al commit 811e1e2, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** (1) anteprima PDF: correzione implementata, build e lint OK, **da confermare a mano su iPhone e Android**; (2) attività come chip e (3) stipendio e contratto: **implementati e verificati** (backend 507/507, e2e 85/85); merge e deploy non fatti.

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

## Esito della prova a mano (parte 1)
- 2026-11-17, committente: su iPhone l'anteprima **resta bianca** anche con l'altezza esplicita; forse dipende dal browser. Il committente decide di rilasciare comunque lo sprint (la correzione non peggiora il desktop) e di riferire dopo la prova sull'app vera. Passo successivo se resta bianca: seconda opzione (iframe montato sempre) o un ripiego "Apri il PDF" (da decidere).

## Cosa manca / note
- Se l'anteprima resta bianca su uno dei due telefoni: seconda opzione (iframe montato sempre) o, su Android, un link "Apri il PDF" al blob URL come ripiego (aggiunta di interfaccia da decidere col committente).

---

# Parte 2 — Attività del Profilo come chip (richiesta ID 20)

> **Stato: implementato** (vedi "Implementazione delle parti 2 e 3" in fondo). Mockup approvati dal committente (2026-11-17): `profile-act-chip`, `profile-act-modifica`, `profile-act-errore`, `profile-act-vuoto`, `profile-act-limite`, `desk-profile-act` in `Docs/design/mockups/`.

## Cosa deve fare (funzionale)
- Le **attività** di ogni ruolo sono mostrate come **chip a angoli ridotti** (non più a pillola completa).
- **Tocco sul testo = modifica** dell'attività in un riquadro con contatore "n / 400" e pulsanti Annulla / Fatto. Il ✕ (area da 44 px) elimina.
- Il testo lungo è **troncato a 3 righe** nel chip; per leggerlo tutto si apre la modifica.
- Limiti invariati: 15 attività per ruolo, 400 caratteri. Oltre 400: messaggio "Un'attività supera i 400 caratteri: accorciala per poterla confermare." e "Fatto" disattivato. A 15: "Hai raggiunto il massimo di 15 attività" e "Elimina un'attività per poterne aggiungere un'altra." Nessuna attività: "Nessuna attività inserita."
- Suggerimento sotto il campo: "Tocca un'attività per modificarla. Al massimo 15 attività per ruolo, ciascuna fino a 400 caratteri."
- Le **tecnologie restano come sono** (decisione del committente).
- Vale ovunque il componente è usato (anche onboarding).

## Indicazioni per chi implementa (non vincolanti)
- `ChipInput.jsx` (oggi chip `rounded-full`, fino a 400 caratteri, solo ✕) è condiviso con le tecnologie: valutare una variante per le attività invece di cambiare il comportamento delle tecnologie. Nessuna dipendenza nuova.
- Colori e raggi: `DESIGN.md` §3 (chip `#f3e8d6`, raggio dei chip delle attività 10 px, bersagli ≥ 44 px).
- Nessuna modifica a API, modello dati o limiti del server.

---

# Parte 3 — Stipendio e contratto (richiesta ID 7, ID 15 limitato)

> **Stato: implementato** (vedi in fondo). Mockup approvati (2026-11-17): `detail-stipendio-contratto`, `detail-solo-contratto`, `jobs-filtri-contratto`, `jobs-filtri-contratto-attivi`. Decisioni in `SPEC-DELTA.md` A16 e B12.

## Cosa deve fare (funzionale)
- **Dettaglio job:** sotto "azienda · località" una riga di chip con **stipendio** (evidenziato, icona banconote) e **tipo di contratto** (neutro, icona valigetta), della stessa dimensione dei chip dei candidati. Si mostra solo il dato presente; senza dati la riga non compare. Lo stipendio è mostrato **come arriva dalla fonte** (nessun periodo, nessuna conversione di valuta).
- **Filtri della lista:** due nuovi gruppi nel pannello Filtri: **Contratto** (pillole a selezione multipla: Full-time, Part-time, Temporaneo, solo i valori previsti) e **Stipendio** (segmenti **Tutti / Con stipendio / Senza stipendio**, come Recruiter). Si combinano in AND con gli altri filtri, con OR dentro il multiplo; "Azzera filtri" e il conteggio dei filtri attivi li includono.
- **La card di lista non cambia.**
- I job raccolti **prima** di questo sprint non hanno il contratto (e lo stipendio non è mai stato salvato): restano fuori dai filtri attivi, come "candidati" per i job senza il dato.
- **Esclusi** per decisione del committente: data di inizio (la fonte non la fornisce), filtro per importo (valuta e periodo ignoti), modalità remote/hybrid/on-site (rimandata, `SPEC-DELTA.md` B12; tracking ID 15 e ID 27).

## Dati disponibili dalla fonte (misurati su una raccolta di prova, 122 annunci)
- `salaryInfo`: lista di stringhe (es. "$91000.00"), presente nel 35 % dei casi, in dollari, periodo non indicato.
- `contractType`: sempre presente (Full-time, Part-time, Temporary).
- Nessun campo per la data di inizio; `workType` vuoto; modalità remote solo nel testo della descrizione.

## Indicazioni per chi implementa (non vincolanti)
- **Bug esistente:** `_normalize_item` (`apps/jobs/sources/apify_linkedin.py`) legge `item.get("salary")` ma il campo della fonte è `salaryInfo`: `Job.salary` oggi resta sempre vuoto anche se `JobDetailPage.jsx` lo stampa già. Mappare `salaryInfo` (lista) in una stringa leggibile, ad es. intervallo con due valori; rispettare il `max_length` 255 (un job oltre il limite è scartato, §5 della spec tecnica).
- **Nuovo campo** per il tipo di contratto sul modello `Job` (con migrazione), valori normalizzati, esposto nel `JobSerializer`; parametri di filtro in `GET /api/jobs/` (es. `contract` CSV e `salary` yes|no|all) e nei valori ammessi di `utils/jobFilters.js`; `JobFiltersSheet.jsx`; query string come gli altri filtri. Da decidere se i filtri salvati (§4.21) includono i due nuovi gruppi (vedi punti da verificare).
- Nessuna chiamata aggiuntiva alla fonte: i dati sono già nella risposta della raccolta. Nessuna dipendenza nuova.
- Aggiornare in questo sprint: spec 01 (§4.5, §4.6, §4.21) e 02 (modello dati, API §12, test §13), test backend delle fonti e della lista, `job-list.spec.js`.

## Punti da verificare in revisione
1. **Sprint unico:** su richiesta del committente le parti 2 e 3 sono nello stesso sprint 82 e sullo stesso branch della correzione dell'anteprima: valutare se separare i commit al momento dell'implementazione.
2. **Filtri salvati:** i nuovi gruppi Contratto e Stipendio vanno salvati nei filtri preferiti? Non deciso.
3. **Stipendio senza periodo:** un importo come "$91.000" può essere annuo o orario; il committente ha scelto di mostrarlo così com'è. Rivedere se gli utenti lo trovano fuorviante.
4. **Valute:** la fonte restituisce dollari anche per annunci europei (campione piccolo): da verificare su più annunci prima di mostrare il simbolo.
5. **Dati storici:** i job già raccolti non hanno il contratto; nessun recupero previsto.
6. **Test su telefono:** la parte 1 (anteprima) resta da provare a mano su iPhone e Android prima del merge.
7. Specifiche 01/02: le parti 2 e 3 non sono ancora descritte come as-is; vanno aggiornate nello stesso commit dell'implementazione.

---

# Implementazione delle parti 2 e 3

## Decisioni prese col committente (prima di implementare)
- **Filtri salvati:** includono i nuovi gruppi Contratto e Stipendio (due campi sul preset, migrazione); i preset salvati prima restano senza (= tutti).
- **Tipi di contratto:** si salvano tutti i valori della fonte normalizzati (`full_time`, `part_time`, `temporary`, `contract`, `internship`, `volunteer`, `other`) e il dettaglio li mostra tradotti; il filtro propone solo Full-time, Part-time, Temporaneo, come da mockup.
- **Formato dello stipendio:** come il mockup, uguale in it e en: simbolo della fonte, decimali `.00` tolti, migliaia con il punto, decimali veri con la virgola, due valori uniti da " – " (es. `["$91000.00", "$136500.00"]` → "$91.000 – $136.500"). Nessun periodo, nessuna conversione.
- **Fonte:** contratto e stipendio solo dalla raccolta Apify; i job importati da link o inseriti a mano restano senza (parser della pagina guest invariato).

## Parte 2 — Attività come chip
- Nuovo `components/ActivityChipsInput.jsx` (stessa interfaccia di `ChipInput`: lista di stringhe, `maxLength`, `flagTooLong`, più `maxItems`), usato da `ExperienceGroupEditor` per le attività; le **tecnologie restano su `ChipInput`**, invariato.
- Chip ad angoli ridotti (raggio 10 px, sfondo `primary-soft`), testo troncato a 3 righe (`line-clamp-3`); tocco sul testo = modifica in un riquadro con contatore "n / 400", Annulla / Fatto (Invio conferma, Esc annulla); oltre 400 caratteri bordo e contatore rossi, messaggio e "Fatto" disattivato; ✕ in un'area di 44 px; contatore "n / 15" accanto all'etichetta; a 15 attività il campo è disattivato con il messaggio e il suggerimento "Elimina un'attività…"; senza attività "Nessuna attività inserita.". Vale anche nell'onboarding.
- Testi (it/en): `profileExtras.activitiesTapHint`, `activitiesEmpty`, `activitiesMaxReached`, `activitiesMaxHint`, `activityEdit`, `activityEditLabel`, `activityDone`, `activityTooLong`; nuovo segnaposto `onboarding.activitiesPlaceholder` ("Scrivi un'attività e premi Invio"). L'etichetta del campo resta "Attività / competenze in questo ruolo" (il mockup dice "Attività": tenuta per non cambiare il testo condiviso con l'onboarding e gli e2e).
- Nessuna modifica a API, modello o limiti del server.

## Parte 3 — Stipendio e contratto
- **Bug corretto:** `_normalize_item` leggeva `salary`, campo che la fonte non usa: ora legge `salaryInfo` (`_format_salary`, massimo 255 caratteri) con ripiego su `salary`.
- **Modello:** `Job.contract_type` (choices `Job.ContractType`), `JobFilterPreset.contract_types` e `has_salary`; migrazione `jobs/0023_contract_type_and_filters` (solo campi nuovi con default vuoto: nessun dato esistente cambia).
- **Raccolta:** `contract_type` da `contractType` (`_normalize_contract_type`, valore ignoto = vuoto), salvato in `collection.py`.
- **API:** `JobSerializer.contract_type`; `GET /api/jobs/?contract=<CSV>&salary=yes|no|all` (400 con valori non ammessi, due messaggi nuovi in `gettext` tradotti nel `.po`, `.mo` ricompilato); preset con `contract_types` e `has_salary`.
- **Frontend:** `JobDetailPage` riga di chip sotto "azienda · località" (stipendio evidenziato con icona banconote, contratto neutro con icona valigetta, solo se presenti; la retribuzione non è più nella riga di testo); `JobFiltersSheet` gruppi Contratto (pillole multiple) e Stipendio (segmenti); `JobListPage` parametri `contract` e `salary` nella query string, conteggio dei filtri attivi, "Azzera filtri", salvataggio e applicazione dei preset; `utils/jobFilters.js` `CONTRACT_TYPES`, `SALARY_VALUES`. **Card di lista invariata.**
- Dati di prova e2e (`seed_e2e_jobs`): stipendio e contratto su quattro job.

## Verifica (parti 2 e 3)
- `npm run build` OK; `npx oxlint src e2e` 0 errori, 9 warning (gli stessi); tutte le chiavi usate esistono in it ed en (631).
- Backend: `manage.py test` in un container usa e getta (`-e DJANGO_DEBUG=true -e REGISTRATION_INVITE_CODE=`): **507 test OK** (19 nuovi in `apps/jobs/test_sprint82.py`); `makemigrations --check` nessuna differenza.
- **E2e completa** sullo stack usa e getta (un worker, runner limitato a 1,4 GB, anteprima spenta durante la prova): **85/85** in 17 minuti (82 di prima + filtri Contratto e Stipendio con preset, dettaglio con / senza dati, attività come chip). Lo spec di impaginazione (Chromium 360/390/1280, iPhone 13 e iPhone SE in WebKit) passa anche con i chip nel Profilo e nell'onboarding.
- Le immagini dello stack di prova (`appapply-e2e-*`) sono state ricostruite (`docker compose -p appapply-e2e … build web frontend-build`).
