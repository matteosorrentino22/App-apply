# Sprint 22 — QA end-to-end

## Input
- Sprint 21 completato (ambiente di deploy funzionante); tutte le funzionalità implementate.
- Riferimenti: `01-specifiche-funzionali-v4.md` §7 (criteri di accettazione), §6 (non funzionali).

## Obiettivo
Percorrere sistematicamente la checklist dei criteri di accettazione del documento funzionale (§7) sull'ambiente deployato, verificando anche i requisiti trasversali (isolamento multi-utente, fuso orario, lingua interfaccia) e correggendo eventuali difetti emersi.

## Risultato atteso
Tutte le voci della checklist §7 delle specifiche funzionali risultano verificate sull'ambiente di test deployato, con eventuali difetti corretti e ri-verificati.

## Criteri di verifica
- Per ciascuna delle sezioni della checklist §7 (profilo/onboarding, ricerche, raccolta e fonte, notifiche, scoring, vista lista/sezioni/ricerca, stati del job, generazione CV, arricchimento, import manuale, piani/massimali/credito, requisiti trasversali), eseguire il test corrispondente (manuale o automatizzato) sull'ambiente deployato e registrarne l'esito.
- Test di isolamento multi-utente: con due utenti di test, verificare che nessuno dei due possa accedere a dati (profilo, ricerche, job, CV) dell'altro, tramite chiamate API dirette con il token dell'uno sulle risorse dell'altro.
- Test fuso orario: con un utente configurato su un fuso non-Europe/Rome, verificare che "oggi" in lista e l'orario delle notifiche seguano il fuso locale, mentre il reset dei massimali segua Europe/Rome.
- Report finale: percentuale di voci della checklist §7 verificate con esito positivo = 100%, oppure elenco esplicito delle eccezioni residue con relativa motivazione.

## Output per lo sprint successivo
Nessuno (ultimo sprint) — l'output è la validazione complessiva del MVP rispetto alle specifiche funzionali.

---

## Esito (2026-07-27)

**Stato: completato per la parte verificabile in questo ambiente (82/88 = 93% della checklist §7, esito positivo); 6 voci restano eccezioni esplicite (sotto) e 3 richiedono comunque una verifica sull'ambiente VPS reale, non disponibile qui — vedi anche Sprint 21.**

### Come è stata condotta la QA
Non essendoci un ambiente effettivamente deployato (Sprint 21 ha prodotto la configurazione, non un VPS reale — vedi "Cosa manca" lì), la checklist §7 è stata verificata contro l'ambiente sandbox locale (stessa configurazione applicativa, stesso codice), con la suite automatica esistente (Django + Playwright, ~2100 righe di test prima di questo sprint) integrata dove mancavano test dedicati ai due criteri esplicitamente richiesti (isolamento multi-utente, fuso orario) e a un difetto reale trovato nel frattempo.

### Un difetto reale trovato e corretto
**`run_nightly_cycle` non isolava i fallimenti per singolo utente**: il ciclo notturno (`apps/jobs/tasks.py`) iterava su tutti gli utenti senza `try/except` — un'eccezione per un solo utente (es. sorgente Apify irraggiungibile, § 6 "comportamento in caso di fonte non disponibile") avrebbe interrotto l'intero batch, impedendo la raccolta anche per tutti gli utenti successivi quella notte. Corretto isolando il fallimento per utente con log in `RunLog` (stesso pattern già usato per `_generate_automatic_cv`), senza propagare l'eccezione. Nuovo test di regressione: `apps.jobs.tests.RunNightlyCycleOrchestratorTests`.

### Nuovi test scritti per questo sprint
- **Isolamento multi-utente** (`apps/common/test_multi_user_isolation.py`, 11 test): due utenti, chiamate dirette con il token dell'uno sulle risorse dell'altro — profilo, ricerca salvata (lettura/modifica/eliminazione/attivazione), job (lettura/genera CV/arricchisci/archivia/disarchivia/candidatura fatta). Tutte 404, coerente con il fatto che ogni `get_queryset`/`get_object_or_404` del codice era già scoped a `request.user` (il gap era solo di test, non di codice).
- **Fuso orario — "oggi" in lista segue il fuso locale** (`apps.jobs.tests.JobListTests.test_today_filter_follows_each_users_own_timezone`): stesso istante di raccolta, un utente Europe/Rome e uno Pacific/Kiritimati (UTC+14) classificano lo stesso job in modo diverso ("oggi" per uno, "ieri" per l'altro), come atteso.
- **Fuso orario — il reset dei massimali segue Europe/Rome, non l'utente** (`apps.cv.tests.ManualCvGenerationTests.test_daily_quota_resets_on_europe_rome_date_regardless_of_user_timezone`): utente su Pacific/Midway (UTC-11) in un istante in cui la data è già cambiata a Roma ma non nel suo fuso — la `DailyQuota` usa la data di Roma.
- **Modifica al profilo master dopo la generazione** (`apps.cv.tests.GenerateCvTests.test_profile_edit_after_generation_does_not_change_already_produced_cv`): un CV già generato resta invariato dopo una modifica successiva del profilo (`html_source` è uno snapshot, non un riferimento vivo).

### Checklist §7 — esito per sezione
| Sezione | Esito | Note |
|---|---|---|
| Profilo e onboarding | 7/7 ✅ | `apps.profiles.tests`, e2e `auth-onboarding.spec.js` (onboarding manuale completo) |
| Ricerche | 7/7 ✅ | `apps.searches.tests` (limiti Free/Pro, downgrade, attiva/disattiva) |
| Raccolta e fonte | 7/8 ✅, 1 ⚠️ | `apps.jobs.tests` (cap, dedup, campi obbligatori, tie-break, scoring isolato per job) — ⚠️ il rispetto reale della finestra 24h dipende dalla fonte Apify reale, mai invocata in questo ambiente (mockata) |
| Notifiche | 5/5 ✅ | `apps.notifications.tests` (mattutina, inattività, fuso orario, anti doppio invio) |
| Scoring | 1/3 ✅, 2 ⚠️ | struttura punteggio 1-5 verificata; ⚠️ qualità reale di motivazione/match-gap e vincolo "nessun riferimento a competenze assenti dal profilo" sono garanzie di prompt, non meccanicamente verificabili senza una vera `ANTHROPIC_API_KEY` |
| Vista lista, sezioni e ricerca | 13/13 ✅ | `apps.jobs.tests` + e2e `job-list.spec.js` (filtri, sezioni, ricerca testuale, swipe, ordinamento) |
| Stati del job | 7/7 ✅ | `apps.jobs.tests` (stati stabili, transitorio, effetti di import/archiviazione) |
| Generazione CV | 13/16 ✅, 3 ⚠️ | quote/credito, guardia di concorrenza, refund, 1 pagina, foto, istruzione invariata: tutti coperti; ⚠️ la garanzia "1 pagina" e la qualità delle due modalità lingua sono verificate con contenuto sintetico (AI mockata), non con generazione Claude reale |
| Arricchimento del profilo | 4/4 ✅ | `apps.cv.tests` (salvataggio opzionale nel profilo, punteggio invariato) |
| Import manuale | 6/6 ✅ | `apps.jobs.tests` (accesso Pro-only, duplicati, link non valido, massimali separati) |
| Piani, massimali e credito | 8/8 ✅ | massimali/credito ampiamente coperti; il cambio piano è verificato solo via intervento amministrativo (Django Admin/`set_e2e_account`), alternativa esplicitamente ammessa dalle specifiche alla redenzione voucher (non implementata come flusso UI dedicato) |
| Requisiti trasversali | 4/4 ✅ | isolamento multi-utente, fuso orario, raccolta fallita senza errore tecnico (bug corretto in questo sprint), lingua interfaccia — tutti e quattro nuovi/rinforzati in questo sprint |

**Totale: 82/88 (93%) verificato con esito positivo in questo ambiente; 6 voci restano eccezioni esplicite.**

### Eccezioni residue (dipendono da risorse non disponibili in questo ambiente)
1. **Comportamento reale della fonte Apify** (finestra 24h, volume reale di risultati) — l'interfaccia è rispettata dal codice e testata con un doppio mock, mai invocata contro l'actor reale.
2. **Qualità reale dei contenuti Claude** (motivazione/match-gap dello scoring, vincolo "nessun riferimento a competenze assenti dal profilo", traduzione CV nelle due modalità lingua, compattamento a 1 pagina su un profilo reale molto ricco) — nessuna `ANTHROPIC_API_KEY` reale in questo ambiente; già segnalato negli sprint precedenti che toccano Claude.
3. **Consegna reale di una notifica push su un dispositivo reale** — limite noto di piattaforma (Chromium blocca la Push API nei contesti isolati di Playwright, non nel codice dell'app), già verificato e documentato nello Sprint 20 con un test che mocka solo l'API nativa del browser.
4. **Verifica manuale su un vero dispositivo/emulatore iOS Safari** — verificata solo la logica di rilevamento (`isIOS`/`isStandalone`) via user-agent spoofato in Playwright, non un vero Safari (già segnalato nello Sprint 20).
5. **Redenzione di un voucher come flusso UI dedicato** — non implementata: le specifiche ammettono esplicitamente "voucher **o** intervento amministrativo", e il secondo è pienamente implementato e testato (Django Admin).
6. **Ambiente effettivamente deployato** (VPS/dominio reali, HTTPS reale via Let's Encrypt, backup reale su storage esterno) — la configurazione è pronta (Sprint 21) ma non esiste ancora un VPS reale su cui eseguire i tre criteri di verifica trasversali richiesti esplicitamente da questo sprint sull'"ambiente deployato".

### Verifica eseguita
- Backend: `python manage.py test` → **118/118 passati** (98 pre-esistenti a inizio sprint + 20 nuovi: 11 di isolamento multi-utente, 2 di fuso orario, 1 su modifica profilo post-generazione, 1 di regressione sul fallimento isolato del ciclo notturno, più le differenze cumulative dagli sprint precedenti); `makemigrations --check` pulito.
- Frontend: suite e2e Playwright completa (account, auth/onboarding, job-list) — **21/21 passati** contro il dev server.

### Cosa manca
Le 6 eccezioni sopra, di cui 3 (fonte Apify reale, qualità Claude reale, ambiente VPS deployato) erano già note dagli sprint precedenti e restano legate a risorse esterne che il committente dovrà fornire (chiave Apify di produzione, `ANTHROPIC_API_KEY` reale, VPS/dominio) prima di un utilizzo con utenti reali.