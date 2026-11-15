# Sprint 78 — Redesign UI: profilo, impostazioni, ricerche

> **Periodo:** 2026-11-15 · **Branch:** `sprint-78-profilo` (da `sprint-77-raccolta`, mai su `main`) · **Copia di lavoro:** `/root/App-apply-dev` · **Stato:** implementato e verificato (e2e 49/49, screenshot a 360/390/1280 px); **merge e deploy non fatti** (in attesa dell'ok del committente).

## Input
Perimetro da `Docs/design/IMPLEMENTATION-PLAN.md` (sprint 78) e `SCREENS.md` §4. Mockup: `profilo`, `profile-exp`, `impostazioni`, `ricerche`, `ricerca-nuova`, `delete-search`, `search-deactivated`, `settings-limiti`, `settings-email`, `settings-email-sent`, `confirm-email`, `settings-fuso`, `settings-privacy`, `settings-password`, `settings-delete`, `notifications-ios`, `logout-confirm`. Regole: tutto ciò che si fa oggi in Profilo e Impostazioni resta possibile; nessuna API né backend; nessuna dipendenza; `ExperienceGroupEditor` e `RichBulletInput` senza cambi di props né di comportamento (solo stile); it/en; nessuna pagina più larga dello schermo; LegalFooter raggiungibile.

Prima di partire: produzione su `main` (f6584e5), container invariati da `docker-compose.prod.yml`, sito 200 (l'unica differenza nella copia di produzione è il blocco dell'anteprima nel Caddyfile, approvato nello Sprint 77). Numero: `git log` e `ls sprints/` arrivano entrambi a 77.

## Decisioni prese
- **Sottopagine con route proprie:** `/settings` (elenco), `/settings/searches`, `/settings/limits`, `/settings/privacy`; un indirizzo sconosciuto sotto `/settings/` torna all'elenco. Le altre voci (lingua del CV, email, fuso, lingua, password, istruzioni iOS) sono **pannelli** come nei mockup; raccolta automatica, foto nel CV e notifiche sono **interruttori** nell'elenco. "Notifiche" e "Lingua" non sono sottopagine perché nel mockup sono righe dell'elenco.
- **Notifiche:** due livelli come prima. L'interruttore è la preferenza dell'account; sotto la riga lo stato di questo dispositivo con "Attiva notifiche". Il mockup ha solo l'interruttore: unire i due livelli avrebbe cambiato il comportamento (spegnere la preferenza elimina le sottoscrizioni di **tutti** i dispositivi).
- **Difetto corretto (segnalato nello Sprint 73):** su iPhone fuori dalla schermata Home le istruzioni non comparivano mai. Il controllo "supporto push" veniva prima di "iOS non installata" e Safari, fuori dalla Home, non espone il push. Ora il controllo su iOS viene prima; in più c'è il pannello "Come fare" in tre passi (mockup `notifications-ios`).
- **Eliminare una ricerca chiede conferma** (mockup `delete-search`; prima era immediato).
- **Fuso orario:** pannello con l'elenco IANA completo e "Salva". Il mockup mostra sei fusi a scelta: tenuto l'elenco completo, come oggi, per non togliere scelte. Prima il cambio si applicava subito, ora con "Salva".
- **Profilo:** sezioni a fisarmonica con il contenuto **sempre montato** (nascosto se chiuso). I campi obbligatori (nome, cognome, città e paese) continuano a bloccare il salvataggio anche a sezione chiusa: la sezione si apre e il browser mostra il messaggio sul campo. Il nome sta in "Dati di contatto" (il mockup lo mostra solo in testata, senza dove modificarlo).
- **Esito del salvataggio del profilo:** banner in cima e avviso (toast), perché la barra "Salva modifiche" è in fondo.
- **Barre in basso:** "Salva modifiche" (Profilo) e "Nuova ricerca" (Ricerche) sostituiscono la barra di tab, come richiesto. I mockup `profilo` e `ricerche` disegnano entrambe le barre: vale la regola dello Sprint 75.
- **Piano e saldo:** in una card in cima all'elenco, con la nota che li gestisce l'amministratore. Nessun acquisto in app.
- **Editor condivisi:** il titolo interno (`legend`) è nascosto alla vista con il CSS del contenitore (resta per gli screen reader), perché il titolo è quello della fisarmonica. `ExperienceGroupEditor` ha **solo** un ritocco di stile: larghezze minime dei campi e padding della scheda (a 360 px il campo Ruolo si riduceva a poche lettere). Props e comportamento invariati, `RichBulletInput` non toccato.

## Confronto funzione per funzione (prima → dopo)
### Impostazioni
| Funzione (prima, `AccountPage`) | Dopo |
|---|---|
| Piano e saldo (sola lettura) | card in cima all'elenco |
| "I tuoi limiti di oggi" (tabella) | riga → `/settings/limits`: saldo e righe con barra di avanzamento (stessi dati, stessi `data-testid`) |
| Ricerche: elenco con tipo, keywords, città/paese, "In uso" | riga "Ricerche salvate · N attive" → `/settings/searches`: card con tipo, keywords, città/paese, interruttore "In uso" / "Disattivata" |
| Attiva / Disattiva (avviso sul Free con il nome della ricerca spenta) | interruttore; stesso avviso, con "OK" |
| Modifica in linea | "Modifica" → pannello con gli stessi campi |
| Elimina (immediato) | "Elimina" → finestra di conferma |
| Nuova ricerca (form in pagina, nasce disattivata) | "Nuova ricerca" nella barra in basso → pannello con tipo, keywords, città, paese e l'avviso "nasce disattivata" |
| Errori (limite di piano, server) | nel pannello o in cima alla pagina |
| Raccolta automatica (Sprint 77, nel pannello di raccolta) | anche nell'elenco: interruttore e orario, Free bloccata |
| Lingua interfaccia (select) | riga → pannello Italiano / English |
| Fuso orario (select con elenco IANA) | riga → pannello con lo stesso elenco e "Salva" |
| Lingua del CV (radio) | riga → pannello con le stesse due scelte |
| Foto nel CV (checkbox) | interruttore |
| Preferenza notifiche (checkbox) + "Attiva notifiche" + stati | interruttore + stato del dispositivo sotto la riga + pannello iOS |
| Email di accesso (form) | riga → pannello con lo stesso form; "link inviato" in un riquadro |
| Cambia password (form) | `/settings/privacy` → pannello |
| Documenti legali con versione e data | `/settings/privacy`, con in più la dichiarazione d'età |
| Esporta i miei dati | `/settings/privacy`, riga |
| Elimina account (finestra con password e spunta) | `/settings/privacy`, zona pericolosa; finestra `Modal` con gli stessi campi |
| Esci con conferma (Sprint 73) | in fondo all'elenco, invariato |

### Profilo
| Funzione (prima) | Dopo |
|---|---|
| Nome, cognome (obbligatori) | "Dati di contatto" (aperta) |
| Obiettivo (2000 caratteri, nota) | sezione "Obiettivo" |
| Sommario | "Sommario professionale" |
| Telefono, email del CV, città e paese (obbligatori), LinkedIn | "Dati di contatto" |
| Foto: anteprima, caricamento (salvato con "Salva"), "Rimuovi foto" con `window.confirm` | anteprima, "Carica", "Rimuovi foto" con finestra dell'app; nome del file scelto e nota del salvataggio |
| Esperienze per azienda, tecnologie, 15 × 400, avviso oltre 5 | "Esperienze · N aziende", stesso editor, avviso in un `Banner` |
| Istruzione, competenze, certificazioni, lingue | sezioni con conteggio, stessi editor |
| "Salva modifiche" (salvataggio sezione per sezione, id reali) | barra in basso, stessa logica; esito in cima e come avviso |

## Implementazione
- Nuovi: `pages/settings/SettingsPage.jsx`, `SearchesPage.jsx`, `LimitsPage.jsx`, `PrivacyPage.jsx`; `components/settings/SettingsList.jsx` (`SettingsGroup`, `SettingsRow`, `SettingsSubpageHeader`), `components/settings/NotificationsRow.jsx`; `lib/dataExport.js` (`useDataExport`).
- Rimosso: `pages/AccountPage.jsx`.
- Riscritti nella presentazione: `pages/ProfilePage.jsx`, `components/UsageLimitsCard.jsx`, `components/AccountDataActions.jsx` (eliminazione in `Modal`, export con l'hook), `components/EmailChangeForm.jsx`.
- Ritocchi: `ui/accordion.jsx` (`keepMounted`), `TimezoneSelect.jsx` (stile), `ExperienceGroupEditor.jsx` (solo stile).
- `App.jsx`: nuove route.
- Testi (it/en): nuovo gruppo `settings.*`; `profileExtras.masterSubtitle`, `contactSection`, `objectiveSection`, `companiesOne/Many`, `degreesOne/Many`, `photoUpload`, `photoRemoveTitle`, `saving`; `usage.reached`; `emailChange.newEmailPlaceholder`; `profile.title` diventa "Profilo".
- Backend / API: nessun cambio.

## E2e
| Spec / test | Prima | Dopo |
|---|---|---|
| `account` › crea, attiva, disattiva ed elimina una ricerca | form in pagina, pulsanti "Attiva"/"Disattiva"/"Elimina" | sottopagina dalla riga dell'elenco, pannello "Nuova ricerca" con l'avviso, interruttore "Usa la ricerca «…»", "Elimina" con finestra (Annulla, poi conferma), indietro del browser verso l'elenco |
| `account` › limite di piano | form in pagina | pannello in `/settings/searches`, messaggio nel pannello |
| `account` › impostazioni persistono | radio e checkbox in pagina | pannello "Lingua del CV generato", interruttore "Includi la foto nel CV" |
| `account` › titolo e limiti di oggi | riquadro in pagina | riga → `/settings/limits` |
| `account` › piano e saldo, iOS | — | invariati, passano |
| **nuovo** `account` › privacy e sicurezza | — | link diretto, documenti con versione, età minima, pannello password (password diverse), finestra di eliminazione (pulsante attivo solo con password e spunta), "‹ Impostazioni" |
| **nuovo** `account` › raccolta automatica nell'elenco | — | Free bloccata ("Solo piano Pro"); Pro: attivazione con 07:00 |
| **nuovo** `account` › profilo | — | fisarmoniche, campo obbligatorio vuoto in una sezione chiusa (la sezione si riapre), "Salva modifiche" → "Profilo aggiornato." e nome in testata |
| `push-subscription`, `auth-onboarding` | — | invariati, passano |

## Verifica
- `npm run build` OK; `npx oxlint src e2e` 0 errori, 9 warning (gli stessi).
- **E2e** sullo stack usa e getta: `account`, `push-subscription`, `auth-onboarding` 15/16 al primo giro. L'unico fallimento era un'asserzione da precisare: il link "Informativa privacy" compare anche nel piè di pagina legale, ora la ricerca è limitata al contenuto. Poi **suite completa 49/49** (46 + 3 nuovi).
- **Screenshot** (360/390/1280 px, utenti di prova Pro e Free con profilo, 6 esperienze, foto e due ricerche), 20 stati: elenco Impostazioni (Pro con raccolta automatica attiva e Free), pannelli lingua del CV, email, fuso, lingua, finestra Esci, ricerche, nuova e modifica ricerca, elimina ricerca, avviso "ricerca disattivata" del Free, limiti di oggi, privacy, pannello password, finestra di eliminazione account, profilo, profilo con esperienze aperte e avviso oltre 5, finestra "Rimuovi foto", pannello iOS (contesto con user agent iPhone).
- Nessuna pagina sborda (62 misure); nessun errore JavaScript. Nel controllo corretto lo stile dell'editor delle esperienze a 360 px.
- Backend non toccato: test backend non necessari. Stack di prova abbattuto.

## Cosa manca / note
- `confirm-email` (pagina di conferma della nuova email, `ConfirmEmailChangePage`) e le pagine di accesso: restyling nello sprint 79 (accesso, onboarding, legale).
- Il pannello del fuso non ha la ricerca per nome (elenco nativo del dispositivo, come prima).
- "Scopri il piano Pro" e la card del piano non portano a un acquisto: piano e credito restano gestiti dall'amministratore.
